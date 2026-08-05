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


XAVF_BELGI = {"qizil": "🔴", "sariq": "🟡", "yashil": "🟢"}
XAVF_NOMI = {
    "qizil": "qonunga zid",
    "sariq": "siz uchun noqulay",
    "yashil": "e'tibor bering",
}
TUR_NOMI = {
    "mehnat": "Mehnat shartnomasi",
    "ijara": "Ijara shartnomasi",
    "kredit": "Kredit / qarz shartnomasi",
    "oldi-sotdi": "Oldi-sotdi shartnomasi",
    "xizmat": "Xizmat ko'rsatish shartnomasi",
    "boshqa": "Shartnoma",
}


def shartnoma_xabari(javob) -> List[str]:
    """Shartnoma tahlili — umumiy mazmun, bandlar, xulosa.

    Modda matni bu yerga KIRITILMAYDI: bandlar ro'yxati o'zi uzun, har biriga
    to'liq modda matnini qo'shsak xabar bir necha ekranga cho'ziladi. Asl
    matnni foydalanuvchi "Qonun moddalari" tugmasi orqali ochadi.
    """
    m = javob.umumiy_mazmun
    qatorlar = [f"📋 <b>{_tozala(TUR_NOMI.get(javob.shartnoma_turi, 'Shartnoma'))}</b>\n"]
    for nomi, qiymat in (("Tomonlar", m.tomonlar), ("Predmet", m.predmet),
                         ("Summa", m.summa), ("Muddat", m.muddat)):
        if qiymat:
            qatorlar.append(f"<b>{nomi}:</b> {_tozala(qiymat)}")
    qismlar = ["\n".join(qatorlar)]

    if javob.bandlar:
        qizil = sum(1 for b in javob.bandlar if b.xavf == "qizil")
        bosh = f"⚠️ <b>Diqqat qiling — {len(javob.bandlar)} ta band</b>"
        if javob.bandlar_soni:
            bosh += f" (jami {javob.bandlar_soni} tadan)"
        if qizil:
            bosh += f"\nShundan <b>{qizil} tasi qonunga zid</b>."
        qismlar.append(bosh)

        for b in javob.bandlar:
            band = (
                f"{XAVF_BELGI.get(b.xavf, '🟡')} <b>{_tozala(b.band)}-band</b> — "
                f"<i>{XAVF_NOMI.get(b.xavf, '')}</i>\n"
                f"{_tozala(b.mazmuni)}\n\n{_tozala(b.izoh)}"
            )
            if b.modda:
                band += (
                    f"\n\n📖 <a href=\"{b.modda.lex_url}\">"
                    f"{_tozala(b.modda.qonun_nomi)}, {_tozala(b.modda.modda_raqami)}</a>"
                )
            qismlar.append(band)
    else:
        qismlar.append("Diqqat talab qiladigan band topilmadi.")

    if javob.xulosa:
        qismlar.append("✅ <b>Xulosa</b>\n\n" + _tozala(javob.xulosa))
    qismlar.append(f"⚠️ <i>{_tozala(javob.disclaimer)}</i>")
    return bolaklarga_bol("\n\n".join(qismlar))


JARIMA_BELGI = {"asos": "🔴", "diqqat": "🟡", "joyida": "🟢", "noma'lum": "⚪️"}
JARIMA_DARAJA = {
    "asos": "bekor qilish uchun asos",
    "diqqat": "tekshirib ko'ring",
    "joyida": "muammo ko'rinmayapti",
    "noma'lum": "ma'lumot yetarli emas",
}


def jarima_xabari(javob) -> List[str]:
    """Jarima tekshiruvi natijasi."""
    if javob.asoslar_soni:
        bosh = f"⚠️ <b>Bekor qilishni so'rashga {javob.asoslar_soni} ta asos topildi</b>"
    else:
        bosh = "🚗 <b>Muddatlar bo'yicha aniq asos topilmadi</b>"
    if javob.shikoyat_kunlari is not None and javob.shikoyat_kunlari >= 0:
        bosh += f"\n⏳ Shikoyat berishga <b>{javob.shikoyat_kunlari} kun</b> qoldi."
    qismlar = [bosh]

    for t in javob.tekshiruvlar:
        matn = (
            f"{JARIMA_BELGI.get(t.holat, '⚪️')} <b>{_tozala(t.nomi)}</b> — "
            f"<i>{JARIMA_DARAJA.get(t.holat, '')}</i>\n{_tozala(t.izoh)}"
        )
        if t.modda:
            matn += (
                f"\n\n📖 <a href=\"{t.modda.lex_url}\">"
                f"{_tozala(t.modda.qonun_nomi)}, {_tozala(t.modda.modda_raqami)}</a>"
            )
        qismlar.append(matn)

    qismlar.append("✅ <b>Xulosa</b>\n\n" + _tozala(javob.xulosa))
    qismlar.append(f"⚠️ <i>{_tozala(javob.disclaimer)}</i>")
    return bolaklarga_bol("\n\n".join(qismlar))


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
