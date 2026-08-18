import base64
import binascii
import json
import logging
import re
import struct
from datetime import datetime
from typing import Optional, Tuple

import httpx

from ..config import GEMINI_API_KEY, GEMINI_MODEL
from ..models import JarimaSorov, RadarKuzatuv

log = logging.getLogger(__name__)

MAX_RASM_HAJMI = 8 * 1024 * 1024
SOROV_MUDDATI = 120

# Modeldan XULOSA emas, KUZATUV so'raladi. "Bu noqonuniymi?" deb so'rasak,
# model rozi bo'lishga moyil bo'ladi va har suratda buzilish "topadi".
_KORSATMA = """Bu yo'l chetidagi tezlik o'lchash moslamasi (radar) surati.
Sen faqat SURATDA KO'RINGANINI tasvirlaysan. Huquqiy baho berma, "qonuniy"
yoki "noqonuniy" deb yozma — bu senga topshirilmagan.

Faqat quyidagi JSON ni qaytar, boshqa hech narsa yozma:

{
  "radar_bormi": true/false,
  "ornatilish": "trenoga" | "avtomobilda" | "ustunda" | "qolda" | "noanik",
  "patrul_avtomobili": true/false/null,
  "avtomobil_tavsifi": "",
  "odam_bormi": true/false,
  "xodim_formada": true/false/null,
  "moslama_qarovsiz": true/false,
  "yashiringan": true/false,
  "yashirish_tavsifi": "",
  "moslama_rusumi": "",
  "tezlik_belgisi": null,
  "korinadigan_belgilar": [],
  "joy_belgilari": [],
  "izoh": ""
}

Maydonlarni qanday to'ldirish:
- ornatilish: "trenoga" — uch oyoqli tagliksa (shtativ) turgan bo'lsa;
  "avtomobilda" — avtomobil ichida yoki ustida; "ustunda" — doimiy ustun yoki
  ramada; "qolda" — odam qo'lida ushlab turgan bo'lsa.
- patrul_avtomobili: yaqinida yo'l-patrul xizmati avtomobili KO'RINSA true
  (oq-ko'k rang, "YPX"/"ДПС"/"Patrul" yozuvi, chiroqli panel). Oddiy fuqarolik
  avtomobili bo'lsa false. Umuman avtomobil ko'rinmasa ham false.
  Kadr juda tor bo'lib, atrofni ko'rib bo'lmasa null.
- avtomobil_tavsifi: ko'ringan avtomobilni qisqa tasvirla (rangi, yozuvlari).
- xodim_formada: odam ko'rinsa va u YPX formasida bo'lsa true, fuqarolik
  kiyimida bo'lsa false. Odam ko'rinmasa null.
- moslama_qarovsiz: radar yonida hech kim yo'q bo'lsa true.
- yashiringan: radar buta, daraxt, yo'l belgisi, to'siq yoki to'xtatilgan
  avtomobil ortiga qo'yilgan bo'lsa true. yashirish_tavsifi da nima to'sib
  turganini yoz.
- moslama_rusumi: moslama korpusida rusum yozuvi ko'rinsa yoz (masalan
  Vizir, Iskra, Binar, Kordon, Sokol). Ko'rinmasa bo'sh qoldir.
- tezlik_belgisi: kadrda tezlik cheklovi yo'l belgisi ko'rinsa, undagi son.
- korinadigan_belgilar: boshqa yo'l belgilari matni.
- joy_belgilari: joyni aniqlashga yordam beradigani — kilometr ustuni,
  ko'cha nomi, bino, mo'ljal.

MUHIM: ko'rmagan narsangni yozma. Ishonchsiz bo'lsang null yoki bo'sh qoldir.
"Ehtimol", "ko'rinishidan" degan taxminlar bu yerda zarar keltiradi."""


class RadarXato(Exception):
    """Radar suratini ko'rib bo'lmaganda ko'tariladi."""


def mavjud() -> bool:
    return bool(GEMINI_API_KEY)


def suratdan_kuzat(bayt: bytes, mime: str = "image/jpeg") -> RadarKuzatuv:
    """Radar suratidan kuzatuvlarni o'qiydi (huquqiy baho bermaydi)."""
    if not bayt:
        raise RadarXato("Rasm bo'sh.")
    if len(bayt) > MAX_RASM_HAJMI:
        raise RadarXato("Rasm hajmi 8 MB dan oshmasligi kerak.")
    if not mavjud():
        raise RadarXato(
            "Rasmdan o'qish bu serverda sozlanmagan. Radar qanday turganini "
            "so'z bilan yozing — tekshiruvni shunda ham o'tkazaman."
        )

    xom = _gemini_sorovi(bayt, mime)
    kuzatuv = _json_ajrat(xom)

    if not kuzatuv.radar_bormi:
        raise RadarXato(
            "Suratda tezlik o'lchash moslamasi ko'rinmadi. Radar va uning "
            "atrofi (yonidagi avtomobil, odam) bir kadrga tushgan surat "
            "yuboring — asosiy dalil aynan atrofda bo'ladi."
        )

    kuzatuv.sana, kuzatuv.gps = _exif_sana_va_gps(bayt)
    return kuzatuv


def kuzatuvni_sorovga(kuzatuv: RadarKuzatuv, sorov: Optional[JarimaSorov] = None) -> JarimaSorov:
    """Kuzatuvni JarimaSorov maydonlariga o'girib, mavjud tekshiruvga ulaydi.

    Surat allaqachon to'ldirilgan maydonni bekor qilmaydi: foydalanuvchi qo'lda
    kiritgan ma'lumot suratdan olingan taxmindan ustun turadi.
    """
    sorov = sorov.model_copy() if sorov else JarimaSorov()

    if not sorov.radar_turi:
        sorov.radar_turi = {
            "trenoga": "trenoga",
            "avtomobilda": "patrul",
            "ustunda": "statsionar",
        }.get(kuzatuv.ornatilish, "")

    if sorov.patrul_avtomobili is None:
        sorov.patrul_avtomobili = kuzatuv.patrul_avtomobili
    if sorov.xodim_formada is None:
        sorov.xodim_formada = kuzatuv.xodim_formada
    if not sorov.moslama_qarovsiz:
        # Faqat odam umuman ko'rinmagan bo'lsa. "Odam bor, lekin formada emas"
        # boshqa band (32) bo'yicha ketadi, ikki marta hisoblanmasin.
        sorov.moslama_qarovsiz = kuzatuv.moslama_qarovsiz and not kuzatuv.odam_bormi

    return sorov


def dislokatsiya_sorovi(kuzatuv: RadarKuzatuv) -> str:
    """34-band bo'yicha dislokatsiya so'rovi uchun joy va vaqt matni.

    Dislokatsiya aynan JOY va VAQT bo'yicha tekshiriladi, shuning uchun
    so'rovda ular qanchalik aniq bo'lsa, javobdan qochish shunchalik qiyin.
    """
    qismlar = []
    if kuzatuv.sana:
        qismlar.append(f"vaqt: {kuzatuv.sana}")
    if kuzatuv.gps:
        kenglik, uzunlik = kuzatuv.gps
        qismlar.append(f"koordinata: {kenglik:.5f}, {uzunlik:.5f}")
    if kuzatuv.joy_belgilari:
        qismlar.append("mo'ljal: " + ", ".join(kuzatuv.joy_belgilari))
    if kuzatuv.moslama_rusumi:
        qismlar.append(f"moslama rusumi: {kuzatuv.moslama_rusumi}")
    return "; ".join(qismlar)


# ---------- Gemini ----------

def _gemini_sorovi(bayt: bytes, mime: str) -> str:
    try:
        javob = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent",
            params={"key": GEMINI_API_KEY},
            json={
                "contents": [{"parts": [
                    {"text": _KORSATMA},
                    {"inline_data": {"mime_type": mime,
                                     "data": base64.b64encode(bayt).decode()}},
                ]}],
                # temperature=0: bu kuzatuv, ijodkorlik emas
                "generationConfig": {
                    "temperature": 0,
                    "maxOutputTokens": 2048,
                    "responseMimeType": "application/json",
                },
            },
            timeout=SOROV_MUDDATI,
        )
        javob.raise_for_status()
        nomzodlar = javob.json().get("candidates") or []
        if not nomzodlar:
            raise RadarXato("Suratni tahlil qilib bo'lmadi, qaytadan urinib ko'ring.")
        qismlar = nomzodlar[0].get("content", {}).get("parts") or []
        return "".join(q.get("text", "") for q in qismlar).strip()
    except RadarXato:
        raise
    except Exception as e:
        log.warning("Radar suratini o'qib bo'lmadi: %s", e)
        raise RadarXato(_xato_matni(e)) from e


def _xato_matni(e: Exception) -> str:
    """Xato sababini to'g'ri aytish — odam aybni o'z suratidan qidirmasin."""
    s = str(e).lower()
    if "429" in s or "rate limit" in s or "quota" in s or "resource_exhausted" in s:
        return ("Surat tahlili xizmati hozir band (so'rovlar limiti). Bir necha "
                "daqiqadan so'ng urinib ko'ring.")
    if "401" in s or "403" in s or "api key" in s:
        return "Surat tahlili bu serverda sozlanmagan (kalit noto'g'ri)."
    if "timeout" in s or "timed out" in s:
        return "Surat tahlili juda uzoq davom etdi. Kichikroq surat yuboring."
    return "Suratni tahlil qilib bo'lmadi. Radar va uning atrofi ko'ringan aniq surat yuboring."


def _json_ajrat(xom: str) -> RadarKuzatuv:
    """Model javobidan JSON ajratadi.

    responseMimeType so'ralgan bo'lsa ham, zaxira provayder yoki eski model
    javobni ```json bloki ichida qaytarishi mumkin.
    """
    matn = xom.strip()
    blok = re.search(r"```(?:json)?\s*(.+?)```", matn, re.S)
    if blok:
        matn = blok.group(1).strip()
    qavs = re.search(r"\{.*\}", matn, re.S)
    if qavs:
        matn = qavs.group(0)
    try:
        malumot = json.loads(matn)
    except json.JSONDecodeError as e:
        log.warning("Radar javobi JSON emas: %s", xom[:300])
        raise RadarXato(
            "Surat tahlili natijasini o'qib bo'lmadi, qaytadan urinib ko'ring."
        ) from e
    try:
        return RadarKuzatuv(**malumot)
    except Exception as e:
        log.warning("Radar kuzatuvi modelga to'g'ri kelmadi: %s", e)
        raise RadarXato(
            "Surat tahlili natijasi kutilgan shaklda emas, qaytadan urinib ko'ring."
        ) from e


# ---------- EXIF ----------
#
# Pillow qo'shilmadi: butun kerak bo'lgani JPEG dan ikkita qiymat — suratga
# olingan vaqt va koordinata. Ular dislokatsiya so'rovini aniq qiladi
# (34-band joy va VAQT bo'yicha tekshiriladi). PNG va HEIC da EXIF o'qilmaydi;
# bunda so'rov shunchaki joy belgilari bilan tuziladi.

_EXIF_SANA = 0x9003      # DateTimeOriginal
_EXIF_IFD = 0x8769
_GPS_IFD = 0x8825
_TIP_HAJMI = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 7: 1, 9: 4, 10: 8}


def _exif_sana_va_gps(bayt: bytes) -> Tuple[str, Optional[Tuple[float, float]]]:
    """JPEG EXIF dan suratga olingan vaqt va koordinatani oladi.

    EXIF ishonchli dalil emas (uni o'zgartirish mumkin) va shu sababli u
    tekshiruv natijasiga ta'sir qilmaydi — faqat shikoyat matnida so'ralgan
    dislokatsiyani aniqlashtirish uchun ishlatiladi.
    """
    try:
        tiff, tartib = _tiff_boshi(bayt)
        if tiff is None:
            return "", None
        asosiy = _ifd_oqi(tiff, tartib, _birinchi_ifd_ofseti(tiff, tartib))

        sana = ""
        for manba in (asosiy, _ichki_ifd(tiff, tartib, asosiy, _EXIF_IFD)):
            xom = manba.get(_EXIF_SANA)
            if isinstance(xom, bytes):
                sana = _sanani_formatla(xom)
                if sana:
                    break

        gps = _gps_oqi(tiff, tartib, _ichki_ifd(tiff, tartib, asosiy, _GPS_IFD))
        return sana, gps
    except Exception as e:  # EXIF buzuq bo'lsa butun tekshiruv to'xtamasin
        log.debug("EXIF o'qilmadi: %s", e)
        return "", None


def _tiff_boshi(bayt: bytes) -> Tuple[Optional[bytes], str]:
    """JPEG APP1 (Exif) bo'lagidan TIFF sarlavhasini topadi."""
    if not bayt.startswith(b"\xff\xd8"):
        return None, "<"
    i = 2
    while i + 4 <= len(bayt):
        if bayt[i] != 0xFF:
            return None, "<"
        belgi, uzunlik = bayt[i + 1], struct.unpack(">H", bayt[i + 2:i + 4])[0]
        tana = bayt[i + 4:i + 2 + uzunlik]
        if belgi == 0xE1 and tana.startswith(b"Exif\x00\x00"):
            tiff = tana[6:]
            if tiff[:2] == b"II":
                return tiff, "<"
            if tiff[:2] == b"MM":
                return tiff, ">"
            return None, "<"
        if belgi == 0xDA:  # rasm ma'lumoti boshlandi, EXIF yo'q
            return None, "<"
        i += 2 + uzunlik
    return None, "<"


def _birinchi_ifd_ofseti(tiff: bytes, tartib: str) -> int:
    return struct.unpack(tartib + "I", tiff[4:8])[0]


def _ifd_oqi(tiff: bytes, tartib: str, ofset: int) -> dict:
    """Bitta IFD jadvalini {teg: qiymat} ko'rinishida qaytaradi."""
    natija: dict = {}
    if ofset <= 0 or ofset + 2 > len(tiff):
        return natija
    soni = struct.unpack(tartib + "H", tiff[ofset:ofset + 2])[0]
    for n in range(soni):
        p = ofset + 2 + n * 12
        if p + 12 > len(tiff):
            break
        teg, tip, sanoq = struct.unpack(tartib + "HHI", tiff[p:p + 8])
        hajmi = _TIP_HAJMI.get(tip, 0) * sanoq
        if not hajmi:
            continue
        if hajmi <= 4:
            xom = tiff[p + 8:p + 8 + hajmi]
        else:
            q = struct.unpack(tartib + "I", tiff[p + 8:p + 12])[0]
            if q + hajmi > len(tiff):
                continue
            xom = tiff[q:q + hajmi]
        natija[teg] = _qiymat(xom, tip, sanoq, tartib)
    return natija


def _qiymat(xom: bytes, tip: int, sanoq: int, tartib: str):
    if tip in (1, 2, 7):
        return xom
    if tip == 3:
        qiymatlar = struct.unpack(tartib + "H" * sanoq, xom)
    elif tip == 4:
        qiymatlar = struct.unpack(tartib + "I" * sanoq, xom)
    elif tip in (5, 10):
        harf = "II" if tip == 5 else "ii"
        sonlar = struct.unpack(tartib + harf * sanoq, xom)
        qiymatlar = tuple(
            sonlar[i] / sonlar[i + 1] if sonlar[i + 1] else 0.0
            for i in range(0, len(sonlar), 2)
        )
    elif tip == 9:
        qiymatlar = struct.unpack(tartib + "i" * sanoq, xom)
    else:
        return xom
    return qiymatlar[0] if sanoq == 1 else qiymatlar


def _ichki_ifd(tiff: bytes, tartib: str, asosiy: dict, teg: int) -> dict:
    ofset = asosiy.get(teg)
    if not isinstance(ofset, int):
        return {}
    return _ifd_oqi(tiff, tartib, ofset)


def _sanani_formatla(xom: bytes) -> str:
    """EXIF "2026:08:06 14:31:02" -> "2026-08-06 14:31"."""
    try:
        matn = xom.split(b"\x00")[0].decode("ascii", "ignore").strip()
        return datetime.strptime(matn, "%Y:%m:%d %H:%M:%S").strftime("%Y-%m-%d %H:%M")
    except (ValueError, binascii.Error):
        return ""


def _gps_oqi(tiff: bytes, tartib: str, gps: dict) -> Optional[Tuple[float, float]]:
    """GPS IFD dan (kenglik, uzunlik) ni o'nlik darajada qaytaradi."""
    kenglik = _daraja(gps.get(2), gps.get(1))
    uzunlik = _daraja(gps.get(4), gps.get(3))
    if kenglik is None or uzunlik is None:
        return None
    return kenglik, uzunlik


def _daraja(qiymat, yonalish) -> Optional[float]:
    """(daraja, daqiqa, soniya) uchligini o'nlik darajaga o'giradi."""
    if not isinstance(qiymat, tuple) or len(qiymat) != 3:
        return None
    daraja = qiymat[0] + qiymat[1] / 60 + qiymat[2] / 3600
    belgi = b""
    if isinstance(yonalish, bytes):
        belgi = yonalish.split(b"\x00")[0].upper()
    return -daraja if belgi in (b"S", b"W") else daraja
