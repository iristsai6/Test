# main.py
# pip install fastapi uvicorn sqlmodel python-dotenv httpx

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Field, Session, SQLModel, create_engine, select
from typing import Optional
from datetime import datetime
import httpx, os, json
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = "sqlite:///./bar.db"
engine = create_engine(DATABASE_URL, echo=False)

def get_session():
    with Session(engine) as s:
        yield s

# ── Models ────────────────────────────────────────────────────────────────────

class Cocktail(SQLModel, table=True):
    id:           Optional[int] = Field(default=None, primary_key=True)
    zh:           str
    en:           str
    base:         str
    base_label:   str
    strength:     str
    flavor:       str
    method:       str
    glass:        str
    ingredients:  str   # JSON string
    story:        str
    who:          str
    is_custom:    bool = False
    created_at:   str  = Field(default_factory=lambda: datetime.utcnow().isoformat())

class Bar(SQLModel, table=True):
    id:               Optional[int] = Field(default=None, primary_key=True)
    name:             str
    city:             str = "高雄"
    address:          str
    description:      str
    bar_type:         str
    signature_drinks: str   # JSON string
    map_query:        str
    created_at:       str  = Field(default_factory=lambda: datetime.utcnow().isoformat())

class UserState(SQLModel, table=True):
    id:              Optional[int] = Field(default=None, primary_key=True)
    user_id:         str = Field(index=True)
    drink_count:     int = 0
    checked_rules:   str = "[]"
    custom_commands: str = "[]"
    updated_at:      str = Field(default_factory=lambda: datetime.utcnow().isoformat())

# ── Schemas ───────────────────────────────────────────────────────────────────

class CocktailCreate(SQLModel):
    zh: str; en: str; base: str; base_label: str
    strength: str; flavor: str; method: str; glass: str
    ingredients: str; story: str; who: str; is_custom: bool = True

class BarCreate(SQLModel):
    name: str; city: str = "高雄"; address: str
    description: str; bar_type: str
    signature_drinks: str; map_query: str

class UserStateUpdate(SQLModel):
    drink_count:     Optional[int] = None
    checked_rules:   Optional[str] = None
    custom_commands: Optional[str] = None

class ClaudeRequest(SQLModel):
    question: str

# ── Seed data ─────────────────────────────────────────────────────────────────

SEED_COCKTAILS = [
    {"zh":"馬丁尼","en":"Martini","base":"gin","base_label":"琴酒","strength":"強烈","flavor":"辛辣","method":"攪拌","glass":"馬丁尼杯","ingredients":"[\"琴酒 60ml\",\"辛口苦艾酒 10ml\"]","story":"不僅007愛喝，邱吉爾曾說：調馬丁尼時，只要對著法國方向鞠個躬就夠了。冷冽、乾淨且充滿力量。","who":"喜歡乾淨俐落、不要任何甜味的你"},
    {"zh":"尼格羅尼","en":"Negroni","base":"gin","base_label":"琴酒","strength":"強烈","flavor":"苦甜","method":"攪拌","glass":"古典杯","ingredients":"[\"琴酒 30ml\",\"金巴利 30ml\",\"紅苦艾酒 30ml\"]","story":"起源於佛羅倫斯，三等份的完美平衡。深紅色澤代表義大利式優雅，苦澀中藏著甘甜。","who":"想探索不甜調酒、喜歡義式風格的你"},
    {"zh":"琴蕾","en":"Gimlet","base":"gin","base_label":"琴酒","strength":"中等","flavor":"酸甜","method":"搖盪","glass":"馬丁尼杯","ingredients":"[\"琴酒 45ml\",\"萊姆汁 15ml\",\"糖漿 7.5ml\"]","story":"《漫長的告別》中的傳說調酒，最初是讓水手對抗壞血病的救命靈藥。","who":"愛清爽平衡感、想入門琴酒的你"},
    {"zh":"白色佳人","en":"White Lady","base":"gin","base_label":"琴酒","strength":"中等","flavor":"酸甜","method":"搖盪","glass":"馬丁尼杯","ingredients":"[\"琴酒 40ml\",\"橙酒 30ml\",\"檸檬汁 20ml\"]","story":"調酒界最優雅的月光，純白乾滑，橙酒與檸檬酸甜掩蓋了烈酒的鋒芒。","who":"初探琴酒又喜歡橙香的你"},
    {"zh":"臨別一語","en":"Last Word","base":"gin","base_label":"琴酒","strength":"強烈","flavor":"草本","method":"搖盪","glass":"馬丁尼杯","ingredients":"[\"琴酒 22.5ml\",\"綠夏翠絲 22.5ml\",\"黑櫻桃酒 22.5ml\",\"萊姆汁 22.5ml\"]","story":"禁酒令消失後在西雅圖復活的傳奇。草本感極重，繁複且銳利。","who":"調酒老手、愛挑戰複雜層次的你"},
    {"zh":"琴費斯","en":"Gin Fizz","base":"gin","base_label":"琴酒","strength":"輕微","flavor":"清爽","method":"搖盪","glass":"高球杯","ingredients":"[\"琴酒 45ml\",\"檸檬汁 30ml\",\"糖漿 15ml\",\"蘇打水適量\"]","story":"氣泡感在舌尖炸裂就像夏日及時雨，是最經典的消暑救贖。","who":"剛接觸調酒、喜歡氣泡感的你"},
    {"zh":"古典","en":"Old Fashioned","base":"whisky","base_label":"威士忌","strength":"強烈","flavor":"苦甜","method":"攪拌","glass":"古典杯","ingredients":"[\"波本威士忌 45ml\",\"方糖 1顆\",\"安格斯特拉苦精 2dash\",\"柳橙皮\"]","story":"雞尾酒的始祖。方糖慢融的過程中感受酒的層次演化，是用來「品」而不是喝乾的酒。","who":"老靈魂、想認識威士忌的你"},
    {"zh":"威士忌酸酒","en":"Whiskey Sour","base":"whisky","base_label":"威士忌","strength":"中等","flavor":"酸甜","method":"搖盪","glass":"古典杯","ingredients":"[\"威士忌 45ml\",\"檸檬汁 30ml\",\"糖漿 15ml\",\"蛋白 1顆\"]","story":"蛋白讓整杯酒穿上絲絨外衣，在酸甜之間尋找威士忌木質調，滑順到讓你忘記是高濃度烈酒。","who":"有些基礎、想探索威士忌柔軟面的你"},
    {"zh":"曼哈頓","en":"Manhattan","base":"whisky","base_label":"威士忌","strength":"強烈","flavor":"濃郁","method":"攪拌","glass":"馬丁尼杯","ingredients":"[\"裸麥威士忌 60ml\",\"紅苦艾酒 30ml\",\"安格斯特拉苦精 2dash\"]","story":"雞尾酒之后。深邃濃郁帶著草本氣息，象徵19世紀紐約上流社會的繁華與迷人。","who":"追求深邃複雜、不妥協的老靈魂"},
    {"zh":"盤尼西林","en":"Penicillin","base":"whisky","base_label":"威士忌","strength":"中等","flavor":"煙燻","method":"搖盪","glass":"古典杯","ingredients":"[\"調和蘇格蘭威士忌 45ml\",\"艾雷島威士忌 7.5ml（漂浮）\",\"檸檬汁 22.5ml\",\"蜂蜜薑汁糖漿 22.5ml\"]","story":"煙燻泥煤與薑汁辛辣在喉嚨撞擊，像寒冬裡的一把火，專治靈魂的疲憊。","who":"威士忌老手、愛複雜煙燻層次的你"},
    {"zh":"薄荷茱莉普","en":"Mint Julep","base":"whisky","base_label":"威士忌","strength":"中等","flavor":"清爽","method":"直調","glass":"銀杯","ingredients":"[\"波本威士忌 60ml\",\"薄荷葉 8-10片\",\"糖漿 15ml\",\"碎冰\"]","story":"肯塔基賽馬會的官方飲品。大量碎冰在銀杯上結起白霜，薄荷與波本達到野性的契合。","who":"喜歡清爽又有酒感、愛戶外氛圍的你"},
    {"zh":"莫希托","en":"Mojito","base":"rum","base_label":"蘭姆酒","strength":"輕微","flavor":"清爽","method":"直調","glass":"高球杯","ingredients":"[\"白蘭姆酒 45ml\",\"萊姆汁 30ml\",\"糖漿 15ml\",\"薄荷葉 8片\",\"蘇打水適量\"]","story":"海明威在哈瓦那留下的經典。薄荷要拍碎而不切斷，讓精油滲入碳酸，每一口都是古巴的海風。","who":"不常喝酒的新手、喜歡清爽的你"},
    {"zh":"黛綺莉","en":"Daiquiri","base":"rum","base_label":"蘭姆酒","strength":"中等","flavor":"酸甜","method":"搖盪","glass":"雞尾酒杯","ingredients":"[\"白蘭姆酒 60ml\",\"萊姆汁 22.5ml\",\"糖漿 15ml\"]","story":"調酒師的試金石，簡單到殘酷，卻能體現蘭姆酒最原始的甜美。","who":"想感受酒本身風味、講究比例的你"},
    {"zh":"邁泰","en":"Mai Tai","base":"rum","base_label":"蘭姆酒","strength":"強烈","flavor":"果香","method":"搖盪","glass":"Tiki杯","ingredients":"[\"深色蘭姆酒 30ml\",\"淺色蘭姆酒 30ml\",\"橙酒 15ml\",\"杏仁糖漿 15ml\",\"萊姆汁 30ml\"]","story":"大溪地語意為「極致的美味」，果香濃郁到讓你忘記裡面藏著兩份烈酒，小心後勁。","who":"派對主角、享受熱帶氛圍的你"},
    {"zh":"椰林飄香","en":"Piña Colada","base":"rum","base_label":"蘭姆酒","strength":"輕微","flavor":"甜美","method":"搖盪","glass":"颶風杯","ingredients":"[\"蘭姆酒 45ml\",\"鳳梨汁 90ml\",\"椰奶 30ml\"]","story":"波多黎各的國酒，椰奶與鳳梨融合出綿密口感，適合在陽光直射的午後慵懶度過。","who":"喜歡甜飲、想要海灘度假感的你"},
    {"zh":"瑪格麗特","en":"Margarita","base":"tequila","base_label":"龍舌蘭","strength":"中等","flavor":"酸鹹","method":"搖盪","glass":"瑪格麗特杯","ingredients":"[\"龍舌蘭 45ml\",\"橙酒 15ml\",\"萊姆汁 30ml\",\"杯緣鹽\"]","story":"杯緣鹽圈完美引發龍舌蘭的甜味，每一口都帶著淚水的鹹與回憶的酸甜。","who":"愛派對、不怕酸的人"},
    {"zh":"龍舌蘭日出","en":"Tequila Sunrise","base":"tequila","base_label":"龍舌蘭","strength":"輕微","flavor":"果香","method":"直調","glass":"高球杯","ingredients":"[\"龍舌蘭 45ml\",\"柳橙汁 90ml\",\"紅石榴糖漿 15ml\"]","story":"紅石榴緩緩沉入杯底形成美麗漸層，象徵著墨西哥高原上初升的暖陽。","who":"喜歡視覺好看、入口不刺激的你"},
    {"zh":"帕羅瑪","en":"Paloma","base":"tequila","base_label":"龍舌蘭","strength":"輕微","flavor":"柚香","method":"直調","glass":"高球杯","ingredients":"[\"龍舌蘭 45ml\",\"葡萄柚蘇打 120ml\",\"萊姆汁 15ml\",\"鹽\"]","story":"在墨西哥人氣遠超瑪格麗特，葡萄柚微苦讓龍舌蘭植物氣息顯得溫柔平易。","who":"龍舌蘭入門者、喜歡微苦清爽的你"},
    {"zh":"莫斯科騾子","en":"Moscow Mule","base":"vodka","base_label":"伏特加","strength":"輕微","flavor":"薑汁","method":"直調","glass":"銅杯","ingredients":"[\"伏特加 45ml\",\"薑汁啤酒 120ml\",\"萊姆汁 15ml\"]","story":"為了促銷滯銷銅杯而生，卻成了永恆的經典。清涼解暑，薑汁帶來獨特的辛爽感。","who":"不常喝酒、喜歡清爽口感的你"},
    {"zh":"咖啡馬丁尼","en":"Espresso Martini","base":"vodka","base_label":"伏特加","strength":"中等","flavor":"濃郁","method":"搖盪","glass":"馬丁尼杯","ingredients":"[\"伏特加 45ml\",\"濃縮咖啡 30ml\",\"咖啡酒 15ml\",\"糖漿 7.5ml\"]","story":"一位名模要求：「給我來杯能吵醒我、然後弄醉我的酒」，這杯帶著咖啡油脂的馬丁尼就此誕生。","who":"愛咖啡、深夜不想睡又想微醺的你"},
    {"zh":"長島冰茶","en":"Long Island Iced Tea","base":"vodka","base_label":"伏特加","strength":"強烈","flavor":"酸甜","method":"直調","glass":"高球杯","ingredients":"[\"伏特加 15ml\",\"琴酒 15ml\",\"蘭姆酒 15ml\",\"龍舌蘭 15ml\",\"橙酒 15ml\",\"可樂適量\",\"檸檬汁 30ml\"]","story":"它沒有茶，卻有著紅茶的視覺。五種烈酒堆疊出的後勁極強，是派對初學者最致命的溫柔鄉。","who":"今晚想徹底放鬆的派對動物"},
    {"zh":"柯夢波丹","en":"Cosmopolitan","base":"vodka","base_label":"伏特加","strength":"中等","flavor":"果香","method":"搖盪","glass":"馬丁尼杯","ingredients":"[\"伏特加 45ml\",\"橙酒 15ml\",\"蔓越莓汁 30ml\",\"萊姆汁 15ml\"]","story":"因《慾望城市》成為都會女性的標配，充滿現代大都市的精緻、活力與自信。","who":"喜歡粉紅系、都會感的你"},
    {"zh":"側車","en":"Sidecar","base":"brandy","base_label":"白蘭地","strength":"中等","flavor":"酸甜","method":"搖盪","glass":"馬丁尼杯","ingredients":"[\"干邑白蘭地 50ml\",\"橙酒 20ml\",\"檸檬汁 20ml\",\"杯緣糖\"]","story":"白蘭地調酒的「完美比例」，名字來源於一戰時期常用的側掛摩托車，古典優雅。","who":"初探白蘭地、喜歡優雅酸甜感的你"},
    {"zh":"亞歷山大","en":"Alexander","base":"brandy","base_label":"白蘭地","strength":"中等","flavor":"奶香","method":"搖盪","glass":"馬丁尼杯","ingredients":"[\"白蘭地 30ml\",\"棕色可可酒 30ml\",\"鮮奶油 30ml\"]","story":"1922年為瑪麗公主婚禮設計，像一杯帶酒精的可可奶昔，絲滑細緻，是成人的深夜甜點。","who":"喜歡甜、奶香、不想感受酒感的你"},
    {"zh":"薩澤拉克","en":"Sazerac","base":"brandy","base_label":"白蘭地","strength":"強烈","flavor":"草本","method":"攪拌","glass":"古典杯","ingredients":"[\"白蘭地 45ml\",\"艾碧斯（洗杯用）\",\"佩喬苦精 2dash\",\"方糖 1顆\"]","story":"誕生於紐奧良，被公認為世界第一杯雞尾酒。杯壁那抹艾碧斯香氣是這杯酒高貴神祕的靈魂。","who":"調酒歷史愛好者、愛挑戰強烈草本的你"},
    {"zh":"馬蹄","en":"Horse's Neck","base":"brandy","base_label":"白蘭地","strength":"輕微","flavor":"清爽","method":"直調","glass":"高球杯","ingredients":"[\"白蘭地 45ml\",\"薑汁汽水 120ml\",\"檸檬皮（長條捲旋）\"]","story":"亮點在那條誇張捲旋而下的檸檬皮，遠看就像馬脖子。白蘭地最平易近人的喝法。","who":"白蘭地新手、喜歡清爽長飲的你"},
]

SEED_BARS = [
    {"name":"Bar Home","city":"高雄","address":"高雄市苓雅區四維三路 30 號","description":"高雄精品調酒先驅，主打手工冰塊與季節性酒單。調酒師會根據你的喜好現場設計酒款，空間低調精緻，適合深度聊天或小酌。","bar_type":"cocktail","signature_drinks":"[\"季節特調\",\"Negroni Variations\",\"Smoke Cocktail\"]","map_query":"Bar Home 高雄"},
    {"name":"Fourplay Cuisine & Lounge","city":"高雄","address":"高雄市前金區中正四路 207 號","description":"兼具餐廳與酒吧，夜晚搖身一變為高雄最具格調的調酒空間，調酒師背景豐富，酒單充滿驚喜。","bar_type":"cocktail","signature_drinks":"[\"Espresso Martini\",\"Gin Sour\",\"Barrel-aged Cocktail\"]","map_query":"Fourplay 高雄"},
    {"name":"The Dogfish","city":"高雄","address":"高雄市鹽埕區大義街 2 號 B1","description":"藏身鹽埕老屋地下室，復古工業風，以日式精準工藝調製西式調酒，每杯都有故事。","bar_type":"cocktail","signature_drinks":"[\"Old Fashioned\",\"Gimlet\",\"House Special\"]","map_query":"The Dogfish 高雄鹽埕"},
    {"name":"Zinga Whisky Bar","city":"高雄","address":"高雄市苓雅區福德三路 186 號","description":"高雄藏瓶數量數一數二的威士忌吧，從單一麥芽到調和威士忌應有盡有。侍酒師熱愛分享，適合純飲入門。","bar_type":"whisky","signature_drinks":"[\"Yamazaki 12yr\",\"Glenfarclas 21yr\",\"Bourbon Flight\"]","map_query":"Zinga Whisky Bar 高雄"},
    {"name":"W Bar","city":"高雄","address":"高雄市三民區九如一路 540 號","description":"老屋改建，木質調裝潢充滿溫度，收藏百款以上威士忌，定期舉辦品飲會，氛圍沉穩適合獨飲。","bar_type":"whisky","signature_drinks":"[\"Islay Single Malt\",\"Japanese Whisky\",\"Rob Roy\"]","map_query":"W Bar 高雄三民"},
    {"name":"L'Appart Wine Bar","city":"高雄","address":"高雄市鹽埕區大成街 53 號","description":"主打自然酒與橘酒，不定期引進小農酒莊作品，搭配精選起司盤與冷盤，是高雄最有法式情懷的空間。","bar_type":"wine","signature_drinks":"[\"Orange Wine\",\"Pét-Nat\",\"Beaujolais\"]","map_query":"L'Appart Wine Bar 高雄"},
    {"name":"醴芒 Wine & Dine","city":"高雄","address":"高雄市前金區（近中正四路）","description":"新世界舊世界皆有收藏，侍酒師根據餐點與預算推薦，適合商務聚餐或浪漫約會。","bar_type":"wine","signature_drinks":"[\"Burgundy Pinot Noir\",\"Chilean Sauvignon Blanc\",\"Champagne\"]","map_query":"醴芒 Wine 高雄"},
    {"name":"啤酒頭釀造 Beer Head","city":"高雄","address":"高雄市鹽埕區七賢三路 33 號","description":"台灣在地精釀品牌，以二十四節氣為靈感設計酒款，每季限量，在地食材入酒是一大亮點。","bar_type":"craft_beer","signature_drinks":"[\"節氣 IPA\",\"芒果小麥\",\"黑麥司陶特\"]","map_query":"啤酒頭 高雄鹽埕"},
    {"name":"The 9th Tap","city":"高雄","address":"高雄市苓雅區自強三路一帶","description":"多品牌精釀生啤輪換，隨時有 10 款以上選擇，氣氛熱鬧適合群體聚會，配餐炸物也很出色。","bar_type":"craft_beer","signature_drinks":"[\"West Coast IPA\",\"Sour Ale\",\"Nitro Stout\"]","map_query":"The 9th Tap 高雄"},
    {"name":"無名所 Nowhere Bar","city":"高雄","address":"高雄市鹽埕區（入口資訊請 Google 查尋提示）","description":"入口藏在一間普通商店後方，完整復刻禁酒令年代的吧台與卡座。不接受 walk-in，需提前傳訊預約。","bar_type":"speakeasy","signature_drinks":"[\"Prohibition Cocktail\",\"Rye Manhattan\",\"Absinthe Drip\"]","map_query":"Nowhere Bar 高雄鹽埕"},
    {"name":"House No.9","city":"高雄","address":"高雄市新興區（細節請私訊 IG 查詢）","description":"藏身公寓三樓，無招牌，以會員制運作。調酒師曾赴東京修習，酒單高度客製化，每位來客都獲得獨一無二的體驗。","bar_type":"speakeasy","signature_drinks":"[\"Bespoke Cocktail\",\"Aged Negroni\",\"Milk Punch\"]","map_query":"House No.9 高雄新興"},
    {"name": "谷山映像館","city": "高雄",  "address": "804高雄市鼓山區延平里濱海一路58號","description": "獨立模仿的沖洗暗房相當有趣。與當地歷史與文化結合讓酒館不只是酒館，更是在繁雜社會的避風港","bar_type": "cocktail",  "signature_drinks": "[\"翠嶺泡泉\", \"潮聲未歇\", \"鼓山周杰倫\"]",  "map_query": "谷山映像館"},
    {"name": "Gallery 20.5","city": "高雄",  "address": "802高雄市苓雅區中正二路56巷33弄20號1樓","description": "隱身於畫廊之中的故事，沿著通往1920的時光隧道，專屬禁酒令時期的獨特浪漫，仔細尋找秘密通道，我在那等你","bar_type": "Speakeasy","signature_drinks":"[\"金鹹桃\", \"芭芒柳汽水 OMG Tonic\", \"文化中心4號出口\", \"松露薯條\"]","map_query": "Gallery 20.5"}
]

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="走跳酒Bar API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 上線後改成你的 GitHub Pages URL
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "歡迎來到走跳酒Bar API 伺服器！"}

@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)
    # Seed if empty
    with Session(engine) as s:
        if not s.exec(select(Cocktail)).first():
            for c in SEED_COCKTAILS:
                s.add(Cocktail(**c))
            s.commit()
        if not s.exec(select(Bar)).first():
            for b in SEED_BARS:
                s.add(Bar(**b))
            s.commit()

# ── Cocktail routes ───────────────────────────────────────────────────────────

@app.get("/cocktails")
def list_cocktails(base: Optional[str] = None, session: Session = Depends(get_session)):
    q = select(Cocktail)
    if base:
        q = q.where(Cocktail.base == base)
    return session.exec(q).all()

@app.post("/cocktails", status_code=201)
def create_cocktail(data: CocktailCreate, session: Session = Depends(get_session)):
    c = Cocktail(**data.dict())
    session.add(c); session.commit(); session.refresh(c)
    return c

@app.put("/cocktails/{id}")
def update_cocktail(id: int, data: CocktailCreate, session: Session = Depends(get_session)):
    c = session.get(Cocktail, id)
    if not c: raise HTTPException(404, "Not found")
    for k, v in data.dict().items(): setattr(c, k, v)
    session.add(c); session.commit(); session.refresh(c)
    return c

@app.delete("/cocktails/{id}")
def delete_cocktail(id: int, session: Session = Depends(get_session)):
    c = session.get(Cocktail, id)
    if not c: raise HTTPException(404, "Not found")
    session.delete(c); session.commit()
    return {"ok": True}

# ── Bar routes ────────────────────────────────────────────────────────────────

@app.get("/bars")
def list_bars(bar_type: Optional[str] = None, session: Session = Depends(get_session)):
    q = select(Bar)
    if bar_type:
        q = q.where(Bar.bar_type == bar_type)
    return session.exec(q).all()

@app.post("/bars", status_code=201)
def create_bar(data: BarCreate, session: Session = Depends(get_session)):
    b = Bar(**data.dict())
    session.add(b); session.commit(); session.refresh(b)
    return b

@app.put("/bars/{id}")
def update_bar(id: int, data: BarCreate, session: Session = Depends(get_session)):
    b = session.get(Bar, id)
    if not b: raise HTTPException(404, "Not found")
    for k, v in data.dict().items(): setattr(b, k, v)
    session.add(b); session.commit(); session.refresh(b)
    return b

@app.delete("/bars/{id}")
def delete_bar(id: int, session: Session = Depends(get_session)):
    b = session.get(Bar, id)
    if not b: raise HTTPException(404, "Not found")
    session.delete(b); session.commit()
    return {"ok": True}

# ── User state routes ─────────────────────────────────────────────────────────

def _get_or_create(user_id: str, session: Session) -> UserState:
    u = session.exec(select(UserState).where(UserState.user_id == user_id)).first()
    if not u:
        u = UserState(user_id=user_id)
        session.add(u); session.commit(); session.refresh(u)
    return u

@app.get("/user/{user_id}")
def get_user(user_id: str, session: Session = Depends(get_session)):
    return _get_or_create(user_id, session)

@app.patch("/user/{user_id}")
def update_user(user_id: str, data: UserStateUpdate, session: Session = Depends(get_session)):
    u = _get_or_create(user_id, session)
    if data.drink_count     is not None: u.drink_count     = data.drink_count
    if data.checked_rules   is not None: u.checked_rules   = data.checked_rules
    if data.custom_commands is not None: u.custom_commands = data.custom_commands
    u.updated_at = datetime.utcnow().isoformat()
    session.add(u); session.commit(); session.refresh(u)
    return u

@app.post("/user/{user_id}/reset")
def reset_user(user_id: str, session: Session = Depends(get_session)):
    u = _get_or_create(user_id, session)
    u.drink_count = 0
    u.updated_at = datetime.utcnow().isoformat()
    session.add(u); session.commit()
    return {"ok": True}

# ── Claude proxy ──────────────────────────────────────────────────────────────

ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")

@app.post("/ask-claude")
async def ask_claude(req: ClaudeRequest):
    if not ANTHROPIC_KEY:
        raise HTTPException(500, "ANTHROPIC_API_KEY not set in .env")
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
                "system": "你是走跳酒Bar的調酒師助手，語氣親切如朋友。根據用戶描述推薦1-2款調酒並說明原因，用繁體中文，60-90字內。",
                "messages": [{"role": "user", "content": req.question}],
            },
        )
    if r.status_code != 200:
        raise HTTPException(r.status_code, r.text)
    data = r.json()
    return {"reply": "".join(c.get("text", "") for c in data.get("content", []))}

# uvicorn main:app --reload --port 8000
