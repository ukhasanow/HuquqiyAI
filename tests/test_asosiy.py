# LLM'siz ishlaydigan qismlar uchun testlar:
# baza yaxlitligi, qidiruv (lotin + kirill), ariza generatori, API endpointlar.
import pytest
from fastapi.testclient import TestClient

from app import storage
from app.main import app
from app.services import retrieval
from app.services.ariza import ariza_tuz

client = TestClient(app)


# ---------- Baza yaxlitligi ----------

def test_baza_toliq():
    moddalar = storage.moddalarni_oqi()
    assert len(moddalar) >= 42
    for m in moddalar:
        assert m["id"] and m["qonun_nomi"] and m["modda_raqami"]
        assert m["lex_url"].startswith("https://lex.uz/")
        assert m["holat"] in ("verified", "needs_verification")
        if m["holat"] == "verified":
            assert len(m["matn"]) > 50, f"{m['id']} matni juda qisqa"


def test_organlar_toliq():
    organlar = storage.organlarni_oqi()
    mavzular = {o["mavzu"] for o in organlar}
    assert "umumiy" in mavzular  # fallback organ bo'lishi shart
    for o in organlar:
        assert o["nomi"] and o["manzil"]


# ---------- Qidiruv ----------

def test_qidiruv_lotin():
    moddalar = storage.moddalarni_oqi()
    natija = retrieval.moddalarni_qidir("aliment miqdori qancha", moddalar)
    assert natija[0]["id"].startswith("oila-")


def test_qidiruv_kirill():
    moddalar = storage.moddalarni_oqi()
    natija = retrieval.moddalarni_qidir("Иш ҳақимни тўламаяпти, нима қилай?", moddalar)
    idlar = [m["id"] for m in natija]
    assert any(i.startswith("mehnat-") for i in idlar[:3])


def test_qidiruv_topilmasa_hammasi():
    moddalar = storage.moddalarni_oqi()
    natija = retrieval.moddalarni_qidir("xxxyyyzzz", moddalar)
    assert len(natija) == len(moddalar)  # fallback: yakuniy tanlov LLM'da


# ---------- Ariza generatori ----------

def _namuna_modda():
    return storage.modda_top("mehnat-253")


def _namuna_organ():
    return storage.organ_top("mehnat")


def test_ariza_tuziladi():
    matn = ariza_tuz(
        fish="Aliyev Alisher",
        vaziyat="Ish haqim 2 oydan beri to'lanmayapti.",
        moddalar=[_namuna_modda()],
        organ=_namuna_organ(),
        telefon="+998901234567",
    )
    assert "ARIZA" in matn
    assert "Aliyev Alisher" in matn
    assert "253-moddasi" in matn
    assert "_____________ (imzo)" in matn


def test_ariza_shahar_va_sanasiz():
    """Hujjatda shahar va sana bo'lmasligi kerak — yoziladigan yagona joy imzo."""
    matn = ariza_tuz(
        fish="Test Testov",
        vaziyat="Vaziyat",
        moddalar=[_namuna_modda()],
        organ=_namuna_organ(),
    )
    import datetime
    bugun = datetime.date.today()
    assert str(bugun.year) not in matn  # sana yo'q
    assert matn.count("(imzo)") == 1  # yoziladigan bitta joy — imzo
    assert "[" not in matn  # boshqa to'ldiriladigan joy yo'q


def test_ariza_fishsiz_xato():
    with pytest.raises(ValueError):
        ariza_tuz(fish="  ", vaziyat="", moddalar=[_namuna_modda()], organ=_namuna_organ())


def test_ariza_moddasiz_xato():
    with pytest.raises(ValueError):
        ariza_tuz(fish="Test", vaziyat="", moddalar=[], organ=_namuna_organ())


def test_sud_uchun_davo_arizasi():
    organ = storage.organ_top("fuqarolik")
    matn = ariza_tuz(fish="Test", vaziyat="", moddalar=[_namuna_modda()], organ=organ)
    assert "DA'VO ARIZASI" in matn


# ---------- API endpointlar ----------

def test_bosh_sahifa():
    r = client.get("/")
    assert r.status_code == 200
    assert "HuquqiyAI" in r.text


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["moddalar_soni"] >= 42


def test_ariza_endpoint():
    r = client.post("/api/ariza", json={
        "fish": "Aliyev Alisher",
        "vaziyat": "Test vaziyat",
        "modda_idlari": ["mehnat-253", "mehnat-269"],
        "murojaat_mavzusi": "mehnat",
    })
    assert r.status_code == 200
    assert "253-, 269-moddalari" in r.json()["matn"]


def test_ariza_endpoint_notogri_modda():
    r = client.post("/api/ariza", json={"fish": "Test", "modda_idlari": ["yoq-id"]})
    assert r.status_code == 422


def test_admin_parolsiz_yopiq():
    assert client.get("/api/admin/moddalar").status_code == 401
    assert client.get("/api/admin/moddalar", headers={"X-Admin-Parol": "xato"}).status_code == 401
