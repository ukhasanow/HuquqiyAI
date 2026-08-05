# Telegram bot obyektlari.
#
# Bot faqat TELEGRAM_BOT_TOKEN berilgan bo'lsa yaratiladi: token qo'yilmagan
# muhitda (masalan, faqat sayt ishlatiladigan deploy'da) ilova oldingidek
# ishlashi kerak, bot yo'qligi xato emas.
from typing import Optional

from ..config import TELEGRAM_BOT_TOKEN

_bot = None
_dispatcher = None

# Telegram javob olmasa (yoki kech olsa) o'sha update'ni qayta yuboradi.
# Bir savolga ikki marta javob bermaslik uchun yaqinda ko'rilganlari eslanadi.
_korilgan_update_idlar: set = set()
_KORILGAN_CHEGARA = 1000


def mavjud() -> bool:
    return bool(TELEGRAM_BOT_TOKEN)


def bot():
    """Bot obyekti (birinchi chaqiruvda yaratiladi)."""
    global _bot
    if _bot is None:
        if not mavjud():
            raise RuntimeError("TELEGRAM_BOT_TOKEN berilmagan")
        from aiogram import Bot
        from aiogram.client.default import DefaultBotProperties

        # parse_mode markazlashgan holda belgilanadi: handler'lar har xabarda
        # takrorlamasin va biror joyda unutilib qolmasin.
        _bot = Bot(token=TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    return _bot


def dispatcher():
    global _dispatcher
    if _dispatcher is None:
        from aiogram import Dispatcher
        from aiogram.fsm.storage.memory import MemoryStorage

        from .handlers import router

        _dispatcher = Dispatcher(storage=MemoryStorage())
        _dispatcher.include_router(router)
    return _dispatcher


def takroriy_update(update_id: Optional[int]) -> bool:
    """Shu update allaqachon qabul qilinganmi."""
    if update_id is None:
        return False
    if update_id in _korilgan_update_idlar:
        return True
    _korilgan_update_idlar.add(update_id)
    if len(_korilgan_update_idlar) > _KORILGAN_CHEGARA:
        # Eng kichik yarmini tashlaymiz: update_id o'sib boradi, shuning uchun
        # kichiklari eng eski hisoblanadi.
        for eski in sorted(_korilgan_update_idlar)[: _KORILGAN_CHEGARA // 2]:
            _korilgan_update_idlar.discard(eski)
    return False


async def buyruqlarni_ornat() -> None:
    """Telegram'dagi buyruqlar menyusi (xabar maydonidagi «/» tugmasi)."""
    from aiogram.types import BotCommand

    await bot().set_my_commands([
        BotCommand(command="start", description="Boshlash"),
        BotCommand(command="rejim", description="Javob uslubi: oddiy yoki pro"),
        BotCommand(command="ovoz", description="Ovozli javob sozlamasi"),
        BotCommand(command="yordam", description="Nima qila olaman"),
    ])


async def yopish() -> None:
    global _bot
    if _bot is not None:
        await _bot.session.close()
        _bot = None
