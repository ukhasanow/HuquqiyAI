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


def _modellar(nom: str, sukut: str) -> list:
    """Vergul bilan ajratilgan model ro'yxatini o'qiydi.

    Limitlar HAR MODEL uchun alohida hisoblanadi (o'lchandi: Groq'da
    gpt-oss-120b qoldig'i 4323 ga tushganda gpt-oss-20b hamon 7924 edi).
    Shuning uchun bitta provayderga bir necha model berilsa, bepul sig'im
    shuncha barobar oshadi va foydalanuvchi limitni umuman ko'rmaydi.
    """
    return [q.strip() for q in os.getenv(nom, sukut).split(",") if q.strip()]


GEMINI_MODELLAR = _modellar("GEMINI_MODEL", "gemini-flash-latest")
# Boshqa xizmatlar (rasm/OCR: documents, radar, jarima, ovoz) bitta model
# nomini kutadi — ular uchun ro'yxatning birinchisi ishlatiladi.
GEMINI_MODEL = GEMINI_MODELLAR[0]
# Uchinchi provayder: ovozni matnga o'girish (Whisper) va LLM zaxirasi.
# Navbatda oxirgi turadi — Gemini bepul kvotasi (kuniga 20 ta so'rov) tugagach
# ishga tushadi, ya'ni pulli chaqiruv faqat haqiqatan zarur bo'lganda ketadi.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
# Groq — bepul va saxiy limitli zaxira. OpenAI bilan bir xil API shaklida.
# Model tanlovi o'lchovga asoslangan: llama-3.3-70b `json_schema` ni umuman
# qo'llab-quvvatlamaydi, qwen3.6-27b esa bizning prompt hajmiga sig'maydi.
# gpt-oss-120b ikkalasidan ham o'tdi va o'zbekcha javobi to'g'ri chiqdi.
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODELLAR = _modellar("GROQ_MODEL", "openai/gpt-oss-120b,openai/gpt-oss-20b")
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

# ---------- Statistikani tashqarida saqlash ----------
# Render bepul tierda disk VAQTINCHALIK: har deploy'da va xizmat uxlab
# uyg'onganda yozilgan fayllar yo'qoladi. Statistika shu sababli saqlanmaydi.
#
# Ikkalasi berilsa, statistika fayl o'rniga tashqi kalit-qiymat omborida
# saqlanadi (Upstash Redis REST API — oddiy HTTP, yangi paket kerak emas).
# Berilmasa, hammasi oldingidek faylga yoziladi — lokal ishlab chiqish uchun.
# Upstash o'z panelida o'zgaruvchilarni UPSTASH_REDIS_REST_* deb beradi va
# odam ularni aynan shu nom bilan ko'chirib qo'yadi. Ikkala nom ham qabul
# qilinadi — aks holda sozlama jimgina ishlamay, statistika yo'qolib ketardi.
STATISTIKA_KV_URL = (
    os.getenv("STATISTIKA_KV_URL") or os.getenv("UPSTASH_REDIS_REST_URL") or ""
).rstrip("/")
STATISTIKA_KV_TOKEN = (
    os.getenv("STATISTIKA_KV_TOKEN") or os.getenv("UPSTASH_REDIS_REST_TOKEN") or ""
)

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
