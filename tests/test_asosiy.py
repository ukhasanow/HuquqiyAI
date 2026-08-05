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


def test_mavzular_organlar_bilan_mos():
    """LLM tanlaydigan har bir mavzu uchun bazada organ bo'lishi shart.
    Aks holda model to'g'ri mavzu qaytarsa ham foydalanuvchi "umumiy"ga tushadi."""
    from app.services.llm import MUROJAAT_MAVZULARI

    organ_mavzulari = {o["mavzu"] for o in storage.organlarni_oqi()}
    yetishmayotgan = set(MUROJAAT_MAVZULARI) - organ_mavzulari
    assert not yetishmayotgan, f"organlar.json da yo'q mavzular: {yetishmayotgan}"


def test_har_bir_kodeks_qidiruvda_topiladi():
    """Har bir qonun uchun hayotiy savol top-3 da to'g'ri kodeksni chiqarishi kerak."""
    moddalar = storage.moddalarni_oqi()
    tekshiruv = [
        ("Ish haqimni 2 oydan beri to'lashmayapti", "mehnat-"),
        ("Ajrashmoqchiman, aliment to'lamayapti", "oila-"),
        ("Muzlatgich buzuq chiqdi, pulini qaytarishadimi?", "istemol-"),
        ("Ijara shartnomam bor, uydan chiqarib yubormoqchi", "uyjoy-"),
        ("Tezlikni oshirganim uchun kamera jarima yozdi", "mjk-"),
        ("Telefonimni o'g'irlab ketishdi", "jk-"),
    ]
    for savol, prefiks in tekshiruv:
        idlar = [m["id"] for m in retrieval.moddalarni_qidir(savol, moddalar)]
        assert any(i.startswith(prefiks) for i in idlar[:3]), f"{savol!r} -> {idlar}"


def test_kundalik_murojaatlar_javobsiz_qolmaydi():
    """Jonli sinovda javobsiz qolgan, lekin juda ko'p uchraydigan savollar."""
    moddalar = storage.moddalarni_oqi()
    for savol, kutilgan in [
        ("Qo'shnim tunda juda shovqin qilyapti, nima qilsam bo'ladi?", "mjk-192"),
        ("Uy egasi garov pulimni qaytarmadi", "fuqarolik-1023"),
    ]:
        idlar = [m["id"] for m in retrieval.moddalarni_qidir(savol, moddalar)]
        assert kutilgan in idlar[:3], f"{savol!r} -> {idlar}"


def test_qidiruv_apostrofsiz_va_kirill():
    """Foydalanuvchilar apostrofsiz ("ogirlab") va kirillda yozadi —
    ikkalasi ham teglardagi apostrofli shakl bilan mos tushishi kerak."""
    moddalar = storage.moddalarni_oqi()
    for savol, kutilgan in [
        ("Telefonimni ogirlab ketishdi", "jk-169"),
        ("Иш ҳақимни тўламаяпти", "mehnat-"),
        ("Квартирадан кўчириб юборишмоқчи", "uyjoy-"),
    ]:
        idlar = [m["id"] for m in retrieval.moddalarni_qidir(savol, moddalar)]
        assert any(i.startswith(kutilgan) for i in idlar[:3]), f"{savol!r} -> {idlar}"


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


def test_qidiruv_topilmasa_cheklangan():
    """Mos modda topilmasa butun baza emas, cheklangan namuna qaytadi —
    aks holda baza o'sgani sayin LLM so'rovi va javob vaqti o'sib boradi.

    Namuna har hujjatdan bittadan olinadi: fayldagi birinchi N yozuv bitta-ikkita
    kodeksga tiqilib qolar va savol mavzusiga umuman aloqasi bo'lmasligi mumkin edi."""
    moddalar = storage.moddalarni_oqi()
    natija = retrieval.moddalarni_qidir("xxxyyyzzz", moddalar)
    hujjatlar = {m["id"].split("-")[0] for m in moddalar}
    assert len(natija) == min(retrieval.FALLBACK_CHEGARA, len(hujjatlar))
    assert len({m["id"].split("-")[0] for m in natija}) == len(natija)


def test_qidiruv_indeksi_baza_ozgarsa_yangilanadi():
    """Kesh eskirib qolmasligi kerak: yangi ro'yxatga yangi indeks quriladi."""
    moddalar = storage.moddalarni_oqi()
    retrieval.moddalarni_qidir("aliment", moddalar)
    soxta = [dict(moddalar[0], id="test-x", teglar=["xyzqwe"], sarlavha="", matn="")]
    natija = retrieval.moddalarni_qidir("xyzqwe", soxta)
    assert natija and natija[0]["id"] == "test-x"


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


def test_ovoz_endpointi_transkript_qaytaradi(monkeypatch):
    """Saytdagi mikrofon botdagi AYNAN shu xizmatni ishlatadi."""
    from app.services import ovoz

    monkeypatch.setattr(ovoz, "mavjud", lambda: True)
    monkeypatch.setattr(ovoz, "matnga_ogir", lambda *a, **k: "  Ish haqim berilmayapti  ")
    r = client.post("/api/ovoz", files={"fayl": ("ovoz.ogg", b"opus", "audio/ogg")})
    assert r.status_code == 200
    assert r.json() == {"matn": "Ish haqim berilmayapti"}


def test_ovoz_endpointi_sozlanmagan_bolsa_503(monkeypatch):
    from app.services import ovoz

    monkeypatch.setattr(ovoz, "mavjud", lambda: False)
    r = client.post("/api/ovoz", files={"fayl": ("ovoz.ogg", b"opus", "audio/ogg")})
    assert r.status_code == 503


def test_ovoz_endpointi_katta_fayl_rad_etadi(monkeypatch):
    from app.config import MAX_OVOZ_HAJMI
    from app.services import ovoz

    monkeypatch.setattr(ovoz, "mavjud", lambda: True)
    r = client.post("/api/ovoz",
                    files={"fayl": ("ovoz.ogg", b"x" * (MAX_OVOZ_HAJMI + 1), "audio/ogg")})
    assert r.status_code == 413


def test_ovoz_endpointi_xatoni_tushunarli_qaytaradi(monkeypatch):
    from app.services import ovoz

    monkeypatch.setattr(ovoz, "mavjud", lambda: True)
    monkeypatch.setattr(ovoz, "matnga_ogir",
                        lambda *a, **k: (_ for _ in ()).throw(ovoz.OvozXato("Matn bilan yozing.")))
    r = client.post("/api/ovoz", files={"fayl": ("ovoz.ogg", b"opus", "audio/ogg")})
    assert r.status_code == 422
    assert "Matn bilan yozing." in r.json()["detail"]


def test_admin_parolsiz_yopiq():
    assert client.get("/api/admin/moddalar").status_code == 401
    assert client.get("/api/admin/moddalar", headers={"X-Admin-Parol": "xato"}).status_code == 401
