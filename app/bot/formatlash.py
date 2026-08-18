import html
import re
from typing import List


XABAR_CHEGARASI = 3900


def _tozala(matn: str) -> str:
    return html.escape(matn or "", quote=False)


def _urgu(matn: str) -> str:
    """Izoh matnini Telegram HTML uchun tayyorlaydi: `**qalin**` -> `<b>`.

    Xizmat modullaridagi izohlar HTML emas, `**qalin**` bilan yoziladi —
    saytda ular `qalinFormat()` orqali textContent bo'lib chiqadi, bu yerda
    esa `<b>` ga aylanadi. Bitta manbadan ikki xil chiqish.

    Tartib muhim: AVVAL hammasi escape qilinadi, keyin qalin belgilanadi.
    Izohga foydalanuvchi kiritgan qiymat qo'shilishi mumkin (masalan qarordagi
    modda raqami), va undagi "<" xabarni Telegram uchun buzib qo'yardi.
    """
    xavfsiz = html.escape(matn or "", quote=False)
    return _QALIN.sub(r"<b>\1</b>", xavfsiz)



_QALIN = re.compile(r"\*\*(.+?)\*\*", re.S)


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
        qismlar.append("✅ <b>Xulosa</b>\n\n" + _urgu(javob.xulosa))
    qismlar.append(f"⚠️ <i>{_tozala(javob.disclaimer)}</i>")
    return bolaklarga_bol("\n\n".join(qismlar))


JARIMA_BELGI = {"asos": "🔴", "diqqat": "🟡", "joyida": "🟢", "noma'lum": "⚪️"}
JARIMA_DARAJA = {
    "asos": "bekor qilish uchun asos",
    "diqqat": "tekshirib ko'ring",
    "joyida": "muammo ko'rinmayapti",
    "noma'lum": "ma'lumot yetarli emas",
}


def statistika_xabari(s: dict, moddalar_soni: int) -> List[str]:
    """Admin uchun bot va sayt ko'rsatkichlari."""
    jami = s.get("jami_sorovlar", 0)
    topildi = s.get("javob_topildi", 0)
    kesim = s.get("manba_kesimi", {})
    bot = kesim.get("bot", {})
    sayt = kesim.get("sayt", {})

    def ulush(qism, butun):
        return f"{round(qism / butun * 100)}%" if butun else "—"

    qatorlar = [
        "📊 <b>HuquqiyAI statistikasi</b>\n",
        f"<b>Jami so'rovlar:</b> {jami}",
        f"<b>Javob topildi:</b> {topildi} ({ulush(topildi, jami)})",
        f"<b>Foydalanuvchilar:</b> {s.get('foydalanuvchilar_soni', 0)} "
        f"(bot {s.get('bot_foydalanuvchilar_soni', 0)} · "
        f"sayt {s.get('sayt_foydalanuvchilar_soni', 0)})",
        f"<b>Bazada:</b> {moddalar_soni} modda/band",
        "",
        "🤖 <b>Telegram bot</b>",
        f"So'rovlar: {bot.get('jami', 0)} · topildi: {ulush(bot.get('topildi', 0), bot.get('jami', 0))}",
        f"Ovozli savol: {bot.get('ovozli', 0)} · ovozli javob: {s.get('ovozli_javoblar', 0)}",
        f"Oddiy / Pro: {bot.get('oddiy', 0)} / {bot.get('pro', 0)}",
        "",
        "🌐 <b>Sayt</b>",
        f"So'rovlar: {sayt.get('jami', 0)} · topildi: {ulush(sayt.get('topildi', 0), sayt.get('jami', 0))}",
        f"Ovozli savol: {sayt.get('ovozli', 0)}",
        "",
        "🧰 <b>Vositalar</b>",
        f"📋 Shartnoma tahlili: {s.get('shartnoma_tahlillari', 0)}",
        f"🚗 Jarima tekshiruvi: {s.get('jarima_tekshiruvlari', 0)} "
        f"(asos topilgani: {s.get('jarima_asos_topildi', 0)})",
    ]

    turlar = s.get("shartnoma_turlari") or {}
    if turlar:
        eng = sorted(turlar.items(), key=lambda x: -x[1])[:5]
        qatorlar.append("Shartnoma turlari: " + ", ".join(f"{t} — {n}" for t, n in eng))

    mavzular = s.get("mavzular") or {}
    if mavzular:
        eng = sorted(mavzular.items(), key=lambda x: -x[1])[:5]
        qatorlar += ["", "🏷 <b>Eng ko'p mavzular</b>"]
        qatorlar += [f"{i}. {_tozala(m)} — {n}" for i, (m, n) in enumerate(eng, 1)]

    kunlik = s.get("kunlik_30") or []
    if kunlik:
        oxirgi_7 = kunlik[-7:]
        hafta = sum(k.get("jami", 0) for k in oxirgi_7)
        qatorlar += [
            "",
            f"📅 <b>Oxirgi 7 kun:</b> {hafta} so'rov "
            f"(kuniga o'rtacha {round(hafta / 7, 1)})",
            f"Bugun: {kunlik[-1].get('jami', 0)}",
        ]

    topilmagan = s.get("topilmagan_savollar") or []
    if topilmagan:
        qatorlar += ["", f"❓ <b>Javob topilmagan savollar:</b> {len(topilmagan)} ta"]
        for t in topilmagan[:5]:
            qatorlar.append(f"• <i>{_tozala(str(t.get('savol', ''))[:90])}</i>")

    return bolaklarga_bol("\n".join(qatorlar))


def oqilgan_jarima_xabari(sorov) -> List[str]:
    """Rasmdan o'qilgan ma'lumotlar — foydalanuvchi tekshirishi uchun.

    Model sanani yoki tezlikni xato o'qishi mumkin, u holda butun xulosa
    noto'g'ri bo'ladi. Shuning uchun o'qilgani albatta ko'rsatiladi.
    """
    qatorlar = ["📄 <b>Qarordan o'qidim:</b>\n"]
    maydonlar = [
        ("Qoidabuzarlik sanasi", sorov.hodisa_sanasi),
        ("Qaror sanasi", sorov.qaror_sanasi),
        ("Qaror raqami", sorov.qaror_raqami),
        ("Modda", sorov.modda),
        ("Qoidalar bandi", sorov.band),
        ("Summa", sorov.summa),
        ("Qayd etilgan tezlik", f"{sorov.qayd_etilgan_tezlik} km/soat"
                                if sorov.qayd_etilgan_tezlik else ""),
        ("Ruxsat etilgan tezlik", f"{sorov.ruxsat_etilgan_tezlik} km/soat"
                                  if sorov.ruxsat_etilgan_tezlik else ""),
        ("Kamera orqali", "ha" if sorov.kamera else ""),
    ]
    for nomi, qiymat in maydonlar:
        if qiymat:
            qatorlar.append(f"<b>{nomi}:</b> {_tozala(str(qiymat))}")
    if len(qatorlar) == 1:
        qatorlar.append("<i>Hech qanday ma'lumot o'qib bo'lmadi.</i>")
    qatorlar.append(
        "\n⚠️ <i>Noto'g'ri o'qilgan bo'lsa, /jarima orqali qo'lda kiriting — "
        "xulosa aynan shu ma'lumotlarga tayanadi.</i>"
    )
    return bolaklarga_bol("\n".join(qatorlar))


def hujjat_xabari(javob) -> List[str]:
    """Hujjat turi, tekshirish ro'yxati va bekor qilish yo'li.

    Muddat eng tepada turadi: odam avval "menda qancha vaqt bor?" degan
    savolga javob oladi, tafsilotni keyin o'qiydi. Tur taxminiy bo'lsa, bu
    ochiq aytiladi — noto'g'ri tur noto'g'ri muddat degani.
    """
    qatorlar = [f"📑 <b>{_tozala(javob.turi_nomi)}</b>"]
    if javob.ishonch == "taxmin" and javob.turi != "boshqa":
        qatorlar.append(
            "<i>Turi taxminan aniqlandi — quyidagi muddat sizga tegishli "
            "ekanini hujjatning o'zidan tekshiring.</i>"
        )

    if javob.muddat:
        qatorlar.append(
            f"\n⏳ <b>Shikoyat muddati: {_tozala(javob.muddat)}</b>"
            f"\n<i>{_tozala(javob.muddat_izohi)}</i>"
        )
    elif javob.muddat_izohi:
        qatorlar.append(f"\n⏳ <i>{_tozala(javob.muddat_izohi)}</i>")

    if javob.tekshiruvlar:
        qatorlar.append("\n<b>🔍 Hujjatda nimani tekshirish kerak</b>")
        for i, t in enumerate(javob.tekshiruvlar, 1):
            qatorlar.append(f"\n<b>{i}. {_tozala(t.nomi)}</b>")
            qatorlar.append(_urgu(t.izoh))
            if t.modda:
                qatorlar.append(
                    f"<i>📖 {_tozala(t.modda.modda_raqami)} — "
                    f"{_tozala(t.modda.qonun_nomi)}</i>"
                )

    if javob.bekor_yoli:
        qatorlar.append("\n<b>⚖️ Qanday bekor qildiriladi</b>")
        for i, q in enumerate(javob.bekor_yoli, 1):
            qatorlar.append(f"\n<b>{i}.</b> {_urgu(q.matn)}")
            if q.modda:
                qatorlar.append(
                    f"<i>📖 {_tozala(q.modda.modda_raqami)} — "
                    f"{_tozala(q.modda.qonun_nomi)}</i>"
                )

    qatorlar.append(f"\n⚠️ <i>{_tozala(javob.ogohlantirish)}</i>")
    return bolaklarga_bol("\n".join(qatorlar))


def radar_kuzatuvi_xabari(kuzatuv, dislokatsiya: str = "") -> List[str]:
    """Suratdan nima ko'rilgani — huquqiy xulosadan ALOHIDA ko'rsatiladi.

    Model suratni xato o'qishi mumkin (masalan oq "Malibu"ni patrul avtomobili
    deb bilishi), shuning uchun odam ko'rgani bilan solishtira olishi kerak.
    """
    ORNATILISH = {
        "trenoga": "uch oyoqli tagliksa (trenoga)",
        "avtomobilda": "avtomobilda",
        "ustunda": "doimiy ustunda",
        "qolda": "xodim qo'lida",
        "noanik": "aniqlab bo'lmadi",
    }
    UCHLIK = {True: "ha", False: "yo'q", None: "aniqlab bo'lmadi"}

    qatorlar = ["📡 <b>Suratda ko'rganim:</b>\n"]
    maydonlar = [
        ("O'rnatilishi", ORNATILISH.get(kuzatuv.ornatilish, kuzatuv.ornatilish)),
        ("Yonida patrul avtomobili", UCHLIK[kuzatuv.patrul_avtomobili]),
        ("Avtomobil", kuzatuv.avtomobil_tavsifi),
        ("Odam bor", "ha" if kuzatuv.odam_bormi else "yo'q"),
        ("Formadagi xodim", UCHLIK[kuzatuv.xodim_formada]),
        ("Moslama qarovsiz", "ha" if kuzatuv.moslama_qarovsiz else ""),
        ("Yashiringan", kuzatuv.yashirish_tavsifi if kuzatuv.yashiringan else ""),
        ("Moslama rusumi", kuzatuv.moslama_rusumi),
        ("Tezlik belgisi", f"{kuzatuv.tezlik_belgisi} km/soat"
                           if kuzatuv.tezlik_belgisi else ""),
        ("Suratga olingan", kuzatuv.sana),
    ]
    for nomi, qiymat in maydonlar:
        if qiymat:
            qatorlar.append(f"<b>{nomi}:</b> {_tozala(str(qiymat))}")
    if kuzatuv.joy_belgilari:
        qatorlar.append("<b>Mo'ljal:</b> " + _tozala(", ".join(kuzatuv.joy_belgilari)))

    if dislokatsiya:
        qatorlar.append(
            "\n📍 <b>Dislokatsiya so'rovi uchun</b> (34-band bo'yicha "
            "murojaatingizga shu ma'lumotni kiriting):\n"
            f"<code>{_tozala(dislokatsiya)}</code>"
        )
    qatorlar.append(
        "\n⚠️ <i>Bu — suratdan ko'rilgan holat, huquqiy xulosa emas. Noto'g'ri "
        "ko'rilgan bo'lsa, /jarima orqali qo'lda kiriting.</i>"
    )
    return bolaklarga_bol("\n".join(qatorlar))


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
            f"<i>{JARIMA_DARAJA.get(t.holat, '')}</i>\n{_urgu(t.izoh)}"
        )
        if t.modda:
            matn += (
                f"\n\n📖 <a href=\"{t.modda.lex_url}\">"
                f"{_tozala(t.modda.qonun_nomi)}, {_tozala(t.modda.modda_raqami)}</a>"
            )
        qismlar.append(matn)

    qismlar.append("✅ <b>Xulosa</b>\n\n" + _urgu(javob.xulosa))
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
