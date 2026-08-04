# Asosiy javob oqimi — HTTP qatlamidan mustaqil.
#
# Sayt (app/main.py) ham, Telegram bot ham AYNAN shu modulni chaqiradi.
# Mantiq ikki joyda takrorlansa, ular vaqt o'tib bir-biridan uzoqlashadi:
# birida tuzatilgan xato ikkinchisida qolib ketadi.
#
# Shu sababli bu yerda FastAPI'ga oid hech narsa yo'q (HTTPException ham) —
# xatolar domen istisnolari ko'rinishida ko'tariladi, ularni HTTP kodiga
# yoki Telegram xabariga aylantirish chaqiruvchining ishi.
from typing import List, Optional

from .. import storage
from ..config import ANTHROPIC_API_KEY, GEMINI_API_KEY
from ..models import ChatJavob
from . import kesh, llm, retrieval, statistika


class JavobXato(Exception):
    """Javob tayyorlashda yuzaga kelgan, foydalanuvchiga ko'rsatsa bo'ladigan xato."""

    def __init__(self, foydalanuvchi_matni: str):
        super().__init__(foydalanuvchi_matni)
        self.foydalanuvchi_matni = foydalanuvchi_matni


class AiSozlanmagan(JavobXato):
    """Hech qanday AI provayder kaliti berilmagan (sozlash xatosi, vaqtinchalik emas)."""

    def __init__(self):
        super().__init__(
            "AI provayder sozlanmagan (ANTHROPIC_API_KEY yoki GEMINI_API_KEY kerak). "
            ".env faylini tekshiring."
        )


class AiXato(JavobXato):
    """AI provayder so'rovi muvaffaqiyatsiz tugadi (kredit, limit, tarmoq)."""

    def __init__(self, asl: Exception):
        super().__init__(_ai_xato_matni(asl))
        self.asl = asl


def _ai_xato_matni(e: Exception) -> str:
    """AI provayder xatolarini foydalanuvchiga tushunarli o'zbekcha xabarga aylantiradi."""
    s = str(e).lower()
    if "credit balance" in s or "billing" in s:
        return "AI xizmati vaqtincha mavjud emas (hisob to'ldirilishi kerak). Birozdan so'ng urinib ko'ring."
    if "authentication" in s or "invalid x-api-key" in s or "401" in s:
        return "AI xizmati sozlanmagan (API kalit noto'g'ri). Administratorga murojaat qiling."
    if "rate limit" in s or "429" in s:
        return "So'rovlar ko'payib ketdi. Bir daqiqadan so'ng qaytadan urinib ko'ring."
    if "overloaded" in s or "529" in s:
        return "AI xizmati hozir band. Birozdan so'ng qaytadan urinib ko'ring."
    return "AI xizmatida vaqtinchalik xatolik yuz berdi. Qaytadan urinib ko'ring."


def uch_qismli_javob(
    savol: str,
    rejim: str = "oddiy",
    tarix: Optional[List[dict]] = None,
    hujjat_matni: Optional[str] = None,
) -> ChatJavob:
    """Umumiy oqim: retrieval -> LLM -> bazadan yig'ish.
    Chat ham, hujjat tahlili ham shu funksiyadan o'tadi."""
    if not ANTHROPIC_API_KEY and not GEMINI_API_KEY:
        raise AiSozlanmagan()

    hamma_moddalar = storage.moddalarni_oqi()
    qidiruv_matni = savol if not hujjat_matni else (savol + " " + hujjat_matni[:2000])
    nomzodlar = retrieval.moddalarni_qidir(qidiruv_matni, hamma_moddalar)

    try:
        natija = llm.javob_yarat(savol, nomzodlar, rejim=rejim, tarix=tarix, hujjat_matni=hujjat_matni)
    except Exception as e:
        raise AiXato(e) from e

    # 1-qism: modda matnlari FAQAT bazadan olinadi (LLM'dan emas)
    moddalar = []
    for mid in natija.get("tegishli_modda_idlari", [])[:3]:
        m = storage.modda_top(mid)
        if m:
            moddalar.append(m)

    # 3-qism: kontakt bazadan
    organ = storage.organ_top(natija.get("murojaat_mavzusi", "umumiy"))

    return ChatJavob(
        javob_topildi=bool(natija.get("javob_topildi")) and bool(moddalar),
        moddalar=moddalar,
        tavsiya=natija.get("tavsiya", ""),
        murojaat=organ,
        murojaat_mavzusi=natija.get("murojaat_mavzusi", "umumiy"),
    )


def javob_ol(savol: str, rejim: str = "oddiy", tarix: Optional[List[dict]] = None) -> ChatJavob:
    """Keshni hisobga olgan holda javob qaytaradi.

    Kesh faqat mustaqil savolga tegishli: suhbat tarixi bo'lsa javob oldingi
    xabarlarga bog'liq bo'ladi va uni boshqa foydalanuvchiga berib bo'lmaydi.
    """
    kesh_kaliti = kesh.kalit(savol, rejim, storage.versiya()) if not tarix else None
    javob = kesh.ol(kesh_kaliti)
    if javob is not None:
        return javob

    javob = uch_qismli_javob(savol, rejim, tarix)
    # Javob topilmagan savollarni keshlamaymiz: baza to'ldirilgach
    # o'sha savol to'g'ri javob berishi kerak.
    if javob.javob_topildi:
        kesh.qoy(kesh_kaliti, javob)
    return javob


def statistikani_yoz(
    javob: ChatJavob, rejim: str, foydalanuvchi_id: Optional[str], savol: str
) -> None:
    """Statistika yozilmasa ham asosiy javob buzilmasligi kerak.

    Javob yuborilgandan KEYIN (fon vazifasi sifatida) chaqiriladi — diskka
    yozish va qulf kutish foydalanuvchi kutadigan vaqtga qo'shilmasin.
    """
    try:
        statistika.sorov_hisobla(
            rejim=rejim,
            javob_topildi=javob.javob_topildi,
            murojaat_mavzusi=javob.murojaat_mavzusi,
            foydalanuvchi_id=foydalanuvchi_id,
            savol=savol,
        )
    except Exception:
        pass
