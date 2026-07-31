# HuquqiyAI — FastAPI ilova va routelar
import secrets
from typing import Optional

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import storage
from .config import ADMIN_PASSWORD, ANTHROPIC_API_KEY, GEMINI_API_KEY, MAX_HUJJAT_HAJMI, STATIC_DIR
from .models import ArizaJavob, ArizaSorov, ChatJavob, ChatSorov, ModdaKiritish
from .services import ariza, documents, llm, retrieval, statistika

app = FastAPI(title="HuquqiyAI", description="O'zbekiston uchun huquqiy AI yordamchi")


# ---------- Yordamchi funksiyalar ----------

def _admin_tekshir(parol: Optional[str]) -> None:
    if not parol or not secrets.compare_digest(parol, ADMIN_PASSWORD):
        raise HTTPException(status_code=401, detail="Noto'g'ri admin parol")


def _api_xato_matni(e: Exception) -> str:
    """Anthropic API xatolarini foydalanuvchiga tushunarli o'zbekcha xabarga aylantiradi."""
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


def _uch_qismli_javob(savol: str, rejim: str, tarix, hujjat_matni: Optional[str] = None) -> ChatJavob:
    """Umumiy oqim: retrieval -> LLM -> bazadan yig'ish.
    Chat ham, hujjat tahlili ham shu funksiyadan o'tadi."""
    if not ANTHROPIC_API_KEY and not GEMINI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="AI provayder sozlanmagan (ANTHROPIC_API_KEY yoki GEMINI_API_KEY kerak). .env faylini tekshiring.",
        )
    hamma_moddalar = storage.moddalarni_oqi()
    qidiruv_matni = savol if not hujjat_matni else (savol + " " + hujjat_matni[:2000])
    nomzodlar = retrieval.moddalarni_qidir(qidiruv_matni, hamma_moddalar)

    try:
        natija = llm.javob_yarat(savol, nomzodlar, rejim=rejim, tarix=tarix, hujjat_matni=hujjat_matni)
    except Exception as e:  # API xatolari foydalanuvchiga tushunarli qaytsin
        raise HTTPException(status_code=502, detail=_api_xato_matni(e))

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


def _statistika_yoz(javob: ChatJavob, rejim: str, foydalanuvchi_id: Optional[str], savol: str) -> None:
    """Statistika yozilmasa ham asosiy javob buzilmasligi kerak."""
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


# ---------- Ochiq API ----------

@app.get("/health", include_in_schema=False)
def health():
    """Uptime monitoring va bosh sahifadagi ochiq hisoblagich uchun."""
    return {
        "holat": "ok",
        "moddalar_soni": len(storage.moddalarni_oqi()),
        "javoblar_soni": statistika.javoblar_soni(),
    }

@app.post("/api/chat", response_model=ChatJavob)
def chat(sorov: ChatSorov, x_foydalanuvchi_id: Optional[str] = Header(None)):
    tarix = [t.model_dump() for t in (sorov.tarix or [])]
    javob = _uch_qismli_javob(sorov.savol, sorov.rejim, tarix)
    _statistika_yoz(javob, sorov.rejim, x_foydalanuvchi_id, sorov.savol)
    return javob


@app.post("/api/hujjat", response_model=ChatJavob)
async def hujjat_tahlili(
    fayl: UploadFile = File(...),
    savol: str = Form(""),
    rejim: str = Form("oddiy"),
    x_foydalanuvchi_id: Optional[str] = Header(None),
):
    bayt = await fayl.read()
    if len(bayt) > MAX_HUJJAT_HAJMI:
        raise HTTPException(status_code=413, detail="Fayl hajmi 10 MB dan oshmasligi kerak")
    try:
        matn = documents.matn_ajrat(fayl.filename or "hujjat", bayt)
    except documents.HujjatXato as e:
        raise HTTPException(status_code=422, detail=str(e))
    javob = _uch_qismli_javob(savol, rejim, tarix=None, hujjat_matni=matn)
    _statistika_yoz(javob, rejim, x_foydalanuvchi_id, savol)
    return javob


@app.post("/api/ariza", response_model=ArizaJavob)
def ariza_qoralamasi(sorov: ArizaSorov):
    """Javobdagi modda va organ asosida ariza qoralamasini tuzadi (LLM'siz)."""
    moddalar = [m for mid in sorov.modda_idlari if (m := storage.modda_top(mid))]
    organ = storage.organ_top(sorov.murojaat_mavzusi)
    if not moddalar or not organ:
        raise HTTPException(status_code=422, detail="Ariza uchun modda yoki organ topilmadi")
    try:
        matn = ariza.ariza_tuz(
            fish=sorov.fish,
            vaziyat=sorov.vaziyat,
            moddalar=moddalar,
            organ=organ,
            manzil=sorov.manzil,
            telefon=sorov.telefon,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return ArizaJavob(matn=matn)


# ---------- Admin API (parol bilan) ----------

@app.get("/api/admin/moddalar")
def admin_moddalar_royxati(x_admin_parol: Optional[str] = Header(None)):
    _admin_tekshir(x_admin_parol)
    return storage.moddalarni_oqi()


@app.post("/api/admin/moddalar")
def admin_modda_saqlash(modda: ModdaKiritish, x_admin_parol: Optional[str] = Header(None)):
    _admin_tekshir(x_admin_parol)
    if modda.holat not in ("verified", "needs_verification"):
        raise HTTPException(status_code=422, detail="holat: verified yoki needs_verification bo'lishi kerak")
    return storage.modda_qosh_yoki_yangila(modda.model_dump())


@app.get("/api/admin/statistika")
def admin_statistika(x_admin_parol: Optional[str] = Header(None)):
    _admin_tekshir(x_admin_parol)
    return statistika.statistika_oqi()


# ---------- Statik sahifalar ----------

@app.get("/", include_in_schema=False)
def bosh_sahifa():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/admin", include_in_schema=False)
def admin_sahifa():
    return FileResponse(STATIC_DIR / "admin.html")


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
