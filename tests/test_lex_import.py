# lex.uz importeri testlari (tarmoqqa chiqmaydi — tests/fixtures/ dagi HTML kesmalari).
#
# Asosiy fikr: parserning to'g'riligini "ko'zdan kechirish" bilan emas, ALLAQACHON
# tekshirilgan moddalar bilan solishtirib isbotlaymiz. Fixture'dan olingan matn
# data/qonunlar.json dagi yozuv bilan belgima-belgi mos kelishi shart.
import json
import sys
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "tools"))

import lex_import  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _fixture(nom: str) -> str:
    return (FIXTURES / nom).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def baza():
    return {m["id"]: m for m in json.loads((BASE_DIR / "data" / "qonunlar.json").read_text(encoding="utf-8"))}


def _moddalar(fixture_nomi: str, akt: str):
    return lex_import.moddalarni_ajrat(_fixture(fixture_nomi), akt)


def _id_boyicha(moddalar, prefiks):
    return {lex_import.modda_id(prefiks, m["raqam"]): m for m in moddalar}


# ---------- Asosiy regressiya: bazadagi tekshirilgan moddalar ----------

@pytest.mark.parametrize(
    "fixture_nomi,akt,prefiks,idlar",
    [
        ("lex_oila.html", "-104720", "oila", ["oila-40", "oila-41", "oila-42"]),
        ("lex_mjk.html", "-97664", "mjk", ["mjk-128-1"]),
        ("lex_mehnat.html", "-6257288", "mehnat", ["mehnat-111"]),
    ],
)
def test_matn_bazadagi_yozuv_bilan_aynan_bir_xil(baza, fixture_nomi, akt, prefiks, idlar):
    olingan = _id_boyicha(_moddalar(fixture_nomi, akt), prefiks)
    for mid in idlar:
        kutilgan = baza[mid]
        m = olingan[mid]
        assert m["matn"] == kutilgan["matn"], f"{mid}: modda matni farq qiladi"
        assert m["sarlavha"] == kutilgan["sarlavha"], f"{mid}: sarlavha farq qiladi"
        assert m["lex_url"] == kutilgan["lex_url"], f"{mid}: lex_url farq qiladi"


# ---------- 1-tuzoq: LexUZ sharhi qonun matni emas ----------

def test_lexuz_sharhi_matnga_tushmaydi():
    """Fixture'da COMMENT bloklari bor; ular modda matniga qo'shilmasligi kerak."""
    xom = _fixture("lex_oila.html")
    assert "LexUZ sharhi" in xom, "fixture COMMENT blokini o'z ichiga olishi kerak"
    for m in _moddalar("lex_oila.html", "-104720"):
        assert "LexUZ sharhi" not in m["matn"]
        assert "Qarang:" not in m["matn"]


def test_tahrir_tarixi_matnga_tushmaydi():
    """CHANGES_ORIGINS bloki ("... tahririda — Qonunchilik ma'lumotlari...")
    qonun matni emas, izoh."""
    for m in _moddalar("lex_oila.html", "-104720"):
        assert "tahririda —" not in m["matn"]


# ---------- 2-tuzoq: <sup> ----------

def test_ustki_indeks_saqlanadi(baza):
    """128<sup>1</sup> teglar shunchaki olib tashlansa "1281" bo'lib ketadi."""
    moddalar = _moddalar("lex_mjk.html", "-97664")
    m = moddalar[0]
    assert m["raqam"] == "128¹"
    assert lex_import.modda_id("mjk", m["raqam"]) == "mjk-128-1"
    assert m["sarlavha"].startswith("128¹-modda.")
    assert "1281" not in m["sarlavha"]


def test_modda_id_shakllari():
    assert lex_import.modda_id("oila", "41") == "oila-41"
    assert lex_import.modda_id("mjk", "128¹") == "mjk-128-1"
    assert lex_import.modda_id("mjk", "324³") == "mjk-324-3"


# ---------- Bob sarlavhalari modda emas ----------

def test_bob_sarlavhasi_modda_sifatida_olinmaydi():
    xom = _fixture("lex_oila.html")
    assert "-bob." in xom, "fixture bob sarlavhasini o'z ichiga olishi kerak"
    for m in _moddalar("lex_oila.html", "-104720"):
        assert "-bob." not in m["sarlavha"]
        assert m["sarlavha"].split(".")[0].endswith("-modda")


# ---------- Bo'sh joy normallashtirish ----------

def test_ortiqcha_bosh_joy_qolmaydi():
    """lex.uz matn ichidagi havolalar atrofida ikki karra probel qoldiradi."""
    for fixture_nomi, akt in [("lex_oila.html", "-104720"), ("lex_mehnat.html", "-6257288")]:
        for m in _moddalar(fixture_nomi, akt):
            assert "  " not in m["matn"]
            assert "\t" not in m["matn"]
            assert "\xa0" not in m["matn"]


def test_paragraflar_qator_bilan_ajratiladi():
    m = _id_boyicha(_moddalar("lex_mehnat.html", "-6257288"), "mehnat")["mehnat-111"]
    assert "\n" in m["matn"]
    assert not m["matn"].startswith("\n") and not m["matn"].endswith("\n")


# ---------- Registr bazadagi qiymatlar bilan mos ----------

def test_registrdagi_qonun_nomlari_bazaga_mos(baza):
    """HUJJATLAR dagi qonun_nomi bazadagi yozuvlar bilan bir xil bo'lishi shart —
    aks holda import mavjud yozuvlarning nomini buzadi."""
    prefiks_nomlari = {}
    for m in baza.values():
        prefiks_nomlari.setdefault(m["id"].split("-")[0], set()).add(m["qonun_nomi"])
    for kalit, (_akt, prefiks, nom) in lex_import.HUJJATLAR.items():
        mavjud = prefiks_nomlari.get(prefiks)
        if mavjud:
            assert nom in mavjud, f"{kalit}: registrdagi nom bazadagidan farq qiladi"


def test_faqat_royxati_ustki_indeksni_tushunadi():
    assert lex_import._faqat_royxati("5, 7") == {"5", "7"}
    assert lex_import._faqat_royxati("128¹,324-3") == {"128-1", "324-3"}
    assert lex_import._faqat_royxati("41-modda") == {"41"}


# ---------- Bazaga yozish ----------

def test_bazaga_qosh_mavjud_teglarni_saqlaydi(tmp_path, monkeypatch):
    """Teglar qo'lda tanlanadi va qidiruvda eng katta vaznga ega —
    qayta import ularni o'chirib yubormasligi kerak."""
    fayl = tmp_path / "qonunlar.json"
    eski = {
        "id": "test-1", "qonun_nomi": "Test", "modda_raqami": "1-modda",
        "sarlavha": "1-modda. Eski", "matn": "eski matn", "lex_url": "u",
        "teglar": ["qolda", "tanlangan"], "holat": "verified",
    }
    fayl.write_text(json.dumps([eski], ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(lex_import, "QONUNLAR_FAYL", fayl)

    yangi = {**eski, "matn": "yangilangan matn", "teglar": ["avtomatik"]}
    qoshildi, yangilandi = lex_import.bazaga_qosh([yangi])

    natija = json.loads(fayl.read_text(encoding="utf-8"))
    assert (qoshildi, yangilandi) == (0, 1)
    assert len(natija) == 1
    assert natija[0]["matn"] == "yangilangan matn"
    assert natija[0]["teglar"] == ["qolda", "tanlangan"]


def test_bazaga_qosh_dublikat_yaratmaydi(tmp_path, monkeypatch):
    fayl = tmp_path / "qonunlar.json"
    fayl.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(lex_import, "QONUNLAR_FAYL", fayl)

    yozuv = {
        "id": "test-5", "qonun_nomi": "Test", "modda_raqami": "5-modda",
        "sarlavha": "5-modda. Sarlavha", "matn": "matn", "lex_url": "u",
        "teglar": [], "holat": "verified",
    }
    lex_import.bazaga_qosh([yozuv])
    lex_import.bazaga_qosh([yozuv])
    assert len(json.loads(fayl.read_text(encoding="utf-8"))) == 1
