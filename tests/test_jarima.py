# Jarima qonuniyligini tekshirish testlari.
#
# Bu yerda AI yo'q — hammasi aniq arifmetika, shuning uchun natijalar ham
# aniq tekshiriladi. Eng muhim testlar: muddat chegarasidagi bir kunlik farq
# va konstantalarning qonun matniga mosligi.
from datetime import date

from fastapi.testclient import TestClient

from app.main import app
from app.models import JarimaSorov
from app.services import jarima

client = TestClient(app)

BUGUN = date(2026, 8, 5)


def _sorov(**kw) -> JarimaSorov:
    return JarimaSorov(**kw)


def _tekshiruv(javob, nomi_boshi: str):
    return next(t for t in javob.tekshiruvlar if t.nomi.startswith(nomi_boshi))


# ---------- Konstantalar qonun matniga bog'langanmi ----------

def test_muddatlar_qonun_matniga_mos():
    """Konstantalar MJK matnidan olingan. Qonun o'zgarsa (importer --tekshir
    bilan yangilanganda) bu test yiqilib, konstantalarni eslatadi."""
    from app import storage

    m36 = storage.modda_top("mjk-36")["matn"]
    assert "bir yildan kechiktirmay" in m36
    assert "bir oydan kechiktirmay" in m36  # kamera uchun
    assert jarima.JAZO_MUDDATI_OY == 12 and jarima.KAMERA_JAZO_MUDDATI_OY == 1

    m316 = storage.modda_top("mjk-316")["matn"]
    assert "oʻn kun ichida" in m316
    assert jarima.SHIKOYAT_MUDDATI_KUN == 10

    m330 = storage.modda_top("mjk-330")["matn"]
    assert "uch oy davomida" in m330
    assert jarima.IJRO_MUHLATI_OY == 3


def test_havola_qilinadigan_moddalar_bazada_bor():
    from app import storage

    for modda_id in (jarima.MUDDAT_MODDASI, jarima.ISTISNO_MODDASI,
                     jarima.SHIKOYAT_MODDASI, jarima.IJRO_MODDASI,
                     jarima.KAMERA_MODDASI, jarima.BAYONNOMA_MODDASI,
                     jarima.QAROR_MODDASI):
        assert storage.modda_top(modda_id), f"{modda_id} bazada yo'q"


# ---------- Kalendar oy arifmetikasi ----------

def test_oy_qoshish_kalendar_boyicha():
    assert jarima.oy_qoshish(date(2026, 1, 15), 1) == date(2026, 2, 15)
    assert jarima.oy_qoshish(date(2026, 1, 15), 12) == date(2027, 1, 15)
    assert jarima.oy_qoshish(date(2026, 11, 30), 3) == date(2027, 2, 28)


def test_oy_qoshish_oy_oxirini_qisqartiradi():
    """31-yanvar + 1 oy = 28-fevral (30 kun qo'shish emas)."""
    assert jarima.oy_qoshish(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert jarima.oy_qoshish(date(2024, 1, 31), 1) == date(2024, 2, 29)  # kabisa yili


# ---------- 36-modda: javobgarlikka tortish muddati ----------

def test_kamera_jarimasi_bir_oydan_kech_asos_boladi():
    """Kamera jarimasi hodisadan bir oy ichida qo'llanilishi kerak."""
    javob = jarima.jarimani_tekshir(_sorov(
        hodisa_sanasi=date(2026, 4, 1), qaror_sanasi=date(2026, 7, 1), kamera=True,
    ), bugun=BUGUN)
    t = _tekshiruv(javob, "Javobgarlikka tortish")
    assert t.holat == "asos"
    assert "271-moddaning 7-bandiga" in t.izoh
    assert t.modda.id == "mjk-36"
    assert javob.asoslar_soni >= 1


def test_kamera_jarimasi_bir_oy_ichida_joyida():
    javob = jarima.jarimani_tekshir(_sorov(
        hodisa_sanasi=date(2026, 7, 1), qaror_sanasi=date(2026, 7, 20), kamera=True,
    ), bugun=BUGUN)
    assert _tekshiruv(javob, "Javobgarlikka tortish").holat == "joyida"


def test_muddat_chegarasi_aniq_kunda_hisoblanadi():
    """Chegara kuni — hali muddat ichida, ertasi kuni — o'tgan."""
    ichida = jarima.jarimani_tekshir(_sorov(
        hodisa_sanasi=date(2026, 6, 10), qaror_sanasi=date(2026, 7, 10), kamera=True,
    ), bugun=BUGUN)
    tashqarida = jarima.jarimani_tekshir(_sorov(
        hodisa_sanasi=date(2026, 6, 10), qaror_sanasi=date(2026, 7, 11), kamera=True,
    ), bugun=BUGUN)
    assert _tekshiruv(ichida, "Javobgarlikka tortish").holat == "joyida"
    assert _tekshiruv(tashqarida, "Javobgarlikka tortish").holat == "asos"


def test_oddiy_jarimada_muddat_bir_yil():
    """Kamerasiz jarimada chegara — bir yil, uch oy hali asos emas."""
    javob = jarima.jarimani_tekshir(_sorov(
        hodisa_sanasi=date(2026, 4, 1), qaror_sanasi=date(2026, 7, 1), kamera=False,
    ), bugun=BUGUN)
    assert _tekshiruv(javob, "Javobgarlikka tortish").holat == "joyida"

    eski = jarima.jarimani_tekshir(_sorov(
        hodisa_sanasi=date(2024, 4, 1), qaror_sanasi=date(2026, 7, 1), kamera=False,
    ), bugun=BUGUN)
    assert _tekshiruv(eski, "Javobgarlikka tortish").holat == "asos"


def test_sanasiz_muddat_nomalum():
    javob = jarima.jarimani_tekshir(_sorov(kamera=True), bugun=BUGUN)
    t = _tekshiruv(javob, "Javobgarlikka tortish")
    assert t.holat == "noma'lum"
    assert javob.asoslar_soni == 0


# ---------- 316-modda: shikoyat muddati ----------

def test_shikoyat_muddati_hisoblanadi():
    javob = jarima.jarimani_tekshir(_sorov(
        qaror_sanasi=date(2026, 8, 1), qaror_olingan_sanasi=date(2026, 8, 1),
    ), bugun=BUGUN)
    assert javob.shikoyat_kunlari == 6
    assert "6 kun qoldi" in _tekshiruv(javob, "Shikoyat berish").izoh


def test_shikoyat_muddati_otgan_bolsa_tiklash_taklif_qilinadi():
    javob = jarima.jarimani_tekshir(_sorov(
        qaror_sanasi=date(2026, 6, 1), qaror_olingan_sanasi=date(2026, 6, 1),
    ), bugun=BUGUN)
    t = _tekshiruv(javob, "Shikoyat berish")
    assert t.holat == "diqqat"
    assert "tiklashni so'rab" in t.izoh
    assert javob.shikoyat_kunlari < 0


def test_qaror_olingan_sana_ustun():
    """Muddat qaror chiqarilgan emas, NUSXASI OLINGAN kundan boshlanadi."""
    javob = jarima.jarimani_tekshir(_sorov(
        qaror_sanasi=date(2026, 6, 1), qaror_olingan_sanasi=date(2026, 8, 3),
    ), bugun=BUGUN)
    assert javob.shikoyat_kunlari == 8


# ---------- 330-modda: ijro muhlati ----------

def test_uch_oydan_eski_qaror_diqqatga_olinadi():
    javob = jarima.jarimani_tekshir(_sorov(qaror_sanasi=date(2026, 1, 1)), bugun=BUGUN)
    t = _tekshiruv(javob, "Qaror ijrosining")
    assert t.holat == "diqqat"
    assert t.modda.id == "mjk-330"


def test_yangi_qarorning_ijro_muhlati_joyida():
    javob = jarima.jarimani_tekshir(_sorov(qaror_sanasi=date(2026, 7, 20)), bugun=BUGUN)
    assert _tekshiruv(javob, "Qaror ijrosining").holat == "joyida"


# ---------- Kamera, modda va band ----------

def test_kamera_tekshiruvi_faqat_kamera_jarimasida():
    kamerali = jarima.jarimani_tekshir(_sorov(kamera=True), bugun=BUGUN)
    oddiy = jarima.jarimani_tekshir(_sorov(kamera=False), bugun=BUGUN)
    assert any(t.nomi.startswith("Kamera") for t in kamerali.tekshiruvlar)
    assert not any(t.nomi.startswith("Kamera") for t in oddiy.tekshiruvlar)


def test_kamerada_bayonnoma_tekshiruvi_yoq():
    """Kamera jarimasida bayonnoma tuzilmaydi — keraksiz maslahat berilmasin."""
    kamerali = jarima.jarimani_tekshir(_sorov(kamera=True), bugun=BUGUN)
    assert not any(t.nomi.startswith("Bayonnoma") for t in kamerali.tekshiruvlar)


def test_modda_bazadan_biriktiriladi():
    javob = jarima.jarimani_tekshir(_sorov(modda="128-3"), bugun=BUGUN)
    t = _tekshiruv(javob, "Qaysi modda")
    assert t.holat == "joyida"
    assert t.modda.id == "mjk-128-3"


def test_ustki_indeksli_modda_tushuniladi():
    assert jarima._mjk_id("128³") == "mjk-128-3"
    assert jarima._mjk_id("128-3-modda") == "mjk-128-3"
    assert jarima._mjk_id(" 131 ") == "mjk-131"


def test_notogri_modda_nomalum():
    javob = jarima.jarimani_tekshir(_sorov(modda="9999"), bugun=BUGUN)
    assert _tekshiruv(javob, "Qaysi modda").holat == "noma'lum"


def test_qoidalar_bandi_biriktiriladi():
    javob = jarima.jarimani_tekshir(_sorov(band="116"), bugun=BUGUN)
    t = _tekshiruv(javob, "Qoidalarning qaysi bandi")
    assert t.holat == "joyida"
    assert t.modda.id == "yhqoida-116"
    assert t.modda.matn


def test_bandsiz_qaror_diqqatga_olinadi():
    javob = jarima.jarimani_tekshir(_sorov(), bugun=BUGUN)
    assert _tekshiruv(javob, "Qoidalarning qaysi bandi").holat == "diqqat"


# ---------- Umumiy xulq ----------

def test_asoslar_royxat_boshida():
    """Odam ro'yxatni tepadan o'qiydi — asos pastda qolib ketmasin."""
    javob = jarima.jarimani_tekshir(_sorov(
        hodisa_sanasi=date(2026, 4, 1), qaror_sanasi=date(2026, 7, 1), kamera=True,
    ), bugun=BUGUN)
    assert javob.tekshiruvlar[0].holat == "asos"


def test_jarima_noqonuniy_deb_elon_qilinmaydi():
    """Tizim hech qachon "to'lamang" demaydi — faqat asos ko'rsatadi."""
    javob = jarima.jarimani_tekshir(_sorov(
        hodisa_sanasi=date(2026, 4, 1), qaror_sanasi=date(2026, 7, 1), kamera=True,
    ), bugun=BUGUN)
    matn = (javob.xulosa + javob.disclaimer + " ".join(t.izoh for t in javob.tekshiruvlar)).lower()
    assert "to'lamang" not in matn
    assert "noqonuniy" not in javob.xulosa.lower()
    assert "sud yoki vakolatli organ" in javob.disclaimer


def test_asos_topilmasa_xulosa_halol():
    javob = jarima.jarimani_tekshir(_sorov(
        hodisa_sanasi=date(2026, 7, 1), qaror_sanasi=date(2026, 7, 10), kamera=True,
    ), bugun=BUGUN)
    assert javob.asoslar_soni == 0
    assert "qonuniy degani emas" in javob.xulosa


# ---------- API ----------

def test_jarima_endpointi():
    r = client.post("/api/jarima", json={
        "hodisa_sanasi": "2026-04-01",
        "qaror_sanasi": "2026-07-01",
        "kamera": True,
        "modda": "128-3",
    })
    assert r.status_code == 200
    d = r.json()
    assert d["asoslar_soni"] >= 1
    assert d["tekshiruvlar"][0]["holat"] == "asos"
    assert d["tekshiruvlar"][0]["modda"]["id"] == "mjk-36"


def test_jarima_endpointi_bosh_sorov_bilan_ishlaydi():
    """Hech narsa bilmagan odam ham nimani tekshirish kerakligini bilib olsin."""
    r = client.post("/api/jarima", json={})
    assert r.status_code == 200
    d = r.json()
    assert d["asoslar_soni"] == 0
    assert len(d["tekshiruvlar"]) >= 5


# ---------- 321-modda: bekor qilish asoslari ----------

def test_asoslilik_tekshiruvi_tort_asosni_sanaydi():
    """321-modda "jarima qaysi holatda asossiz" savolining qonundagi javobi."""
    javob = jarima.jarimani_tekshir(_sorov(), bugun=BUGUN)
    t = _tekshiruv(javob, "Qaror asosli")
    assert t.modda.id == "mjk-321"
    for asos in ("bir tomonlama", "mos kelmaydi", "jiddiy buzilgan", "adolatsiz"):
        assert asos in t.izoh


def test_aybdorlik_tekshiruvi_bor():
    javob = jarima.jarimani_tekshir(_sorov(), bugun=BUGUN)
    t = _tekshiruv(javob, "Aybdorligingiz")
    assert t.modda.id == "mjk-307"
    assert "AYBDORLIGINGIZ" in t.izoh


# ---------- 315, 318, 324: shikoyat yo'li ----------

def test_shikoyat_yoli_sudni_va_yuqori_organni_korsatadi():
    """Foydalanuvchi "qayerga murojaat qilaman" degan savolga javob olishi kerak."""
    javob = jarima.jarimani_tekshir(_sorov(), bugun=BUGUN)
    matn = " ".join(javob.shikoyat_yoli)
    assert "yuqori turuvchi organga" in matn
    assert "tuman (shahar) sudiga" in matn


def test_shikoyat_yolida_davlat_boji_va_ijro_toxtashi_bor():
    """Ikkalasi ham amaliy jihatdan juda muhim va qonunda aniq yozilgan."""
    matn = " ".join(jarima.jarimani_tekshir(_sorov(), bugun=BUGUN).shikoyat_yoli)
    assert "Davlat boji to'lanmaydi" in matn
    assert "ijrosini to'xtatib turadi" in matn


def test_tolangan_jarimada_pul_qaytarish_eslatiladi():
    """324-modda: qaror bekor qilinsa undirib olingan summa qaytariladi."""
    tolangan = jarima.jarimani_tekshir(_sorov(tolangan=True), bugun=BUGUN)
    tolanmagan = jarima.jarimani_tekshir(_sorov(tolangan=False), bugun=BUGUN)
    assert any("qaytariladi" in q for q in tolangan.shikoyat_yoli)
    assert not any("qaytariladi" in q for q in tolanmagan.shikoyat_yoli)


# ---------- Shikoyat qoralamasi ----------

def _shikoyat(**kw):
    from app.services.ariza import shikoyat_tuz

    asosiy = dict(fish="Karimov Bobur", qaror_raqami="KM-447",
                  qaror_sanasi="2026-08-01", qaror_organi="YHXX boshqarmasi",
                  asoslar=["Muddat 60 kunga o'tkazib yuborilgan."],
                  moddalar=[{"qonun_nomi": "MJK", "modda_raqami": "36-modda"}])
    asosiy.update(kw)
    return shikoyat_tuz(**asosiy)


def test_shikoyatda_aniq_talab_bor():
    """Ariza "ko'rib chiqishingizni so'rayman" deydi, shikoyat esa aniq
    talab qo'yishi kerak: qarorni bekor qilish va ishni tugatish."""
    matn = _shikoyat()
    assert "SHIKOYAT" in matn
    assert "321-moddasiga muvofiq SO'RAYMAN" in matn
    assert "qarorni bekor qilishni" in matn
    assert "ish yuritishni tugatishni" in matn


def test_shikoyatda_qaror_malumotlari_bor():
    matn = _shikoyat(summa="1 062 500 so'm")
    assert "KM-447-sonli" in matn
    assert "2026-08-01 kuni" in matn
    assert "YHXX boshqarmasi tomonidan" in matn
    assert "1 062 500 so'm" in matn


def test_tolangan_bolsa_pulni_qaytarish_talabi_qoshiladi():
    assert "324-moddasiga" in _shikoyat(tolangan=True)
    assert "324-moddasiga" not in _shikoyat(tolangan=False)


def test_bitta_modda_birlik_shaklda():
    assert "36-moddasi bilan" in _shikoyat()
    assert "36-moddalari" not in _shikoyat()


def test_asossiz_shikoyatda_bosh_joy_qoldiriladi():
    """Asos topilmasa ham shikoyat tuzish mumkin — odam o'zi yozadi."""
    matn = _shikoyat(asoslar=[], moddalar=[])
    assert "o'z so'zingiz bilan yozing" in matn


def test_fishsiz_shikoyat_rad_etiladi():
    import pytest as _pytest

    with _pytest.raises(ValueError):
        _shikoyat(fish="   ")


def test_shikoyat_endpointi():
    r = client.post("/api/jarima/shikoyat", json={
        "fish": "Karimov Bobur Anvarovich",
        "qaror_organi": "Toshkent shahar YHXX",
        "jarima": {
            "hodisa_sanasi": "2026-05-02", "qaror_sanasi": "2026-08-01",
            "kamera": True, "modda": "128-3", "qaror_raqami": "KM-447",
        },
    })
    assert r.status_code == 200
    d = r.json()
    assert d["fayl_nomi"] == "shikoyat.txt"
    # Tekshiruvda topilgan asos shikoyatga o'zi tushishi kerak
    assert "60 kunga o'tkazib yuborilgan" in d["matn"]
    assert "321-moddasiga muvofiq SO'RAYMAN" in d["matn"]


def test_shikoyat_endpointi_fishsiz_422():
    r = client.post("/api/jarima/shikoyat", json={"fish": "", "jarima": {}})
    assert r.status_code == 422
