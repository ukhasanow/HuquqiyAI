# Savolga mos moddalarni topish (BM25 uslubidagi leksik qidiruv).
# Semantik qidiruv (embedding) — keyingi bosqich (README'ga qarang).
import math
import re
from typing import Dict, List, Set, Tuple

# O'zbek lotin yozuvidagi turli apostrof belgilarini birlashtiramiz
_APOSTROFLAR = str.maketrans({"ʻ": "'", "ʼ": "'", "’": "'", "‘": "'", "`": "'"})

# O'zbek kirill yozuvini lotinga o'girish — kirillcha savollar ham qidiruvda ishlasin
_KIRILL_JUFT = [
    ("ш", "sh"), ("ч", "ch"), ("нг", "ng"), ("ё", "yo"), ("ю", "yu"), ("я", "ya"),
    ("ц", "ts"), ("щ", "sh"), ("ғ", "g'"), ("ў", "o'"), ("қ", "q"), ("ҳ", "h"),
    ("а", "a"), ("б", "b"), ("в", "v"), ("г", "g"), ("д", "d"), ("е", "e"),
    ("ж", "j"), ("з", "z"), ("и", "i"), ("й", "y"), ("к", "k"), ("л", "l"),
    ("м", "m"), ("н", "n"), ("о", "o"), ("п", "p"), ("р", "r"), ("с", "s"),
    ("т", "t"), ("у", "u"), ("ф", "f"), ("х", "x"), ("э", "e"), ("ъ", "'"),
    ("ь", ""),
]


def _kirilldan_lotinga(matn: str) -> str:
    for k, l in _KIRILL_JUFT:
        matn = matn.replace(k, l)
    return matn

# Qidiruvda ma'nosiz keng tarqalgan so'zlar (apostrofsiz shaklda — pastga qarang)
_STOP = {
    "va", "bilan", "uchun", "ham", "yoki", "bu", "shu", "u", "men", "meni",
    "mening", "nima", "qanday", "qilish", "qilsam", "boladi", "kerak",
    "mumkin", "haqida", "boyicha", "deb", "edi", "esa",
}


def normallashtir(matn: str) -> str:
    """Matnni solishtirish uchun yagona shaklga keltiradi.

    Kirill lotinga o'giriladi, apostrofning barcha ko'rinishi olib tashlanadi.
    Hujjat turini aniqlash ham shu shakldan foydalanadi: hujjatda "qaror",
    "қарор" yoki "qaroʻr" yozilgan bo'lishi mumkin, ular bir xil bo'lishi kerak.
    """
    matn = matn.lower().translate(_APOSTROFLAR)
    return _kirilldan_lotinga(matn).replace("'", "")


def _normalizatsiya(matn: str) -> List[str]:
    """Matnni qidiruv tokenlariga ajratadi.

    Apostrof BUTUNLAY olib tashlanadi: foydalanuvchilar ko'pincha "ogirlab",
    "istemolchi" deb yozadi, bazadagi teglar esa "o'g'irlash", "iste'molchi".
    Ikkalasi bir shaklga keltirilmasa, bunday savollar hech narsa topmaydi.
    """
    tokenlar = re.findall(r"[a-z]+|\d+", normallashtir(matn))
    return [t for t in tokenlar if t not in _STOP and len(t) > 2]


def _mos(a: str, b: str) -> bool:
    """Yengil o'zak-moslik: qo'shimchalarni hisobga olib prefiks bo'yicha solishtirish."""
    if a == b:
        return True
    n = min(len(a), len(b))
    if n < 4:
        return False
    k = max(4, n - 2)
    return a[:k] == b[:k]


# _mos ikki tokenni faqat dastlabki 4 belgisi bir xil bo'lgandagina moslashtiradi
# (qisqa tokenlar esa aynan teng bo'lishi kerak). Shu sababli lug'atni dastlabki
# 4 belgi bo'yicha guruhlarga bo'lish mumkin — savol tokeni uchun butun lug'atni
# emas, bitta guruhni ko'rish yetarli. Baza o'sganda qidiruv shu hisobdan sekinlashmaydi.
def _guruh_kaliti(token: str) -> str:
    return token[:4]


# ---------- Skoring sozlamalari ----------

# Teg va sarlavha — qo'lda tanlangan signal, matn esa statistik. Shuning uchun
# ular ko'paytma sifatida saqlanadi: mos kelgan so'zning IDF qiymati shu vaznga
# ko'paytiriladi.
TEG_VAZN = 4.0
SARLAVHA_VAZN = 2.0

# BM25 sozlamalari. b — uzunlik normallashtirish kuchi: 0 bo'lsa uzunlik
# hisobga olinmaydi (eski xatti-harakat), 1 bo'lsa to'liq. Soliq va FPK
# moddalari boshqa kodekslarnikidan bir necha barobar uzun, shuning uchun
# normallashtirishsiz ular tasodifiy so'z mosligi bilan yuqoriga chiqib qoladi.
BM25_K1 = 1.2
BM25_B = 0.75

# Mos modda topilmaganda LLM'ga yuboriladigan moddalar chegarasi.
# Chegarasiz butun baza yuborilar edi — baza o'sgani sayin javob sekinlashadi
# va bunday holatda LLM baribir javob_topildi=false qaytaradi.
FALLBACK_CHEGARA = 15


class _Indeks:
    """Bir korpus uchun bir marta quriladigan teskari indeks.

    matn:     token -> {modda_o'rni: tf}
    teg:      token -> {modda_o'rni}
    sarlavha: token -> {modda_o'rni}
    """

    def __init__(self, moddalar: List[dict]):
        self.moddalar = moddalar
        self.matn: Dict[str, Dict[int, int]] = {}
        self.teg: Dict[str, Set[int]] = {}
        self.sarlavha: Dict[str, Set[int]] = {}
        self.uzunlik: List[int] = []
        self.guruhlar: Dict[str, Set[str]] = {}

        for i, m in enumerate(moddalar):
            matn_tokenlar = _normalizatsiya(m.get("matn", ""))
            self.uzunlik.append(len(matn_tokenlar))
            for t in matn_tokenlar:
                self.matn.setdefault(t, {})
                self.matn[t][i] = self.matn[t].get(i, 0) + 1
            for t in _normalizatsiya(" ".join(m.get("teglar", []))):
                self.teg.setdefault(t, set()).add(i)
            for t in _normalizatsiya(m.get("sarlavha", "")):
                self.sarlavha.setdefault(t, set()).add(i)

        self.ort_uzunlik = (sum(self.uzunlik) / len(self.uzunlik)) if self.uzunlik else 0.0
        for lugat in (self.matn, self.teg, self.sarlavha):
            for t in lugat:
                self.guruhlar.setdefault(_guruh_kaliti(t), set()).add(t)

    def mos_tokenlar(self, savol_tokeni: str) -> List[str]:
        return [t for t in self.guruhlar.get(_guruh_kaliti(savol_tokeni), ()) if _mos(savol_tokeni, t)]

    def idf(self, tokenlar: List[str]) -> float:
        """Kam uchraydigan so'z og'irroq. df — shu so'z (yoki uning o'zakdoshi)
        uchraydigan moddalar soni."""
        hujjatlar: Set[int] = set()
        for t in tokenlar:
            hujjatlar.update(self.matn.get(t, {}))
            hujjatlar.update(self.teg.get(t, ()))
            hujjatlar.update(self.sarlavha.get(t, ()))
        df = len(hujjatlar)
        n = len(self.moddalar)
        if df == 0:
            return 0.0
        return math.log(1 + (n - df + 0.5) / (df + 0.5))


# Indeks faqat baza o'zgarganda qayta quriladi. Ro'yxat obyektining o'zi kalit
# bo'ladi: storage kesh yangilanganda yangi ro'yxat obyekti keladi. Ro'yxatga
# kuchli havola saqlanadi, shuning uchun `is` solishtiruvi ishonchli.
_indeks_kesh: dict = {"royxat": None, "indeks": None}


def _indeks(moddalar: List[dict]) -> _Indeks:
    if _indeks_kesh["royxat"] is moddalar:
        return _indeks_kesh["indeks"]
    indeks = _Indeks(moddalar)
    _indeks_kesh["royxat"] = moddalar
    _indeks_kesh["indeks"] = indeks
    return indeks


def _zaxira_namuna(moddalar: List[dict]) -> List[dict]:
    """Mos modda topilmaganda LLM'ga yuboriladigan namuna.

    Fayldagi birinchi N yozuv emas — u bitta-ikkita kodeksga tiqilib qoladi va
    savol mavzusiga umuman aloqasi bo'lmasligi mumkin. O'rniga har hujjatdan
    bittadan modda olinadi: kamida mavzular kesimi ko'rinadi.
    """
    korilgan: Set[str] = set()
    namuna = []
    for m in moddalar:
        hujjat = m["id"].split("-")[0]
        if hujjat not in korilgan:
            korilgan.add(hujjat)
            namuna.append(m)
            if len(namuna) >= FALLBACK_CHEGARA:
                break
    return namuna


def moddalarni_qidir(savol: str, moddalar: List[dict], top_n: int = 5) -> List[dict]:
    """Savolga eng mos moddalarni qaytaradi. Hech narsa topilmasa —
    bazadan cheklangan namuna qaytadi (yakuniy tanlovni LLM qiladi)."""
    indeks = _indeks(moddalar)
    ballar: Dict[int, float] = {}

    for st in _normalizatsiya(savol):
        mos = indeks.mos_tokenlar(st)
        if not mos:
            continue
        idf = indeks.idf(mos)
        if idf <= 0:
            continue

        # Matn: BM25 — takrorlanish foydali, lekin uzun modda jazolanadi
        chastota: Dict[int, int] = {}
        for t in mos:
            for i, tf in indeks.matn.get(t, {}).items():
                chastota[i] = chastota.get(i, 0) + tf
        for i, tf in chastota.items():
            norma = 1 - BM25_B + BM25_B * (indeks.uzunlik[i] / indeks.ort_uzunlik if indeks.ort_uzunlik else 1)
            ballar[i] = ballar.get(i, 0.0) + idf * tf * (BM25_K1 + 1) / (tf + BM25_K1 * norma)

        # Teg va sarlavha: mavjudlik yetarli, takrorlanish ma'no bermaydi
        for t in mos:
            for i in indeks.teg.get(t, ()):
                ballar[i] = ballar.get(i, 0.0) + TEG_VAZN * idf
            for i in indeks.sarlavha.get(t, ()):
                ballar[i] = ballar.get(i, 0.0) + SARLAVHA_VAZN * idf

    if not ballar:
        return _zaxira_namuna(moddalar)  # ishonch past

    tartib: List[Tuple[float, int]] = sorted(((-b, i) for i, b in ballar.items()))
    return [moddalar[i] for _, i in tartib[:top_n]]
