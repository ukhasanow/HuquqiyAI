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

# Qidiruvda ma'nosiz keng tarqalgan so'zlar (apostrofsiz shaklda — pastga qarang)
_STOP = {
    "va", "bilan", "uchun", "ham", "yoki", "bu", "shu", "u", "men", "meni",
    "mening", "nima", "qanday", "qilish", "qilsam", "boladi", "kerak",
    "mumkin", "haqida", "boyicha", "deb", "edi", "esa",
}


def _normalizatsiya(matn: str) -> List[str]:
    """Matnni qidiruv tokenlariga ajratadi.

    Apostrof BUTUNLAY olib tashlanadi: foydalanuvchilar ko'pincha "ogirlab",
    "istemolchi" deb yozadi, bazadagi teglar esa "o'g'irlash", "iste'molchi".
    Ikkalasi bir shaklga keltirilmasa, bunday savollar hech narsa topmaydi.
    """
    matn = matn.lower().translate(_APOSTROFLAR)
    matn = _kirilldan_lotinga(matn)
    matn = matn.replace("'", "")
    tokenlar = re.findall(r"[a-z]+|\d+", matn)
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


# Savolga mos modda topilmaganda LLM'ga yuboriladigan moddalar chegarasi.
# Chegarasiz butun baza yuborilar edi — baza o'sgani sayin javob sekinlashadi
# va bunday holatda LLM baribir javob_topildi=false qaytaradi.
FALLBACK_CHEGARA = 12

# Har so'rovda har bir moddaning matnini qaytadan tokenlash qimmat, tokenlar
# esa faqat baza o'zgarganda o'zgaradi. Ro'yxat obyektining o'zi kalit bo'ladi:
# storage kesh yangilanganda yangi ro'yxat obyekti keladi va indeks qayta
# quriladi. Ro'yxatga kuchli havola saqlanadi, shuning uchun `is` solishtiruvi
# ishonchli.
_indeks_kesh: dict = {"royxat": None, "yozuvlar": None}


def _indeks(moddalar: List[dict]) -> List[tuple]:
    """Har bir modda uchun (teg, sarlavha, matn) tokenlari — bir marta hisoblanadi."""
    if _indeks_kesh["royxat"] is moddalar:
        return _indeks_kesh["yozuvlar"]
    yozuvlar = [
        (
            m,
            _normalizatsiya(" ".join(m.get("teglar", []))),
            _normalizatsiya(m.get("sarlavha", "")),
            set(_normalizatsiya(m.get("matn", ""))),
        )
        for m in moddalar
    ]
    _indeks_kesh["royxat"] = moddalar
    _indeks_kesh["yozuvlar"] = yozuvlar
    return yozuvlar


def moddalarni_qidir(savol: str, moddalar: List[dict], top_n: int = 5) -> List[dict]:
    """Savolga eng mos moddalarni qaytaradi. Hech narsa topilmasa —
    bazadan cheklangan namuna qaytadi (yakuniy tanlovni LLM qiladi)."""
    savol_tokenlar = _normalizatsiya(savol)
    natijalar = []
    for m, teg_tokenlar, sarlavha_tokenlar, matn_tokenlar in _indeks(moddalar):
        ball = 0
        for st in savol_tokenlar:
            # Teglar qo'lda tanlangani uchun eng ishonchli signal: apostrof
            # olib tashlangach ba'zi so'zlar tasodifan o'xshab qoladi
            # (masalan "og'ir" va "o'g'irlab"), teg vazni shu shovqindan
            # ustun turishi kerak.
            if any(_mos(st, t) for t in teg_tokenlar):
                ball += 4
            if any(_mos(st, t) for t in sarlavha_tokenlar):
                ball += 2
            if any(_mos(st, t) for t in matn_tokenlar):
                ball += 1
        if ball > 0:
            natijalar.append((ball, m))
    natijalar.sort(key=lambda x: -x[0])
    if not natijalar:
        return list(moddalar[:FALLBACK_CHEGARA])  # ishonch past
    return [m for _, m in natijalar[:top_n]]
