# Ovozli xabarni matnga o'girish (STT).
#
# Telegram ovozli xabarni OGG/Opus formatida beradi. Uni boshqa formatga
# o'girish uchun ffmpeg kerak bo'lardi — Render bepul tierda esa apt yo'q.
# Shuning uchun audio provayderga O'ZGARTIRILMASDAN yuboriladi: Gemini ham,
# Whisper ham OGG/Opus'ni to'g'ridan-to'g'ri qabul qiladi.
#
# Asosiy provayder — Gemini: loyihada kaliti allaqachon bor (llm.py zaxira
# provayderi) va o'zbek tilini tushunadi. OPENAI_API_KEY berilsa, Gemini
# ishlamay qolganda Whisper'ga o'tiladi.
import base64
from typing import Optional

import httpx

from ..config import GEMINI_API_KEY, GEMINI_MODEL, OPENAI_API_KEY

# Ovozni matnga o'girish — ijodkorlik talab qilmaydi, aksincha zarar qiladi:
# model eshitmagan so'zini "to'g'rilab" yozib qo'yishi mumkin.
_KORSATMA = (
    "Bu ovozli xabar — O'zbekiston fuqarosining huquqiy savoli. "
    "Uni AYNAN eshitilganidek matnga ko'chir. "
    "Faqat transkriptni qaytar: izoh, tarjima, tuzatish va qo'shimcha so'z yozma. "
    "Xabar o'zbek tilida bo'lsa o'zbek lotin yozuvida yoz. "
    "Agar nutq eshitilmasa yoki tushunarsiz bo'lsa, bo'sh satr qaytar."
)

SOROV_MUDDATI = 90


class OvozXato(Exception):
    """Ovozni matnga o'girib bo'lmadi (foydalanuvchiga ko'rsatiladigan xabar)."""


def mavjud() -> bool:
    return bool(GEMINI_API_KEY or OPENAI_API_KEY)


def matnga_ogir(bayt: bytes, mime: str = "audio/ogg") -> str:
    """Ovoz baytlarini matnga o'giradi. Provayderlar navbati llm.py uslubida."""
    if not bayt:
        raise OvozXato("Ovozli xabar bo'sh.")

    oxirgi_xato: Optional[Exception] = None
    if GEMINI_API_KEY:
        try:
            return _gemini_transkript(bayt, mime)
        except Exception as e:
            oxirgi_xato = e
    if OPENAI_API_KEY:
        try:
            return _whisper_transkript(bayt, mime)
        except Exception as e:
            oxirgi_xato = e

    if oxirgi_xato is not None:
        raise OvozXato(
            "Ovozli xabarni matnga o'girib bo'lmadi. Savolingizni matn bilan yozib ko'ring."
        ) from oxirgi_xato
    raise OvozXato(
        "Ovozli xabarlarni qayta ishlash sozlanmagan. Savolingizni matn bilan yozing."
    )


def _gemini_transkript(bayt: bytes, mime: str) -> str:
    javob = httpx.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent",
        params={"key": GEMINI_API_KEY},
        json={
            "contents": [{
                "parts": [
                    {"text": _KORSATMA},
                    {"inline_data": {"mime_type": mime, "data": base64.b64encode(bayt).decode()}},
                ]
            }],
            # temperature=0: transkript ijodiy bo'lmasligi kerak
            "generationConfig": {"temperature": 0, "maxOutputTokens": 1024},
        },
        timeout=SOROV_MUDDATI,
    )
    javob.raise_for_status()
    nomzodlar = javob.json().get("candidates") or []
    if not nomzodlar:
        return ""
    qismlar = nomzodlar[0].get("content", {}).get("parts") or []
    return "".join(q.get("text", "") for q in qismlar).strip()


def _whisper_transkript(bayt: bytes, mime: str) -> str:
    kengaytma = "ogg" if "ogg" in mime else mime.split("/")[-1]
    javob = httpx.post(
        "https://api.openai.com/v1/audio/transcriptions",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
        files={"file": (f"ovoz.{kengaytma}", bayt, mime)},
        data={"model": "whisper-1", "language": "uz"},
        timeout=SOROV_MUDDATI,
    )
    javob.raise_for_status()
    return (javob.json().get("text") or "").strip()
