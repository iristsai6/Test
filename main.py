# main.py
# 安裝依賴：pip install fastapi uvicorn sqlmodel python-dotenv httpx

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Field, Session, SQLModel, create_engine, select
from typing import Optional
from datetime import datetime
import httpx, os
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────
# Database
# ─────────────────────────────────────────
DATABASE_URL = "sqlite:///./bar.db"
engine = create_engine(DATABASE_URL, echo=False)

def get_session():
    with Session(engine) as s:
        yield s

# ─────────────────────────────────────────
# Models
# ─────────────────────────────────────────

class Cocktail(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    zh: str
    en: str
    base: str           # gin / whisky / rum / tequila / vodka / brandy
    base_label: str     # 琴酒 / 威士忌 …
    strength: str       # 輕微 / 中等 / 強烈
    flavor: str
    method: str
    glass: str
    ingredients: str    # JSON string, e.g. '["琴酒 60ml","苦艾酒 10ml"]'
    story: str
    who: str
    is_custom: bool = False
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class Bar(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    city: str = "高雄"
    address: str
    description: str
    bar_type: str       # cocktail / whisky / wine / craft_beer / speakeasy
    signature_drinks: str   # JSON string
    map_query: str
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class UserState(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(index=True)   # 簡易識別，可換成 auth token
    drink_count: int = 0
    checked_rules: str = "[]"          # JSON string, e.g. "[0,2,5]"
    custom_commands: str = "[]"        # JSON string
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

# ─────────────────────────────────────────
# Pydantic Schemas (request bodies)
# ─────────────────────────────────────────

class CocktailCreate(SQLModel):
    zh: str; en: str; base: str; base_label: str
    strength: str; flavor: str; method: str; glass: str
    ingredients: str; story: str; who: str; is_custom: bool = True

class BarCreate(SQLModel):
    name: str; city: str = "高雄"; address: str
    description: str; bar_type: str
    signature_drinks: str; map_query: str

class UserStateUpdate(SQLModel):
    drink_count: Optional[int] = None
    checked_rules: Optional[str] = None
    custom_commands: Optional[str] = None

class ClaudeRequest(SQLModel):
    question: str

# ─────────────────────────────────────────
# App
# ─────────────────────────────────────────

app = FastAPI(title="走跳酒Bar API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # 上線後改成你的 GitHub Pages URL
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)

# ─────────────────────────────────────────
# 🍸 Cocktails
# ─────────────────────────────────────────

@app.get("/cocktails")
def list_cocktails(base: Optional[str] = None, session: Session = Depends(get_session)):
    q = select(Cocktail)
    if base:
        q = q.where(Cocktail.base == base)
    return session.exec(q).all()

@app.post("/cocktails", status_code=201)
def create_cocktail(data: CocktailCreate, session: Session = Depends(get_session)):
    cocktail = Cocktail(**data.dict())
    session.add(cocktail)
    session.commit()
    session.refresh(cocktail)
    return cocktail

@app.delete("/cocktails/{id}")
def delete_cocktail(id: int, session: Session = Depends(get_session)):
    c = session.get(Cocktail, id)
    if not c:
        raise HTTPException(404, "Cocktail not found")
    session.delete(c)
    session.commit()
    return {"ok": True}

# ─────────────────────────────────────────
# 🏪 Bars
# ─────────────────────────────────────────

@app.get("/bars")
def list_bars(bar_type: Optional[str] = None, session: Session = Depends(get_session)):
    q = select(Bar)
    if bar_type:
        q = q.where(Bar.bar_type == bar_type)
    return session.exec(q).all()

@app.post("/bars", status_code=201)
def create_bar(data: BarCreate, session: Session = Depends(get_session)):
    bar = Bar(**data.dict())
    session.add(bar)
    session.commit()
    session.refresh(bar)
    return bar

@app.put("/bars/{id}")
def update_bar(id: int, data: BarCreate, session: Session = Depends(get_session)):
    bar = session.get(Bar, id)
    if not bar:
        raise HTTPException(404, "Bar not found")
    for k, v in data.dict().items():
        setattr(bar, k, v)
    bar.updated_at = datetime.utcnow().isoformat() if hasattr(bar, "updated_at") else None
    session.add(bar)
    session.commit()
    session.refresh(bar)
    return bar

@app.delete("/bars/{id}")
def delete_bar(id: int, session: Session = Depends(get_session)):
    bar = session.get(Bar, id)
    if not bar:
        raise HTTPException(404, "Bar not found")
    session.delete(bar)
    session.commit()
    return {"ok": True}

# ─────────────────────────────────────────
# 📊 User State
# ─────────────────────────────────────────

def get_or_create_user(user_id: str, session: Session) -> UserState:
    user = session.exec(select(UserState).where(UserState.user_id == user_id)).first()
    if not user:
        user = UserState(user_id=user_id)
        session.add(user)
        session.commit()
        session.refresh(user)
    return user

@app.get("/user/{user_id}")
def get_user_state(user_id: str, session: Session = Depends(get_session)):
    return get_or_create_user(user_id, session)

@app.patch("/user/{user_id}")
def update_user_state(user_id: str, data: UserStateUpdate, session: Session = Depends(get_session)):
    user = get_or_create_user(user_id, session)
    if data.drink_count is not None:
        user.drink_count = data.drink_count
    if data.checked_rules is not None:
        user.checked_rules = data.checked_rules
    if data.custom_commands is not None:
        user.custom_commands = data.custom_commands
    user.updated_at = datetime.utcnow().isoformat()
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

@app.post("/user/{user_id}/reset")
def reset_drink_count(user_id: str, session: Session = Depends(get_session)):
    user = get_or_create_user(user_id, session)
    user.drink_count = 0
    user.updated_at = datetime.utcnow().isoformat()
    session.add(user)
    session.commit()
    return {"ok": True, "drink_count": 0}

# ─────────────────────────────────────────
# 🤖 Claude Proxy（隱藏 API Key）
# ─────────────────────────────────────────

ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")

@app.post("/ask-claude")
async def ask_claude(req: ClaudeRequest):
    if not ANTHROPIC_KEY:
        raise HTTPException(500, "API key not configured")
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_KEY,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1000,
                "system": "你是走跳酒Bar的調酒師助手，語氣親切如朋友。根據用戶描述，從酒單中推薦1-2款並說明原因，用繁體中文，60-90字內。",
                "messages": [{"role": "user", "content": req.question}],
            },
        )
    if r.status_code != 200:
        raise HTTPException(r.status_code, r.text)
    data = r.json()
    return {"reply": "".join(c.get("text","") for c in data.get("content",[]))}

# ─────────────────────────────────────────
# Run: uvicorn main:app --reload --port 8000
# ─────────────────────────────────────────
