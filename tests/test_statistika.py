# Statistika moduli va unga bog'liq endpointlar uchun testlar.
# Har bir test statistika faylini vaqtinchalik katalogga yo'naltiradi,
# real data/statistika.json'ga tegilmaydi.
import pytest
from fastapi.testclient import TestClient

from app import storage
from app.main import app
from app.services import statistika

client = TestClient(app)


@pytest.fixture
def vaqtinchalik_fayl(tmp_path, monkeypatch):
    fayl = tmp_path / "statistika.json"
    monkeypatch.setattr(statistika, "STATISTIKA_FAYL", fayl)
    return fayl


# ---------- Statistika moduli ----------

def test_sorov_hisoblanadi(vaqtinchalik_fayl):
    statistika.sorov_hisobla(
        rejim="oddiy", javob_topildi=True, murojaat_mavzusi="mehnat",
        foydalanuvchi_id="anon-1", savol="Ish haqim to'lanmayapti",
    )
    statistika.sorov_hisobla(
        rejim="pro", javob_topildi=False, murojaat_mavzusi="umumiy",
        foydalanuvchi_id="anon-2", savol="Kosmik huquq bo'yicha savol",
    )
    s = statistika.statistika_oqi()
    assert s["jami_sorovlar"] == 2
    assert s["javob_topildi"] == 1
    assert s["javob_topilmadi"] == 1
    assert s["rejimlar"]["oddiy"] == 1
    assert s["rejimlar"]["pro"] == 1
    assert s["mavzular"]["mehnat"] == 1
    assert s["foydalanuvchilar_soni"] == 2
    assert len(s["kunlik_30"]) == 30
    assert s["kunlik_30"][-1]["jami"] == 2  # bugungi kun oxirida


def test_savol_matni_faqat_topilmaganda_saqlanadi(vaqtinchalik_fayl):
    statistika.sorov_hisobla(
        rejim="oddiy", javob_topildi=True, murojaat_mavzusi="oila",
        savol="Aliment qanday undiriladi?",
    )
    statistika.sorov_hisobla(
        rejim="oddiy", javob_topildi=False, murojaat_mavzusi="umumiy",
        savol="Dron uchirish qoidalari qanday?",
    )
    matn = vaqtinchalik_fayl.read_text(encoding="utf-8")
    assert "Aliment qanday undiriladi?" not in matn  # topilgan savol matni saqlanmaydi
    s = statistika.statistika_oqi()
    assert [t["savol"] for t in s["topilmagan_savollar"]] == ["Dron uchirish qoidalari qanday?"]


def test_foydalanuvchi_takrorlanmaydi(vaqtinchalik_fayl):
    for _ in range(3):
        statistika.sorov_hisobla(
            rejim="oddiy", javob_topildi=True, murojaat_mavzusi="mehnat",
            foydalanuvchi_id="anon-bir",
        )
    assert statistika.statistika_oqi()["foydalanuvchilar_soni"] == 1


# ---------- Endpointlar ----------

def test_health_javoblar_soni(vaqtinchalik_fayl):
    statistika.sorov_hisobla(rejim="oddiy", javob_topildi=True, murojaat_mavzusi="mehnat")
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["javoblar_soni"] == 1


def test_admin_statistika_parolsiz_yopiq():
    assert client.get("/api/admin/statistika").status_code == 401
    assert client.get("/api/admin/statistika", headers={"X-Admin-Parol": "xato"}).status_code == 401


def test_admin_statistika_parol_bilan(vaqtinchalik_fayl):
    from app.config import ADMIN_PASSWORD
    r = client.get("/api/admin/statistika", headers={"X-Admin-Parol": ADMIN_PASSWORD})
    assert r.status_code == 200
    d = r.json()
    for kalit in ("jami_sorovlar", "rejimlar", "mavzular", "kunlik_30", "topilmagan_savollar"):
        assert kalit in d


# ---------- Yangi baza maydonlari va namunaviy savollar ----------

def test_organlarda_yangi_maydonlar():
    for o in storage.organlarni_oqi():
        assert o.get("ish_vaqti"), f"{o['mavzu']} organida ish_vaqti yo'q"
        assert o.get("hududiy_havola", "").startswith("https://"), f"{o['mavzu']} organida hududiy_havola yo'q"


def test_bosh_sahifada_besh_misol():
    r = client.get("/")
    assert r.status_code == 200
    assert r.text.count('class="misol"') == 5
    assert 'id="hisoblagich"' in r.text
