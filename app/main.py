# HuquqiyAI — FastAPI ilova va routelar
import asyncio
import logging
import secrets
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import bot as telegram_bot
from . import storage
from .config import (
    ADMIN_PASSWORD,
    MAX_HUJJAT_HAJMI,
    MAX_OVOZ_HAJMI,
    STATIC_DIR,
    TELEGRAM_WEBHOOK_SECRET,
    TELEGRAM_WEBHOOK_URL,
)
from .models import (
    ArizaJavob,
    ArizaSorov,
    ChatJavob,
    ChatSorov,
    JarimaJavob,
    JarimaRasmJavob,
    JarimaSorov,
    ModdaKiritish,
    OvozJavob,
    RadarJavob,
    ShartnomaJavob,
    ShikoyatSorov,
)
from .services import ariza, documents, kesh, llm, ovoz, statistika
from .services import hujjat as hujjat_xizmati
from .services import jarima as jarima_xizmati
from .services import radar as radar_xizmati
from .services import shartnoma as shartnoma_xizmati
from .services.javob import AiSozlanmagan, AiXato, javob_ol, statistikani_yoz, uch_qismli_javob

log = logging.getLogger(__name__)

WEBHOOK_YOLI = "/telegram/webhook"


_fon_vazifalari: set = set()


@asynccontextmanager
async def _hayot(_app: FastAPI):
    if telegram_bot.mavjud() and TELEGRAM_WEBHOOK_URL:
        try:
        
            await telegram_bot.bot().set_webhook(
                url=TELEGRAM_WEBHOOK_URL.rstrip("/") + WEBHOOK_YOLI,
                secret_token=TELEGRAM_WEBHOOK_SECRET or None,
            )
            await telegram_bot.buyruqlarni_ornat()
            log.info("Telegram webhook o'rnatildi")
        except Exception:
            # Webhook o'rnatilmasa ham sayt ishlashi kerak
            log.exception("Telegram webhook o'rnatilmadi")
    yield
    if telegram_bot.mavjud():
        await telegram_bot.yopish()


app = FastAPI(
    title="HuquqiyAI",
    description="O'zbekiston uchun huquqiy AI yordamchi",
    lifespan=_hayot,
)


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
    """Uptime monitoring va bosh sahifadagi ochiq hisoblagich uchun.

    `statistika_saqlash` — sozlash xatosini darhol ko'rsatadi: Render'da disk
    vaqtinchalik, shuning uchun "fayl" qiymati statistika saqlanmasligini
    anglatadi. Sir oshkor qilinmaydi, faqat qaysi usul faolligi.

    `provayderlar` — zaxira jimgina o'lib qolmasligi uchun. Ro'yxat NAVBAT
    TARTIBIDA: har element bitta "provayder/model" bosqichi, chunki limitlar
    model bo'yicha hisoblanadi. Tartibning o'zi ham ma'lumot — pulli provayder
    haqiqatan oxirida turibdimi, shu yerdan ko'rinadi. Sabablar: hisob |
    kalit | limit | model | band | uzildi | xato | ishlayapti | sozlanmagan |
    noma'lum (hali chaqirilmagan).
    """
    return {
        "holat": "ok",
        "moddalar_soni": len(storage.moddalarni_oqi()),
        "javoblar_soni": statistika.javoblar_soni(),
        "statistika_saqlash": "tashqi" if statistika.tashqi_saqlash() else "fayl",
        "bot": "yoqilgan" if telegram_bot.mavjud() else "o'chiq",
        "kesh": kesh.holat(),
        "provayderlar": llm.provayderlar_holati(),
    }

@app.post("/api/chat", response_model=ChatJavob)
def chat(sorov: ChatSorov, fon: BackgroundTasks, x_foydalanuvchi_id: Optional[str] = Header(None)):
    tarix = [t.model_dump() for t in (sorov.tarix or [])]
    try:
        javob = javob_ol(sorov.savol, sorov.rejim, tarix)
    except (AiSozlanmagan, AiXato) as e:
        raise _http_xato(e)

    fon.add_task(statistikani_yoz, javob, sorov.rejim, x_foydalanuvchi_id, sorov.savol, "sayt")
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
        matn = documents.matn_ajrat(fayl.filename or "hujjat", bayt, fayl.content_type or "")
    except documents.HujjatXato as e:
        raise HTTPException(status_code=422, detail=str(e))
    try:
        javob = uch_qismli_javob(savol, rejim, tarix=None, hujjat_matni=matn)
    except (AiSozlanmagan, AiXato) as e:
        raise _http_xato(e)
    # Tekshirish ro'yxati va bekor qilish yo'li AI'siz qo'shiladi: odam
    # hujjatni tushunish uchun emas, u bilan nima qilishni bilish uchun yuklaydi.
    javob.hujjat_yoli = hujjat_xizmati.tahlil(matn)
    fon.add_task(statistikani_yoz, javob, rejim, x_foydalanuvchi_id, savol, "sayt")
    return javob


@app.post("/api/jarima", response_model=JarimaJavob)
def jarima_tekshiruvi(sorov: JarimaSorov, fon: BackgroundTasks,
                      x_foydalanuvchi_id: Optional[str] = Header(None)):
    """Jarima qarorini tekshiruv ro'yxati bo'yicha baholaydi.

    AI ishlatilmaydi: jarimaning taqdirini muddatlar hal qiladi va sanalar
    ayirmasini model taxmin qilishi mumkin emas. Shu sababli javob tez
    qaytadi va provayder ishlamay qolganda ham ishlayveradi.
    """
    javob = jarima_xizmati.jarimani_tekshir(sorov)
    fon.add_task(statistika.jarima_hisobla, javob.asoslar_soni, x_foydalanuvchi_id)
    return javob


@app.post("/api/jarima/rasm", response_model=JarimaRasmJavob)
async def jarima_rasmi(fon: BackgroundTasks, fayl: UploadFile = File(...),
                       x_foydalanuvchi_id: Optional[str] = Header(None)):
    """Jarima qarori rasmidan ma'lumotlarni o'qib, darhol tekshiradi.

    AI faqat MATNNI O'QIYDI — huquqiy xulosani arifmetik tekshiruvlar beradi.
    O'qilgan qiymatlar javobda qaytariladi va foydalanuvchi ularni tuzatishi
    mumkin: model sanani xato o'qisa, butun xulosa noto'g'ri bo'lardi.
    """
    bayt = await fayl.read()
    try:
        sorov = await asyncio.to_thread(
            jarima_xizmati.rasmdan_oqi, bayt, fayl.content_type or "image/jpeg"
        )
    except jarima_xizmati.RasmXato as e:
        raise HTTPException(status_code=422, detail=str(e))
    javob = jarima_xizmati.jarimani_tekshir(sorov)
    fon.add_task(statistika.jarima_hisobla, javob.asoslar_soni, x_foydalanuvchi_id)
    return JarimaRasmJavob(oqilgan=sorov, tekshiruv=javob)


@app.post("/api/jarima/radar", response_model=RadarJavob)
async def jarima_radari(fon: BackgroundTasks, fayl: UploadFile = File(...),
                        x_foydalanuvchi_id: Optional[str] = Header(None)):
    """Radar o'rnatilishi suratini YPX nizomi bo'yicha tekshiradi.

    AI faqat suratdagi holatni TASVIRLAYDI (patrul avtomobili bormi, odam
    formadami), huquqiy xulosani jarima moduli chiqaradi. Kuzatuv javobda
    qaytariladi — model xato ko'rsa, odam buni ko'rib tuzatishi mumkin.
    """
    bayt = await fayl.read()
    try:
        kuzatuv = await asyncio.to_thread(
            radar_xizmati.suratdan_kuzat, bayt, fayl.content_type or "image/jpeg"
        )
    except radar_xizmati.RadarXato as e:
        raise HTTPException(status_code=422, detail=str(e))
    sorov = radar_xizmati.kuzatuvni_sorovga(kuzatuv)
    javob = jarima_xizmati.jarimani_tekshir(sorov)
    fon.add_task(statistika.jarima_hisobla, javob.asoslar_soni, x_foydalanuvchi_id)
    return RadarJavob(
        kuzatuv=kuzatuv,
        tekshiruv=javob,
        dislokatsiya_sorovi=radar_xizmati.dislokatsiya_sorovi(kuzatuv),
    )


@app.post("/api/jarima/shikoyat", response_model=ArizaJavob)
def jarima_shikoyati(sorov: ShikoyatSorov):
    """Jarima qarori ustidan shikoyat qoralamasi.

    Asoslar tekshiruv natijasidan olinadi — odam ularni qaytadan yozmaydi.
    LLM ishlatilmaydi: matn qat'iy shablon va bazadagi modda raqamlari.
    """
    javob = jarima_xizmati.jarimani_tekshir(sorov.jarima)
    asoslar = [t.izoh for t in javob.tekshiruvlar if t.holat == "asos"]
    moddalar = [t.modda.model_dump() for t in javob.tekshiruvlar
                if t.holat == "asos" and t.modda]
    try:
        matn = ariza.shikoyat_tuz(
            fish=sorov.fish,
            qaror_raqami=sorov.jarima.qaror_raqami,
            qaror_sanasi=(sorov.jarima.qaror_sanasi.isoformat()
                          if sorov.jarima.qaror_sanasi else ""),
            qaror_organi=sorov.qaror_organi,
            asoslar=asoslar,
            moddalar=moddalar,
            summa=sorov.jarima.summa,
            tolangan=sorov.jarima.tolangan,
            manzil=sorov.manzil,
            telefon=sorov.telefon,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return ArizaJavob(matn=matn, fayl_nomi="shikoyat.txt")


@app.post("/api/shartnoma", response_model=ShartnomaJavob)
async def shartnoma_tahlili(
    fon: BackgroundTasks,
    fayl: UploadFile = File(...),
    x_foydalanuvchi_id: Optional[str] = Header(None),
):
    """Shartnomani band-band tahlil qiladi.

    /api/hujjat dan farqi — javob shakli: u yerda uch qismli javob (modda,
    tavsiya, organ), bu yerda esa bandlar ro'yxati va har biriga xavf bahosi.
    Shartnomada 8-10 ta muammoli band bo'lishi mumkin, ular uch qadamli
    tavsiyaga sig'maydi.
    """
    bayt = await fayl.read()
    if len(bayt) > MAX_HUJJAT_HAJMI:
        raise HTTPException(status_code=413, detail="Fayl hajmi 10 MB dan oshmasligi kerak")
    try:
        matn = documents.matn_ajrat(fayl.filename or "hujjat", bayt, fayl.content_type or "")
    except documents.HujjatXato as e:
        raise HTTPException(status_code=422, detail=str(e))
    try:
        javob = await asyncio.to_thread(shartnoma_xizmati.shartnomani_tahlil, matn)
    except (AiSozlanmagan, AiXato) as e:
        raise _http_xato(e)

    fon.add_task(statistika.shartnoma_hisobla, javob.shartnoma_turi, x_foydalanuvchi_id)
    return javob


@app.post("/api/ovoz", response_model=OvozJavob)
async def ovozni_matnga(fayl: UploadFile = File(...)):
    """Brauzerdan kelgan ovozni matnga o'giradi (Telegram bot bilan bir xil xizmat).

    Faqat transkript qaytariladi, javob emas: matn foydalanuvchiga ko'rsatiladi,
    u tuzatib yoki tasdiqlab o'zi /api/chat ga yuboradi. Bu shaffoflik nutq
    noto'g'ri tanilgan holatni ko'rinadigan qiladi.
    """
    if not ovoz.mavjud():
        raise HTTPException(status_code=503, detail="Ovozni matnga o'girish sozlanmagan")
    bayt = await fayl.read()
    if not bayt:
        raise HTTPException(status_code=422, detail="Ovozli xabar bo'sh")
    if len(bayt) > MAX_OVOZ_HAJMI:
        raise HTTPException(status_code=413, detail="Ovozli xabar hajmi juda katta")
    try:
        # Provayder so'rovi sinxron va sekin — event loop'ni qotirib qo'ymasin.
        matn = await asyncio.to_thread(
            ovoz.matnga_ogir, bayt, fayl.content_type or "audio/ogg"
        )
    except ovoz.OvozXato as e:
        raise HTTPException(status_code=422, detail=str(e))
    return OvozJavob(matn=matn.strip())


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


@app.get("/api/admin/telegram")
async def admin_telegram_holati(x_admin_parol: Optional[str] = Header(None)):
    """Webhook haqiqatan o'rnatilganmi va Telegram xato qaytaryaptimi.

    Bot javob bermaganda birinchi shu yerga qaraladi:
    `pending_update_count` — navbatda turgan (yetkazilmagan) savollar soni,
    `last_error_message` — Telegram webhook'ga yetkaza olmagan oxirgi sabab.
    api.telegram.org ba'zi tarmoqlardan ochilmaydi, shuning uchun so'rov
    serverning o'zidan yuboriladi.
    """
    _admin_tekshir(x_admin_parol)
    if not telegram_bot.mavjud():
        raise HTTPException(status_code=404, detail="Bot sozlanmagan")
    try:
        holat_obyekti = await telegram_bot.bot().get_webhook_info()
    except Exception as e:
        # Sabab odatda tarmoq yoki noto'g'ri token — admin uni ko'rishi kerak.
        raise HTTPException(status_code=502, detail=f"Telegram javob bermadi: {e}")
    malumot = holat_obyekti.model_dump(mode="json")
    malumot["kutilgan_url"] = (
        TELEGRAM_WEBHOOK_URL.rstrip("/") + WEBHOOK_YOLI if TELEGRAM_WEBHOOK_URL else ""
    )
    malumot["sir_yoqilgan"] = bool(TELEGRAM_WEBHOOK_SECRET)
    return malumot


# ---------- Telegram webhook ----------

async def _updateni_qayta_ishla(malumot: dict) -> None:
    from aiogram.types import Update

    try:
        await telegram_bot.dispatcher().feed_update(
            telegram_bot.bot(), Update.model_validate(malumot)
        )
    except Exception:
        log.exception("Telegram update'ini qayta ishlashda xato")


@app.post(WEBHOOK_YOLI, include_in_schema=False)
async def telegram_webhook(
    sorov: Request,
    x_telegram_bot_api_secret_token: Optional[str] = Header(None),
):
    """Telegram'dan kelgan update.

    Javob DARHOL qaytariladi: savolga javob tayyorlash 10-15 soniya davom
    etadi, Telegram esa javob kechiksa o'sha update'ni qayta yuboradi va
    foydalanuvchi bir savolga bir necha javob oladi.
    """
    if not telegram_bot.mavjud():
        raise HTTPException(status_code=404, detail="Bot sozlanmagan")
    if TELEGRAM_WEBHOOK_SECRET and not (
        x_telegram_bot_api_secret_token
        and secrets.compare_digest(x_telegram_bot_api_secret_token, TELEGRAM_WEBHOOK_SECRET)
    ):
        raise HTTPException(status_code=403, detail="Noto'g'ri webhook siri")

    malumot = await sorov.json()
    if telegram_bot.takroriy_update(malumot.get("update_id")):
        return {"ok": True}

    vazifa = asyncio.create_task(_updateni_qayta_ishla(malumot))
    _fon_vazifalari.add(vazifa)
    vazifa.add_done_callback(_fon_vazifalari.discard)
    return {"ok": True}


# ---------- Statik sahifalar ----------

@app.get("/", include_in_schema=False)
def bosh_sahifa():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/admin", include_in_schema=False)
def admin_sahifa():
    return FileResponse(STATIC_DIR / "admin.html")


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
