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


# ---------- Tashqi qavat (Upstash) ----------
#
# Bu testlar tarmoqqa CHIQMAYDI: httpx chaqiruvlari almashtiriladi. Maqsad —
# qavatlar orasidagi mantiq to'g'riligini tekshirish, Upstash'ni emas.

from app.models import ChatJavob  # noqa: E402


def _javob(tavsiya="test tavsiya"):
    return ChatJavob(javob_topildi=True, moddalar=[], tavsiya=tavsiya,
                     murojaat_mavzusi="mehnat")


def test_kv_ochiq_bolmasa_tarmoqqa_chiqilmaydi(monkeypatch):
    """Ombor sozlanmagan bo'lsa kesh oddiy xotira keshi bo'lib qolishi kerak."""
    monkeypatch.setattr(kesh, "STATISTIKA_KV_URL", "")
    monkeypatch.setattr(kesh, "STATISTIKA_KV_TOKEN", "")
    monkeypatch.setattr(kesh.httpx, "get", _portlaydi)
    monkeypatch.setattr(kesh.httpx, "post", _portlaydi)
    k = _kalit("kv yo'q")
    kesh.qoy(k, _javob())
    assert kesh.ol(k).tavsiya == "test tavsiya"


def _portlaydi(*a, **k):
    raise AssertionError("tarmoqqa chiqildi")


def test_xotirada_bolsa_omborga_borilmaydi(monkeypatch):
    """Xotira birinchi qavat: tarmoq so'rovi javobga kechikish qo'shmasin."""
    monkeypatch.setattr(kesh, "STATISTIKA_KV_URL", "https://misol")
    monkeypatch.setattr(kesh, "STATISTIKA_KV_TOKEN", "t")
    monkeypatch.setattr(kesh.httpx, "post", lambda *a, **k: _SoxtaJavob({}))
    k = _kalit("xotirada bor")
    kesh.qoy(k, _javob())
    monkeypatch.setattr(kesh.httpx, "get", _portlaydi)  # endi tegilmasligi kerak
    assert kesh.ol(k) is not None


class _SoxtaJavob:
    def __init__(self, malumot, xato=False):
        self._m = malumot
        self._xato = xato

    def raise_for_status(self):
        if self._xato:
            raise RuntimeError("500")

    def json(self):
        return self._m


def test_qayta_ishga_tushgandan_keyin_ombordan_tiklanadi(monkeypatch):
    """Asosiy maqsad: Render uxlab-uyg'onganda isitilgan kesh yo'qolmasin."""
    monkeypatch.setattr(kesh, "STATISTIKA_KV_URL", "https://misol")
    monkeypatch.setattr(kesh, "STATISTIKA_KV_TOKEN", "t")
    saqlangan = {}

    def soxta_post(url, **kw):
        saqlangan[url.split("/setex/")[1].split("/")[0]] = kw["content"].decode()
        return _SoxtaJavob({})

    def soxta_get(url, **kw):
        return _SoxtaJavob({"result": saqlangan.get(url.rsplit("/", 1)[1])})

    monkeypatch.setattr(kesh.httpx, "post", soxta_post)
    monkeypatch.setattr(kesh.httpx, "get", soxta_get)

    k = _kalit("ombordan tiklanadi")
    kesh.qoy(k, _javob("ombordagi javob"))
    kesh.tozala()                       # xotira yo'qoldi (qayta ishga tushish)
    tiklangan = kesh.ol(k)
    assert tiklangan is not None, "ombordan tiklanmadi"
    assert tiklangan.tavsiya == "ombordagi javob"
    # Tiklangach xotiraga ko'chirilishi kerak — ikkinchi so'rov tarmoqsiz
    monkeypatch.setattr(kesh.httpx, "get", _portlaydi)
    assert kesh.ol(k) is not None


def test_ombor_yiqilsa_javob_buzilmaydi(monkeypatch):
    """Kesh — tezlashtirish vositasi. U yiqilsa xizmat to'xtamasligi shart."""
    monkeypatch.setattr(kesh, "STATISTIKA_KV_URL", "https://misol")
    monkeypatch.setattr(kesh, "STATISTIKA_KV_TOKEN", "t")
    monkeypatch.setattr(kesh.httpx, "post",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("tarmoq")))
    monkeypatch.setattr(kesh.httpx, "get",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("tarmoq")))
    k = _kalit("ombor yiqilgan")
    kesh.qoy(k, _javob())              # xato ko'tarilmasligi kerak
    assert kesh.ol(k) is not None      # xotiradan qaytadi
    kesh.tozala()
    assert kesh.ol(k) is None          # ombor yo'q — lekin xato ham yo'q


def test_kv_kaliti_url_uchun_xavfsiz():
    """Kalit ichida savol matni bor: bo'sh joy va | URL'ni buzadi."""
    k = _kalit("Ish haqi to'lanmayapti | juda uzun " + "a" * 500)
    kv = kesh._kv_kalit(k)
    assert kv.startswith("kesh:")
    assert len(kv) < 80
    assert all(c.isalnum() or c in ":" for c in kv)
