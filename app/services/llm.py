# AI modellari bilan ishlash qatlami.
# Asosiy provayder — Anthropic; u ishlamasa (kredit/limit/xato) avtomatik
# ravishda Google Gemini zaxira provayderiga o'tiladi. Ikkalasi ham bir xil
# tuzilgan JSON javob qaytaradi, shuning uchun qolgan kod provayderni sezmaydi.
# Kirish — oddiy matn (savol yoki hujjat matni), manbasidan qat'i nazar.
import json
from typing import List, Optional

import anthropic
import httpx

from ..config import ANTHROPIC_API_KEY, GEMINI_API_KEY, GEMINI_MODEL, MODEL

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
            or "authentication" in m.lower() or "api key" in m.lower()]
    return " | ".join(ogir + [m for m in matnlar if m not in ogir])


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
        try:
            return _anthropic_shartnoma(tizim, xabarlar)
        except Exception as e:
            xatolar.append(e)
    if GEMINI_API_KEY:
        try:
            return _gemini_shartnoma(tizim, xabarlar)
        except Exception as e:
            xatolar.append(e)
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
                "maxOutputTokens": 4096,
            },
        },
        timeout=90,
    )
    javob.raise_for_status()
    return json.loads(javob.json()["candidates"][0]["content"]["parts"][0]["text"])


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
                "maxOutputTokens": 2048,
            },
        },
        timeout=60,
    )
    javob.raise_for_status()
    matn = javob.json()["candidates"][0]["content"]["parts"][0]["text"]
    natija = json.loads(matn)
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

    # Provayderlar navbati: Anthropic -> Gemini. Birinchisi ishlamasa
    # (kredit tugashi, limit, tarmoq xatosi) ikkinchisiga o'tiladi.
    # Xatolar YIG'ILADI, oxirgisi emas: Anthropic kredit tugashi bilan
    # yiqilib, keyin Gemini limitga urilsa, faqat oxirgisi ko'rsatilsa
    # foydalanuvchi "so'rovlar ko'payib ketdi" degan chalg'ituvchi xabar
    # oladi va kutadi — aslida hisob to'ldirilishi kerak.
    xatolar: List[Exception] = []
    if _client is not None:
        try:
            return _tavsiyani_matnga(_anthropic_javob(tizim, xabarlar, batafsil))
        except Exception as e:
            xatolar.append(e)
    if GEMINI_API_KEY:
        try:
            return _tavsiyani_matnga(_gemini_javob(tizim, xabarlar, batafsil))
        except Exception as e:
            xatolar.append(e)
    if xatolar:
        raise RuntimeError(_xatolar_matni(xatolar))
    raise RuntimeError("Hech qanday AI provayder sozlanmagan (API kalit yo'q)")
