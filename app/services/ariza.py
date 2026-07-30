# Ariza qoralamasi generatori.
# LLM chaqirilmaydi — modda va organ ma'lumotlari bazadan (allaqachon
# tekshirilgan javobdan) olinadi, foydalanuvchi faqat o'z ma'lumotini kiritadi.
# Hujjatda shahar va sana yo'q — yoziladigan yagona joy: imzo.
from typing import List


def ariza_tuz(
    fish: str,
    vaziyat: str,
    moddalar: List[dict],
    organ: dict,
    manzil: str = "",
    telefon: str = "",
) -> str:
    """Tayyor ariza matnini qaytaradi."""
    if not fish.strip():
        raise ValueError("F.I.Sh kiritilishi shart")
    if not moddalar:
        raise ValueError("Asossiz javob uchun ariza tuzib bo'lmaydi")

    sarlavha = "DA'VO ARIZASI" if "sud" in organ.get("nomi", "").lower() else "ARIZA"

    # Bitta qonunning moddalarini birlashtirish: "Mehnat kodeksining 253-, 269-moddalari"
    guruhlar: dict = {}
    for m in moddalar:
        guruhlar.setdefault(m["qonun_nomi"], []).append(m["modda_raqami"])
    qismlar = []
    for qonun, raqamlar in guruhlar.items():
        if len(raqamlar) == 1:
            qismlar.append(f"{qonun}ning {raqamlar[0]}si")
        else:
            royxat = ", ".join(r.replace("-modda", "-") for r in raqamlar)
            qismlar.append(f"{qonun}ning {royxat}moddalari")
    asoslar = "; ".join(qismlar)

    qatorlar = [f"{organ['nomi']}ga"]
    if organ.get("manzil"):
        qatorlar.append(organ["manzil"])
    qatorlar += ["", f"{fish.strip()}dan"]
    if manzil.strip():
        qatorlar.append(f"Manzil: {manzil.strip()}")
    if telefon.strip():
        qatorlar.append(f"Telefon: {telefon.strip()}")
    qatorlar += ["", sarlavha, ""]

    if vaziyat.strip():
        qatorlar += ["Vaziyat bayoni:", vaziyat.strip(), ""]

    qatorlar += [
        f"Yuqoridagilarga asosan, {asoslar}ga muvofiq vaziyatimni ko'rib "
        "chiqishingizni va qonunda belgilangan choralarni ko'rishingizni so'rayman.",
        "",
        "Hurmat bilan,",
        fish.strip(),
        "",
        "_____________ (imzo)",
    ]
    return "\n".join(qatorlar)
