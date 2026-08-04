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
    "• 📄 PDF, DOCX yoki TXT hujjat yuboring — huquqiy tahlil qilaman\n"
    "• Javobdan keyin «Ariza tayyorlash» tugmasi chiqadi\n\n"
    "<b>Buyruqlar</b>\n"
    "/rejim — javob uslubi: <b>oddiy</b> (sodda til) yoki <b>pro</b> (protsessual tafsilotlar)\n"
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


def _ariza_tugmasi() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="📄 Ariza tayyorlash", callback_data="ariza:boshla")
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
    if not javob.javob_topildi:
        await _yubor(xabar, formatlash.topilmadi_xabari(javob))
        return

    # Avval umumiy xulosa: odam "menda ahvol qanday?" degan savolga javobni
    # uzun modda matnlarini o'qimasdan oldin oladi.
    xulosa = formatlash.xulosa_xabari(javob)
    if xulosa:
        await _yubor(xabar, xulosa)

    for modda in javob.moddalar:
        bolaklar = formatlash.modda_xabari(modda.model_dump())
        for i, bolak in enumerate(bolaklar):
            await xabar.answer(
                bolak,
                reply_markup=_modda_tugmasi(modda.model_dump()) if i == len(bolaklar) - 1 else None,
                disable_web_page_preview=True,
            )

    holat.javobni_saqla(xabar.chat.id, savol, javob)
    await _yubor(xabar, formatlash.tavsiya_xabari(javob), _ariza_tugmasi())


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


# ---------- Ariza (dialog) ----------

@router.callback_query(F.data == "ariza:boshla")
async def ariza_boshla(soro: CallbackQuery, state: FSMContext) -> None:
    oxirgi = holat.oxirgi_javob(soro.message.chat.id)
    if not oxirgi or not oxirgi["modda_idlari"]:
        await soro.answer("Avval savol bering — ariza javobdagi moddalar asosida tuziladi.", show_alert=True)
        return
    await state.set_state(ArizaHolati.fish)
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

    oxirgi = holat.oxirgi_javob(xabar.chat.id)
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
