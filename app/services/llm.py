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
MUROJAAT_MAVZULARI = ["mehnat", "iste'molchi", "oila", "oila-sud", "fuqarolik", "umumiy"]

_JAVOB_TOOL = {
    "name": "huquqiy_javob",
    "description": "Foydalanuvchi savoliga tuzilgan huquqiy javobni qaytarish",
    "input_schema": {
        "type": "object",
        "properties": {
            "javob_topildi": {
                "type": "boolean",
                "description": "Berilgan moddalar orasida savolga tegishlisi bormi",
            },
            "tegishli_modda_idlari": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Savolga bevosita tegishli moddalarning ID ro'yxati (muhimlik tartibida, ko'pi bilan 3 ta)",
            },
            "tavsiya": {
                "type": "string",
                "description": "UMUMIY TAVSIYA: vaziyatga mos tushuntirish va keyingi qadamlar",
            },
            "murojaat_mavzusi": {
                "type": "string",
                "enum": MUROJAAT_MAVZULARI,
                "description": "Qaysi davlat organiga murojaat qilish kerakligini belgilovchi mavzu",
            },
        },
        "required": ["javob_topildi", "tegishli_modda_idlari", "tavsiya", "murojaat_mavzusi"],
    },
}

# Gemini structured output uchun xuddi shu sxemaning OpenAPI ko'rinishi
_GEMINI_SXEMA = {
    "type": "OBJECT",
    "properties": {
        "javob_topildi": {"type": "BOOLEAN"},
        "tegishli_modda_idlari": {"type": "ARRAY", "items": {"type": "STRING"}},
        "tavsiya": {"type": "STRING"},
        "murojaat_mavzusi": {"type": "STRING", "enum": MUROJAAT_MAVZULARI},
    },
    "required": ["javob_topildi", "tegishli_modda_idlari", "tavsiya", "murojaat_mavzusi"],
}

_TIZIM_PROMPT = """Sen — HuquqiyAI, O'zbekiston fuqarolari uchun huquqiy yordamchisan.

QAT'IY QOIDALAR:
1. FAQAT quyida berilgan qonun moddalari asosida javob ber. O'z xotirangdagi boshqa qonunlarga tayanma.
2. Modda matnini QAYTA YOZMA va iqtibos KELTIRMA — modda matni foydalanuvchiga bazadan alohida ko'rsatiladi. Sen faqat tegishli moddalar ID'sini tanlaysan.
3. Berilgan moddalar savolga mos kelmasa, javob_topildi=false qil va tavsiyada buni ochiq ayt: savol bazadagi mavzularga kirmasligini tushuntir va umumiy yo'nalish ber (murojaat_mavzusi="umumiy").
4. Tavsiyada aniq, amaliy keyingi qadamlarni yoz (nima qilish, qanday hujjat kerak bo'lishi mumkin).
5. Huquqiy maslahat o'rnini bosmasligni unutma — murakkab vaziyatlarda advokatga murojaat qilishni tavsiya qil.
6. TIL QOIDASI: tavsiyani foydalanuvchi savoli qaysi tilda va yozuvda bo'lsa, o'sha tilda yoz — o'zbek lotin, o'zbek kirill (ўзбек кирилл) yoki rus tilida. Aralash bo'lsa, savolning asosiy tilini tanla.

{rejim_korsatmasi}"""

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


def _anthropic_javob(tizim: str, xabarlar: List[dict]) -> dict:
    javob = _client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=tizim + "\n\nJavobni faqat huquqiy_javob tool orqali qaytar.",
        messages=xabarlar,
        tools=[_JAVOB_TOOL],
        tool_choice={"type": "tool", "name": "huquqiy_javob"},
    )
    for blok in javob.content:
        if blok.type == "tool_use" and blok.name == "huquqiy_javob":
            return dict(blok.input)
    raise RuntimeError("Model tool chaqirmadi")


def _gemini_javob(tizim: str, xabarlar: List[dict]) -> dict:
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
                "response_schema": _GEMINI_SXEMA,
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
            matn=m["matn"] if m.get("holat") == "verified" else "(matn hali tekshirilmagan — tanlama)",
        )
        for m in nomzod_moddalar
    )

    tizim = _TIZIM_PROMPT.format(rejim_korsatmasi=_REJIMLAR.get(rejim, _REJIMLAR["oddiy"]))
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
            return _anthropic_javob(tizim, xabarlar)
        except Exception as e:
            oxirgi_xato = e
    if GEMINI_API_KEY:
        try:
            return _gemini_javob(tizim, xabarlar)
        except Exception as e:
            oxirgi_xato = e
    if oxirgi_xato:
        raise oxirgi_xato
    raise RuntimeError("Hech qanday AI provayder sozlanmagan (API kalit yo'q)")
