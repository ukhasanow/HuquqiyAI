# Muhit sozlamalari (.env faylidan o'qiladi)
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "static"

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL = os.getenv("MODEL", "claude-sonnet-4-5")
# Zaxira provayder: Anthropic ishlamasa (kredit/limit) Gemini'ga o'tiladi
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
# Ovozli xabarni matnga o'girish uchun ixtiyoriy zaxira (Whisper).
# Asosiy provayder — Gemini, kaliti yuqorida.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "huquqiy-admin-2026")

# Yuklanadigan hujjat uchun cheklovlar
MAX_HUJJAT_HAJMI = 10 * 1024 * 1024  # 10 MB
MAX_HUJJAT_BELGILAR = 30_000  # LLM'ga yuboriladigan matn uzunligi

# ---------- Telegram bot ----------
# Token bo'lmasa bot moduli umuman yuklanmaydi va sayt oldingidek ishlaydi —
# Render'da token qo'yilmagan holatda ham deploy sinmasligi kerak.
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Ilovaning tashqi manzili, masalan https://huquqiyai-kjpa.onrender.com
# Berilsa, ishga tushishda webhook avtomatik o'rnatiladi; bo'lmasa bot faqat
# polling rejimida (python -m app.bot.polling) ishlaydi.
#
# Render Blueprint bu qiymatni xizmatning o'zidan oladi va u SXEMASIZ keladi
# ("huquqiyai.onrender.com"), Telegram esa to'liq URL talab qiladi.
def _webhook_manzili(xom: str) -> str:
    xom = (xom or "").strip().rstrip("/")
    if not xom:
        return ""
    return xom if "://" in xom else "https://" + xom


TELEGRAM_WEBHOOK_URL = _webhook_manzili(os.getenv("TELEGRAM_WEBHOOK_URL", ""))

# Webhook'ga kelgan so'rov haqiqatan Telegram'dan ekanini tekshirish uchun.
# Manzilning o'zi maxfiy emas — sir shu header'da.
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")

# Ovozli xabar cheklovlari (5-bosqich)
MAX_OVOZ_DAVOMIYLIGI = 60  # soniya
MAX_OVOZ_HAJMI = 20 * 1024 * 1024
