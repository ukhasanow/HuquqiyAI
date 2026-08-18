import re
from typing import List, Optional

from .. import storage
from ..config import ANTHROPIC_API_KEY, GEMINI_API_KEY, GROQ_API_KEY, MAX_HUJJAT_BELGILAR, OPENAI_API_KEY
from ..models import ModdaJavob, ShartnomaBand, ShartnomaJavob, ShartnomaMazmuni
from . import llm, retrieval
from .javob import AiSozlanmagan, AiXato

# Shartnoma bandi: "4.3." yoki "4.3" yoki "1.2.1." qatorning boshida.
_BAND_NAQSHI = re.compile(r"^\s*(\d+(?:\.\d+)+)\.?\s+(.+)$", re.MULTILINE)

BAND_UCHUN_NOMZOD = 3
MAX_NOMZOD = 30

# Bandlarga ajratib bo'lmagan (raqamlanmagan) shartnoma uchun zaxira
UMUMIY_NOMZOD = 20

XAVF_TARTIBI = {"qizil": 0, "sariq": 1, "yashil": 2}

_TUR_BELGILARI = [
    ("mehnat", ("mehnat shartnomasi", "ish beruvchi", "xodim", "lavozim", "ish haqi")),
    ("ijara", ("ijara", "ijaraga beruvchi", "ijaraga oluvchi", "yollash")),
    ("kredit", ("kredit", "qarz shartnomasi", "qarz oluvchi", "foiz stavkasi", "bank")),
    ("oldi-sotdi", ("oldi-sotdi", "sotuvchi", "xaridor", "tovar", "mahsulot")),
]


ASOSIY_MODDALAR = {
    "mehnat": [
        "mehnat-21",    # xodimning huquqlari
        "mehnat-130",   # sinov muddati
        "mehnat-132",   # sinov natijasi
        "mehnat-137",   # mehnat shartlarini o'zgartirish
        "mehnat-160",   # xodim tashabbusi bilan bekor qilish
        "mehnat-182",   # ish vaqtining normal davomiyligi
        "mehnat-183",   # qisqartirilgan ish vaqti
        "mehnat-208",   # bayram kunlari
        "mehnat-209",   # dam olish/bayram kunlarida ishlash
        "mehnat-253",   # ish haqini to'lash muddatlari
        "mehnat-262",   # ish vaqtidan tashqari ish haqi
        "mehnat-263",   # dam olish kunidagi ish haqi
        "mehnat-269",   # ish haqidan ushlab qolish chegarasi
        "mehnat-343",   # to'liq moddiy javobgarlik
    ],
    "ijara": [
        "fuqarolik-535", "fuqarolik-539", "fuqarolik-540",
        "fuqarolik-544", "fuqarolik-551", "fuqarolik-552", "fuqarolik-260",
    ],
    "kredit": [
        "fuqarolik-732", "fuqarolik-733", "fuqarolik-734",
        "fuqarolik-735", "fuqarolik-260", "istemol-13",
    ],
    "oldi-sotdi": [
        "istemol-13", "istemol-14", "istemol-15",
        "istemol-17", "istemol-20", "fuqarolik-386",
    ],
}


def turni_taxmin(matn: str) -> str:
    """Shartnoma turini matndagi so'zlar bo'yicha taxmin qiladi.

    Bu yakuniy tur EMAS — yakuniysini LLM belgilaydi. Bu faqat qaysi imperativ
    normalarni nomzodlarga qo'shishni hal qilish uchun kerak.
    """
    past = (matn or "").lower()
    ballar = [
        (sum(past.count(soz) for soz in sozlar), tur)
        for tur, sozlar in _TUR_BELGILARI
    ]
    eng_yaxshi = max(ballar)
    return eng_yaxshi[1] if eng_yaxshi[0] else "boshqa"


def bandlarga_ajrat(matn: str) -> List[str]:
    """Shartnoma matnidan raqamlangan bandlarni ajratadi."""
    return [f"{raqam} {mazmun.strip()}" for raqam, mazmun in _BAND_NAQSHI.findall(matn or "")]


def _nomzod_moddalar(matn: str) -> List[dict]:
    """Tahlil uchun nomzod moddalar.

    Ikki manba birlashtiriladi: shartnoma turiga xos imperativ normalar
    (doim) va har band bo'yicha alohida qidiruv natijalari. Butun shartnoma
    bitta so'rov qilib berilsa, uzun bandlarning tokenlari qisqa (lekin
    muhim) bandlarni bosib ketadi.
    """
    hamma = storage.moddalarni_oqi()
    korilgan = set()
    nomzodlar = []

    def qosh(modda):
        if modda and modda["id"] not in korilgan:
            korilgan.add(modda["id"])
            nomzodlar.append(modda)

    for modda_id in ASOSIY_MODDALAR.get(turni_taxmin(matn), []):
        qosh(storage.modda_top(modda_id))

    bandlar = bandlarga_ajrat(matn)
    if not bandlar:
        for m in retrieval.moddalarni_qidir(matn[:2000], hamma, top_n=UMUMIY_NOMZOD):
            qosh(m)
        return nomzodlar[:MAX_NOMZOD]

    for band in bandlar:
        if len(nomzodlar) >= MAX_NOMZOD:
            break
        for m in retrieval.moddalarni_qidir(band, hamma, top_n=BAND_UCHUN_NOMZOD):
            qosh(m)
    return nomzodlar[:MAX_NOMZOD]


def _moddani_biriktir(modda_id: str) -> Optional[ModdaJavob]:
    """LLM tanlagan ID bo'yicha ASL moddani bazadan oladi.

    Model mavjud bo'lmagan ID qaytarsa (yoki o'ylab topsa) — band moddasiz
    ko'rsatiladi. Yolg'on havoladan ko'ra havolasizlik yaxshiroq.
    """
    if not modda_id:
        return None
    m = storage.modda_top(modda_id.strip())
    return ModdaJavob(**m) if m else None


def _bandlarni_tuz(xom: list) -> List[ShartnomaBand]:
    bandlar = []
    for b in xom or []:
        xavf = b.get("xavf") if b.get("xavf") in XAVF_TARTIBI else "sariq"
        bandlar.append(ShartnomaBand(
            band=str(b.get("band", "")).strip(),
            mazmuni=str(b.get("mazmuni", "")).strip(),
            xavf=xavf,
            izoh=str(b.get("izoh", "")).strip(),
            modda=_moddani_biriktir(str(b.get("modda_id", ""))),
        ))
   
    bandlar.sort(key=lambda b: XAVF_TARTIBI[b.xavf])
    return bandlar


def shartnomani_tahlil(hujjat_matni: str) -> ShartnomaJavob:
    """Shartnomani band-band tahlil qiladi."""
    if not any((ANTHROPIC_API_KEY, GEMINI_API_KEY, GROQ_API_KEY, OPENAI_API_KEY)):
        raise AiSozlanmagan()

    matn = (hujjat_matni or "").strip()[:MAX_HUJJAT_BELGILAR]
    if not matn:
        raise AiXato(ValueError("Hujjat matni bo'sh"))

    try:
        natija = llm.shartnoma_tahlil_yarat(matn, _nomzod_moddalar(matn))
    except Exception as e:
        raise AiXato(e) from e

    mazmun = natija.get("umumiy_mazmun") or {}
    turi = natija.get("shartnoma_turi")
    return ShartnomaJavob(
        shartnoma_turi=turi if turi in llm.SHARTNOMA_TURLARI else "boshqa",
        umumiy_mazmun=ShartnomaMazmuni(
            tomonlar=str(mazmun.get("tomonlar", "")),
            predmet=str(mazmun.get("predmet", "")),
            summa=str(mazmun.get("summa", "")),
            muddat=str(mazmun.get("muddat", "")),
        ),
        bandlar=_bandlarni_tuz(natija.get("bandlar")),
        xulosa=str(natija.get("xulosa", "")),
        bandlar_soni=int(natija.get("bandlar_soni") or 0),
    )
