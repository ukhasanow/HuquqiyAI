# Jarima qonuniyligini tekshirish.
#
# NEGA BU YERDA AI YO'Q. Jarimaning taqdirini hal qiladigan narsa — muddatlar,
# ya'ni sanalar ayirmasi. Buni model "taxmin qilishi" mumkin emas: bir kun
# xato hisob odamni asossiz shikoyatga yoki aksincha, haqiqiy asosdan voz
# kechishga olib boradi. Shuning uchun muddat tekshiruvlari oddiy arifmetika
# bilan bajariladi, izohlar esa bazadagi ASL modda matniga havola qiladi.
#
# MUHIM QOIDA: bu modul hech qachon "jarima noqonuniy, to'lamang" demaydi.
# U faqat "shu asos tekshirishga arziydi" deydi va shikoyat muddatini
# eslatadi. Yakuniy bahoni sud yoki vakolatli organ beradi.
from datetime import date
from typing import List, Optional

from .. import storage
from ..models import JarimaJavob, JarimaSorov, JarimaTekshiruv, ModdaJavob

# Muddatlar MJK matnidan olingan (tests/test_jarima.py ularni modda matni
# bilan solishtiradi — qonun o'zgarsa test yiqiladi va bu yer yangilanadi):
#
#   36-modda   — jazo huquqbuzarlik sodir etilgan kundan bir yildan kechiktirmay;
#                kamera orqali qayd etilganda esa bir oydan kechiktirmay
#   316-modda  — qaror nusxasi olingan kundan o'n kun ichida shikoyat
#   330-modda  — qaror chiqarilgan kundan uch oy ijroga qaratilmasa, ijro etilmaydi
JAZO_MUDDATI_OY = 12
KAMERA_JAZO_MUDDATI_OY = 1
SHIKOYAT_MUDDATI_KUN = 10
IJRO_MUHLATI_OY = 3

# Tekshiruvlar shu moddalarga havola qiladi
MUDDAT_MODDASI = "mjk-36"
ISTISNO_MODDASI = "mjk-271"
SHIKOYAT_MODDASI = "mjk-316"
IJRO_MODDASI = "mjk-330"
KAMERA_MODDASI = "mjk-309-1"
BAYONNOMA_MODDASI = "mjk-281"
QAROR_MODDASI = "mjk-311"
ASOSLILIK_MODDASI = "mjk-321"   # qarorni bekor qilish asoslari
AYB_MODDASI = "mjk-307"         # ko'rib chiqishda aniqlanishi lozim bo'lgan holatlar
SHIKOYAT_YOLI_MODDASI = "mjk-315"  # kimga shikoyat beriladi
IJRO_TOXTASH_MODDASI = "mjk-318"   # shikoyat ijroni to'xtatadi
QAYTARISH_MODDASI = "mjk-324"      # bekor qilinsa pul qaytariladi

HOLATLAR = ("asos", "diqqat", "joyida", "noma'lum")


def _modda(modda_id: str) -> Optional[ModdaJavob]:
    m = storage.modda_top(modda_id)
    return ModdaJavob(**m) if m else None


def oy_qoshish(sana: date, oylar: int) -> date:
    """Sanaga oy qo'shadi (kalendar oy, 30 kun emas).

    Qonun "bir oy", "uch oy" deydi — bu 30/90 kun degani emas. Oyning oxirgi
    kunlari uchun kun raqami qisqartiriladi (31-yanvar + 1 oy = 28-fevral).
    """
    oy = sana.month - 1 + oylar
    yil = sana.year + oy // 12
    oy = oy % 12 + 1
    kun = min(sana.day, _oydagi_kunlar(yil, oy))
    return date(yil, oy, kun)


def _oydagi_kunlar(yil: int, oy: int) -> int:
    if oy == 12:
        return 31
    return (date(yil + oy // 12, oy % 12 + 1, 1) - date(yil, oy, 1)).days


def _javobgarlik_muddati(sorov: JarimaSorov) -> JarimaTekshiruv:
    """36-modda: jazo qo'llash muddati o'tgan bo'lsa, 271-modda bo'yicha ish
    tugatilishi LOZIM. Bu eng kuchli asos."""
    oy = KAMERA_JAZO_MUDDATI_OY if sorov.kamera else JAZO_MUDDATI_OY
    manba = "kamera orqali qayd etilgan" if sorov.kamera else "umumiy tartibdagi"

    if not sorov.hodisa_sanasi or not sorov.qaror_sanasi:
        return JarimaTekshiruv(
            nomi="Javobgarlikka tortish muddati",
            holat="noma'lum",
            izoh=(
                f"Bu {manba} jarima uchun eng muhim tekshiruv. Qoidabuzarlik sodir "
                f"etilgan sana va qaror chiqarilgan sanani kiriting — muddat o'tgan "
                f"bo'lsa, ish tugatilishi lozim."
            ),
            modda=_modda(MUDDAT_MODDASI),
        )

    chegara = oy_qoshish(sorov.hodisa_sanasi, oy)
    if sorov.qaror_sanasi > chegara:
        kechikish = (sorov.qaror_sanasi - chegara).days
        return JarimaTekshiruv(
            nomi="Javobgarlikka tortish muddati",
            holat="asos",
            izoh=(
                f"Qoidabuzarlik {sorov.hodisa_sanasi.isoformat()} kuni sodir bo'lgan, "
                f"qaror esa {sorov.qaror_sanasi.isoformat()} kuni chiqarilgan. "
                f"{manba.capitalize()} jarima uchun muddat — {oy} oy, ya'ni "
                f"{chegara.isoformat()} gacha. Muddat {kechikish} kunga o'tkazib "
                f"yuborilgan. 271-moddaning 7-bandiga ko'ra bunday holatda ish "
                f"tugatilishi lozim."
            ),
            modda=_modda(MUDDAT_MODDASI),
        )
    return JarimaTekshiruv(
        nomi="Javobgarlikka tortish muddati",
        holat="joyida",
        izoh=(
            f"Qaror muddat ichida chiqarilgan ({manba} jarima uchun {oy} oy, "
            f"{chegara.isoformat()} gacha edi)."
        ),
        modda=_modda(MUDDAT_MODDASI),
    )


def _ijro_muhlati(sorov: JarimaSorov, bugun: date) -> JarimaTekshiruv:
    """330-modda: qaror uch oy ijroga qaratilmasa, ijro etilmaydi."""
    if not sorov.qaror_sanasi:
        return JarimaTekshiruv(
            nomi="Qaror ijrosining muhlati",
            holat="noma'lum",
            izoh="Qaror sanasini kiriting — eski qaror ijro etilmasligi mumkin.",
            modda=_modda(IJRO_MODDASI),
        )

    chegara = oy_qoshish(sorov.qaror_sanasi, IJRO_MUHLATI_OY)
    if bugun > chegara:
        return JarimaTekshiruv(
            nomi="Qaror ijrosining muhlati",
            holat="diqqat",
            izoh=(
                f"Qaror {sorov.qaror_sanasi.isoformat()} kuni chiqarilgan va "
                f"{IJRO_MUHLATI_OY} oy ({chegara.isoformat()}) o'tgan. Agar shu "
                f"muddat ichida qaror ijroga qaratilmagan bo'lsa, u ijro "
                f"etilmaydi. Ijro to'xtatilgan yoki kechiktirilgan bo'lsa, bu "
                f"muddat to'xtab turadi — shuning uchun ijro ish yuritilgan-"
                f"yuritilmaganini aniqlashtiring."
            ),
            modda=_modda(IJRO_MODDASI),
        )
    return JarimaTekshiruv(
        nomi="Qaror ijrosining muhlati",
        holat="joyida",
        izoh=f"Ijro muhlati hali o'tmagan ({chegara.isoformat()} gacha).",
        modda=_modda(IJRO_MODDASI),
    )


def _shikoyat_muddati(sorov: JarimaSorov, bugun: date):
    """316-modda: qaror nusxasi olingan kundan o'n kun.

    (tekshiruv, qolgan_kun) qaytaradi.
    """
    boshlanish = sorov.qaror_olingan_sanasi or sorov.qaror_sanasi
    if not boshlanish:
        return JarimaTekshiruv(
            nomi="Shikoyat berish muddati",
            holat="noma'lum",
            izoh=(
                f"Qaror nusxasini qachon olganingizni kiriting — shikoyatga "
                f"{SHIKOYAT_MUDDATI_KUN} kun beriladi."
            ),
            modda=_modda(SHIKOYAT_MODDASI),
        ), None

    oxirgi_kun = date.fromordinal(boshlanish.toordinal() + SHIKOYAT_MUDDATI_KUN)
    qolgan = (oxirgi_kun - bugun).days
    manba = "qaror nusxasi olingan" if sorov.qaror_olingan_sanasi else "qaror chiqarilgan"

    if qolgan < 0:
        return JarimaTekshiruv(
            nomi="Shikoyat berish muddati",
            holat="diqqat",
            izoh=(
                f"{SHIKOYAT_MUDDATI_KUN} kunlik muddat {abs(qolgan)} kun oldin "
                f"tugagan ({manba} kun — {boshlanish.isoformat()}). Muddat uzrli "
                f"sabab bilan o'tkazib yuborilgan bo'lsa (kasallik, safar, qaror "
                f"qo'lingizga tegmagani), uni tiklashni so'rab ariza bering."
            ),
            modda=_modda(SHIKOYAT_MODDASI),
        ), qolgan
    return JarimaTekshiruv(
        nomi="Shikoyat berish muddati",
        holat="joyida" if qolgan > 2 else "diqqat",
        izoh=(
            f"Shikoyat berishga {qolgan} kun qoldi (oxirgi kun — "
            f"{oxirgi_kun.isoformat()}). Kechiktirmang."
        ),
        modda=_modda(SHIKOYAT_MODDASI),
    ), qolgan


def _kamera_tekshiruvi(sorov: JarimaSorov) -> Optional[JarimaTekshiruv]:
    """309¹-modda: kamera jarimasida javobgar — transport vositasi egasi."""
    if not sorov.kamera:
        return None
    return JarimaTekshiruv(
        nomi="Kamera orqali qayd etilgan jarima",
        holat="diqqat",
        izoh=(
            "Kamera jarimasi transport vositasi egasiga yoziladi. Agar o'sha "
            "paytda mashinani boshqa shaxs boshqargan bo'lsa (ishonchnoma, "
            "ijara, sotilgan bo'lsa) yoki mashina o'g'irlangan bo'lsa, buni "
            "dalillar bilan ko'rsatib shikoyat qilishingiz mumkin. Fotosurat "
            "bilan tanishishni ham talab qiling: unda davlat raqami va "
            "qoidabuzarlik aniq ko'rinishi kerak."
        ),
        modda=_modda(KAMERA_MODDASI),
    )


def _hujjat_tekshiruvlari(sorov: JarimaSorov) -> List[JarimaTekshiruv]:
    """Qaror va bayonnoma rasmiylashtirilishi bo'yicha eslatmalar.

    Bularni sana kabi hisoblab bo'lmaydi — odam hujjatga qarab o'zi
    tekshiradi. Shuning uchun holat "diqqat", ya'ni nimaga qarash kerakligi
    ko'rsatiladi.
    """
    tekshiruvlar = [
        JarimaTekshiruv(
            nomi="Qaror nusxasi topshirilganmi",
            holat="diqqat",
            izoh=(
                "Qaror nusxasi sizga topshirilishi yoki yuborilishi shart. "
                "Nusxa qo'lingizga tegmagan bo'lsa, shikoyat muddati boshlanmagan "
                "hisoblanadi — buni shikoyatda alohida ko'rsating."
            ),
            modda=_modda(QAROR_MODDASI),
        ),
    ]
    if not sorov.kamera:
        # Kamera jarimasida bayonnoma tuzilmaydi — qaror bevosita chiqariladi
        tekshiruvlar.append(JarimaTekshiruv(
            nomi="Bayonnoma to'g'ri tuzilganmi",
            holat="diqqat",
            izoh=(
                "Bayonnomada sana, joy, huquqbuzarlik mohiyati, tegishli modda, "
                "guvohlar va sizning tushuntirishingiz bo'lishi kerak. Siz "
                "imzolamagan yoki e'tirozingiz yozilmagan bo'lsa, buni "
                "shikoyatda ko'rsating. Bayonnoma nusxasini olishga haqlisiz."
            ),
            modda=_modda(BAYONNOMA_MODDASI),
        ))
    return tekshiruvlar


def _modda_tekshiruvi(sorov: JarimaSorov) -> Optional[JarimaTekshiruv]:
    """Qarorda ko'rsatilgan MJK moddasi bazada bormi."""
    if not sorov.modda:
        return JarimaTekshiruv(
            nomi="Qaysi modda bo'yicha jarima solingan",
            holat="noma'lum",
            izoh=(
                "Qarorda MJK moddasi ko'rsatilishi shart. Uni kiriting — "
                "jarima miqdori shu moddadagi chegarada bo'lishi kerak."
            ),
            modda=None,
        )
    modda = _modda(_mjk_id(sorov.modda))
    if not modda:
        return JarimaTekshiruv(
            nomi="Qaysi modda bo'yicha jarima solingan",
            holat="noma'lum",
            izoh=(
                f"«{sorov.modda}» moddasi bazada topilmadi. Modda raqamini "
                f"qarordagidek kiriting (masalan 128-3)."
            ),
            modda=None,
        )
    return JarimaTekshiruv(
        nomi="Qaysi modda bo'yicha jarima solingan",
        holat="joyida",
        izoh=(
            "Jarima miqdori shu moddada ko'rsatilgan chegarada bo'lishi kerak. "
            "Qarordagi summani modda matni bilan solishtiring."
        ),
        modda=modda,
    )


def _band_tekshiruvi(sorov: JarimaSorov) -> Optional[JarimaTekshiruv]:
    """Qoidalarning qaysi bandi buzilgani ko'rsatilganmi."""
    if not sorov.band:
        return JarimaTekshiruv(
            nomi="Qoidalarning qaysi bandi buzilgan",
            holat="diqqat",
            izoh=(
                "Qarorda Yo'l harakati qoidalarining aynan qaysi bandi "
                "buzilgani ko'rsatilishi kerak. Ko'rsatilmagan bo'lsa yoki band "
                "sizning holatingizga to'g'ri kelmasa — bu shikoyat uchun asos."
            ),
            modda=None,
        )
    band = _modda(f"yhqoida-{sorov.band.strip().rstrip('.')}")
    if not band:
        return JarimaTekshiruv(
            nomi="Qoidalarning qaysi bandi buzilgan",
            holat="noma'lum",
            izoh=f"Qoidalarning «{sorov.band}» bandi bazada topilmadi.",
            modda=None,
        )
    return JarimaTekshiruv(
        nomi="Qoidalarning qaysi bandi buzilgan",
        holat="joyida",
        izoh=(
            "Band matnini o'qing: unda tasvirlangan holat sizning "
            "vaziyatingizga to'g'ri kelmasa, bu shikoyat uchun asos."
        ),
        modda=band,
    )


def _asoslilik_tekshiruvi() -> JarimaTekshiruv:
    """321-modda qarorni bekor qilishning TO'RT asosini sanab beradi.

    Bu ro'yxat muddatlardan farqli — uni hisoblab bo'lmaydi, odam qaror va
    bayonnomaga qarab o'zi solishtiradi. Lekin aynan shu ro'yxat "jarima
    qaysi holatlarda asossiz" degan savolning qonundagi javobi.
    """
    return JarimaTekshiruv(
        nomi="Qaror asosli chiqarilganmi",
        holat="diqqat",
        izoh=(
            "Qonun qarorni bekor qilish yoki o'zgartirish uchun to'rt asosni "
            "belgilaydi. Qarorni shular bo'yicha solishtiring:\n"
            "1) ish to'liq bo'lmagan holda yoki bir tomonlama ko'rib chiqilgan "
            "(tushuntirishingiz olinmagan, dalillaringiz tekshirilmagan);\n"
            "2) qo'llanilgan modda ishning haqiqiy holatiga mos kelmaydi "
            "(qarordagi modda yoki Qoidalar bandi sizning holatingizni "
            "tasvirlamaydi);\n"
            "3) ish yuritish qoidalari jiddiy buzilgan (bayonnoma noto'g'ri "
            "tuzilgan, sizni xabardor qilishmagan);\n"
            "4) qo'llanilgan jazo adolatsiz."
        ),
        modda=_modda(ASOSLILIK_MODDASI),
    )


def _aybdorlik_tekshiruvi() -> JarimaTekshiruv:
    """307-modda: aybdorlik ANIQLANISHI SHART."""
    return JarimaTekshiruv(
        nomi="Aybdorligingiz aniqlanganmi",
        holat="diqqat",
        izoh=(
            "Ishni ko'rib chiqishda huquqbuzarlik sodir etilgan-etilmagani, "
            "uning vaqti va joyi hamda sizning AYBDORLIGINGIZ aniqlanishi shart. "
            "Aybdorlik dalil bilan tasdiqlanmagan bo'lsa yoki qoidabuzarlik "
            "hodisasining o'zi bo'lmasa, ish yuritish tugatilishi kerak."
        ),
        modda=_modda(AYB_MODDASI),
    )


def _shikoyat_yoli(sorov: JarimaSorov) -> List[str]:
    """Shikoyat qayerga va qanday beriladi (315, 318, 324-moddalar)."""
    qadamlar = [
        "Shikoyatni <b>yuqori turuvchi organga (mansabdor shaxsga)</b> yoki "
        "<b>jinoyat ishlari bo'yicha tuman (shahar) sudiga</b> berish mumkin.",
        "Shikoyat qarorni chiqargan organ orqali yoki bevosita sudga yuboriladi. "
        "Organ uni uch sutka ichida ish bilan birga tegishli joyga jo'natadi.",
        "<b>Davlat boji to'lanmaydi</b> — shikoyat bergan shaxs undan ozod etilgan.",
        "Muddatida berilgan shikoyat qaror <b>ijrosini to'xtatib turadi</b>: "
        "shikoyat ko'rib chiqilgunga qadar jarimani to'lash talab qilinmaydi "
        "(joyning o'zida undiriladigan jarima bundan mustasno).",
        "Shikoyat tushgan kundan <b>o'n kun ichida</b> ko'rib chiqiladi.",
    ]
    if sorov.tolangan:
        qadamlar.append(
            "Jarimani to'lagan bo'lsangiz ham shikoyat bering: qaror bekor "
            "qilinib ish tugatilsa, <b>undirib olingan pul qaytariladi</b>."
        )
    return qadamlar


def _mjk_id(modda: str) -> str:
    """"128³", "128-3", "128-3-modda" -> "mjk-128-3"."""
    USTKIDAN = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")
    m = modda.strip().lower().replace("-modda", "").replace("modda", "").strip()
    asos = m.rstrip("⁰¹²³⁴⁵⁶⁷⁸⁹")
    ustki = m[len(asos):].translate(USTKIDAN)
    return f"mjk-{asos}" + (f"-{ustki}" if ustki else "")


def _xulosa(tekshiruvlar: List[JarimaTekshiruv], qolgan: Optional[int]) -> str:
    asoslar = [t for t in tekshiruvlar if t.holat == "asos"]
    if asoslar:
        matn = (
            f"Jarimani bekor qilishni so'rashga {len(asoslar)} ta jiddiy asos "
            f"topildi: " + ", ".join(t.nomi.lower() for t in asoslar) + ". "
            "Shikoyat bering — asosni qaror va hujjatlar nusxasi bilan birga ko'rsating."
        )
    else:
        matn = (
            "Muddatlar bo'yicha aniq asos topilmadi. Bu jarima albatta "
            "qonuniy degani emas: quyidagi «diqqat» belgili bandlarni qaror va "
            "bayonnoma bilan solishtirib chiqing."
        )
    if qolgan is not None and qolgan >= 0:
        matn += f" Shikoyat berishga {qolgan} kun qoldi."
    elif qolgan is not None:
        matn += " Shikoyat muddati o'tgan — uni tiklashni so'rab ariza berishingiz mumkin."
    return matn


def jarimani_tekshir(sorov: JarimaSorov, bugun: Optional[date] = None) -> JarimaJavob:
    """Jarima qarorini tekshiruv ro'yxati bo'yicha baholaydi."""
    bugun = bugun or date.today()

    shikoyat, qolgan = _shikoyat_muddati(sorov, bugun)
    tekshiruvlar: List[JarimaTekshiruv] = [
        _javobgarlik_muddati(sorov),
        _ijro_muhlati(sorov, bugun),
        shikoyat,
    ]
    kamera = _kamera_tekshiruvi(sorov)
    if kamera:
        tekshiruvlar.append(kamera)
    tekshiruvlar.append(_modda_tekshiruvi(sorov))
    tekshiruvlar.append(_band_tekshiruvi(sorov))
    tekshiruvlar.append(_asoslilik_tekshiruvi())
    tekshiruvlar.append(_aybdorlik_tekshiruvi())
    tekshiruvlar.extend(_hujjat_tekshiruvlari(sorov))

    # Asos topilganlari birinchi: odam ro'yxatni tepadan o'qiydi
    tartib = {"asos": 0, "diqqat": 1, "noma'lum": 2, "joyida": 3}
    tekshiruvlar.sort(key=lambda t: tartib[t.holat])

    return JarimaJavob(
        tekshiruvlar=tekshiruvlar,
        asoslar_soni=sum(1 for t in tekshiruvlar if t.holat == "asos"),
        shikoyat_kunlari=qolgan,
        xulosa=_xulosa(tekshiruvlar, qolgan),
        shikoyat_yoli=_shikoyat_yoli(sorov),
    )
