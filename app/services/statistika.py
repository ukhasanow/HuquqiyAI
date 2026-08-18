import copy
import json
import logging
import threading
from datetime import date, timedelta
from typing import Optional

import httpx

from ..config import DATA_DIR, STATISTIKA_KV_TOKEN, STATISTIKA_KV_URL

log = logging.getLogger(__name__)

STATISTIKA_FAYL = DATA_DIR / "statistika.json"
KV_KALIT = "huquqiyai:statistika"
KV_MUDDATI = 15  # soniya — statistika javob yo'lida emas, fon vazifasida yoziladi

_lock = threading.Lock()

# Topilmagan savollar ro'yxati cheksiz o'smasligi uchun chegara
MAX_TOPILMAGAN = 300

MANBALAR = ("sayt", "bot")


def _bosh_kesim() -> dict:
    """Bitta manba (sayt yoki bot) bo'yicha ko'rsatkichlar."""
    return {"jami": 0, "topildi": 0, "ovozli": 0, "oddiy": 0, "pro": 0}


_BOSH_HOLAT = {
    "jami_sorovlar": 0,
    "javob_topildi": 0,
    "javob_topilmadi": 0,
    "rejimlar": {"oddiy": 0, "pro": 0},
    "manbalar": {"sayt": 0, "bot": 0},  # so'rov qayerdan keldi
    "ovozli_sorovlar": 0,  # ovozli xabar orqali kelgan savollar
    "ovozli_javoblar": 0,  # TTS bilan yuborilgan javoblar
    "shartnoma_tahlillari": 0,
    "shartnoma_turlari": {},  # {"mehnat": 3, "ijara": 1, ...}
    "jarima_tekshiruvlari": 0,
    "jarima_asos_topildi": 0,  # shundan nechtasida bekor qilish asosi topilgan
    
    "manba_kesimi": {manba: _bosh_kesim() for manba in MANBALAR},
    "mavzular": {},
    "kunlik": {},  # {"2026-07-31": {"jami": 0, "topildi": 0, "sayt": 0, "bot": 0}}
    "foydalanuvchilar": [],  # anonim ID'lar (takrorlanmas)
    "topilmagan_savollar": [],  # [{"sana": ..., "savol": ...}]
}


def tashqi_saqlash() -> bool:
    """Statistika tashqi omborda saqlanadimi."""
    return bool(STATISTIKA_KV_URL and STATISTIKA_KV_TOKEN)


def _kv_oqi() -> Optional[dict]:
    """Tashqi ombordan o'qish. Xato bo'lsa None (ilova to'xtamasligi kerak)."""
    try:
        javob = httpx.get(
            f"{STATISTIKA_KV_URL}/get/{KV_KALIT}",
            headers={"Authorization": f"Bearer {STATISTIKA_KV_TOKEN}"},
            timeout=KV_MUDDATI,
        )
        javob.raise_for_status()
        xom = javob.json().get("result")
        return json.loads(xom) if xom else copy.deepcopy(_BOSH_HOLAT)
    except Exception as e:
        log.warning("Statistikani tashqi ombordan o'qib bo'lmadi: %s", e)
        return None


def _kv_saqla(s: dict) -> bool:
    try:
        javob = httpx.post(
            f"{STATISTIKA_KV_URL}/set/{KV_KALIT}",
            headers={"Authorization": f"Bearer {STATISTIKA_KV_TOKEN}"},
            content=json.dumps(s, ensure_ascii=False).encode("utf-8"),
            timeout=KV_MUDDATI,
        )
        javob.raise_for_status()
        return True
    except Exception as e:
        log.warning("Statistikani tashqi omborga yozib bo'lmadi: %s", e)
        return False


def _toldir(s: dict) -> dict:
    """Yetishmagan kalitlarni to'ldiradi.

    Yangi maydon qo'shilganda eski yozuv o'qilishi bilan KeyError bermasligi
    kerak — bu fayl uchun ham, tashqi ombor uchun ham bir xil.
    """
    for k, v in _BOSH_HOLAT.items():
        s.setdefault(k, copy.deepcopy(v))
    for manba in MANBALAR:
        kesim = s["manba_kesimi"].setdefault(manba, {})
        for k, v in _bosh_kesim().items():
            kesim.setdefault(k, v)
    return s


def _oqi() -> dict:
    if tashqi_saqlash():
        s = _kv_oqi()
        # Tashqi ombor javob bermasa faylga tushmaymiz: u yerdagi eski
        # ma'lumot ustiga yozilib, tashqi ombordagisi yo'qolib ketardi.
        return _toldir(s) if s is not None else copy.deepcopy(_BOSH_HOLAT)

    if not STATISTIKA_FAYL.exists():
        return copy.deepcopy(_BOSH_HOLAT)
    try:
        with open(STATISTIKA_FAYL, encoding="utf-8") as f:
            s = json.load(f)
    except (json.JSONDecodeError, OSError):
        return copy.deepcopy(_BOSH_HOLAT)
    return _toldir(s)


def _saqla(s: dict) -> None:
    if tashqi_saqlash():
        _kv_saqla(s)
        return
    with open(STATISTIKA_FAYL, "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)


def sorov_hisobla(
    rejim: str,
    javob_topildi: bool,
    murojaat_mavzusi: str = "umumiy",
    foydalanuvchi_id: Optional[str] = None,
    savol: str = "",
    manba: str = "sayt",
    ovozli: bool = False,
) -> None:
    """Bitta so'rovni hisobga oladi. Savol matni faqat javob topilmaganda saqlanadi."""
    bugun = date.today().isoformat()
    with _lock:
        s = _oqi()
        s["jami_sorovlar"] += 1
        if javob_topildi:
            s["javob_topildi"] += 1
        else:
            s["javob_topilmadi"] += 1

        rejim = rejim if rejim in ("oddiy", "pro") else "oddiy"
        s["rejimlar"][rejim] = s["rejimlar"].get(rejim, 0) + 1

        manba = manba if manba in MANBALAR else "sayt"
        s["manbalar"][manba] = s["manbalar"].get(manba, 0) + 1
        if ovozli:
            s["ovozli_sorovlar"] += 1

        kesim = s["manba_kesimi"][manba]
        kesim["jami"] += 1
        kesim[rejim] += 1
        if javob_topildi:
            kesim["topildi"] += 1
        if ovozli:
            kesim["ovozli"] += 1

        mavzu = murojaat_mavzusi or "umumiy"
        s["mavzular"][mavzu] = s["mavzular"].get(mavzu, 0) + 1

        kun = s["kunlik"].setdefault(bugun, {"jami": 0, "topildi": 0})
        kun["jami"] += 1
        kun[manba] = kun.get(manba, 0) + 1
        if javob_topildi:
            kun["topildi"] += 1

        if foydalanuvchi_id:
            fid = str(foydalanuvchi_id)[:64]
            if fid not in s["foydalanuvchilar"]:
                s["foydalanuvchilar"].append(fid)

        if not javob_topildi and savol.strip():
            s["topilmagan_savollar"].append({"sana": bugun, "savol": savol.strip()[:500]})
            s["topilmagan_savollar"] = s["topilmagan_savollar"][-MAX_TOPILMAGAN:]

        _saqla(s)


def shartnoma_hisobla(turi: str, foydalanuvchi_id: Optional[str] = None) -> None:
    """Shartnoma tahlilini hisobga oladi (tur bo'yicha kesimda).

    Statistika yozilmasa ham tahlil buzilmasligi kerak — shuning uchun
    chaqiruvchi buni fon vazifasi sifatida bajaradi.
    """
    with _lock:
        s = _oqi()
        s["shartnoma_tahlillari"] += 1
        turi = turi or "boshqa"
        s["shartnoma_turlari"][turi] = s["shartnoma_turlari"].get(turi, 0) + 1
        if foydalanuvchi_id:
            fid = str(foydalanuvchi_id)[:64]
            if fid not in s["foydalanuvchilar"]:
                s["foydalanuvchilar"].append(fid)
        _saqla(s)


def jarima_hisobla(asoslar_soni: int, foydalanuvchi_id: Optional[str] = None) -> None:
    """Jarima tekshiruvini hisobga oladi.

    Asos topilgan tekshiruvlar ulushi — funksiya haqiqatan foyda berayotganini
    ko'rsatadigan yagona ko'rsatkich.
    """
    with _lock:
        s = _oqi()
        s["jarima_tekshiruvlari"] += 1
        if asoslar_soni:
            s["jarima_asos_topildi"] += 1
        if foydalanuvchi_id:
            fid = str(foydalanuvchi_id)[:64]
            if fid not in s["foydalanuvchilar"]:
                s["foydalanuvchilar"].append(fid)
        _saqla(s)


def ovozli_javob_hisobla() -> None:
    """Ovozli javob (TTS) yuborilganini hisobga oladi."""
    with _lock:
        s = _oqi()
        s["ovozli_javoblar"] += 1
        _saqla(s)


def statistika_oqi() -> dict:
    """Admin panel uchun to'liq statistika (oxirgi 30 kun kunlik kesimda)."""
    with _lock:
        s = _oqi()
    bugun = date.today()
    kunlik_30 = []
    for i in range(29, -1, -1):
        kun = (bugun - timedelta(days=i)).isoformat()
        k = s["kunlik"].get(kun, {})
        kunlik_30.append({
            "sana": kun,
            "jami": k.get("jami", 0),
            "topildi": k.get("topildi", 0),
            # Manba bo'yicha ajratish keyin qo'shilgan — eski kunlarda yo'q
            "sayt": k.get("sayt", 0),
            "bot": k.get("bot", 0),
        })
    # Bot foydalanuvchilari "tg:<chat_id>" ko'rinishida saqlanadi
    bot_foydalanuvchilar = sum(1 for f in s["foydalanuvchilar"] if str(f).startswith("tg:"))
    return {
        "jami_sorovlar": s["jami_sorovlar"],
        "javob_topildi": s["javob_topildi"],
        "javob_topilmadi": s["javob_topilmadi"],
        "rejimlar": s["rejimlar"],
        "manbalar": s["manbalar"],
        "ovozli_sorovlar": s["ovozli_sorovlar"],
        "ovozli_javoblar": s["ovozli_javoblar"],
        "manba_kesimi": s["manba_kesimi"],
        "shartnoma_tahlillari": s["shartnoma_tahlillari"],
        "shartnoma_turlari": s["shartnoma_turlari"],
        "jarima_tekshiruvlari": s["jarima_tekshiruvlari"],
        "jarima_asos_topildi": s["jarima_asos_topildi"],
        "mavzular": s["mavzular"],
        "kunlik_30": kunlik_30,
        "foydalanuvchilar_soni": len(s["foydalanuvchilar"]),
        "bot_foydalanuvchilar_soni": bot_foydalanuvchilar,
        "sayt_foydalanuvchilar_soni": len(s["foydalanuvchilar"]) - bot_foydalanuvchilar,
        "topilmagan_savollar": list(reversed(s["topilmagan_savollar"])),
    }


def javoblar_soni() -> int:
    """Ochiq hisoblagich uchun: javob topilgan so'rovlar soni."""
    with _lock:
        return _oqi()["javob_topildi"]
