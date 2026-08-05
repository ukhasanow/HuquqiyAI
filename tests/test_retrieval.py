# Qidiruv sifati testlari — real savollar bo'yicha regressiya to'ri.
#
# Bu testlarning maqsadi qidiruv kodini emas, JAVOB SIFATINI qo'riqlash:
# baza kengayganda yoki skoring o'zgarganda foydalanuvchi savoli hamon
# to'g'ri kodeksga tushishi kerak. Teg qo'shilganda ham shu yerda tekshiriladi.
import json
from pathlib import Path

import pytest

from app import storage
from app.services import llm, retrieval

BASE_DIR = Path(__file__).resolve().parent.parent


# (savol, kutilgan hujjat prefiksi) — javob top-3 ichida bo'lishi kerak.
# Savollar ataylab foydalanuvchi tilida: qonun atamalari emas, jonli gap.
SAVOLLAR = [
    # Mehnat
    ("ish haqimni bermayapti nima qilay", "mehnat"),
    ("meni ishdan bo'shatib yuborishdi, noqonuniy", "mehnat"),
    ("mehnat ta'tili necha kun", "mehnat"),
    # Oila
    ("aliment miqdori qancha bo'ladi", "oila"),
    ("nikohdan ajrashmoqchiman qanday", "oila"),
    # Iste'molchi
    ("telefon buzuq chiqdi qaytarib bermoqchiman", "istemol"),
    # Fuqarolik
    ("qo'shnim ijara haqini to'lamayapti", "fuqarolik"),
    # Uy-joy
    ("ijara shartnomam bor, uydan chiqarib yubormoqchi", "uyjoy"),
    ("kommunal to'lovlarni to'lamasam nima bo'ladi", "uyjoy"),
    # Ma'muriy va jinoyat
    ("mashinada telefonda gaplashsam jarima bormi", "mjk"),
    ("meni aldab pulimni olishdi firibgarlik", "jk"),
    # Yer
    ("tomorqa yerimni tortib olishmoqchi", "yer"),
    ("yer uchastkasini qanday ro'yxatdan o'tkazaman", "yer"),
    ("uy qurish uchun yer olsam bo'ladimi", "yer"),
    # Sud (FPK)
    ("sudga da'vo arizasi qanday yoziladi", "fpk"),
    ("sudga ariza berish uchun davlat boji qancha", "fpk"),
    ("apellyatsiya shikoyatini necha kunda berish kerak", "fpk"),
    # Soliq
    ("daromad solig'i necha foiz", "soliq"),
    ("deklaratsiyani qachon topshirish kerak", "soliq"),
    ("uy-joy uchun mol-mulk solig'idan ozod bo'lamanmi", "soliq"),
    # Murojaatlar
    ("arizamga necha kunda javob berishadi", "murojaat"),
    ("hokimiyatga shikoyat qilsam ko'rib chiqishadimi", "murojaat"),
    # Yo'l harakati (Qonun)
    ("haydovchilik guvohnomasi qanday olinadi", "yhq"),
    ("guvohnomamni bekor qilishdi", "yhq"),
    # Yo'l harakati qoidalari — jarima qaysi bandni buzganini ko'rsatadi
    ("temir yo'l kesishmasidan qanday o'tish kerak", "yhqoida"),
    ("quvib o'tish qachon taqiqlanadi", "yhqoida"),
    ("qayerda to'xtab turish mumkin emas", "yhqoida"),
    # YPX nizomi — radardan foydalanish tartibi (jarima qonuniyligi uchun)
    ("radar sertifikati bormi, tekshirsa bo'ladimi", "ypx"),
    ("yo'l patrul xodimi meni to'xtatganda nima qilishi kerak", "ypx"),
    # Konstitutsiya
    ("ta'lim olish huquqim bormi", "konst"),
    ("pensiya olish huquqi konstitutsiyada bormi", "konst"),
]


@pytest.fixture(scope="module")
def moddalar():
    return storage.moddalarni_oqi()


@pytest.mark.parametrize("savol,hujjat", SAVOLLAR, ids=[s[:32] for s, _ in SAVOLLAR])
def test_savol_togri_hujjatga_tushadi(moddalar, savol, hujjat):
    idlar = [m["id"] for m in retrieval.moddalarni_qidir(savol, moddalar)]
    assert any(i.startswith(hujjat + "-") for i in idlar[:3]), f"{savol!r} -> {idlar}"


def test_har_bir_hujjat_kamida_bitta_savol_bilan_qoplangan(moddalar):
    """Yangi kodeks qo'shilsa, unga savol ham yozilsin — aks holda uning
    qidiruvda topilishini hech narsa tekshirmaydi."""
    bazadagi = {m["id"].split("-")[0] for m in moddalar}
    qoplangan = {h for _, h in SAVOLLAR}
    assert bazadagi - qoplangan == set(), f"savolsiz qolgan hujjatlar: {bazadagi - qoplangan}"


# ---------- Skoring xatti-harakati ----------

def test_kam_uchraydigan_soz_ogirroq(moddalar):
    """IDF: butun bazada uchraydigan so'z ("shartnoma") kam uchraydigani
    ("aliment") bilan bir xil vaznda bo'lsa, aniq savol ham umumiy moddaga
    tushib ketardi."""
    indeks = retrieval._indeks(moddalar)
    kam = indeks.idf(indeks.mos_tokenlar("aliment"))
    kop = indeks.idf(indeks.mos_tokenlar("shartnoma"))
    assert kam > kop > 0


def test_uzun_modda_uzunligi_uchun_ustunlik_olmaydi(moddalar):
    """BM25 uzunlik normallashtirishi: bir xil so'z uchragan ikki moddadan
    uzunrog'i shu hisobga yuqoriga chiqmasligi kerak."""
    indeks = retrieval._indeks(moddalar)
    assert indeks.ort_uzunlik > 0
    assert len(indeks.uzunlik) == len(moddalar)
    # Normallashtirish koeffitsienti uzunlik bilan o'sadi (ball esa unga bo'linadi)
    qisqa = min(indeks.uzunlik)
    uzun = max(indeks.uzunlik)
    n_qisqa = 1 - retrieval.BM25_B + retrieval.BM25_B * qisqa / indeks.ort_uzunlik
    n_uzun = 1 - retrieval.BM25_B + retrieval.BM25_B * uzun / indeks.ort_uzunlik
    assert n_uzun > n_qisqa


def test_teg_matndan_kuchliroq(moddalar):
    """Teglar qo'lda tanlangan signal — matndagi tasodifiy moslikdan ustun turishi kerak."""
    assert retrieval.TEG_VAZN > retrieval.SARLAVHA_VAZN > 1


# ---------- Baza yaxlitligi ----------

def test_mavzular_organlar_bilan_mos():
    """LLM tanlagan mavzu bo'yicha kontakt bazadan olinadi: ro'yxatlar teng
    bo'lmasa, model tanlagan mavzuga organ topilmay "umumiy"ga tushib qoladi."""
    organlar = json.loads((BASE_DIR / "data" / "organlar.json").read_text(encoding="utf-8"))
    assert {o["mavzu"] for o in organlar} == set(llm.MUROJAAT_MAVZULARI)


def test_modda_idlari_takrorlanmaydi(moddalar):
    idlar = [m["id"] for m in moddalar]
    assert len(idlar) == len(set(idlar))


def test_hamma_modda_lex_url_va_matnga_ega(moddalar):
    for m in moddalar:
        assert m["matn"].strip(), m["id"]
        assert m["lex_url"].startswith("https://lex.uz/acts/"), m["id"]
        assert m["teglar"], m["id"]
        assert m["holat"] in ("verified", "needs_verification"), m["id"]
