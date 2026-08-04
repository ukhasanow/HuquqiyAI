# Lokal ishlab chiqish uchun: python -m app.bot.polling
#
# Produksiyada webhook ishlatiladi (app/main.py dagi /telegram/webhook).
# Polling'ni webhook o'rnatilgan bot uchun ishga tushirib bo'lmaydi, shuning
# uchun boshlashdan oldin webhook olib tashlanadi.
import asyncio
import logging

from . import bot, buyruqlarni_ornat, dispatcher, mavjud


async def asosiy() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if not mavjud():
        raise SystemExit("TELEGRAM_BOT_TOKEN berilmagan (.env faylini tekshiring)")

    b = bot()
    men = await b.get_me()
    await b.delete_webhook(drop_pending_updates=True)
    await buyruqlarni_ornat()
    logging.info("Polling boshlandi: @%s", men.username)
    try:
        await dispatcher().start_polling(b)
    finally:
        await b.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(asosiy())
    except KeyboardInterrupt:
        pass
