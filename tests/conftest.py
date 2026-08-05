# Testlar uchun umumiy sozlama.
#
# app.config `.env` faylini o'qiydi, ya'ni ishlab chiquvchining mashinasida
# haqiqiy kalitlar test paytida ham ko'rinadi. Ovozli javob (TTS) yoqib
# qo'yilgan bo'lsa, bot oqimi testlari jimgina Gemini'ga so'rov yuborib,
# testlarni tarmoqqa bog'lab qo'yadi. Shuning uchun TTS hamma testda
# o'chirilgan holatda boshlanadi — kerak bo'lgan test uni o'zi yoqadi.
import pytest

from app.services import ovoz


@pytest.fixture(autouse=True)
def _tts_ochiq_holatda():
    asl = ovoz.TTS_PROVAYDER
    ovoz.TTS_PROVAYDER = "yoq"
    yield
    ovoz.TTS_PROVAYDER = asl
