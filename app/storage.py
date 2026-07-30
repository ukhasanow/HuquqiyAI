# JSON bazani o'qish/yozish qatlami
import json
import threading
from typing import Dict, List, Optional

from .config import DATA_DIR

QONUNLAR_FAYL = DATA_DIR / "qonunlar.json"
ORGANLAR_FAYL = DATA_DIR / "organlar.json"

_lock = threading.Lock()


def moddalarni_oqi() -> List[dict]:
    with open(QONUNLAR_FAYL, encoding="utf-8") as f:
        return json.load(f)


def organlarni_oqi() -> List[dict]:
    with open(ORGANLAR_FAYL, encoding="utf-8") as f:
        return json.load(f)


def modda_top(modda_id: str) -> Optional[dict]:
    for m in moddalarni_oqi():
        if m["id"] == modda_id:
            return m
    return None


def organ_top(mavzu: str) -> Optional[dict]:
    organlar = organlarni_oqi()
    for o in organlar:
        if o["mavzu"] == mavzu:
            return o
    # topilmasa umumiy organ (Adliya vazirligi) qaytariladi
    for o in organlar:
        if o["mavzu"] == "umumiy":
            return o
    return None


def moddalarni_saqla(moddalar: List[dict]) -> None:
    with _lock:
        with open(QONUNLAR_FAYL, "w", encoding="utf-8") as f:
            json.dump(moddalar, f, ensure_ascii=False, indent=2)


def modda_qosh_yoki_yangila(yangi: Dict) -> dict:
    """id bo'yicha mavjud bo'lsa yangilaydi, bo'lmasa qo'shadi."""
    with _lock:
        with open(QONUNLAR_FAYL, encoding="utf-8") as f:
            moddalar = json.load(f)
        for i, m in enumerate(moddalar):
            if m["id"] == yangi["id"]:
                moddalar[i] = yangi
                break
        else:
            moddalar.append(yangi)
        with open(QONUNLAR_FAYL, "w", encoding="utf-8") as f:
            json.dump(moddalar, f, ensure_ascii=False, indent=2)
    return yangi
