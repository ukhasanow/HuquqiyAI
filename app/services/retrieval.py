# Savolga mos moddalarni topish (kalit so'z + teg skoring).
# Korpus kichik bo'lgani uchun oddiy leksik qidiruv yetarli;
# semantik qidiruv (embedding) — keyingi bosqich (README'ga qarang).
import re
from typing import List

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

# Qidiruvda ma'nosiz keng tarqalgan so'zlar
_STOP = {
    "va", "bilan", "uchun", "ham", "yoki", "bu", "shu", "u", "men", "meni",
    "mening", "nima", "qanday", "qilish", "qilsam", "bo'ladi", "kerak",
    "mumkin", "haqida", "bo'yicha", "deb", "edi", "esa",
}


def _normalizatsiya(matn: str) -> List[str]:
    matn = matn.lower().translate(_APOSTROFLAR)
    matn = _kirilldan_lotinga(matn)
    tokenlar = re.findall(r"[a-z']+|\d+", matn)
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


def moddalarni_qidir(savol: str, moddalar: List[dict], top_n: int = 5) -> List[dict]:
    """Savolga eng mos moddalarni qaytaradi. Hech narsa topilmasa —
    butun bazani qaytaradi (korpus kichik, yakuniy tanlovni LLM qiladi)."""
    savol_tokenlar = _normalizatsiya(savol)
    natijalar = []
    for m in moddalar:
        teg_tokenlar = _normalizatsiya(" ".join(m.get("teglar", [])))
        sarlavha_tokenlar = _normalizatsiya(m.get("sarlavha", ""))
        matn_tokenlar = set(_normalizatsiya(m.get("matn", "")))
        ball = 0
        for st in savol_tokenlar:
            if any(_mos(st, t) for t in teg_tokenlar):
                ball += 3
            if any(_mos(st, t) for t in sarlavha_tokenlar):
                ball += 2
            if any(_mos(st, t) for t in matn_tokenlar):
                ball += 1
        if ball > 0:
            natijalar.append((ball, m))
    natijalar.sort(key=lambda x: -x[0])
    if not natijalar:
        return list(moddalar)  # ishonch past — hammasini LLM'ga beramiz
    return [m for _, m in natijalar[:top_n]]
