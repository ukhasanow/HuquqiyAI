# HuquqiyAI — FastAPI ilova va routelar
import secrets
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import storage
from .config import ADMIN_PASSWORD, MAX_HUJJAT_HAJMI, STATIC_DIR
from .models import ArizaJavob, ArizaSorov, ChatJavob, ChatSorov, ModdaKiritish
from .services import ariza, documents, statistika
from .services.javob import AiSozlanmagan, AiXato, javob_ol, statistikani_yoz, uch_qismli_javob

app = FastAPI(title="HuquqiyAI", description="O'zbekiston uchun huquqiy AI yordamchi")


# ---------- Yordamchi funksiyalar ----------

def _admin_tekshir(parol: Optional[str]) -> None:
    if not parol or not secrets.compare_digest(parol, ADMIN_PASSWORD):
        raise HTTPException(status_code=401, detail="Noto'g'ri admin parol")


def _http_xato(e) -> HTTPException:
    """Domen istisnosini HTTP kodiga aylantiradi.

    Javob mantiqi (services/javob.py) HTTP haqida hech narsa bilmaydi —
    o'sha modulni Telegram bot ham chaqiradi.
    """
    if isinstance(e, AiSozlanmagan):
        return HTTPException(status_code=503, detail=e.foydalanuvchi_matni)
    return HTTPException(status_code=502, detail=e.foydalanuvchi_matni)


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
def chat(sorov: ChatSorov, fon: BackgroundTasks, x_foydalanuvchi_id: Optional[str] = Header(None)):
    tarix = [t.model_dump() for t in (sorov.tarix or [])]
    try:
        javob = javob_ol(sorov.savol, sorov.rejim, tarix)
    except (AiSozlanmagan, AiXato) as e:
        raise _http_xato(e)

    fon.add_task(statistikani_yoz, javob, sorov.rejim, x_foydalanuvchi_id, sorov.savol)
    return javob


@app.post("/api/hujjat", response_model=ChatJavob)
async def hujjat_tahlili(
    fon: BackgroundTasks,
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
    try:
        javob = uch_qismli_javob(savol, rejim, tarix=None, hujjat_matni=matn)
    except (AiSozlanmagan, AiXato) as e:
        raise _http_xato(e)
    fon.add_task(statistikani_yoz, javob, rejim, x_foydalanuvchi_id, savol)
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
