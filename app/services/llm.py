# AI modellari bilan ishlash qatlami.
# Provayderlar navbati: Anthropic -> Gemini -> OpenAI. Biri ishlamasa
# (kredit/limit/xato) keyingisiga o'tiladi. Tartib narxga qarab tanlangan:
# avval asosiy, so'ng Gemini'ning BEPUL kvotasi, u tugagach pulli OpenAI.
# Uchalasi ham bir xil tuzilgan JSON javob qaytaradi, shuning uchun qolgan
# kod provayderni sezmaydi.
# Kirish — oddiy matn (savol yoki hujjat matni), manbasidan qat'i nazar.
import json
from typing import List, Optional

import anthropic
import httpx

from ..config import (
    ANTHROPIC_API_KEY,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    MODEL,
    OPENAI_API_KEY,
    OPENAI_MODEL,
)

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

# Javob strukturasini kafolatlash uchun majburiy tool chaqiruvi ishlatiladi:
# model modda matnini QAYTA YOZMAYDI — faqat tegishli moddalar ID'sini tanlaydi,
# tavsiya yozadi va murojaat mavzusini belgilaydi. Asl matn bazadan olinadi.
# Bu ro'yxat data/organlar.json dagi "mavzu" qiymatlari bilan bir xil bo'lishi shart —
# model tanlagan mavzu bo'yicha kontakt bazadan olinadi.
MUROJAAT_MAVZULARI = [
    "mehnat",
    "iste'molchi",
    "oila",
    "oila-sud",
    "fuqarolik",
    "ma'muriy",
    "jinoyat",
    "uy-joy",
    "soliq",
    "yer",
    "yol-harakati",
    "umumiy",
]

# Tavsiya hajmi — javob vaqtini belgilaydigan ASOSIY sozlama.
# Vaqtning deyarli hammasi model matn yozishiga ketadi (~30 token/sekund),
# shuning uchun uzunlik bilan vaqt deyarli chiziqli bog'langan. O'lchangan
# natijalar (claude-sonnet-4-5, 5-6 savol bo'yicha o'rtacha):
#
#   qadam × belgi   tavsiya uzunligi   javob vaqti
#   3 × 150         ~380 belgi          ~8.4s     (qisqa, lekin tez)
#   4 × 150         ~630 belgi         ~11.3s     <-- hozirgi tanlov
#   4 × 220         ~980 belgi         ~17.1s     (to'liq, lekin sekin)
#
# Tezlik kerak bo'lsa QADAM_SONI ni 3 ga tushiring; batafsilroq tavsiya kerak
# bo'lsa QADAM_BELGI ni oshiring. Takrorlangan savollar keshdan qaytadi
# (services/kesh.py), shuning uchun bu sozlama faqat yangi savollarga ta'sir qiladi.
TAVSIYA_QADAM_SONI = 4
TAVSIYA_QADAM_BELGI = 150

# Batafsil rejim (Telegram bot). Botda ekran cheklovi yo'q va foydalanuvchi
# javobni o'qishga ko'proq tayyor: qadamlar ko'proq va uzunroq bo'ladi hamda
# vaziyatning umumiy xulosasi qo'shiladi. Buning evaziga javob ~5 soniya
# sekinlashadi, shuning uchun saytda yoqilmagan.
BATAFSIL_QADAM_SONI = 6
BATAFSIL_QADAM_BELGI = 260
XULOSA_BELGI = 450


def _tavsiya_tavsifi(qadam_soni: int, qadam_belgi: int) -> str:
    return (
        f"{qadam_soni - 1}-{qadam_soni} qadam, muhimlik tartibida. "
        f"HAR BIRI BITTA JUMLA, {qadam_belgi} BELGIDAN KAM — bu qat'iy "
        "chegara, undan oshma. Jumlaga eng foydali tafsilotni sig'dir: "
        "QAYERGA murojaat qilish, QANDAY hujjat kerak yoki QANCHA muddat borligini "
        "ayt — odamga aynan shular kerak, umumiy gap emas. "
        "Modda matnini takrorlama (u foydalanuvchiga alohida ko'rsatiladi), "
        "savolni takrorlama, kirish so'zi va umumiy xulosa yozma — har bir jumla "
        "yangi ma'lumot bersin. Faqat oddiy matn va **qalin**; "
        "sarlavha (#), ro'yxat belgisi (-, *) va jadval ishlatma."
    )


_XULOSA_TAVSIFI = (
    "Vaziyatning qisqa umumiy xulosasi: qonun bo'yicha foydalanuvchining ahvoli "
    "qanday va haqlimi yoki yo'qmi — 2-3 jumla, "
    f"{XULOSA_BELGI} belgidan kam. Bu qadamlar ro'yxati EMAS, balki odam birinchi "
    "bo'lib o'qiydigan javob: 'Sizning holatingizda qonun ... deydi, ya'ni siz ...'. "
    "Modda matnini ko'chirma va raqamlarni qayta sanama."
)


def _javob_tool(batafsil: bool = False) -> dict:
    qadam_soni = BATAFSIL_QADAM_SONI if batafsil else TAVSIYA_QADAM_SONI
    qadam_belgi = BATAFSIL_QADAM_BELGI if batafsil else TAVSIYA_QADAM_BELGI
    xossalar = {
        "javob_topildi": {
            "type": "boolean",
            "description": "Berilgan moddalar orasida savolga tegishlisi bormi",
        },
        "tegishli_modda_idlari": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Savolga bevosita tegishli moddalarning ID ro'yxati (muhimlik tartibida, ko'pi bilan 3 ta)",
        },
        # Ro'yxat ataylab tanlangan: erkin matnga qo'yilgan belgi chegarasini
        # model e'tiborsiz qoldiradi (900+ belgi yozadi), ro'yxat esa uzunlikni
        # ancha ishonchli ushlab turadi.
        "tavsiya": {
            "type": "array",
            "items": {"type": "string", "maxLength": qadam_belgi},
            "maxItems": qadam_soni,
            "description": _tavsiya_tavsifi(qadam_soni, qadam_belgi),
        },
        "murojaat_mavzusi": {
            "type": "string",
            "enum": MUROJAAT_MAVZULARI,
            "description": "Qaysi davlat organiga murojaat qilish kerakligini belgilovchi mavzu",
        },
    }
    kerakli = ["javob_topildi", "tegishli_modda_idlari", "tavsiya", "murojaat_mavzusi"]
    if batafsil:
        xossalar["xulosa"] = {
            "type": "string",
            "maxLength": XULOSA_BELGI,
            "description": _XULOSA_TAVSIFI,
        }
        kerakli.append("xulosa")
    return {
        "name": "huquqiy_javob",
        "description": "Foydalanuvchi savoliga tuzilgan huquqiy javobni qaytarish",
        "input_schema": {"type": "object", "properties": xossalar, "required": kerakli},
    }


def _xatolar_matni(xatolar: List[Exception]) -> str:
    """Barcha provayder xatolarini bitta satrga yig'adi.

    Tartib muhim: hisob/kalit muammosi birinchi bo'lishi kerak. Anthropic
    krediti tugab, keyin Gemini limitga urilsa, faqat oxirgisi ko'rsatilsa
    foydalanuvchi "bir daqiqadan so'ng urinib ko'ring" deb kutaveradi —
    aslida hisob to'ldirilmaguncha hech narsa o'zgarmaydi.
    """
    matnlar = [str(e) for e in xatolar]
    ogir = [m for m in matnlar if "credit balance" in m.lower() or "billing" in m.lower()
            or "insufficient_quota" in m.lower()
            or "authentication" in m.lower() or "api key" in m.lower()]
    return " | ".join(ogir + [m for m in matnlar if m not in ogir])


# Har bir provayderning oxirgi HAQIQIY chaqiruvda qanday tugagani — /health uchun.
#
# Nega faol tekshiruv emas: /health'ni uptime monitoring har necha daqiqada
# so'raydi. Har so'rovda provayderga murojaat qilinsa, Gemini bepul kvotasi
# (kuniga 20 ta so'rov) bir soatda yonib bitadi va Anthropic tokeni bekorga
# sarflanadi. Shuning uchun holat foydalanuvchi so'rovlaridan yig'iladi.
#
# Buning narxi: qayta ishga tushgandan keyin birinchi savolgacha holat
# "noma'lum" bo'lib turadi. Ayirboshlash ongli — nosozlik birinchi savoldayoq
# ko'rinadi, monitoring esa kvotani yemaydi.
_holat: dict = {}


def _xato_sababi(e: Exception) -> str:
    """Provayder xatosini qisqa sababga aylantiradi (foydalanuvchi matni emas, diagnostika)."""
    s = str(e).lower()
    # OpenAI hisobi tugaganini 429 bilan qaytaradi va matnida "quota" bor —
    # limitdan OLDIN tekshirilmasa "bir daqiqadan so'ng urinib ko'ring" degan
    # chalg'ituvchi xabar chiqadi, aslida kutish hech narsani o'zgartirmaydi.
    if "credit balance" in s or "billing" in s or "insufficient_quota" in s:
        return "hisob"
    if "authentication" in s or "invalid x-api-key" in s or "api key" in s or "401" in s:
        return "kalit"
    if "quota" in s or "rate limit" in s or "resource_exhausted" in s or "429" in s:
        return "limit"
    # Model nomi yopilgani takrorlanuvchi tuzoq: Google aniq versiyalarni
    # yangi kalitlar uchun to'sadi ("no longer available to new users").
    if "not found" in s or "404" in s:
        return "model"
    if "overloaded" in s or "529" in s:
        return "band"
    # Kesilgan JSON: javob token chegarasida uzilgan yoki bo'sh kelgan.
    if "uzildi" in s or "unterminated" in s or "bo'sh javob" in s:
        return "uzildi"
    return "xato"


def _urin(provayder: str, ish, xatolar: List[Exception]):
    """Provayderni chaqiradi va natijasini holatga yozadi.

    Xato bo'lsa None qaytaradi — chaqiruvchi keyingi provayderga o'tadi.
    """
    try:
        natija = ish()
    except Exception as e:
        _holat[provayder] = _xato_sababi(e)
        xatolar.append(e)
        return None
    _holat[provayder] = "ishlayapti"
    return natija


def provayderlar_holati() -> dict:
    """Provayderlar holati va model nomlari — /health uchun.

    Model nomi sir emas, lekin diagnostikada hal qiluvchi: "model" sababi
    aynan qaysi nom yopilganini shu yerda ko'rsatadi.
    """
    return {
        "anthropic": {
            "holat": _holat.get("anthropic", "noma'lum" if _client else "sozlanmagan"),
            "model": MODEL,
        },
        "gemini": {
            "holat": _holat.get("gemini", "noma'lum" if GEMINI_API_KEY else "sozlanmagan"),
            "model": GEMINI_MODEL,
        },
        "openai": {
            "holat": _holat.get("openai", "noma'lum" if OPENAI_API_KEY else "sozlanmagan"),
            "model": OPENAI_MODEL,
        },
    }


# Gemini "thinking" modellari (gemini-3.x) o'ylash tokenlarini ham
# maxOutputTokens ichidan yeydi — o'lchandi: bir qatorlik savolga 988 ta
# o'ylash tokeni. Byudjet tor bo'lsa u o'ylashga sarflanadi va JSON yarmida
# uzilib qoladi; json.loads "Unterminated string" beradi.
#
# Bu nosozlik ayniqsa xavfli, chunki KO'RINMAYDI: Anthropic krediti tugagan
# paytda xatolar yig'ilganda "hisob" xabari birinchi ko'rsatiladi, foydalanuvchi
# esa zaxira ham o'lganini bilmaydi. Shuning uchun byudjet keng olingan —
# ishlatilmagan token uchun to'lanmaydi, faqat haqiqiy chiqish hisoblanadi.
_GEMINI_JAVOB_TOKEN = 8192
_GEMINI_SHARTNOMA_TOKEN = 12288


def _gemini_matni(javob: httpx.Response) -> str:
    """Gemini javobidan matnni ajratadi, uzilishni ochiq xatoga aylantiradi.

    Chegaraga urilganda `parts` umuman bo'lmasligi mumkin — tekshiruvsiz bu
    KeyError bo'lib chiqadi va sabab yo'qoladi.
    """
    nomzod = javob.json()["candidates"][0]
    if nomzod.get("finishReason") == "MAX_TOKENS":
        raise RuntimeError(
            "Gemini javobi maxOutputTokens chegarasida uzildi "
            "(o'ylash tokenlari byudjetni yeb qo'ygan)"
        )
    for qism in nomzod.get("content", {}).get("parts", []):
        # O'ylash qismlari (thought) javob emas — ular tashlab ketiladi.
        if qism.get("text") and not qism.get("thought"):
            return qism["text"]
    raise RuntimeError(f"Gemini bo'sh javob qaytardi (finishReason={nomzod.get('finishReason')})")


# ---------- OpenAI (uchinchi provayder) ----------

# Gemini'dagi "thinking" tuzog'i bu yerda yo'q (o'lchandi: reasoning_tokens=0),
# lekin chegara baribir qo'yiladi — uzilishni jimgina o'tkazib yubormaslik uchun
# finish_reason tekshiriladi.
_OPENAI_JAVOB_TOKEN = 4096
_OPENAI_SHARTNOMA_TOKEN = 8192


def _openai_sxemaga(sxema: dict) -> dict:
    """Anthropic uchun yozilgan JSON Schema'ni OpenAI strict rejimiga o'giradi.

    Uchinchi sxemani qo'lda yozish o'rniga mavjudi o'giriladi: Gemini nusxasi
    allaqachon ko'rsatdiki, qo'lda takrorlangan sxemalar vaqt o'tib
    bir-biridan uzoqlashadi — biriga qo'shilgan maydon ikkinchisida qolib ketadi.

    Strict rejim talabi: har obyektda additionalProperties=false va BARCHA
    xossalar required ichida. Uzunlik cheklovlari qo'llab-quvvatlanmaydi —
    ular tashlanadi, chegaralar description'da baribir aytilgan.
    """
    if not isinstance(sxema, dict):
        return sxema
    natija = {k: v for k, v in sxema.items() if k not in ("maxLength", "maxItems", "minItems")}
    if "properties" in natija:
        natija["properties"] = {k: _openai_sxemaga(v) for k, v in natija["properties"].items()}
        natija["required"] = list(natija["properties"])
        natija["additionalProperties"] = False
    if "items" in natija:
        natija["items"] = _openai_sxemaga(natija["items"])
    return natija


def _openai_chaqir(nom: str, sxema: dict, tizim: str, xabarlar: List[dict],
                   token: int, timeout: int) -> dict:
    """OpenAI Chat Completions, structured output bilan.

    `xabarlar` allaqachon OpenAI formatida ({"role", "content"}), shuning uchun
    Gemini'dagidek o'girish kerak emas.
    """
    javob = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
        json={
            "model": OPENAI_MODEL,
            "messages": [{"role": "system", "content": tizim}] + xabarlar,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": nom, "strict": True, "schema": sxema},
            },
            "max_completion_tokens": token,
        },
        timeout=timeout,
    )
    javob.raise_for_status()
    tanlov = javob.json()["choices"][0]
    if tanlov.get("finish_reason") == "length":
        raise RuntimeError("OpenAI javobi max_completion_tokens chegarasida uzildi")
    xabar = tanlov["message"]
    # Model rad etsa content bo'sh keladi — tekshirmasak json.loads tushunarsiz
    # xato beradi va sabab yo'qoladi.
    if xabar.get("refusal"):
        raise RuntimeError(f"OpenAI so'rovni rad etdi: {xabar['refusal']}")
    return json.loads(xabar["content"])


def _openai_javob(tizim: str, xabarlar: List[dict], batafsil: bool = False) -> dict:
    natija = _openai_chaqir(
        "huquqiy_javob",
        _openai_sxemaga(_javob_tool(batafsil)["input_schema"]),
        tizim + "\n\nJavobni faqat berilgan JSON sxema bo'yicha qaytar.",
        xabarlar,
        _OPENAI_JAVOB_TOKEN,
        60,
    )
    # Sxema kafolatiga qo'shimcha himoya (Gemini yo'lidagidek)
    if natija.get("murojaat_mavzusi") not in MUROJAAT_MAVZULARI:
        natija["murojaat_mavzusi"] = "umumiy"
    natija.setdefault("tegishli_modda_idlari", [])
    return natija


def _openai_shartnoma(tizim: str, xabarlar: List[dict]) -> dict:
    return _openai_chaqir(
        "shartnoma_tahlili",
        _openai_sxemaga(_shartnoma_tool()["input_schema"]),
        tizim,
        xabarlar,
        _OPENAI_SHARTNOMA_TOKEN,
        90,
    )


def _gemini_sxema(batafsil: bool = False) -> dict:
    """Gemini structured output uchun xuddi shu sxemaning OpenAPI ko'rinishi."""
    xossalar = {
        "javob_topildi": {"type": "BOOLEAN"},
        "tegishli_modda_idlari": {"type": "ARRAY", "items": {"type": "STRING"}},
        "tavsiya": {"type": "ARRAY", "items": {"type": "STRING"}},
        "murojaat_mavzusi": {"type": "STRING", "enum": MUROJAAT_MAVZULARI},
    }
    kerakli = ["javob_topildi", "tegishli_modda_idlari", "tavsiya", "murojaat_mavzusi"]
    if batafsil:
        xossalar["xulosa"] = {"type": "STRING"}
        kerakli.append("xulosa")
    return {"type": "OBJECT", "properties": xossalar, "required": kerakli}

_TIZIM_PROMPT = """Sen — HuquqiyAI, O'zbekiston fuqarolari uchun huquqiy yordamchisan.

QAT'IY QOIDALAR:
1. FAQAT quyida berilgan qonun moddalari asosida javob ber. O'z xotirangdagi boshqa qonunlarga tayanma.
2. Modda matnini QAYTA YOZMA va iqtibos KELTIRMA — modda matni foydalanuvchiga bazadan alohida ko'rsatiladi. Sen faqat tegishli moddalar ID'sini tanlaysan.
3. Aynan shu holatga atalgan modda bo'lmasa-yu, berilgan UMUMIY norma vaziyatga qonuniy
   ravishda tatbiq etilsa — o'sha moddani tanla va uni shu vaziyatga qanday qo'llash
   mumkinligini tushuntir. Masalan, ijara depozitini asossiz ushlab qolish — asossiz
   boyish to'g'risidagi moddaga kiradi. Huquqshunos shunday fikr yuritadi.
3a. javob_topildi=false ni FAQAT berilgan moddalarning hech biri, hatto umumiy norma
    sifatida ham, vaziyatga aloqador bo'lmaganda qo'y. Bunda savol bazadagi mavzularga
    kirmasligini ochiq ayt va umumiy yo'nalish ber (murojaat_mavzusi="umumiy").
    Moddani zo'rlab tortma — aloqasi bo'lmasa, yo'q deb ayt.
4. Tavsiya — bir necha amaliy qadam, eng muhimi birinchi. Har bir qadam o'zicha to'liq
   bo'lsin: nima qilish, qayerga murojaat qilish, qanday hujjat kerak, qancha muddat bor.
   Aniq muddat, hujjat nomi va organ nomini ayt — odamga aynan shu tafsilotlar kerak.
4a. Kirish so'zi, savolni takrorlash, modda matnini qayta aytish va umumiy xulosa YOZMA.
    Har bir jumla yangi ma'lumot bersin — bo'sh gap uchun joy yo'q.
4b. SHAKL: oddiy matn yoz. Ajratish kerak bo'lsa faqat **qalin** ishlat. Markdown sarlavha (#),
    ro'yxat belgisi (-, *) va jadval ISHLATMA — ular foydalanuvchiga xom matn bo'lib ko'rinadi.
5. Huquqiy maslahat o'rnini bosmasligni unutma — murakkab vaziyatlarda advokatga murojaat qilishni tavsiya qil.
6. TIL QOIDASI: tavsiyani foydalanuvchi savoli qaysi tilda va yozuvda bo'lsa, o'sha tilda yoz — o'zbek lotin, o'zbek kirill (ўзбек кирилл) yoki rus tilida. Aralash bo'lsa, savolning asosiy tilini tanla.

{rejim_korsatmasi}"""

# Batafsil rejimda (bot) qo'shimcha ko'rsatma. 4a qoidasi kuchida qoladi —
# xulosa TAVSIYA ichida emas, alohida maydonda yoziladi.
_BATAFSIL_KORSATMA = (
    "BATAFSIL REJIM. Foydalanuvchi javobni Telegram'da o'qiydi, ekran cheklovi yo'q.\n"
    "- Avval `xulosa` maydonini to'ldir: vaziyat qonun bo'yicha qanday baholanishi, "
    "foydalanuvchi haqlimi yoki yo'qmi, 2-3 jumlada, oddiy tilda. Odam birinchi bo'lib "
    "shuni o'qiydi.\n"
    "- Qadamlarni ko'proq va to'liqroq yoz: har birida aniq organ nomi, hujjat nomi yoki "
    "muddat bo'lsin. \"Sudga murojaat qiling\" — yetarli emas; qaysi sudga, qanday ariza "
    "bilan, qancha muddat ichida — shuni ayt.\n"
    "- Muddat o'tib ketgan yoki dalil kerak bo'lgan holatlarni ham eslatib o't."
)

_REJIMLAR = {
    "oddiy": (
        "REJIM: Oddiy odam. Sodda, tushunarli tilda yoz. Yuridik atamalarni "
        "ishlatsang, oddiy so'zlar bilan izohla. Qadam-baqadam nima qilish "
        "kerakligini ayt."
    ),
    "pro": (
        "REJIM: Advokat/Pro. Professional yuridik tilda yoz. Protsessual "
        "muddatlarni, tegishli hujjat turlarini (da'vo arizasi, shikoyat, "
        "ariza va h.k.), sudga taalluqlilik (podsudnost) masalalarini va "
        "protsessual tartibni aniq ko'rsat."
    ),
}


# ---------- Shartnoma tahlili ----------
#
# Bu alohida sxema: uch qismli javob (modda + tavsiya + organ) shartnomaga
# to'g'ri kelmaydi. Odam shartnomadan "qaysi bandi menga zarar keltiradi?"
# degan savolga javob kutadi, ya'ni natija BAND bo'yicha tuzilishi kerak.

SHARTNOMA_TURLARI = ["mehnat", "ijara", "kredit", "oldi-sotdi", "xizmat", "boshqa"]
XAVF_DARAJALARI = ["qizil", "sariq", "yashil"]

MAX_BAND_SONI = 12
BAND_MAZMUN_BELGI = 120
BAND_IZOH_BELGI = 220
SHARTNOMA_XULOSA_BELGI = 500

_XAVF_TAVSIFI = (
    "Bandning xavf darajasi: "
    "'qizil' — qonunga ZID, ya'ni band haqiqiy emas yoki majburiy normani buzadi; "
    "'sariq' — qonuniy, lekin foydalanuvchiga NOQULAY yoki xavf tug'diradi "
    "(masalan katta neustoyka, bir tomonlama bekor qilish huquqi); "
    "'yashil' — odatiy, e'tibor talab qiladigan muhim band. "
    "Faqat HAQIQATAN diqqatga sazovor bandlarni qaytar — oddiy, xavfsiz "
    "bandlarni ro'yxatga kiritma."
)


def _shartnoma_tool() -> dict:
    return {
        "name": "shartnoma_tahlili",
        "description": "Shartnomani band-band tahlil qilib qaytarish",
        "input_schema": {
            "type": "object",
            "properties": {
                "shartnoma_turi": {"type": "string", "enum": SHARTNOMA_TURLARI},
                "umumiy_mazmun": {
                    "type": "object",
                    "description": "Shartnomaning bir qarashda mazmuni",
                    "properties": {
                        "tomonlar": {"type": "string", "maxLength": 150,
                                     "description": "Kim kim bilan shartnoma tuzmoqda"},
                        "predmet": {"type": "string", "maxLength": 150,
                                    "description": "Shartnoma nima haqida"},
                        "summa": {"type": "string", "maxLength": 100,
                                  "description": "Asosiy pul miqdori; yo'q bo'lsa bo'sh satr"},
                        "muddat": {"type": "string", "maxLength": 100,
                                   "description": "Amal qilish muddati; yo'q bo'lsa bo'sh satr"},
                    },
                    "required": ["tomonlar", "predmet", "summa", "muddat"],
                },
                "bandlar_soni": {
                    "type": "integer",
                    "description": "Shartnomada jami nechta raqamlangan band bor",
                },
                "bandlar": {
                    "type": "array",
                    "maxItems": MAX_BAND_SONI,
                    "description": (
                        "Diqqat talab qiladigan bandlar, xavflisi birinchi. "
                        "Bandlar shartnomadagi tartib raqami bilan ko'rsatilsin."
                    ),
                    "items": {
                        "type": "object",
                        "properties": {
                            "band": {"type": "string", "maxLength": 12,
                                     "description": "Band raqami shartnomadagidek, masalan '4.3'"},
                            "mazmuni": {"type": "string", "maxLength": BAND_MAZMUN_BELGI,
                                        "description": "Bandda nima deyilgan — bir qisqa jumla, oddiy tilda"},
                            "xavf": {"type": "string", "enum": XAVF_DARAJALARI,
                                     "description": _XAVF_TAVSIFI},
                            "izoh": {"type": "string", "maxLength": BAND_IZOH_BELGI,
                                     "description": "Nega bu band muhim va odamga qanday ta'sir qiladi — 1-2 jumla"},
                            "modda_id": {"type": "string",
                                         "description": ("Bandga tegishli moddaning ID'si BERILGAN "
                                                         "ro'yxatdan. Mos modda bo'lmasa bo'sh satr qaytar — "
                                                         "ID'ni O'YLAB TOPMA.")},
                        },
                        "required": ["band", "mazmuni", "xavf", "izoh", "modda_id"],
                    },
                },
                "xulosa": {
                    "type": "string",
                    "maxLength": SHARTNOMA_XULOSA_BELGI,
                    "description": (
                        "Yakuniy maslahat: imzolash mumkinmi, imzolashdan oldin qaysi "
                        "bandlarni o'zgartirishni talab qilish kerak. 2-4 jumla, aniq "
                        "band raqamlari bilan."
                    ),
                },
            },
            "required": ["shartnoma_turi", "umumiy_mazmun", "bandlar_soni", "bandlar", "xulosa"],
        },
    }


def _gemini_shartnoma_sxemasi() -> dict:
    return {
        "type": "OBJECT",
        "properties": {
            "shartnoma_turi": {"type": "STRING", "enum": SHARTNOMA_TURLARI},
            "umumiy_mazmun": {
                "type": "OBJECT",
                "properties": {
                    "tomonlar": {"type": "STRING"},
                    "predmet": {"type": "STRING"},
                    "summa": {"type": "STRING"},
                    "muddat": {"type": "STRING"},
                },
                "required": ["tomonlar", "predmet", "summa", "muddat"],
            },
            "bandlar_soni": {"type": "INTEGER"},
            "bandlar": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "band": {"type": "STRING"},
                        "mazmuni": {"type": "STRING"},
                        "xavf": {"type": "STRING", "enum": XAVF_DARAJALARI},
                        "izoh": {"type": "STRING"},
                        "modda_id": {"type": "STRING"},
                    },
                    "required": ["band", "mazmuni", "xavf", "izoh", "modda_id"],
                },
            },
            "xulosa": {"type": "STRING"},
        },
        "required": ["shartnoma_turi", "umumiy_mazmun", "bandlar_soni", "bandlar", "xulosa"],
    }


_SHARTNOMA_PROMPT = """Sen — HuquqiyAI, O'zbekiston fuqarolari uchun huquqiy yordamchisan.
Foydalanuvchi shartnoma yukladi va uni imzolashdan oldin xavfini bilmoqchi.

QAT'IY QOIDALAR:
1. FAQAT quyida berilgan qonun moddalari asosida baho ber. Xotirangdagi boshqa
   qonunlarga tayanma. Modda matnini QAYTA YOZMA va iqtibos KELTIRMA — asl matn
   foydalanuvchiga bazadan alohida ko'rsatiladi. Sen faqat modda ID'sini tanlaysan.
2. modda_id FAQAT berilgan ro'yxatdan bo'lishi mumkin. Mos modda topilmasa bo'sh
   satr qaytar — bandni baribir ko'rsat, lekin ID'ni O'YLAB TOPMA. Bu qoida
   loyihaning asosiy ishonch kafolati.
3. Bandni "qonunga zid" (qizil) deb faqat berilgan moddaning majburiy normasiga
   zid bo'lganda belgila. Shubha bo'lsa — "sariq" qo'y va nega xavfli ekanini tushuntir.
4. Foydalanuvchi — shartnomaning KUCHSIZ tarafi (xodim, ijarachi, qarz oluvchi,
   xaridor). Uning manfaati nuqtai nazaridan bahola.
5. Har band uchun eng muhim narsani ayt: bu band unga amalda nima qilishini.
   Umumiy gap ("bu band muhim") emas, aniq oqibat ("ishdan bo'shasangiz 5 mln to'laysiz").
6. Faqat DIQQAT TALAB QILADIGAN bandlarni qaytar. Oddiy, xavfsiz bandlarni
   (rekvizitlar, tomonlar nomi, umumiy iboralar) ro'yxatga kiritma.
7. Shartnoma umuman shartnoma bo'lmasa yoki matn tushunarsiz bo'lsa —
   bandlar ro'yxatini bo'sh qoldir va xulosada shuni ochiq ayt.
8. TIL: shartnoma qaysi tilda bo'lsa, javobni ham o'sha tilda yoz (o'zbek lotin,
   o'zbek kirill yoki rus). Aralash bo'lsa asosiy tilni tanla.
9. SHAKL: oddiy matn. Markdown sarlavha, ro'yxat belgisi va jadval ISHLATMA."""


def shartnoma_tahlil_yarat(hujjat_matni: str, nomzod_moddalar: List[dict]) -> dict:
    """Shartnomani band-band tahlil qiladi. Provayderlar navbati javob_yarat kabi."""
    tizim = _SHARTNOMA_PROMPT + "\n\nMAVJUD QONUN MODDALARI:\n" + _moddalar_bloki(nomzod_moddalar)
    xabarlar = [{
        "role": "user",
        "content": "Shartnoma matni:\n<shartnoma>\n" + hujjat_matni + "\n</shartnoma>",
    }]

    # Xatolar YIG'ILADI, oxirgisi emas: Anthropic kredit tugashi bilan
    # yiqilib, keyin Gemini limitga urilsa, faqat oxirgisi ko'rsatilsa
    # foydalanuvchi "so'rovlar ko'payib ketdi" degan chalg'ituvchi xabar
    # oladi va kutadi — aslida hisob to'ldirilishi kerak.
    xatolar: List[Exception] = []
    if _client is not None:
        natija = _urin("anthropic", lambda: _anthropic_shartnoma(tizim, xabarlar), xatolar)
        if natija is not None:
            return natija
    if GEMINI_API_KEY:
        natija = _urin("gemini", lambda: _gemini_shartnoma(tizim, xabarlar), xatolar)
        if natija is not None:
            return natija
    if OPENAI_API_KEY:
        natija = _urin("openai", lambda: _openai_shartnoma(tizim, xabarlar), xatolar)
        if natija is not None:
            return natija
    if xatolar:
        raise RuntimeError(_xatolar_matni(xatolar))
    raise RuntimeError("Hech qanday AI provayder sozlanmagan (API kalit yo'q)")


def _anthropic_shartnoma(tizim: str, xabarlar: List[dict]) -> dict:
    javob = _client.messages.create(
        model=MODEL,
        max_tokens=4096,  # band ro'yxati uch qismli javobdan uzunroq
        system=tizim + "\n\nJavobni faqat shartnoma_tahlili tool orqali qaytar.",
        messages=xabarlar,
        tools=[_shartnoma_tool()],
        tool_choice={"type": "tool", "name": "shartnoma_tahlili"},
    )
    for blok in javob.content:
        if blok.type == "tool_use" and blok.name == "shartnoma_tahlili":
            return dict(blok.input)
    raise RuntimeError("Model tool chaqirmadi")


def _gemini_shartnoma(tizim: str, xabarlar: List[dict]) -> dict:
    javob = httpx.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent",
        params={"key": GEMINI_API_KEY},
        json={
            "system_instruction": {"parts": [{"text": tizim}]},
            "contents": [{"role": "user", "parts": [{"text": xabarlar[0]["content"]}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "response_schema": _gemini_shartnoma_sxemasi(),
                "maxOutputTokens": _GEMINI_SHARTNOMA_TOKEN,
            },
        },
        timeout=90,
    )
    javob.raise_for_status()
    return json.loads(_gemini_matni(javob))


# Model modda matnini qayta yozmaydi — u faqat qaysi modda mos kelishini
# aniqlaydi. Shuning uchun uzun moddalarning boshini yuborish yetarli:
# so'rov hajmi (va javob vaqti) sezilarli kamayadi. Foydalanuvchiga baribir
# to'liq matn bazadan ko'rsatiladi.
MAX_MODDA_BELGI = 1200


def _tavsiyani_matnga(natija: dict) -> dict:
    """Model tavsiyani qadamlar ro'yxati qilib qaytaradi (qisqaroq chiqadi),
    tashqi API esa bitta matn kutadi. Har bir qadam alohida xatboshi bo'ladi —
    frontend matnni \\n bo'yicha ajratib ko'rsatadi.

    Zaxira provayder yoki eski javob matn qaytarsa ham buzilmasin.
    """
    t = natija.get("tavsiya")
    if isinstance(t, list):
        natija["tavsiya"] = "\n\n".join(str(q).strip() for q in t if str(q).strip())
    elif t is None:
        natija["tavsiya"] = ""
    else:
        natija["tavsiya"] = str(t)
    natija["xulosa"] = str(natija.get("xulosa") or "")
    return natija


def _qisqartir(matn: str) -> str:
    matn = matn or ""
    if len(matn) <= MAX_MODDA_BELGI:
        return matn
    return matn[:MAX_MODDA_BELGI].rstrip() + "\n[…modda davomi bazada]"


def _moddalar_bloki(moddalar: List[dict]) -> str:
    """Nomzod moddalarni prompt uchun matn blokiga aylantiradi.

    Uch qismli javob ham, shartnoma tahlili ham shu blokdan foydalanadi:
    moddalarni ikki xil ko'rinishda berish model tanlovini ham ikki xil
    qilib qo'yardi.
    """
    return "\n\n".join(
        "<modda id=\"{id}\">\n{qonun} | {raqam}. {sarlavha}\n{matn}\n</modda>".format(
            id=m["id"],
            qonun=m["qonun_nomi"],
            raqam=m["modda_raqami"],
            sarlavha=m["sarlavha"],
            matn=_qisqartir(m["matn"])
            if m.get("holat") == "verified"
            else "(matn hali tekshirilmagan — tanlama)",
        )
        for m in moddalar
    )


def _anthropic_javob(tizim: str, xabarlar: List[dict], batafsil: bool = False) -> dict:
    javob = _client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=tizim + "\n\nJavobni faqat huquqiy_javob tool orqali qaytar.",
        messages=xabarlar,
        tools=[_javob_tool(batafsil)],
        tool_choice={"type": "tool", "name": "huquqiy_javob"},
    )
    for blok in javob.content:
        if blok.type == "tool_use" and blok.name == "huquqiy_javob":
            return dict(blok.input)
    raise RuntimeError("Model tool chaqirmadi")


def _gemini_javob(tizim: str, xabarlar: List[dict], batafsil: bool = False) -> dict:
    """Zaxira provayder: Gemini REST API, structured JSON output bilan."""
    contents = [
        {
            "role": "user" if x["role"] == "user" else "model",
            "parts": [{"text": x["content"]}],
        }
        for x in xabarlar
    ]
    javob = httpx.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent",
        params={"key": GEMINI_API_KEY},
        json={
            "system_instruction": {"parts": [{"text": tizim + "\n\nJavobni faqat berilgan JSON sxema bo'yicha qaytar."}]},
            "contents": contents,
            "generationConfig": {
                "response_mime_type": "application/json",
                "response_schema": _gemini_sxema(batafsil),
                "maxOutputTokens": _GEMINI_JAVOB_TOKEN,
            },
        },
        timeout=60,
    )
    javob.raise_for_status()
    natija = json.loads(_gemini_matni(javob))
    # Sxema kafolatiga qo'shimcha himoya
    if natija.get("murojaat_mavzusi") not in MUROJAAT_MAVZULARI:
        natija["murojaat_mavzusi"] = "umumiy"
    natija.setdefault("tegishli_modda_idlari", [])
    return natija


def javob_yarat(
    savol: str,
    nomzod_moddalar: List[dict],
    rejim: str = "oddiy",
    tarix: Optional[List[dict]] = None,
    hujjat_matni: Optional[str] = None,
    batafsil: bool = False,
) -> dict:
    """Tuzilgan javob oladi: avval Anthropic, ishlamasa Gemini.

    Qaytaradi: {javob_topildi, tegishli_modda_idlari, tavsiya, murojaat_mavzusi}
    """
    moddalar_blok = _moddalar_bloki(nomzod_moddalar)

    tizim = _TIZIM_PROMPT.format(rejim_korsatmasi=_REJIMLAR.get(rejim, _REJIMLAR["oddiy"]))
    if batafsil:
        tizim += "\n\n" + _BATAFSIL_KORSATMA
    tizim += "\n\nMAVJUD QONUN MODDALARI:\n" + moddalar_blok

    xabarlar = []
    # Oldingi suhbat tarixi (faqat matn ko'rinishida, kontekst uchun)
    for t in (tarix or [])[-6:]:
        rol = "user" if t.get("rol") == "user" else "assistant"
        matn = str(t.get("matn", ""))[:2000]
        if matn:
            xabarlar.append({"role": rol, "content": matn})

    foydalanuvchi_matni = savol
    if hujjat_matni:
        foydalanuvchi_matni = (
            "Foydalanuvchi hujjat yukladi. Hujjat matni:\n<hujjat>\n"
            + hujjat_matni
            + "\n</hujjat>\n\nSavol: "
            + (savol or "Ushbu hujjatni huquqiy jihatdan tahlil qilib ber.")
        )
    xabarlar.append({"role": "user", "content": foydalanuvchi_matni})

    # Provayderlar navbati: Anthropic -> Gemini (bepul) -> OpenAI (pulli).
    # Biri ishlamasa (kredit tugashi, limit, tarmoq xatosi) keyingisiga o'tiladi.
    # Xatolar YIG'ILADI, oxirgisi emas: Anthropic kredit tugashi bilan
    # yiqilib, keyin Gemini limitga urilsa, faqat oxirgisi ko'rsatilsa
    # foydalanuvchi "so'rovlar ko'payib ketdi" degan chalg'ituvchi xabar
    # oladi va kutadi — aslida hisob to'ldirilishi kerak.
    xatolar: List[Exception] = []
    if _client is not None:
        natija = _urin(
            "anthropic",
            lambda: _tavsiyani_matnga(_anthropic_javob(tizim, xabarlar, batafsil)),
            xatolar,
        )
        if natija is not None:
            return natija
    if GEMINI_API_KEY:
        natija = _urin(
            "gemini",
            lambda: _tavsiyani_matnga(_gemini_javob(tizim, xabarlar, batafsil)),
            xatolar,
        )
        if natija is not None:
            return natija
    if OPENAI_API_KEY:
        natija = _urin(
            "openai",
            lambda: _tavsiyani_matnga(_openai_javob(tizim, xabarlar, batafsil)),
            xatolar,
        )
        if natija is not None:
            return natija
    if xatolar:
        raise RuntimeError(_xatolar_matni(xatolar))
    raise RuntimeError("Hech qanday AI provayder sozlanmagan (API kalit yo'q)")
