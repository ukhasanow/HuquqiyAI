import base64
import io
import logging
import re
import wave
from typing import Optional, Tuple

import httpx

from ..config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GEMINI_TTS_MODEL,
    GEMINI_TTS_OVOZ,
    MAX_TTS_BELGILAR,
    OPENAI_API_KEY,
    TTS_PROVAYDER,
)

log = logging.getLogger(__name__)


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


def tts_mavjud() -> bool:
    """Ovozli javob yoqilganmi. Provayder env orqali almashtiriladi."""
    return TTS_PROVAYDER == "gemini" and bool(GEMINI_API_KEY)


def matnga_ogir(bayt: bytes, mime: str = "audio/ogg") -> str:
    """Ovoz baytlarini matnga o'giradi. Provayderlar navbati llm.py uslubida."""
    if not bayt:
        raise OvozXato("Ovozli xabar bo'sh.")

    
    oxirgi_xato: Optional[Exception] = None
    if GEMINI_API_KEY:
        try:
            return _gemini_transkript(bayt, mime)
        except Exception as e:
            log.warning("Gemini transkripti ishlamadi: %s", e)
            oxirgi_xato = e
    if OPENAI_API_KEY:
        try:
            return _whisper_transkript(bayt, mime)
        except Exception as e:
            log.warning("Whisper transkripti ishlamadi: %s", e)
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



_TTS_KORSATMA = (
    "Quyidagi huquqiy tavsiyani o'zbek tilida, xotirjam va aniq ohangda, "
    "shoshilmasdan o'qib ber:\n\n"
)


def ovozga_ogir(matn: str) -> Tuple[bytes, str]:
    """Matnni ovozga o'giradi va (bayt, mime) qaytaradi.

    Format haqida: Gemini xom PCM qaytaradi (audio/L16). Telegram'ning
    sendVoice'i esa FAQAT OGG/Opus qabul qiladi, Render bepul tierda ffmpeg
    yo'q — ya'ni OGG'ga o'girib bo'lmaydi. Shuning uchun PCM standart `wave`
    moduli bilan WAV'ga o'raladi va handler uni sendAudio orqali yuboradi.
    Yangi bog'liqlik ham, konvertatsiya ham talab qilinmaydi.
    """
    matn = _tts_uchun_qisqart(matn)
    if not matn:
        raise OvozXato("Ovozga o'giriladigan matn bo'sh.")
    if not tts_mavjud():
        raise OvozXato("Ovozli javob sozlanmagan.")
    return _gemini_nutq(matn)


def _tts_uchun_qisqart(matn: str, chegara: int = MAX_TTS_BELGILAR) -> str:
    """Uzun tavsiyani gap chegarasida kesadi — so'z o'rtasidan kesilmasin."""
    matn = " ".join((matn or "").split())
    if len(matn) <= chegara:
        return matn
    oyna = matn[:chegara]
    kesim = max(oyna.rfind(". "), oyna.rfind("! "), oyna.rfind("? "))
    if kesim < chegara // 2:
        kesim = oyna.rfind(" ")
    return matn[: kesim + 1].strip() if kesim > 0 else oyna.strip()


def _gemini_nutq(matn: str) -> Tuple[bytes, str]:
    javob = httpx.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_TTS_MODEL}:generateContent",
        params={"key": GEMINI_API_KEY},
        json={
            "contents": [{"parts": [{"text": _TTS_KORSATMA + matn}]}],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": GEMINI_TTS_OVOZ}}
                },
            },
        },
        timeout=SOROV_MUDDATI,
    )
    javob.raise_for_status()
    nomzodlar = javob.json().get("candidates") or []
    if not nomzodlar:
        raise OvozXato("Ovozli javob yaratilmadi.")
    for qism in nomzodlar[0].get("content", {}).get("parts") or []:
        ichki = qism.get("inlineData") or qism.get("inline_data")
        if ichki and ichki.get("data"):
            pcm = base64.b64decode(ichki["data"])
            mime = ichki.get("mimeType") or ichki.get("mime_type") or ""
            return _wav_qil(pcm, *_pcm_sozlamalari(mime)), "audio/wav"
    raise OvozXato("Ovozli javob yaratilmadi.")


def _pcm_sozlamalari(mime: str) -> Tuple[int, int]:
    """mime satridan (chastota, kanallar) ni o'qiydi.

    Gemini formatni ikki xil yozadi: "audio/L16;codec=pcm;rate=24000" va
    "audio/l16; rate=24000; channels=1" — shuning uchun qat'iy qiymat emas,
    satrdan o'qiladi.
    """
    chastota = re.search(r"rate=(\d+)", mime or "", re.I)
    kanallar = re.search(r"channels=(\d+)", mime or "", re.I)
    return (int(chastota.group(1)) if chastota else 24000,
            int(kanallar.group(1)) if kanallar else 1)


def _wav_qil(pcm: bytes, chastota: int = 24000, kanallar: int = 1) -> bytes:
    """Xom 16-bitli PCM'ni WAV sarlavhasi bilan o'raydi (ffmpeg'siz)."""
    bufer = io.BytesIO()
    with wave.open(bufer, "wb") as w:
        w.setnchannels(kanallar)
        w.setsampwidth(2)  # 16 bit
        w.setframerate(chastota)
        w.writeframes(pcm)
    return bufer.getvalue()
