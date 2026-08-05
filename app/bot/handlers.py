# Telegram bot handler'lari.
#
# Bu yerda huquqiy mantiq YO'Q: barcha javoblar services/javob.py orqali
# olinadi — sayt ham aynan o'sha modulni chaqiradi.
import asyncio
import html
import logging
from typing import List, Optional

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from .. import storage
from ..config import MAX_HUJJAT_HAJMI, MAX_OVOZ_DAVOMIYLIGI, MAX_OVOZ_HAJMI
from ..services import ariza as ariza_xizmati
from ..services import documents, ovoz
from ..services.javob import (
    AiSozlanmagan,
    AiXato,
    javob_ol,
    ovozli_javobni_yoz,
    statistikani_yoz,
    uch_qismli_javob,
)
from . import formatlash, holat

log = logging.getLogger(__name__)
router = Router()

SALOM = (
    "Assalomu alaykum! Men <b>HuquqiyAI</b> — O'zbekiston qonunchiligi bo'yicha yordamchiman.\n\n"
    "Savolingizni oddiy so'zlar bilan yozing, men sizga:\n"
    "1️⃣ qonunning <b>asl moddasini</b> (o'zgartirmasdan, lex.uz havolasi bilan)\n"
    "2️⃣ amaliy tavsiya\n"
    "3️⃣ qaysi organga murojaat qilishni — aytaman.\n\n"
    "📄 PDF/DOCX hujjat yuborsangiz, uni tahlil qilaman.\n\n"
    "<i>Masalan: «Ish haqimni 2 oydan beri bermayapti, nima qilay?»</i>"
)

YORDAM = (
    "<b>Nima qila olaman</b>\n\n"
    "• Savolingizni yozing — qonun moddasi, tavsiya va murojaat organi bilan javob beraman\n"
    "• 🎤 Ovozli xabar yuboring — tinglab, matnga o'girib javob beraman\n"
    "• 📄 PDF, DOCX yoki TXT hujjat yuboring — huquqiy tahlil qilaman\n"
    "• Javobdan keyin «Ariza tayyorlash» tugmasi chiqadi\n\n"
    "<b>Buyruqlar</b>\n"
    "/rejim — javob uslubi: <b>oddiy</b> (sodda til) yoki <b>pro</b> (protsessual tafsilotlar)\n"
    "/ovoz — javobni ovozli ham yuborish sozlamasi\n"
    "/yordam — shu xabar\n\n"
    "⚠️ <i>Bergan ma'lumotim tanishtiruv xarakteriga ega va professional huquqiy "
    "maslahat o'rnini bosmaydi. Rasmiy manba — lex.uz</i>"
)

BAND_XABARI = "⏳ Oldingi savolingiz ustida ishlayapman — javobni kuting."
# Batafsil javob ~20 soniya oladi. Kutish muddatini oldindan aytish kerak:
# aks holda odam bot ishlamayapti deb o'ylab, savolni qayta yuboraveradi.
KUTING = "🔎 Qonun bazasidan qidiryapman va javob tayyorlayapman — 20-30 soniya oling..."


class ArizaHolati(StatesGroup):
    fish = State()
    manzil = State()
    telefon = State()


# ---------- Yordamchi ----------

def _rejim_tugmalari(joriy: str) -> InlineKeyboardMarkup:
    def belgi(r):
        return ("✅ " if r == joriy else "") + r
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=belgi("oddiy"), callback_data="rejim:oddiy"),
        InlineKeyboardButton(text=belgi("pro"), callback_data="rejim:pro"),
    ]])


def _modda_tugmasi(modda: dict) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔗 lex.uz'da ochish", url=modda["lex_url"])
    ]])


def _javob_tugmalari(kalit: str, moddalar_soni: int) -> InlineKeyboardMarkup:
    """Asosiy javob ostidagi tugmalar.

    Qonun moddalari tugma ortida turadi: ular javobning ishonch asosi, lekin
    ko'pchilik odam avval "menga nima qilish kerak" degan savolga javob oladi
    va faqat kerak bo'lganda asl matnni ochadi.
    """
    qatorlar = []
    if moddalar_soni:
        qatorlar.append([InlineKeyboardButton(
            text=f"📖 Qonun moddalari ({moddalar_soni})",
            callback_data=f"moddalar:{kalit}",
        )])
    qatorlar.append([InlineKeyboardButton(
        text="📄 Ariza tayyorlash", callback_data=f"ariza:{kalit}"
    )])
    return InlineKeyboardMarkup(inline_keyboard=qatorlar)


def _ovoz_tugmalari(joriy: str) -> InlineKeyboardMarkup:
    nomlar = {"avto": "Avto", "doim": "Doim", "yoq": "O'chiq"}
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=("✅ " if tanlov == joriy else "") + nomlar[tanlov],
            callback_data=f"ovoz:{tanlov}",
        )
        for tanlov in holat.OVOZ_TANLOVLARI
    ]])


async def _yubor(xabar: Message, bolaklar: List[str], klaviatura=None) -> None:
    """Bo'laklarni ketma-ket yuboradi; klaviatura oxirgisiga qo'shiladi."""
    for i, bolak in enumerate(bolaklar):
        await xabar.answer(
            bolak,
            reply_markup=klaviatura if i == len(bolaklar) - 1 else None,
            disable_web_page_preview=True,
        )


async def _javobni_yubor(xabar: Message, javob, savol: str) -> None:
    """Javobni suhbat ko'rinishida yuboradi — bitta xabar va tugmalar.

    Ilgari har modda alohida xabar bo'lib, bitta savolga 5-6 ta xabar ketardi.
    Endi odam bir xabarda to'liq javobni oladi, qonun matnini esa "Qonun
    moddalari" tugmasi orqali ochadi.
    """
    if not javob.javob_topildi:
        await _yubor(xabar, formatlash.topilmadi_xabari(javob))
        return

    kalit = holat.javobni_saqla(xabar.chat.id, savol, javob)
    await _yubor(
        xabar,
        formatlash.asosiy_javob_xabari(javob),
        _javob_tugmalari(kalit, len(javob.moddalar)),
    )


async def _moddalarni_yubor(xabar: Message, moddalar: List[dict]) -> None:
    """Qonun moddalari — har biri o'z xabarida, lex.uz tugmasi bilan.

    Modda matni QISQARTIRILMAYDI: qonunning asl matni loyihaning asosiy
    va'dasi. Uzuni xatboshi chegarasi bo'yicha bo'linadi.
    """
    for modda in moddalar:
        bolaklar = formatlash.modda_xabari(modda)
        for i, bolak in enumerate(bolaklar):
            await xabar.answer(
                bolak,
                reply_markup=_modda_tugmasi(modda) if i == len(bolaklar) - 1 else None,
                disable_web_page_preview=True,
            )


async def _ovozli_javob_yubor(xabar: Message, javob) -> None:
    """Tavsiya qismini ovozga o'girib yuboradi.

    Ovozga FAQAT tavsiya tushadi: modda matnlari uzun va quloqqa quruq, ularni
    o'qib berish audio'ni bir necha daqiqaga cho'zadi. Matnli javob esa doim
    to'liq yuboriladi — ovoz uning o'rnini emas, qo'shimchasini bajaradi.

    Bu yerdagi har qanday xato yutiladi: TTS ishlamay qolgani foydalanuvchini
    javobsiz qoldirmasligi kerak.
    """
    matn = (javob.tavsiya or "").strip() or (javob.xulosa or "").strip()
    if not matn or not ovoz.tts_mavjud():
        return
    try:
        bayt, mime = await asyncio.to_thread(ovoz.ovozga_ogir, matn)
        # sendVoice faqat OGG/Opus qabul qiladi, bizda esa WAV (ffmpeg yo'q) —
        # shuning uchun audio fayl sifatida yuboriladi.
        kengaytma = "ogg" if "ogg" in mime else "wav"
        await xabar.answer_audio(
            BufferedInputFile(bayt, filename=f"javob.{kengaytma}"),
            title="Tavsiya (ovozli)",
            caption="🔊 Tavsiyaning ovozli varianti",
        )
        await asyncio.to_thread(ovozli_javobni_yoz)
    except Exception:
        log.exception("Ovozli javob yuborilmadi (chat_id=%s)", xabar.chat.id)


async def _savolga_javob_ber(
    xabar: Message,
    savol: str,
    hujjat_matni: Optional[str] = None,
    ovozli: bool = False,
) -> None:
    """Umumiy oqim: cheklov -> "band" belgisi -> javob -> statistika.

    javob_ol/uch_qismli_javob sinxron va sekin (~10-15s). Ular to'g'ridan-to'g'ri
    chaqirilsa butun event loop (bot ham, sayt ham) shu vaqt davomida qotib
    qoladi — shuning uchun alohida oqimda bajariladi.

    Botda javob HAR DOIM batafsil rejimda so'raladi: bu yerda ekran cheklovi
    yo'q va foydalanuvchi to'liq tushuntirishni kutadi.
    """
    id_ = xabar.chat.id
    ruxsat, kutish = holat.cheklovdan_otdi(id_)
    if not ruxsat:
        await xabar.answer(
            f"⏳ Juda ko'p so'rov yubordingiz. Iltimos, {kutish // 60 + 1} daqiqadan so'ng urinib ko'ring."
        )
        return
    if not holat.band_qil(id_):
        await xabar.answer(BAND_XABARI)
        return

    rejim = holat.rejim(id_)
    kutish_xabari = await xabar.answer(KUTING)
    try:
        await xabar.bot.send_chat_action(chat_id=id_, action="typing")
        if hujjat_matni is None:
            javob = await asyncio.to_thread(javob_ol, savol, rejim, None, True)
        else:
            javob = await asyncio.to_thread(
                uch_qismli_javob, savol, rejim, None, hujjat_matni, True
            )
    except (AiSozlanmagan, AiXato) as e:
        await xabar.answer(f"⚠️ {e.foydalanuvchi_matni}")
        return
    except Exception:
        log.exception("Kutilmagan xato (chat_id=%s)", id_)
        await xabar.answer("⚠️ Kutilmagan xatolik yuz berdi. Qaytadan urinib ko'ring.")
        return
    finally:
        holat.bandni_bosat(id_)
        try:
            await kutish_xabari.delete()
        except Exception:
            pass  # xabar allaqachon o'chirilgan bo'lishi mumkin

    await _javobni_yubor(xabar, javob, savol)
    if javob.javob_topildi and holat.ovoz_kerakmi(id_, ovozli):
        await _ovozli_javob_yubor(xabar, javob)
    await asyncio.to_thread(
        statistikani_yoz, javob, rejim, f"tg:{id_}", savol, "bot", ovozli
    )


# ---------- Buyruqlar ----------

@router.message(CommandStart())
async def start(xabar: Message, state: FSMContext) -> None:
    await state.clear()
    await xabar.answer(SALOM, disable_web_page_preview=True)


@router.message(Command("yordam", "help"))
async def yordam(xabar: Message) -> None:
    await xabar.answer(YORDAM, disable_web_page_preview=True)


@router.message(Command("rejim"))
async def rejim_buyrugi(xabar: Message) -> None:
    joriy = holat.rejim(xabar.chat.id)
    await xabar.answer(
        "Javob uslubini tanlang:\n\n"
        "<b>oddiy</b> — sodda til, kundalik savollar uchun\n"
        "<b>pro</b> — protsessual tafsilotlar, muddatlar va hujjatlar",
        reply_markup=_rejim_tugmalari(joriy),
    )


@router.callback_query(F.data.startswith("rejim:"))
async def rejim_tanlandi(soro: CallbackQuery) -> None:
    yangi = holat.rejim_belgila(soro.message.chat.id, soro.data.split(":", 1)[1])
    await soro.message.edit_reply_markup(reply_markup=_rejim_tugmalari(yangi))
    await soro.answer(f"Rejim: {yangi}")


@router.message(Command("ovoz"))
async def ovoz_buyrugi(xabar: Message) -> None:
    if not ovoz.tts_mavjud():
        await xabar.answer(
            "🔊 Ovozli javob bu serverda sozlanmagan — javoblar faqat matn bilan keladi."
        )
        return
    await xabar.answer(
        "Ovozli javobni qachon yuboray?\n\n"
        "<b>Avto</b> — ovozli savolga ovozli javob (standart)\n"
        "<b>Doim</b> — har javobga ovoz qo'shiladi\n"
        "<b>O'chiq</b> — faqat matn\n\n"
        "<i>Ovozga tavsiya qismi tushadi; qonun moddalari doim matn bilan keladi.</i>",
        reply_markup=_ovoz_tugmalari(holat.ovoz_sozlamasi(xabar.chat.id)),
    )


@router.callback_query(F.data.startswith("ovoz:"))
async def ovoz_tanlandi(soro: CallbackQuery) -> None:
    yangi = holat.ovoz_belgila(soro.message.chat.id, soro.data.split(":", 1)[1])
    await soro.message.edit_reply_markup(reply_markup=_ovoz_tugmalari(yangi))
    await soro.answer(f"Ovozli javob: {yangi}")


# ---------- Qonun moddalarini ochish ----------

ESKI_JAVOB = (
    "Bu javob eskirdi — savolni qaytadan bering, moddalarni yangi javobdan ochasiz."
)


@router.callback_query(F.data.startswith("moddalar:"))
async def moddalarni_korsat(soro: CallbackQuery) -> None:
    malumot = holat.javob_malumoti(soro.data.split(":", 1)[1])
    if not malumot:
        await soro.answer(ESKI_JAVOB, show_alert=True)
        return
    moddalar = [m for mid in malumot["modda_idlari"] if (m := storage.modda_top(mid))]
    if not moddalar:
        await soro.answer("Moddalar topilmadi.", show_alert=True)
        return
    await soro.answer()
    await _moddalarni_yubor(soro.message, moddalar)


# ---------- Ariza (dialog) ----------

@router.callback_query(F.data.startswith("ariza:"))
async def ariza_boshla(soro: CallbackQuery, state: FSMContext) -> None:
    kalit = soro.data.split(":", 1)[1]
    malumot = holat.javob_malumoti(kalit)
    if not malumot or not malumot["modda_idlari"]:
        await soro.answer(ESKI_JAVOB, show_alert=True)
        return
    await state.set_state(ArizaHolati.fish)
    await state.update_data(javob_kaliti=kalit)
    await soro.message.answer(
        "📄 <b>Ariza tayyorlash</b>\n\nTo'liq familiya, ism va otangizning ismini yozing.\n\n"
        "<i>Bekor qilish uchun: /start</i>"
    )
    await soro.answer()


@router.message(ArizaHolati.fish)
async def ariza_fish(xabar: Message, state: FSMContext) -> None:
    fish = (xabar.text or "").strip()
    if len(fish) < 3:
        await xabar.answer("To'liq familiya, ism va otangizning ismini yozing.")
        return
    await state.update_data(fish=fish)
    await state.set_state(ArizaHolati.manzil)
    await xabar.answer("Yashash manzilingiz? (yo'q bo'lsa «-» yuboring)")


@router.message(ArizaHolati.manzil)
async def ariza_manzil(xabar: Message, state: FSMContext) -> None:
    manzil = (xabar.text or "").strip()
    await state.update_data(manzil="" if manzil == "-" else manzil)
    await state.set_state(ArizaHolati.telefon)
    await xabar.answer("Telefon raqamingiz? (yo'q bo'lsa «-» yuboring)")


@router.message(ArizaHolati.telefon)
async def ariza_telefon(xabar: Message, state: FSMContext) -> None:
    telefon = (xabar.text or "").strip()
    malumot = await state.get_data()
    await state.clear()

    oxirgi = holat.javob_malumoti(malumot.get("javob_kaliti", ""))
    if not oxirgi:
        await xabar.answer("Javob ma'lumoti topilmadi. Savolni qaytadan bering.")
        return

    moddalar = [m for mid in oxirgi["modda_idlari"] if (m := storage.modda_top(mid))]
    organ = storage.organ_top(oxirgi["murojaat_mavzusi"])
    if not moddalar or not organ:
        await xabar.answer("Ariza uchun modda yoki organ topilmadi.")
        return

    try:
        matn = ariza_xizmati.ariza_tuz(
            fish=malumot.get("fish", ""),
            vaziyat=oxirgi["savol"],
            moddalar=moddalar,
            organ=organ,
            manzil=malumot.get("manzil", ""),
            telefon="" if telefon == "-" else telefon,
        )
    except ValueError as e:
        await xabar.answer(f"⚠️ {e}")
        return

    await xabar.answer_document(
        BufferedInputFile(matn.encode("utf-8"), filename="ariza.txt"),
        caption=(
            "📄 Ariza qoralamasi tayyor.\n\n"
            "<b>Yuborishdan oldin:</b> vaziyat bayonini o'zingiz to'ldiring, "
            "sana va imzo qo'ying, kerakli hujjat nusxalarini ilova qiling."
        ),
    )


# ---------- Hujjat ----------

@router.message(F.document)
async def hujjat(xabar: Message) -> None:
    hujjat_fayl = xabar.document
    if hujjat_fayl.file_size and hujjat_fayl.file_size > MAX_HUJJAT_HAJMI:
        await xabar.answer("⚠️ Fayl hajmi 10 MB dan oshmasligi kerak.")
        return

    await xabar.bot.send_chat_action(chat_id=xabar.chat.id, action="typing")
    try:
        buffer = await xabar.bot.download(hujjat_fayl)
        matn = documents.matn_ajrat(hujjat_fayl.file_name or "hujjat", buffer.read())
    except documents.HujjatXato as e:
        await xabar.answer(f"⚠️ {e}")
        return
    except Exception:
        log.exception("Hujjatni yuklab bo'lmadi (chat_id=%s)", xabar.chat.id)
        await xabar.answer("⚠️ Faylni yuklab bo'lmadi. Qaytadan urinib ko'ring.")
        return

    savol = (xabar.caption or "").strip()
    await _savolga_javob_ber(xabar, savol, hujjat_matni=matn)


# ---------- Ovozli xabar ----------

@router.message(F.voice | F.audio)
async def ovozli_xabar(xabar: Message) -> None:
    """Ovozli xabar -> transkript -> odatdagi javob oqimi.

    Transkript foydalanuvchiga KO'RSATILADI: nutq noto'g'ri tanilgan bo'lsa,
    u buni javobdan oldin ko'rib, savolini qayta yozishi mumkin.
    """
    ovoz_fayl = xabar.voice or xabar.audio
    if not ovoz.mavjud():
        await xabar.answer(
            "🎤 Ovozli xabarlarni qayta ishlash hozircha sozlanmagan. "
            "Savolingizni matn bilan yozing."
        )
        return
    if ovoz_fayl.duration and ovoz_fayl.duration > MAX_OVOZ_DAVOMIYLIGI:
        await xabar.answer(
            f"🎤 Ovozli xabar juda uzun ({ovoz_fayl.duration} soniya). "
            f"Iltimos, {MAX_OVOZ_DAVOMIYLIGI} soniyagacha yozing yoki matn bilan yuboring."
        )
        return
    if ovoz_fayl.file_size and ovoz_fayl.file_size > MAX_OVOZ_HAJMI:
        await xabar.answer("🎤 Ovozli xabar hajmi juda katta.")
        return

    holati = await xabar.answer("🎧 Ovozli xabaringizni tinglayapman...")
    try:
        await xabar.bot.send_chat_action(chat_id=xabar.chat.id, action="typing")
        buffer = await xabar.bot.download(ovoz_fayl)
        matn = await asyncio.to_thread(
            ovoz.matnga_ogir, buffer.read(), ovoz_fayl.mime_type or "audio/ogg"
        )
    except ovoz.OvozXato as e:
        await xabar.answer(f"⚠️ {e}")
        return
    except Exception:
        log.exception("Ovozli xabarni o'girib bo'lmadi (chat_id=%s)", xabar.chat.id)
        await xabar.answer(
            "⚠️ Ovozli xabarni o'qib bo'lmadi. Savolingizni matn bilan yozib ko'ring."
        )
        return
    finally:
        try:
            await holati.delete()
        except Exception:
            pass

    matn = (matn or "").strip()
    if len(matn) < 3:
        await xabar.answer(
            "🎤 Ovozli xabardan savolni ajratib bo'lmadi. Shovqinsiz joyda qaytadan "
            "yozib yuboring yoki savolni matn bilan yozing."
        )
        return

    await xabar.answer(f"🎤 <b>Savolingiz:</b>\n<i>{html.escape(matn)}</i>")
    await _savolga_javob_ber(xabar, matn, ovozli=True)


# ---------- Oddiy matn ----------

@router.message(F.text.startswith("/"))
async def notanish_buyruq(xabar: Message) -> None:
    """Ro'yxatda yo'q buyruq.

    Bu handler umumiy matn handleridan OLDIN turishi shart: aks holda "/ovozz"
    kabi xato yozilgan buyruq huquqiy savol sifatida AI'ga yuboriladi va
    foydalanuvchi 20 soniya kutib, mutlaqo aloqasiz javob oladi.
    """
    await xabar.answer(
        "Bunday buyruq yo'q. Mavjud buyruqlar:\n"
        "/rejim — javob uslubi\n"
        "/ovoz — ovozli javob sozlamasi\n"
        "/yordam — nima qila olaman\n\n"
        "Savolingizni oddiy matn bilan yozsangiz ham bo'ladi."
    )


@router.message(F.text)
async def savol(xabar: Message) -> None:
    matn = (xabar.text or "").strip()
    if len(matn) < 3:
        await xabar.answer("Savolingizni biroz batafsilroq yozing.")
        return
    if len(matn) > 4000:
        await xabar.answer("Savol juda uzun. Iltimos, qisqaroq yozing (4000 belgigacha).")
        return
    await _savolga_javob_ber(xabar, matn)
