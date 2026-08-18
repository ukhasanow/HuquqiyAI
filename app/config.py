import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "static"

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL = os.getenv("MODEL", "claude-sonnet-4-5")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


def _modellar(nom: str, sukut: str) -> list:
    """Vergul bilan ajratilgan model ro'yxatini o'qiydi.

    Limitlar HAR MODEL uchun alohida hisoblanadi (o'lchandi: Groq'da
    gpt-oss-120b qoldig'i 4323 ga tushganda gpt-oss-20b hamon 7924 edi).
    Shuning uchun bitta provayderga bir necha model berilsa, bepul sig'im
    shuncha barobar oshadi va foydalanuvchi limitni umuman ko'rmaydi.
    """
    return [q.strip() for q in os.getenv(nom, sukut).split(",") if q.strip()]


GEMINI_MODELLAR = _modellar("GEMINI_MODEL", "gemini-flash-latest")

GEMINI_MODEL = GEMINI_MODELLAR[0]

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODELLAR = _modellar("GROQ_MODEL", "openai/gpt-oss-120b,openai/gpt-oss-20b")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODELLAR = _modellar(
    "OPENROUTER_MODEL", "nvidia/nemotron-3-super-120b-a12b:free"
)
BAZAARLINK_API_KEY = os.getenv("BAZAARLINK_API_KEY", "")
BAZAARLINK_MODELLAR = _modellar("BAZAARLINK_MODEL", "auto:free")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "huquqiy-admin-2026")

# Yuklanadigan hujjat uchun cheklovlar
MAX_HUJJAT_HAJMI = 10 * 1024 * 1024  # 10 MB
MAX_HUJJAT_BELGILAR = 30_000  # LLM'ga yuboriladigan matn uzunligi


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")


def _webhook_manzili(xom: str) -> str:
    xom = (xom or "").strip().rstrip("/")
    if not xom:
        return ""
    return xom if "://" in xom else "https://" + xom


TELEGRAM_WEBHOOK_URL = _webhook_manzili(os.getenv("TELEGRAM_WEBHOOK_URL", ""))

TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")


def _admin_idlar(xom: str) -> set:
    return {q.strip() for q in (xom or "").split(",") if q.strip()}


TELEGRAM_ADMIN_IDLAR = _admin_idlar(os.getenv("TELEGRAM_ADMIN_IDLAR", ""))


STATISTIKA_KV_URL = (
    os.getenv("STATISTIKA_KV_URL") or os.getenv("UPSTASH_REDIS_REST_URL") or ""
).rstrip("/")
STATISTIKA_KV_TOKEN = (
    os.getenv("STATISTIKA_KV_TOKEN") or os.getenv("UPSTASH_REDIS_REST_TOKEN") or ""
)

KESH_KV_MUDDATI = int(os.getenv("KESH_MUDDATI", str(24 * 3600)))

# Ovozli xabar cheklovlari (5-bosqich)
MAX_OVOZ_DAVOMIYLIGI = 60  # soniya
MAX_OVOZ_HAJMI = 20 * 1024 * 1024


TTS_PROVAYDER = os.getenv("TTS_PROVAYDER", "yoq").strip().lower()
GEMINI_TTS_MODEL = os.getenv("GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts")
GEMINI_TTS_OVOZ = os.getenv("GEMINI_TTS_OVOZ", "Kore")

MAX_TTS_BELGILAR = 1200
