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
# Zaxira provayder: Anthropic ishlamasa (kredit/limit) Gemini'ga o'tiladi.
# Model nomi "-latest" bilan olinadi: Google eski nomlarni yangi kalitlar uchun
# yopib qo'yadi ("no longer available to new users"), bu esa zaxirani jimgina
# o'lik qilib qo'yadi — nosozlik faqat Anthropic ishlamay qolganda bilinadi.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
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


# Bot statistikasini ko'ra oladigan chat ID lar (vergul bilan).
# Parol emas, ID ishlatiladi: Telegram'da parol yozish uni suhbat tarixida
# ochiq qoldiradi, chat ID ni esa boshqa odam soxtalashtira olmaydi.
def _admin_idlar(xom: str) -> set:
    return {q.strip() for q in (xom or "").split(",") if q.strip()}


TELEGRAM_ADMIN_IDLAR = _admin_idlar(os.getenv("TELEGRAM_ADMIN_IDLAR", ""))

# Ovozli xabar cheklovlari (5-bosqich)
MAX_OVOZ_DAVOMIYLIGI = 60  # soniya
MAX_OVOZ_HAJMI = 20 * 1024 * 1024

# ---------- Ovozli javob, TTS (5-bosqich) ----------
# "gemini" yoki "yoq". O'chirilgan holatda bot faqat matn bilan javob beradi —
# TTS ishlamay qolsa ham asosiy javob buzilmaydi.
TTS_PROVAYDER = os.getenv("TTS_PROVAYDER", "yoq").strip().lower()
GEMINI_TTS_MODEL = os.getenv("GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts")
GEMINI_TTS_OVOZ = os.getenv("GEMINI_TTS_OVOZ", "Kore")

# Ovozga faqat tavsiya qismi o'giriladi. 1200 belgi ~ 90 soniya nutq: undan
# uzun audioni odam oxirigacha tinglamaydi, matn esa doim to'liq yuboriladi.
MAX_TTS_BELGILAR = 1200
