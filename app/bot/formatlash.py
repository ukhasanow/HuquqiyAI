# Javobni Telegram xabariga aylantirish.
#
# parse_mode=HTML ishlatiladi. MarkdownV2 da modda matnidagi har bir `.`, `-`,
# `(` belgisi escape talab qiladi — qonun matni bunday belgilarga to'la va
# bitta e'tibordan qolgani butun xabarni yuborilmaydigan qiladi.
import html
from typing import List

# Telegram matn xabari uchun chegara 4096 belgi. Bir oz zaxira qoldiramiz:
# HTML teglar ham shu hisobga kiradi.
XABAR_CHEGARASI = 3900


def _tozala(matn: str) -> str:
    return html.escape(matn or "", quote=False)


def bolaklarga_bol(matn: str, chegara: int = XABAR_CHEGARASI) -> List[str]:
    """Uzun matnni Telegram cheklovi ostidagi bo'laklarga ajratadi.

    Ajratish joyi tartibi: xatboshi -> gap oxiri -> so'z. So'z o'rtasidan
    kesish faqat chorasiz qolganda (bitta juda uzun "so'z") bo'ladi.
    """
    matn = matn.strip()
    if len(matn) <= chegara:
        return [matn] if matn else []

    bolaklar = []
    qoldiq = matn
    while len(qoldiq) > chegara:
        oyna = qoldiq[:chegara]
        kesim = max(oyna.rfind("\n\n"), oyna.rfind("\n"))
        if kesim < chegara // 2:
            kesim = max(oyna.rfind(". "), oyna.rfind("; "))
            if kesim != -1:
                kesim += 1
        if kesim < chegara // 2:
            kesim = oyna.rfind(" ")
        if kesim <= 0:
            kesim = chegara  # chorasiz: so'z o'rtasidan
        bolaklar.append(qoldiq[:kesim].strip())
        qoldiq = qoldiq[kesim:].strip()
    if qoldiq:
        bolaklar.append(qoldiq)
    return bolaklar


def modda_xabari(modda: dict) -> List[str]:
    """Bitta modda — o'z xabari bilan (uzun bo'lsa bir nechta bo'lak).

    Modda matni QISQARTIRILMAYDI: qonunning asl matni loyihaning asosiy
    va'dasi, uni Telegram cheklovi uchun kesib tashlash mumkin emas.
    """
    bosh = f"📖 <b>{_tozala(modda['modda_raqami'])}</b>\n<i>{_tozala(modda['qonun_nomi'])}</i>\n\n"
    sarlavha = modda.get("sarlavha", "")
    tana = ""
    # Sarlavha odatda "23-modda. Er va xotinning umumiy mulki" — modda raqami
    # yuqorida allaqachon bor, takrorlamaymiz.
    if ". " in sarlavha:
        tana += f"<b>{_tozala(sarlavha.split('. ', 1)[1])}</b>\n\n"
    if modda.get("holat") == "verified":
        tana += _tozala(modda.get("matn", ""))
    else:
        tana += "<i>Matn hali tekshirilmagan — quyidagi havoladan asl manbani oching.</i>"

    bolaklar = bolaklarga_bol(tana, XABAR_CHEGARASI - len(bosh))
    if not bolaklar:
        return [bosh.strip()]
    return [bosh + bolaklar[0]] + bolaklar[1:]


def asosiy_javob_xabari(javob) -> List[str]:
    """Odam o'qiydigan javob — bitta xabarda: xulosa, tavsiya, organ, ogohlantirish.

    Ilgari bu uch alohida xabar edi va uch moddali javob 5-6 ta xabarga
    bo'linib ketardi: suhbat emas, hujjat oqimiga o'xshardi. Endi odam bitta
    xabarda to'liq javob oladi, qonun matnini esa xohlasa tugma orqali ochadi.
    """
    qismlar = []
    if getattr(javob, "xulosa", ""):
        qismlar.append(_tozala(javob.xulosa))
    if javob.tavsiya:
        qismlar.append("💡 <b>Nima qilish kerak</b>\n\n" + _tozala(javob.tavsiya))
    organ_matni = _organ_matni(javob.murojaat)
    if organ_matni:
        qismlar.append(organ_matni)
    qismlar.append(f"⚠️ <i>{_tozala(javob.disclaimer)}</i>")
    return bolaklarga_bol("\n\n".join(qismlar))


def _organ_matni(organ) -> str:
    if not organ:
        return ""
    qatorlar = [f"🏛 <b>Qayerga murojaat qilasiz</b>\n\n<b>{_tozala(organ.nomi)}</b>"]
    if organ.tavsif:
        qatorlar.append(_tozala(organ.tavsif))
    if organ.telefon:
        qatorlar.append(f"☎️ {_tozala(organ.telefon)}")
    if organ.manzil:
        qatorlar.append(f"📍 {_tozala(organ.manzil)}")
    if organ.ish_vaqti:
        qatorlar.append(f"🕘 {_tozala(organ.ish_vaqti)}")
    if organ.onlayn_murojaat:
        qatorlar.append(f"🌐 {_tozala(organ.onlayn_murojaat)}")
    return "\n".join(qatorlar)


def topilmadi_xabari(javob) -> List[str]:
    """Baza savolga javob bera olmaganda — bo'sh javob o'rniga halol xabar."""
    matn = (
        "🔍 <b>Bazadan bu savolga aniq modda topilmadi.</b>\n\n"
        "Bu savolingiz noto'g'ri degani emas — bazada hali barcha qonunlar yo'q. "
        "Savolni boshqacha, aniqroq yozib ko'ring."
    )
    if javob.tavsiya:
        matn += "\n\n" + _tozala(javob.tavsiya)
    if javob.murojaat:
        matn += f"\n\n🏛 <b>{_tozala(javob.murojaat.nomi)}</b>"
        if javob.murojaat.telefon:
            matn += f"\n☎️ {_tozala(javob.murojaat.telefon)}"
    return bolaklarga_bol(matn)
