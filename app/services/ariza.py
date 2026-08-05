# Ariza va shikoyat qoralamasi generatori.
# LLM chaqirilmaydi — modda va organ ma'lumotlari bazadan (allaqachon
# tekshirilgan javobdan) olinadi, foydalanuvchi faqat o'z ma'lumotini kiritadi.
# Hujjatda shahar va sana yo'q — yoziladigan yagona joy: imzo.
from typing import List, Optional


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


def shikoyat_tuz(
    fish: str,
    qaror_raqami: str = "",
    qaror_sanasi: str = "",
    qaror_organi: str = "",
    asoslar: Optional[List[str]] = None,
    moddalar: Optional[List[dict]] = None,
    summa: str = "",
    tolangan: bool = False,
    manzil: str = "",
    telefon: str = "",
) -> str:
    """Jarima qarori ustidan shikoyat qoralamasi.

    Nega alohida funksiya: ariza_tuz() "vaziyatimni ko'rib chiqishingizni
    so'rayman" deb tugaydi, jarima ustidan shikoyatda esa aniq talab bo'lishi
    kerak — QARORNI BEKOR QILISH va ish yuritishni TUGATISH (MJK 321-modda).
    To'langan summa qaytarilishini so'rash ham shu talabga bog'liq (324-modda).

    Manzil ataylab yozilmaydi: shikoyat yuqori turuvchi organga yoki tuman
    (shahar) sudiga berilishi mumkin (315-modda) va tanlovni odam qiladi.
    """
    if not fish.strip():
        raise ValueError("F.I.Sh kiritilishi shart")

    qatorlar = [
        "_____________________________________________",
        "(yuqori turuvchi organ yoki jinoyat ishlari",
        " bo'yicha tuman (shahar) sudi nomi)",
        "",
        f"{fish.strip()}dan",
    ]
    if manzil.strip():
        qatorlar.append(f"Manzil: {manzil.strip()}")
    if telefon.strip():
        qatorlar.append(f"Telefon: {telefon.strip()}")

    qatorlar += ["", "SHIKOYAT", "(ma'muriy huquqbuzarlik to'g'risidagi ish yuzasidan", " chiqarilgan qaror ustidan)", ""]

    qaror = "Menga nisbatan"
    if qaror_organi.strip():
        qaror += f" {qaror_organi.strip()} tomonidan"
    if qaror_sanasi.strip():
        qaror += f" {qaror_sanasi.strip()} kuni"
    if qaror_raqami.strip():
        qaror += f" {qaror_raqami.strip()}-sonli"
    qaror += " ma'muriy jazo qo'llash to'g'risida qaror chiqarilgan"
    if summa.strip():
        qaror += f" va {summa.strip()} miqdorida jarima solingan"
    qatorlar += [qaror + ".", ""]

    qatorlar += [
        "Mazkur qarorni quyidagi asoslarga ko'ra qonuniy emas deb hisoblayman:",
        "",
    ]
    for i, asos in enumerate(asoslar or [], 1):
        qatorlar.append(f"{i}. {asos}")
    if not asoslar:
        qatorlar.append("1. _____________________________________________")
        qatorlar.append("   (asosni o'z so'zingiz bilan yozing)")
    qatorlar.append("")

    if moddalar:
        guruhlar: dict = {}
        for m in moddalar:
            guruhlar.setdefault(m["qonun_nomi"], []).append(m["modda_raqami"])
        qismlar = []
        for qonun, raqamlar in guruhlar.items():
            # Bitta modda — birlik shakl ("36-moddasi"), bir nechtasi — ko'plik
            if len(raqamlar) == 1:
                qismlar.append(f"{qonun}ning {raqamlar[0]}si")
            else:
                royxat = ", ".join(r.replace("-modda", "-").replace("-band", "-") for r in raqamlar)
                birlik = "bandlari" if "Qoidalari" in qonun else "moddalari"
                qismlar.append(f"{qonun}ning {royxat}{birlik}")
        qatorlar += ["Yuqoridagilar " + "; ".join(qismlar) + " bilan tasdiqlanadi.", ""]

    talab = [
        "Yuqoridagilarga asosan, O'zbekiston Respublikasi Ma'muriy javobgarlik",
        "to'g'risidagi kodeksining 321-moddasiga muvofiq SO'RAYMAN:",
        "",
        "1. Menga nisbatan chiqarilgan yuqoridagi qarorni bekor qilishni;",
        "2. Ma'muriy huquqbuzarlik to'g'risidagi ish yuritishni tugatishni.",
    ]
    if tolangan:
        talab.append(
            "3. Shu Kodeksning 324-moddasiga muvofiq undirib olingan pul "
            "summasini qaytarib berishni."
        )
    qatorlar += talab + [""]

    qatorlar += [
        "Ilova: qaror nusxasi; bayonnoma nusxasi (bo'lsa); dalillar.",
        "",
        "Hurmat bilan,",
        fish.strip(),
        "",
        "_____________ (imzo)",
    ]
    return "\n".join(qatorlar)
