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
    moddalar_blok = "\n\n".join(
        "<modda id=\"{id}\">\n{qonun} | {raqam}. {sarlavha}\n{matn}\n</modda>".format(
            id=m["id"],
            qonun=m["qonun_nomi"],
            raqam=m["modda_raqami"],
            sarlavha=m["sarlavha"],
            matn=_qisqartir(m["matn"])
            if m.get("holat") == "verified"
            else "(matn hali tekshirilmagan — tanlama)",
        )
        for m in nomzod_moddalar
    )

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
    oxirgi_xato: Optional[Exception] = None
    if _client is not None:
        try:
            return _tavsiyani_matnga(_anthropic_javob(tizim, xabarlar, batafsil))
        except Exception as e:
            oxirgi_xato = e
    if GEMINI_API_KEY:
        try:
            return _tavsiyani_matnga(_gemini_javob(tizim, xabarlar, batafsil))
        except Exception as e:
            oxirgi_xato = e
    if oxirgi_xato:
        raise oxirgi_xato
    raise RuntimeError("Hech qanday AI provayder sozlanmagan (API kalit yo'q)")
