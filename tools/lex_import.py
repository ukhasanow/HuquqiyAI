#!/usr/bin/env python3
"""lex.uz'dan qonun moddalarini bazaga import qilish.

Modda matni HECH QACHON qo'lda yozilmaydi va model tomonidan generatsiya
qilinmaydi — faqat shu skript orqali lex.uz'dan olinadi. Loyihaning asosiy
ishonch kafolati shunda.

Ishlatish:
    python tools/lex_import.py --hujjat oila --quruq
    python tools/lex_import.py --hujjat soliq --faqat 205,206,207
    python tools/lex_import.py --hujjat oila --tekshir
    python tools/lex_import.py --akt -12345 --prefiks yangi --nom "..."   # registrda yo'q hujjat

lex.uz HTML tuzilishi:
    <div class="CLAUSE_DEFAULT"><div id="-158603">13-modda. Sarlavha</div></div>
    <div class="ACT_TEXT"><div id="...">modda matni</div></div>   (bir nechta bo'lishi mumkin)

Modda matniga FAQAT ACT_TEXT bloklari kiradi. Boshqa bloklar ataylab tashlab
ketiladi: COMMENT (LexUZ sharhi — qonun matni emas), CHANGES_ORIGINS (tahrir
tarixi), BY_DEFAULT/INDEXES_ON_REF (bo'sh yoki navigatsiya).
"""
import argparse
import json
import re
import sys
import time
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
QONUNLAR_FAYL = BASE_DIR / "data" / "qonunlar.json"
KESH_DIR = BASE_DIR / ".cache" / "lex"

# Ma'lum hujjatlar: kalit -> (lex.uz akt id, modda id prefiksi, qonun_nomi, tuzilma).
#
# `tuzilma`:
#   "modda" — qonun/kodeks, "13-modda. Sarlavha" ko'rinishidagi bloklar
#   "band"  — hukumat qarori ilovasi (Yo'l harakati qoidalari), sarlavhasiz
#             raqamlangan bandlar: "116. Transport vositalarining haydovchilari..."
#
# `qonun_nomi` ataylab qo'lda yozilgan: lex.uz sarlavhani BOSH HARFLARDA beradi
# ("OʻZBEKISTON RESPUBLIKASINING OILA KODEKSI"), bazada esa u foydalanuvchiga
# ko'rinadigan odatiy shaklda saqlanadi. Registrsiz har import bu maydonni
# buzar edi.
#
# Fuqarolik kodeksi lex.uz'da ikki qismga bo'lingan (1- va 2-qism), lekin
# bazada bitta kodeks sifatida — ikkalasi ham "fuqarolik" prefiksini oladi.
HUJJATLAR: Dict[str, Tuple[str, str, str, str]] = {
    "oila": ("-104720", "oila", "O'zbekiston Respublikasining Oila kodeksi", "modda"),
    "mehnat": ("-6257288", "mehnat", "O'zbekiston Respublikasining Mehnat kodeksi", "modda"),
    "fuqarolik-1": ("-111189", "fuqarolik", "O'zbekiston Respublikasining Fuqarolik kodeksi", "modda"),
    "fuqarolik-2": ("-180552", "fuqarolik", "O'zbekiston Respublikasining Fuqarolik kodeksi", "modda"),
    "istemol": ("-4704", "istemol", "O'zbekiston Respublikasining \"Iste'molchilarning huquqlarini himoya qilish to'g'risida\"gi Qonuni", "modda"),
    "uyjoy": ("-106136", "uyjoy", "O'zbekiston Respublikasining Uy-joy kodeksi", "modda"),
    "mjk": ("-97664", "mjk", "O'zbekiston Respublikasining Ma'muriy javobgarlik to'g'risidagi kodeksi", "modda"),
    "jk": ("-111453", "jk", "O'zbekiston Respublikasining Jinoyat kodeksi", "modda"),
    "soliq": ("-4674902", "soliq", "O'zbekiston Respublikasining Soliq kodeksi", "modda"),
    "konst": ("-6445145", "konst", "O'zbekiston Respublikasi Konstitutsiyasi", "modda"),
    "yer": ("-152653", "yer", "O'zbekiston Respublikasining Yer kodeksi", "modda"),
    "fpk": ("-3517337", "fpk", "O'zbekiston Respublikasining Fuqarolik protsessual kodeksi", "modda"),
    "murojaat": ("-2509996", "murojaat", "O'zbekiston Respublikasining \"Jismoniy va yuridik shaxslarning murojaatlari to'g'risida\"gi Qonuni", "modda"),
    "yhq": ("-6764454", "yhq", "O'zbekiston Respublikasining \"Yo'l harakati to'g'risida\"gi Qonuni", "modda"),
    # Qoidalar — Qonundan ALOHIDA hujjat. Jarima qarorida ikkalasi ham
    # ko'rsatiladi: MJK moddasi (javobgarlik) va Qoidalar bandi (nima buzilgan).
    "yhqoida": ("-5953883", "yhqoida", "O'zbekiston Respublikasining Yo'l harakati qoidalari", "band"),
}

# Kuchini yo'qotgan, ATAYLAB ishlatilmaydigan tahrirlar — bir xil nom bilan
# lex.uz'da hanuz ochiladi, shuning uchun adashib olinmasligi kerak:
#   -24741   "Yo'l harakati xavfsizligi to'g'risida" (1999) — 21.07.2024 dan kuchsiz,
#            o'rniga -6764454 "Yo'l harakati to'g'risida" (O'RQ-900)
#   -186105  Fuqarolik protsessual kodeksi (1997) — 01.04.2018 dan kuchsiz,
#            o'rniga -3517337 (2018)
#   -2850459 Yo'l harakati qoidalari (VM 370-son, 2015) — 01.05.2022 dan kuchsiz,
#            o'rniga -5953883 (VM 172-son, 2022). Qidiruvda ikkalasi ham chiqadi.

# 128<sup>1</sup> — teglar shunchaki olib tashlansa "1281" bo'lib ketadi,
# aslida 128¹. Shuning uchun avval Unicode ustki indeksga aylantiramiz.
USTKI_INDEKS = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
USTKIDAN_ODDIY = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")

# "13-modda." yoki "128¹-modda." — bob sarlavhalaridan ("1-bob.") ajratish uchun
MODDA_SARLAVHA = re.compile(r"^(\d+[⁰¹²³⁴⁵⁶⁷⁸⁹]*)-modda\.")

# Band boshi: "116. Transport vositalarining..." yoki (lex.uz matnida uchraydi)
# bo'sh joysiz "117.Temir yoʻl kesishmasiga...".
#
# Nuqtadan keyin RAQAM kelmasligi shart: "5.1. yoʻl belgisi bilan belgilangan"
# — bu band emas, band ichidagi yoʻl belgisi raqami. Bo'sh joyni majburiy
# qilsak 117-band butunlay yo'qoladi, raqamga ruxsat bersak yoʻl belgilari
# band bo'lib ketadi.
BAND_BOSHI = re.compile(r"^(\d+)\.\s*(\D.*)$")

# Bob sarlavhasi: "18-bob. Temir yoʻl kesishmalari orqali harakatlanish".
# Qoidalardan keyingi ilovalarda ("Yoʻl belgilari") sarlavhalar boshqacha va
# raqamlash qaytadan boshlanadi — shuning uchun ilova chegarasi tekshiriladi.
BOB_SARLAVHA = re.compile(r"^\d+-bob\.\s*(.+)$")

# Modda matnidan teg nomzodlarini ajratishda tashlab yuboriladigan so'zlar
_TEG_STOP = {
    "va", "bilan", "uchun", "ham", "yoki", "hamda", "ushbu", "mazkur", "boshqa",
    "qilish", "qilishning", "qilinishi", "berish", "berilishi", "olish", "haqida",
    "toʻgʻrisidagi", "togrisidagi", "tartibi", "tartibida", "asoslari", "umumiy",
    "shuningdek", "agar", "lozim", "kerak", "mumkin", "hollarda",
    "boʻlgan", "bolgan", "doir", "etish", "oʻzbekiston", "ozbekiston",
    "respublikasi", "respublikasida", "respublikasining",
}


# ---------- HTML ni bloklarga ajratish ----------

class _BlokParser(HTMLParser):
    """Yuqori darajadagi <div class="..."> bloklarini matni bilan yig'adi.

    Har bir ichki <div> yangi paragraf hisoblanadi — lex.uz moddaning har bir
    xatboshisini alohida div'ga o'raydi.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.bloklar: List[Tuple[str, Optional[str], List[str]]] = []
        self._sinf: Optional[str] = None
        self._chuqurlik = 0
        self._anchor: Optional[str] = None
        self._paragraflar: List[str] = []
        self._joriy: List[str] = []
        self._sup = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "div":
            if self._sinf is None:
                sinf = a.get("class", "")
                if sinf:
                    self._sinf = sinf
                    self._chuqurlik = 1
                    self._anchor = None
                    self._paragraflar = []
                    self._joriy = []
            else:
                self._chuqurlik += 1
                # Blokning birinchi ichki div id'si — lex.uz anchor'i
                if self._anchor is None and a.get("id"):
                    self._anchor = a["id"]
                self._paragrafni_yop()
        elif tag == "sup":
            self._sup = True
        elif tag == "br" and self._sinf is not None:
            self._paragrafni_yop()

    def handle_endtag(self, tag):
        if tag == "sup":
            self._sup = False
        elif tag == "div" and self._sinf is not None:
            self._chuqurlik -= 1
            if self._chuqurlik == 0:
                self._paragrafni_yop()
                self.bloklar.append((self._sinf, self._anchor, self._paragraflar))
                self._sinf = None

    def handle_data(self, data):
        if self._sinf is None:
            return
        if self._sup:
            data = data.strip().translate(USTKI_INDEKS)
        self._joriy.append(data)

    def _paragrafni_yop(self):
        # Ketma-ket bo'sh joylar bittaga keltiriladi: lex.uz matn ichidagi
        # havolalar atrofida ("113-moddasida </a> nazarda") va HTML qatorlarni
        # bo'lish joyida ortiqcha probel qoldiradi. Bu bo'sh joylar qonun
        # matnida ma'no tashimaydi, bazada esa hech qachon uchramaydi.
        matn = re.sub(r"\s+", " ", "".join(self._joriy)).strip()
        if matn:
            self._paragraflar.append(matn)
        self._joriy = []


def bloklarni_ajrat(html: str) -> List[Tuple[str, Optional[str], List[str]]]:
    p = _BlokParser()
    p.feed(html)
    return p.bloklar


# ---------- Moddalarni yig'ish ----------

def moddalarni_ajrat(html: str, akt: str) -> List[dict]:
    """HTML'dan moddalar ro'yxatini qaytaradi (bazaga yozishga tayyor shaklda emas —
    qonun_nomi/prefiks yuqori qatlamda qo'shiladi)."""
    moddalar: List[dict] = []
    joriy: Optional[dict] = None
    for sinf, anchor, paragraflar in bloklarni_ajrat(html):
        matn = "\n".join(paragraflar)
        if sinf == "CLAUSE_DEFAULT":
            mos = MODDA_SARLAVHA.match(matn)
            if mos:
                joriy = {
                    "raqam": mos.group(1),
                    "sarlavha": matn,
                    "anchor": anchor,
                    "paragraflar": [],
                }
                moddalar.append(joriy)
            else:
                joriy = None  # bob/bo'lim sarlavhasi — modda emas
        elif sinf == "ACT_TEXT" and joriy is not None:
            joriy["paragraflar"].extend(paragraflar)
    for m in moddalar:
        m["matn"] = "\n".join(m.pop("paragraflar"))
        m["lex_url"] = f"https://lex.uz/acts/{akt}#{m['anchor']}"
    return moddalar


def bandlarni_ajrat(html: str, akt: str) -> List[dict]:
    """Band tuzilmali hujjatdan (Yo'l harakati qoidalari) bandlarni ajratadi.

    Hujjat ikki qismdan iborat: hukumat qarorining o'zi va uning ilovasidagi
    QOIDALAR. Bandlar faqat ilovada, shuning uchun qarorning "1.", "2."
    punktlari band deb olinmasligi kerak.

    Qoidalardan keyin yana ilovalar keladi ("Yo'l belgilari" va h.k.) va ular
    raqamlashni birdan boshlaydi. Chegara qo'yilmasa, ular mavjud bandlarni
    ustidan yozib, 1-band butun ilova matnini yutib yuboradi.
    """
    bloklar = bloklarni_ajrat(html)

    # Qoidalar matni: birinchi ilova sarlavhasidan keyingi ilova bannerigacha
    boshlanish = None
    for i, (sinf, _, paragraflar) in enumerate(bloklar):
        if sinf == "ACT_TITLE_APPL" and paragraflar:
            boshlanish = i + 1
            break
    if boshlanish is None:
        return []
    tugash = len(bloklar)
    for i in range(boshlanish, len(bloklar)):
        if bloklar[i][0] == "APPL_BANNER_LANDSCAPE_TITLE":
            tugash = i
            break

    bandlar: List[dict] = []
    joriy: Optional[dict] = None
    bob = ""
    for sinf, anchor, paragraflar in bloklar[boshlanish:tugash]:
        if sinf == "TEXT_HEADER_DEFAULT" and paragraflar:
            mos = BOB_SARLAVHA.match(" ".join(paragraflar).strip())
            if mos:
                bob = mos.group(1).strip()
            continue
        if sinf != "ACT_TEXT":
            continue
        for p in paragraflar:
            mos = BAND_BOSHI.match(p)
            if mos:
                joriy = {
                    "raqam": mos.group(1),
                    "bob": bob,
                    "anchor": anchor,
                    "paragraflar": [mos.group(2).strip()],
                }
                bandlar.append(joriy)
            elif joriy is not None:
                joriy["paragraflar"].append(p)

    for b in bandlar:
        bob_nomi = b.pop("bob")
        # Bandlarning o'z sarlavhasi yo'q — bob nomi ishlatiladi. Bu qidiruvda
        # ham foyda beradi: sarlavha matnga nisbatan katta vaznga ega.
        b["sarlavha"] = f"{b['raqam']}-band" + (f". {bob_nomi}" if bob_nomi else "")
        b["matn"] = "\n".join(b.pop("paragraflar"))
        b["lex_url"] = f"https://lex.uz/acts/{akt}#{b['anchor']}"
    return bandlar


def qonun_nomini_top(html: str) -> str:
    """Hujjat sarlavhasi (ACT_TITLE bloki)."""
    for sinf, _, paragraflar in bloklarni_ajrat(html):
        if sinf == "ACT_TITLE" and paragraflar:
            return " ".join(paragraflar).strip()
    return ""


def modda_id(prefiks: str, raqam: str) -> str:
    """128¹ -> "mjk-128-1" (ustki indeks alohida bo'lak bo'lib ajraladi)."""
    asos = raqam.rstrip("⁰¹²³⁴⁵⁶⁷⁸⁹")
    ustki = raqam[len(asos):].translate(USTKIDAN_ODDIY)
    return f"{prefiks}-{asos}" + (f"-{ustki}" if ustki else "")


def teglar_taklif(sarlavha: str, matn: str, soni: int = 5) -> List[str]:
    """Sarlavhadan boshlang'ich teg ro'yxati.

    Bu FAQAT taklif: teglar qidiruvda eng katta vaznga ega (retrieval.py da ×4),
    shuning uchun import qilingandan keyin qo'lda ko'rib chiqilishi kerak —
    foydalanuvchi savolida uchraydigan jonli so'zlar qo'shilsin.
    """
    sarlavha_matni = sarlavha.split(".", 1)[1] if "." in sarlavha else sarlavha
    sozlar = re.findall(r"[\w'ʻʼ]+", sarlavha_matni.lower())
    teglar = []
    for s in sozlar:
        if len(s) > 3 and s not in _TEG_STOP and s not in teglar:
            teglar.append(s)
    return teglar[:soni]


# ---------- lex.uz'dan yuklash (kesh bilan) ----------

def html_ol(akt: str, yangila: bool = False) -> str:
    """Akt HTML'ini qaytaradi. Bir marta yuklab .cache/lex/ ga saqlaydi —
    parser ustida ishlaganda lex.uz qayta-qayta bezovta qilinmasin."""
    KESH_DIR.mkdir(parents=True, exist_ok=True)
    fayl = KESH_DIR / f"{akt}.html"
    if fayl.exists() and not yangila:
        return fayl.read_text(encoding="utf-8")
    manzil = f"https://lex.uz/acts/{akt}"
    sorov = urllib.request.Request(manzil, headers={"User-Agent": "Mozilla/5.0 (HuquqiyAI import)"})
    for urinish in range(3):
        try:
            with urllib.request.urlopen(sorov, timeout=120) as javob:
                html = javob.read().decode("utf-8")
            break
        except Exception as e:  # tarmoq uzilishi — qayta urinamiz
            if urinish == 2:
                raise SystemExit(f"lex.uz'dan yuklab bo'lmadi ({manzil}): {e}")
            time.sleep(2 * (urinish + 1))
    fayl.write_text(html, encoding="utf-8")
    return html


# ---------- Bazaga yozish ----------

def bazaga_qosh(yangilar: List[dict], teglarni_yangila: bool = False) -> Tuple[int, int]:
    """id bo'yicha qo'shadi yoki yangilaydi. (qoshildi, yangilandi) qaytaradi.

    Mavjud yozuvning `teglar` maydoni saqlanadi: teglar qo'lda tanlangan va
    avtomatik takliflardan aniqroq (--teglarni-yangila bilan bekor qilinadi).
    """
    baza = json.loads(QONUNLAR_FAYL.read_text(encoding="utf-8"))
    indeks = {m["id"]: i for i, m in enumerate(baza)}
    qoshildi = yangilandi = 0
    for yangi in yangilar:
        o_rin = indeks.get(yangi["id"])
        if o_rin is None:
            baza.append(yangi)
            indeks[yangi["id"]] = len(baza) - 1
            qoshildi += 1
        else:
            eski = baza[o_rin]
            if not teglarni_yangila and eski.get("teglar"):
                yangi = {**yangi, "teglar": eski["teglar"]}
            if eski != yangi:
                yangilandi += 1
            baza[o_rin] = yangi
    QONUNLAR_FAYL.write_text(
        json.dumps(baza, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return qoshildi, yangilandi


def tekshir(moddalar: List[dict], prefiks: str, akt: str) -> int:
    """Bazadagi mavjud moddalarni lex.uz bilan solishtiradi (qonun o'zgargan
    bo'lishi mumkin). Farqlar sonini qaytaradi.

    Solishtirish anchor bo'yicha: bitta prefiks bir necha aktdan kelgan
    bo'lishi mumkin (Fuqarolik kodeksining ikki qismi), shuning uchun faqat
    shu aktga tegishli yozuvlar tekshiriladi.
    """
    baza = json.loads(QONUNLAR_FAYL.read_text(encoding="utf-8"))
    manba = {m["lex_url"]: m for m in moddalar}
    farq = tekshirildi = 0
    for eski in baza:
        if not eski["id"].startswith(prefiks + "-") or f"/acts/{akt}#" not in eski["lex_url"]:
            continue
        tekshirildi += 1
        yangi = manba.get(eski["lex_url"])
        if yangi is None:
            print(f"  YO'Q: {eski['id']} — lex.uz'da bu anchor topilmadi ({eski['lex_url']})")
            farq += 1
            continue
        for maydon in ("sarlavha", "matn"):
            if eski.get(maydon) != yangi[maydon]:
                print(f"  FARQ: {eski['id']} -> {maydon}")
                farq += 1
                break
    print(f"  ({tekshirildi} ta yozuv tekshirildi)")
    return farq


# ---------- CLI ----------

def _faqat_royxati(qiymat: str) -> set:
    """--faqat 5,128-1,17¹ -> {"5", "128-1", "17-1"} (id oxiri ko'rinishida)."""
    natija = set()
    for bolak in qiymat.split(","):
        b = bolak.strip().replace("-modda", "").strip()
        if not b:
            continue
        asos = b.rstrip("⁰¹²³⁴⁵⁶⁷⁸⁹")
        ustki = b[len(asos):].translate(USTKIDAN_ODDIY)
        natija.add(f"{asos}-{ustki}" if ustki else asos)
    return natija


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="lex.uz'dan moddalarni import qilish")
    p.add_argument("--hujjat", default="", help="registrdagi hujjat: " + ", ".join(HUJJATLAR))
    p.add_argument("--akt", default="", help="lex.uz hujjat id, masalan -104720")
    p.add_argument("--prefiks", default="", help="modda id prefiksi, masalan oila")
    p.add_argument("--nom", default="", help="qonun_nomi (bo'sh bo'lsa lex.uz sarlavhasi)")
    p.add_argument("--tuzilma", default="", choices=["", "modda", "band"],
                   help="hujjat tuzilmasi: modda (standart) yoki band (qaror ilovasi)")
    p.add_argument("--faqat", default="", help="faqat shu modda raqamlari: 5,7,128-1")
    p.add_argument("--quruq", action="store_true", help="faylga yozmasdan ko'rsatish")
    p.add_argument("--tekshir", action="store_true", help="bazadagi moddalarni lex.uz bilan solishtirish")
    p.add_argument("--yangila", action="store_true", help="keshni chetlab lex.uz'dan qayta yuklash")
    p.add_argument("--teglarni-yangila", action="store_true", help="mavjud teglar ustiga avtomatik takliflarni yozish")
    a = p.parse_args(argv)

    if a.hujjat:
        if a.hujjat not in HUJJATLAR:
            print(f"Noma'lum hujjat: {a.hujjat}. Mavjud: {', '.join(HUJJATLAR)}", file=sys.stderr)
            return 1
        akt, prefiks, nom, tuzilma = HUJJATLAR[a.hujjat]
        akt, prefiks, nom = a.akt or akt, a.prefiks or prefiks, a.nom or nom
        tuzilma = a.tuzilma or tuzilma
    elif a.akt and a.prefiks:
        akt, prefiks, nom, tuzilma = a.akt, a.prefiks, a.nom, a.tuzilma or "modda"
    else:
        print("--hujjat yoki (--akt bilan --prefiks) berilishi kerak", file=sys.stderr)
        return 1

    html = html_ol(akt, yangila=a.yangila)
    birlik = "band" if tuzilma == "band" else "modda"
    moddalar = bandlarni_ajrat(html, akt) if tuzilma == "band" else moddalarni_ajrat(html, akt)
    if not moddalar:
        print(f"{birlik.capitalize()} topilmadi — HTML tuzilishi o'zgargan bo'lishi mumkin",
              file=sys.stderr)
        return 1
    print(f"lex.uz/acts/{akt}: {len(moddalar)} ta {birlik} topildi")

    if a.tekshir:
        farq = tekshir(moddalar, prefiks, akt)
        print("Farq yo'q — baza lex.uz bilan mos" if not farq else f"{farq} ta farq topildi")
        return 0 if not farq else 2

    nom = nom or qonun_nomini_top(html)
    if not nom:
        print("qonun_nomi aniqlanmadi — --nom bilan bering", file=sys.stderr)
        return 1

    filtr = _faqat_royxati(a.faqat) if a.faqat else None
    tayyor: Dict[str, dict] = {}
    for m in moddalar:
        mid = modda_id(prefiks, m["raqam"])
        if filtr is not None and mid[len(prefiks) + 1:] not in filtr:
            continue
        # Bir raqam bir necha marta uchrasa (eski tahrirlar) — oxirgisi qoladi
        tayyor[mid] = {
            "id": mid,
            "qonun_nomi": nom,
            "modda_raqami": f"{m['raqam']}-{birlik}",
            "sarlavha": m["sarlavha"],
            "matn": m["matn"],
            "lex_url": m["lex_url"],
            "teglar": teglar_taklif(m["sarlavha"], m["matn"]),
            "holat": "verified",
        }

    if filtr:
        topilmagan = filtr - {mid[len(prefiks) + 1:] for mid in tayyor}
        if topilmagan:
            print(f"OGOHLANTIRISH: bu moddalar topilmadi: {', '.join(sorted(topilmagan))}", file=sys.stderr)

    royxat = list(tayyor.values())
    print(f"Tanlandi: {len(royxat)} ta modda | qonun_nomi: {nom}")
    if not royxat:
        return 1

    if a.quruq:
        for m in royxat[:2]:
            print("-" * 70)
            print(json.dumps(m, ensure_ascii=False, indent=2)[:1500])
        print("-" * 70)
        print("(quruq rejim — fayl o'zgartirilmadi)")
        return 0

    qoshildi, yangilandi = bazaga_qosh(royxat, teglarni_yangila=a.teglarni_yangila)
    print(f"Bazaga yozildi: {qoshildi} ta yangi, {yangilandi} ta yangilandi")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
