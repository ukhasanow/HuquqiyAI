# Hujjat turi, tekshirish ro'yxati va bekor qilish yo'li.
#
# Eng muhim test — test_muddatlar_modda_matniga_mos: muddatlar bu yerda
# qo'lda yozilgan va ular bazadagi ASL modda matni bilan solishtiriladi.
# Qonun o'zgarsa test yiqiladi va kod yangilanadi. Muddatni jimgina eskirib
# ketishiga yo'l qo'yib bo'lmaydi: odam noto'g'ri muddatga ishonib, haqiqiy
# muddatni o'tkazib yuboradi.
import pytest
from fastapi.testclient import TestClient

from app import main, storage
from app.services import hujjat

client = TestClient(main.app)

# Har tur uchun qisqa, lekin haqiqiyga o'xshash namuna
NAMUNALAR = {
    "sud_fuqarolik": (
        "O'ZBEKISTON RESPUBLIKASI NOMIDAN HAL QILUV QARORI. "
        "Yunusobod tumani fuqarolik ishlari bo'yicha sudi sudyasi "
        "da'vogar Karimov A. ning javobgar «Alfa» MChJ ga qarshi da'vo "
        "arizasi bo'yicha fuqarolik ishini ko'rib chiqib, HAL QILDI: "
        "da'vo qanoatlantirilsin, javobgardan 5 000 000 so'm undirilsin."
    ),
    "sud_mjk": (
        "SUD QARORI. Sudya Rahimov ma'muriy huquqbuzarlik to'g'risidagi ishni "
        "ko'rib chiqib, MJtKning 128-3 moddasi bilan ma'muriy javobgarlikka "
        "tortdi. Bayonnoma asosida ma'muriy jazo tayinlandi."
    ),
    "jarima": (
        "JARIMA SOLISH TO'G'RISIDAGI QAROR № 1234567. YHXX. Yo'l harakati "
        "qoidalari buzilgani uchun ma'muriy jarima solindi. Bazaviy hisoblash "
        "miqdorining besh baravari. Davlat raqam belgisi 01A123AA. Tezlik."
    ),
    "ishdan_bosatish": (
        "BUYRUQ. Xodim Aliyev B. bilan mehnat shartnomasi Mehnat kodeksining "
        "161-moddasiga asosan bekor qilinsin, lavozimidan ozod etilsin. "
        "Ish beruvchi tashkilot rahbari. Hisob-kitob qilinsin."
    ),
    "organ_javobi": (
        "Sizning murojaatingiz ko'rib chiqildi. Tekshirish natijasida "
        "murojaatingizda ko'rsatilgan holatlar asossiz deb topildi. "
        "Hokimlik. Shikoyat qanoatlantirilmadi."
    ),
}


# ---------- Tur aniqlash ----------

@pytest.mark.parametrize("kutilgan", sorted(NAMUNALAR))
def test_tur_togri_aniqlanadi(kutilgan):
    turi, _ = hujjat.turni_aniqla(NAMUNALAR[kutilgan])
    assert turi == kutilgan


def test_huquqiy_bolmagan_matn_boshqa_boladi():
    turi, ishonch = hujjat.turni_aniqla(
        "Salom! Ertaga soat 10 da uchrashamizmi? Hujjatlarni olib kelaman."
    )
    assert turi == "boshqa"
    assert ishonch == "taxmin"


def test_bosh_matn_yiqilmaydi():
    assert hujjat.turni_aniqla("") == ("boshqa", "taxmin")
    assert hujjat.turni_aniqla(None) == ("boshqa", "taxmin")


def test_kirill_hujjat_ham_aniqlanadi():
    """Rasmiy hujjatlarning katta qismi kirillda keladi."""
    kirill = (
        "ХАЛ ҚИЛУВ ҚАРОРИ. Судья ... даъвогар Каримов ... жавобгар «Альфа» МЧЖ ... "
        "фуқаролик иши кўриб чиқилиб, даъво қаноатлантирилсин."
    )
    turi, _ = hujjat.turni_aniqla(kirill)
    assert turi == "sud_fuqarolik"


def test_sud_sozisiz_hujjat_sud_qarori_bolmaydi():
    """Majburiy so'z yo'q bo'lsa tur umuman ko'rib chiqilmaydi."""
    turi, _ = hujjat.turni_aniqla(
        "Hal qiluv qarori haqida o'qidim, da'vogar va javobgar tushunchalari qiziq."
    )
    assert turi != "sud_fuqarolik"


def test_sud_chiqargan_jarima_qarori_sud_mjk_boladi():
    """«Sudya» so'zi hal qiladi: YHXX qarorida u bo'lmaydi.

    Farq muhim, chunki tartib boshqa — sud qarori ustidan APELLYATSIYA,
    organ qarori ustidan esa SHIKOYAT beriladi.
    """
    sud_qarori = (
        "O'ZBEKISTON RESPUBLIKASI NOMIDAN SUD QARORI. Chilonzor tumani jinoyat "
        "ishlari bo'yicha sudi sudyasi Rahimov ma'muriy huquqbuzarlik "
        "to'g'risidagi ishni ko'rib chiqib, MJtKning 128-moddasi bo'yicha "
        "ma'muriy jazo tayinladi. Bayonnoma asosida sud majlisida ko'rildi."
    )
    turi, _ = hujjat.turni_aniqla(sud_qarori)
    assert turi == "sud_mjk"


def test_jarima_va_sud_mjk_juftligi_doim_taxmin():
    """Bu juftlikda xato narxi yuqori — ball farqi katta bo'lsa ham «taxmin».

    Ikkalasida ham muddat 10 kun, lekin murojaat qilinadigan joy va tartib
    boshqa: noto'g'ri yo'l bilan berilgan hujjat qaytariladi va odam shu
    orada muddatni boy beradi.
    """
    aralash = (
        "SUD QARORI. Sudya ma'muriy huquqbuzarlik to'g'risidagi ishni ko'rdi. "
        "Jarima solish to'g'risidagi qaror. Ma'muriy jarima. Bazaviy hisoblash "
        "miqdori. Modda. Qaror raqami. Bhm. Tezlik. Yo'l harakati."
    )
    turi, ishonch = hujjat.turni_aniqla(aralash)
    assert turi in ("jarima", "sud_mjk")
    assert ishonch == "taxmin"


def test_toza_yhxx_qarori_aniq_deb_belgilanadi():
    """Sud belgilari yo'q qarorda chalkashlik yo'q — ishonch to'liq."""
    turi, ishonch = hujjat.turni_aniqla(NAMUNALAR["jarima"])
    assert (turi, ishonch) == ("jarima", "aniq")


# ---------- Muddatlar qonun matniga mos ----------

def test_muddatlar_modda_matniga_mos():
    """Ko'rsatilgan muddat bazadagi asl modda matnida bor bo'lishi shart."""
    juftlar = [
        ("sud_fuqarolik", "fpk-385-1", "bir oy ichida"),
        ("sud_mjk", "mjk-324-3", "oʻn sutka ichida"),
        ("jarima", "mjk-316", "oʻn kun"),
        ("organ_javobi", "murojaat-17", "bir yildan kechiktirmay"),
    ]
    for turi, modda_id, ibora in juftlar:
        m = storage.modda_top(modda_id)
        assert m, f"{modda_id} bazada yo'q"
        assert ibora in m["matn"], f"{modda_id} matnida «{ibora}» yo'q — qonun o'zgargan?"
        # Shu modda tegishli turning bekor yo'lida ham keltirilgan bo'lsin
        javob = hujjat.tahlil("", turi=turi)
        idlar = {q.modda.id for q in javob.bekor_yoli if q.modda}
        assert modda_id in idlar, f"{turi} uchun {modda_id} bekor yo'lida keltirilmagan"


def test_sud_fuqarolik_uch_oylik_tiklash_chegarasi():
    """385¹-modda: muddat tiklash iltimosnomasi uch oydan kechiktirmay."""
    m = storage.modda_top("fpk-385-1")
    assert "uch oydan kechiktirmay" in m["matn"]
    matn = " ".join(q.matn for q in hujjat.tahlil("", turi="sud_fuqarolik").bekor_yoli)
    assert "uch oydan kechiktirmay" in matn


def test_ishdan_bosatishda_muddat_taxmin_qilinmaydi():
    """Mehnat nizosi muddati bazada yo'q — uni o'ylab topmaslik kerak."""
    javob = hujjat.tahlil("", turi="ishdan_bosatish")
    assert javob.muddat == ""
    assert "nizo turiga qarab" in javob.muddat_izohi


def test_ogohlantirish_muddatlari_165_moddaga_mos():
    m = storage.modda_top("mehnat-165")
    matn = " ".join(t.izoh for t in hujjat.tahlil("", turi="ishdan_bosatish").tekshiruvlar)
    for ibora in ("ikki oy", "ikki hafta", "uch kun"):
        assert ibora in m["matn"], f"165-moddada «{ibora}» yo'q"
        assert ibora in matn, f"tekshiruv ro'yxatida «{ibora}» yo'q"


# ---------- Javob tuzilishi ----------

@pytest.mark.parametrize("turi", hujjat.TURLAR)
def test_har_tur_uchun_royxat_va_yol_bor(turi):
    """Bironta tur ham bo'sh javob bermasligi kerak — «boshqa» ham."""
    javob = hujjat.tahlil("", turi=turi)
    assert javob.turi == turi
    assert javob.turi_nomi
    assert len(javob.tekshiruvlar) >= 3
    assert len(javob.bekor_yoli) >= 3
    assert javob.ogohlantirish


@pytest.mark.parametrize("turi", hujjat.TURLAR)
def test_keltirilgan_moddalar_bazada_bor(turi):
    """Modda topilmasa `modda` jimgina None bo'lib qoladi — buni ushlaymiz."""
    javob = hujjat.tahlil("", turi=turi)
    havolali = [x for x in javob.tekshiruvlar + javob.bekor_yoli if x.modda]
    if turi != "boshqa":
        assert havolali, f"{turi} uchun birorta qonun havolasi yo'q"
    for x in havolali:
        assert storage.modda_top(x.modda.id), f"{x.modda.id} bazada yo'q"
        assert x.modda.lex_url


def test_izohlarda_html_tegi_yoq():
    """Qalin matn `**` bilan yoziladi: `<b>` saytda ham, botda ham matn
    bo'lib ko'rinib qolardi."""
    for turi in hujjat.TURLAR:
        javob = hujjat.tahlil("", turi=turi)
        for x in javob.tekshiruvlar:
            assert "<b>" not in x.izoh and "<i>" not in x.izoh
        for q in javob.bekor_yoli:
            assert "<b>" not in q.matn and "<i>" not in q.matn


def test_tur_berilsa_aniqlash_otkazib_yuboriladi():
    javob = hujjat.tahlil(NAMUNALAR["jarima"], turi="shartnoma")
    assert javob.turi == "shartnoma"
    assert javob.ishonch == "aniq"


# ---------- Endpoint ----------

def _hujjat_yukla(monkeypatch, matn: str):
    from app.models import ChatJavob

    monkeypatch.setattr(main, "uch_qismli_javob", lambda *a, **k: ChatJavob(
        javob_topildi=True, moddalar=[], tavsiya="Tavsiya"))
    return client.post("/api/hujjat",
                       files={"fayl": ("hujjat.txt", matn.encode(), "text/plain")})


def test_endpoint_hujjat_yolini_qoshadi(monkeypatch):
    r = _hujjat_yukla(monkeypatch, NAMUNALAR["sud_fuqarolik"])
    assert r.status_code == 200
    y = r.json()["hujjat_yoli"]
    assert y["turi"] == "sud_fuqarolik"
    assert y["muddat"] == "1 oy"
    assert y["tekshiruvlar"] and y["bekor_yoli"]


def test_endpoint_organ_javobiga_bir_yil_beradi(monkeypatch):
    r = _hujjat_yukla(monkeypatch, NAMUNALAR["organ_javobi"])
    assert r.json()["hujjat_yoli"]["muddat"] == "1 yil"


def test_oddiy_chatda_hujjat_yoli_bosh(monkeypatch):
    """Fayl yuklanmagan savolda tekshiriladigan hujjat yo'q."""
    from app.models import ChatJavob

    monkeypatch.setattr(main, "javob_ol", lambda *a, **k: ChatJavob(
        javob_topildi=True, moddalar=[], tavsiya="Tavsiya"))
    r = client.post("/api/chat", json={"savol": "Nikohdan qanday ajrashaman?"})
    assert r.status_code == 200
    assert r.json()["hujjat_yoli"] is None
