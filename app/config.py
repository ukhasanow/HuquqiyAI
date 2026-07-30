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
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "huquqiy-admin-2026")

# Yuklanadigan hujjat uchun cheklovlar
MAX_HUJJAT_HAJMI = 10 * 1024 * 1024  # 10 MB
MAX_HUJJAT_BELGILAR = 30_000  # LLM'ga yuboriladigan matn uzunligi
