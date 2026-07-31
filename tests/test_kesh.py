# Javob keshi testlari (LLM'siz).
import time

import pytest

from app import storage
from app.services import kesh


@pytest.fixture(autouse=True)
def _toza():
    kesh.tozala()
    yield
    kesh.tozala()


def _kalit(savol, rejim="oddiy"):
    return kesh.kalit(savol, rejim, storage.versiya())


def test_qoyilgan_javob_qaytadi():
    k = _kalit("Aliment to'lamayapti")
    kesh.qoy(k, "javob-1")
    assert kesh.ol(k) == "javob-1"


def test_yozuv_yoq_bolsa_none():
    assert kesh.ol(_kalit("hech qachon so'ralmagan savol")) is None


def test_yozuv_farqlari_ahamiyatsiz():
    """Bir xil savolning turli yozilishi bitta yozuvga tushishi kerak —
    aks holda kesh deyarli hech qachon ishlamaydi."""
    kesh.qoy(_kalit("Aliment to'lamayapti"), "javob")
    for shakl in [
        "aliment tolamayapti",
        "ALIMENT TO'LAMAYAPTI",
        "aliment  to‘lamayapti!!!",
        "Алимент тўламаяпти",
    ]:
        assert kesh.ol(_kalit(shakl)) == "javob", shakl


def test_mazmuni_boshqa_savollar_toqnashmaydi():
    """Kesh kaliti ma'noni o'zgartiradigan farqlarni saqlashi SHART —
    aks holda foydalanuvchi boshqa savolning javobini oladi."""
    kesh.qoy(_kalit("Ish haqim 3 oydan beri tolanmayapti"), "uch-oy")
    assert kesh.ol(_kalit("Ish haqim 5 oydan beri tolanmayapti")) is None

    kesh.qoy(_kalit("men uni urdim"), "men-urdim")
    assert kesh.ol(_kalit("u meni urdi")) is None


def test_rejim_alohida_keshlanadi():
    kesh.qoy(_kalit("Aliment to'lamayapti", "oddiy"), "oddiy-javob")
    assert kesh.ol(_kalit("Aliment to'lamayapti", "pro")) is None


def test_baza_ozgarsa_kesh_bekor_boladi():
    """Admin modda tahrirlasa eskirgan javob qaytmasligi kerak."""
    k_eski = kesh.kalit("Aliment to'lamayapti", "oddiy", "versiya-1")
    kesh.qoy(k_eski, "eski-javob")
    k_yangi = kesh.kalit("Aliment to'lamayapti", "oddiy", "versiya-2")
    assert kesh.ol(k_yangi) is None


def test_muddat_otgach_bekor_boladi(monkeypatch):
    monkeypatch.setattr(kesh, "MUDDAT", 0.05)
    k = _kalit("Aliment to'lamayapti")
    kesh.qoy(k, "javob")
    time.sleep(0.1)
    assert kesh.ol(k) is None


def test_bosh_savol_keshlanmaydi():
    assert kesh.kalit("!!! ???", "oddiy", "v1") is None
    assert kesh.ol(None) is None
    kesh.qoy(None, "javob")  # yiqilmasligi kerak


def test_chegaradan_oshsa_eng_eskisi_chiqariladi():
    monkeypatch_max = kesh.MAX_YOZUV
    for i in range(monkeypatch_max + 10):
        kesh.qoy(kesh.kalit(f"savol raqam {i}", "oddiy", "v1"), i)
    assert kesh.holat()["yozuvlar"] == monkeypatch_max
    assert kesh.ol(kesh.kalit("savol raqam 0", "oddiy", "v1")) is None
