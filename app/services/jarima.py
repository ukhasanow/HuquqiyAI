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
import base64
import json
import logging
import re
from datetime import date, datetime
from typing import List, Optional

import httpx

from .. import storage
from ..config import GEMINI_API_KEY, GEMINI_MODEL
from ..models import JarimaJavob, JarimaSorov, JarimaTekshiruv, ModdaJavob

log = logging.getLogger(__name__)

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
KAMERA_MODDASI = "mjk-17-1"        # kamera orqali qayd etiladigan moddalar ro'yxati
QAROR_KAMERA_MODDASI = "mjk-309-1"  # kamera qarorining majburiy mazmuni
BAYONNOMA_MODDASI = "mjk-281"
QAROR_MODDASI = "mjk-311"
ASOSLILIK_MODDASI = "mjk-321"   # qarorni bekor qilish asoslari
AYB_MODDASI = "mjk-307"         # ko'rib chiqishda aniqlanishi lozim bo'lgan holatlar
TEZLIK_MODDASI = "mjk-128-3"

# YPX nizomi (VM 975-son) — radardan foydalanish tartibi. 28 va 32-bandlar
# talablarga rioya qilinmay chiqarilgan qarorlar YURIDIK KUCHGA EGA
# BO'LMASLIGINI belgilaydi — bu oddiy bekor qilish asosidan kuchliroq.
SERTIFIKAT_MODDASI = "ypx-28"           # sertifikat va hisobda turish
XOLISLAR_MODDASI = "ypx-29"             # ko'rsatkichga e'tiroz — xolislar ishtiroki
RADAR_MODDASI = "ypx-32"                # patrul avtomobilidan yechib olish taqiqi
DISLOKATSIYA_MODDASI = "ypx-33"         # statsionar kameralar dislokatsiyasi
DISLOKATSIYA_KOCHMA_MODDASI = "ypx-34"  # ko'chma radar dislokatsiyasi
MASULIYAT_MODDASI = "ypx-35"            # xodim moslamani qabul qiladi va mas'ul
XOTIRA_MODDASI = "ypx-36"               # xotiraga o'rnatilgan joy va yo'nalish

# DIQQAT — ko'p uchraydigan yanglish tushuncha. Nizomda "trenoga", "uch oyoqli"
# degan so'z YO'Q, va uch oyoqli tagliksa qo'yilgan radar o'z-o'zidan
# taqiqlanmagan: 30, 31 va 34-bandlar ko'chma fotoradarni ochiq nazarda tutadi.
# Qarorni kuchsiz qiladigan narsa moslamaning TURI emas, quyidagilar:
#   32-band — patrul avtomobili uchun belgilangan moslamani yechib olish,
#             uni begona transport vositasiga o'rnatish, begona shaxsni jalb qilish
#   28-band — sertifikat yo'q / muddati o'tgan / IIB hisobida yo'q
#   34-band — dislokatsiyada ko'rsatilmagan joy yoki vaqt
# Shuning uchun "trenoga" ning o'zi hech qachon "asos" deb belgilanmaydi:
# asossiz shikoyat foydalanuvchini ham, tizimga ishonchni ham yo'qotadi.

# 128³-moddaning oxirgi qismi: "tezlikni oʻlchaydigan maxsus uskunalar va
# transport vositalari spidometri koʻrsatkichlaridagi yoʻl qoʻyilishi mumkin
# boʻlgan jami xatolar hisobga olinib, ularda qayd etilgan tezlikdan soatiga
# 5 kilometr chegirib tashlangan holda, maʼmuriy jazo chorasi qoʻllaniladi."
#
# Ya'ni radar 5 km/soat xatolikka yo'l qo'yadi va u HAYDOVCHI foydasiga
# hisoblanishi shart. Bu eng ko'p e'tibordan chetda qoladigan qoida.
TEZLIK_CHEGIRMASI = 5

# 128³-modda qismlari: (oshirish chegarasi km/soat, BHM baravari)
TEZLIK_JARIMALARI = [(20, 1), (40, 5), (60, 9), (None, 15)]

# 17¹-moddadagi YOPIQ ro'yxat: kamera orqali FAQAT shu moddalar qayd etiladi.
# Ro'yxatda yo'q modda bo'yicha kamera jarimasi solingan bo'lsa — bu asos.
KAMERA_MODDALARI = {
    "mjk-125", "mjk-128", "mjk-128-1", "mjk-128-3", "mjk-128-4", "mjk-128-5",
    "mjk-128-6", "mjk-128-7", "mjk-128-9", "mjk-128-10", "mjk-129", "mjk-130",
    "mjk-135",
}


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
            "dalillar bilan ko'rsatib shikoyat qilishingiz mumkin.\n\n"
            "Qarorga huquqbuzarlik paytidagi **davlat raqami ko'rinadigan "
            "tasvir** ilova qilinishi va qaror **uch kun ichida buyurtma "
            "pochta jo'natmasi** bilan yuborilishi shart (309¹-modda). "
            "Tasvir yo'q yoki raqam o'qilmaydigan bo'lsa — bu asos.\n\n"
            "<i>Eslatma: ko'chma radarda inspektor ko'rsatkich va sertifikatni "
            "ko'rsatishi shart edi, lekin bu talab 2024-yil iyulda bekor "
            "qilingan — endi bu argument ish bermaydi.</i>"
        ),
        modda=_modda(QAROR_KAMERA_MODDASI),
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
        "Shikoyatni **yuqori turuvchi organga (mansabdor shaxsga)** yoki "
        "**jinoyat ishlari bo'yicha tuman (shahar) sudiga** berish mumkin.",
        "Shikoyat qarorni chiqargan organ orqali yoki bevosita sudga yuboriladi. "
        "Organ uni uch sutka ichida ish bilan birga tegishli joyga jo'natadi.",
        "**Davlat boji to'lanmaydi** — shikoyat bergan shaxs undan ozod etilgan.",
        "Muddatida berilgan shikoyat qaror **ijrosini to'xtatib turadi**: "
        "shikoyat ko'rib chiqilgunga qadar jarimani to'lash talab qilinmaydi "
        "(joyning o'zida undiriladigan jarima bundan mustasno).",
        "Shikoyat tushgan kundan **o'n kun ichida** ko'rib chiqiladi.",
    ]
    if sorov.tolangan:
        qadamlar.append(
            "Jarimani to'lagan bo'lsangiz ham shikoyat bering: qaror bekor "
            "qilinib ish tugatilsa, **undirib olingan pul qaytariladi**."
        )
    return qadamlar


def kutilgan_bhm(oshirish: int) -> int:
    """128³-modda qismlariga ko'ra jarima necha baravar BHM bo'lishi kerak."""
    for chegara, baravar in TEZLIK_JARIMALARI:
        if chegara is None or oshirish <= chegara:
            return baravar
    return TEZLIK_JARIMALARI[-1][1]


def _tezlik_tekshiruvi(sorov: JarimaSorov) -> Optional[JarimaTekshiruv]:
    """128³-modda: qayd etilgan tezlikdan 5 km/soat CHEGIRIB tashlanadi.

    Bu chegirma majburiy va haydovchi foydasiga ishlaydi. Ikki xil asos
    beradi: chegirmadan keyin oshirish umuman qolmasa (jarima o'rinsiz) yoki
    jarima qismi noto'g'ri tanlangan bo'lsa (summa ortiqcha).
    """
    qayd, ruxsat = sorov.qayd_etilgan_tezlik, sorov.ruxsat_etilgan_tezlik
    if qayd is None or ruxsat is None:
        return None

    hisobga_olinadigan = qayd - TEZLIK_CHEGIRMASI
    oshirish = hisobga_olinadigan - ruxsat
    asos_matni = (
        f"Radar {qayd} km/soat qayd etgan, ruxsat etilgan tezlik — {ruxsat} km/soat. "
        f"128³-moddaga ko'ra o'lchash xatosi uchun {TEZLIK_CHEGIRMASI} km/soat "
        f"chegirib tashlanishi SHART: {qayd} − {TEZLIK_CHEGIRMASI} = "
        f"{hisobga_olinadigan} km/soat. "
    )

    if oshirish <= 0:
        return JarimaTekshiruv(
            nomi="Tezlik hisobi (5 km/soat chegirmasi)",
            holat="asos",
            izoh=(
                asos_matni
                + "Bu ruxsat etilgan tezlikdan oshmaydi, ya'ni qonun bo'yicha "
                "hisobga olinadigan oshirish yo'q va jarima solish uchun asos yo'q."
            ),
            modda=_modda(TEZLIK_MODDASI),
        )

    kutilgan = kutilgan_bhm(oshirish)
    izoh = (
        asos_matni
        + f"Hisobga olinadigan oshirish — {oshirish} km/soat, bunga 128³-modda "
        f"bo'yicha bazaviy hisoblash miqdorining **{kutilgan} baravari** "
        f"miqdorida jarima to'g'ri keladi."
    )

    if sorov.jarima_bhm is not None and sorov.jarima_bhm > kutilgan:
        return JarimaTekshiruv(
            nomi="Tezlik hisobi (5 km/soat chegirmasi)",
            holat="asos",
            izoh=(
                izoh + f" Sizga esa {sorov.jarima_bhm:g} baravar solingan — "
                f"jarima qismi noto'g'ri tanlangan, summa kamaytirilishi kerak."
            ),
            modda=_modda(TEZLIK_MODDASI),
        )
    return JarimaTekshiruv(
        nomi="Tezlik hisobi (5 km/soat chegirmasi)",
        holat="diqqat",
        izoh=(
            izoh + " Qarordagi summani shu bilan solishtiring: ko'p bo'lsa, "
            "chegirma hisobga olinmagan bo'lishi mumkin."
        ),
        modda=_modda(TEZLIK_MODDASI),
    )


def _radar_tekshiruvi(sorov: JarimaSorov) -> List[JarimaTekshiruv]:
    """Radar qonuniy ishlatilganmi (YPX nizomi, 28-36-bandlar).

    28 va 32-bandlar juda kuchli oqibatni belgilaydi: talablarga rioya
    qilinmay chiqarilgan jarima qarorlari "yuridik kuchga ega bo'lmaydi va
    huquqiy oqibatlar keltirib chiqarmaydi". Ya'ni bu shunchaki bekor qilish
    asosi emas — qaror boshidan kuchga ega emas.

    Lekin bu kuchli oqibat DALIL talab qiladi. Yuqoridagi izohga qarang:
    moslamaning uch oyoqli tagliksa turishi o'zi hech narsani isbotlamaydi.
    """
    if sorov.radar_turi == "statsionar":
        return [JarimaTekshiruv(
            nomi="Radar qonuniy o'rnatilganmi",
            holat="diqqat",
            izoh=(
                "Doimiy (statsionar) kameralarning joylashuvi va ish tartibi "
                "hududiy ichki ishlar boshlig'i tasdiqlagan dislokatsiya bilan "
                "belgilanadi. Kamera dislokatsiyada ko'rsatilmagan joyda "
                "o'rnatilgan bo'lsa, buni shikoyatda so'rang."
            ),
            modda=_modda(DISLOKATSIYA_MODDASI),
        )]

    tekshiruvlar = []
    tekshiruvlar.append(_band32_tekshiruvi(sorov))

    if sorov.moslama_qarovsiz:
        tekshiruvlar.append(JarimaTekshiruv(
            nomi="Moslama qarovsiz qoldirilganmi",
            holat="asos",
            izoh=(
                "35-bandga ko'ra tezlik o'lchash vositasini xizmatga jalb "
                "etilgan YPX xodimi qabul qilib oladi va uning butligi, sozligi "
                "hamda **belgilangan tartibda ishlatilishiga mas'ul** "
                "hisoblanadi. Moslama odamsiz, qarovsiz qoldirilgan bo'lsa, bu "
                "talab bajarilmagan.\n\n"
                "Shikoyatda o'sha kuni moslamani qaysi xodim qabul qilganini va "
                "u qayerda bo'lganini so'rang."
            ),
            modda=_modda(MASULIYAT_MODDASI),
        ))

    tekshiruvlar.append(JarimaTekshiruv(
        nomi="Radar sertifikati va hisobda turishi",
        holat="diqqat",
        izoh=(
            "Sertifikatga ega bo'lmagan, sertifikat muddati tugagan yoki ichki "
            "ishlar organlari hisobida bo'lmagan tezlik o'lchash vositasi "
            "asosida chiqarilgan qarorlar **yuridik kuchga ega bo'lmaydi** "
            "(28-band). Shikoyatda moslamaning sertifikati, uning amal qilish "
            "muddati va hisobda turishi to'g'risidagi ma'lumotni so'rang — "
            "javob berilmasa yoki muddat o'tgan bo'lsa, bu mustaqil asos."
        ),
        modda=_modda(SERTIFIKAT_MODDASI),
    ))
    if sorov.radar_turi in ("trenoga", "kochma"):
        tekshiruvlar.append(JarimaTekshiruv(
            nomi="Radar dislokatsiyaga muvofiq qo'yilganmi",
            holat="diqqat",
            izoh=(
                "Ko'chma fotoradar va mobil komplekslarni qo'llash joyi va vaqti "
                "DYHXX saf bo'limi boshlig'i tasdiqlagan dislokatsiyaga muvofiq "
                "belgilanadi (34-band). Shikoyatda o'sha kungi tasdiqlangan "
                "dislokatsiya nusxasini so'rang: radar unda ko'rsatilmagan joyda "
                "turgan bo'lsa, bu asos bo'ladi."
            ),
            modda=_modda(DISLOKATSIYA_KOCHMA_MODDASI),
        ))
        tekshiruvlar.append(JarimaTekshiruv(
            nomi="Moslama xotirasiga joy va yo'nalish kiritilganmi",
            holat="diqqat",
            izoh=(
                "36-bandga ko'ra xodim xizmatni boshlashdan oldin moslama "
                "xotirasiga uning **o'rnatilgan joyi va harakat yo'nalishi** "
                "to'g'risidagi ma'lumotni kiritishi shart. Shikoyatda shu "
                "yozuvni so'rang: u yo'q bo'lsa yoki qarordagi joy bilan mos "
                "kelmasa, o'lchov belgilangan tartibda o'tkazilmagan bo'ladi."
            ),
            modda=_modda(XOTIRA_MODDASI),
        ))
    if sorov.norozilik_bildirilgan:
        tekshiruvlar.append(JarimaTekshiruv(
            nomi="E'tirozingiz xolislar ishtirokida rasmiylashtirilganmi",
            holat="asos",
            izoh=(
                "29-band: haydovchi maxsus moslama qayd etgan ko'rsatkichdan "
                "norozi bo'lsa, holat **xolislar ishtirokida** "
                "rasmiylashtirilishi shart. Siz e'tiroz bildirgan bo'lsangiz-u, "
                "xolislar jalb qilinmagan bo'lsa, bu tartib buzilgan.\n\n"
                "Shikoyatda xolislar to'g'risidagi ma'lumotni (F.I.Sh., "
                "imzolari) so'rang — ular ish materiallarida bo'lishi kerak."
            ),
            modda=_modda(XOLISLAR_MODDASI),
        ))
    return tekshiruvlar


def _band32_tekshiruvi(sorov: JarimaSorov) -> JarimaTekshiruv:
    """32-band: moslamani yechib olish, begona shaxs, begona transport vositasi.

    Bu yerda "asos" faqat DALIL bo'lganda beriladi. Radarning uch oyoqli
    tagliksa turishi dalil emas — ko'chma fotoradar nizomda ruxsat etilgan
    (30, 31, 34-bandlar). Dalil deb quyidagilar hisoblanadi: moslamani xizmatga
    aloqasi bo'lmagan shaxs boshqargani yoki yonida patrul avtomobili
    bo'lmagani (ya'ni moslama patrul avtomobilidan yechib olingani).
    """
    dalillar = []
    if sorov.begona_shaxs or sorov.xodim_formada is False:
        dalillar.append(
            "moslamani xizmatga aloqasi bo'lmagan shaxs boshqargan"
        )
    if sorov.patrul_avtomobili is False:
        dalillar.append(
            "moslama yonida YPX patrul avtomobili bo'lmagan, ya'ni u patrul "
            "avtomobilidan yechib olingan bo'lishi mumkin"
        )

    if dalillar:
        return JarimaTekshiruv(
            nomi="Radar belgilangan tartibda ishlatilganmi",
            holat="asos",
            izoh=(
                "32-band tezlik o'lchash moslamalarini patrul avtomobilidan "
                "o'zboshimchalik bilan yechib olishni, ularni begona transport "
                "vositalariga o'rnatishni va xizmatga aloqador bo'lmagan "
                "fuqarolarni jalb qilishni QAT'IYAN taqiqlaydi. Bunday holda "
                "chiqarilgan qarorlar **yuridik kuchga ega bo'lmaydi va "
                "huquqiy oqibatlar keltirib chiqarmaydi**.\n\n"
                "Sizning holatingizda: " + "; ".join(dalillar) + ".\n\n"
                "Shikoyatda shu holatni bayon qiling (surat yoki video bo'lsa "
                "ilova qiling) va moslamaning qaysi patrul avtomobiliga "
                "biriktirilgani hamda uni qaysi xodim qabul qilgani "
                "to'g'risidagi ma'lumotni so'rang."
            ),
            modda=_modda(RADAR_MODDASI),
        )

    izoh = (
        "Uch oyoqli tagliksa (trenoga) qo'yilgan radarning o'zi taqiqlanmagan: "
        "ko'chma fotoradar nizomning 30, 31 va 34-bandlarida ochiq nazarda "
        "tutilgan. Qarorni kuchsiz qiladigan narsa moslamaning turi emas, "
        "quyidagilardan biri:\n"
        "• moslama patrul avtomobilidan yechib olingan yoki begona transport "
        "vositasiga o'rnatilgan;\n"
        "• uni YPX xodimi emas, boshqa shaxs boshqargan;\n"
        "• u dislokatsiyada ko'rsatilmagan joyda turgan.\n\n"
        "Radar yonida patrul avtomobili bormidi, uni formadagi xodim "
        "boshqarganmi — shuni eslang. Suratingiz bo'lsa yuboring, tekshirib "
        "beraman."
    ) if sorov.radar_turi == "trenoga" else (
        "32-band moslamani patrul avtomobilidan yechib olishni, begona "
        "transport vositasiga o'rnatishni va begona shaxsni jalb qilishni "
        "taqiqlaydi. Radar yonida patrul avtomobili bormidi va uni formadagi "
        "xodim boshqarganmi — shuni aniqlashtiring."
    )
    return JarimaTekshiruv(
        nomi="Radar belgilangan tartibda ishlatilganmi",
        holat="diqqat",
        izoh=izoh,
        modda=_modda(RADAR_MODDASI),
    )


def _kamera_modda_royxati(sorov: JarimaSorov) -> Optional[JarimaTekshiruv]:
    """17¹-modda kamera orqali qayd etiladigan moddalarning YOPIQ ro'yxatini beradi."""
    if not sorov.kamera or not sorov.modda:
        return None
    mid = _mjk_id(sorov.modda)
    # "128-1" kabi qismli moddalar ham ro'yxatdagi asosiy modda bilan tekshiriladi
    if mid in KAMERA_MODDALARI:
        return JarimaTekshiruv(
            nomi="Bu modda kamera orqali qayd etiladimi",
            holat="joyida",
            izoh=(
                "Ha, bu modda 17¹-moddadagi ro'yxatda bor — kamera orqali qayd "
                "etilishi mumkin."
            ),
            modda=_modda(KAMERA_MODDASI),
        )
    return JarimaTekshiruv(
        nomi="Bu modda kamera orqali qayd etiladimi",
        holat="asos",
        izoh=(
            f"17¹-modda kamera orqali qayd etiladigan huquqbuzarliklarning "
            f"YOPIQ ro'yxatini belgilaydi va «{sorov.modda}» o'sha ro'yxatda "
            f"ko'rinmayapti. Ro'yxatda bo'lmagan modda bo'yicha kamera jarimasi "
            f"solinishi mumkin emas — buni shikoyatda birinchi o'ringa qo'ying."
        ),
        modda=_modda(KAMERA_MODDASI),
    )


def _takroriylik_eslatmasi() -> JarimaTekshiruv:
    """17¹-modda: kamera jarimasida takroriylik hisobga OLINMAYDI."""
    return JarimaTekshiruv(
        nomi="Takroriylik hisobga olinganmi",
        holat="diqqat",
        izoh=(
            "Kamera orqali qayd etilgan huquqbuzarlikda takroriylik hisobga "
            "olinmaydi. Agar sizga «takroran sodir etgani uchun» og'irlashtirilgan "
            "jarima solingan bo'lsa, bu shikoyat uchun asos."
        ),
        modda=_modda(KAMERA_MODDASI),
    )


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
    tezlik = _tezlik_tekshiruvi(sorov)
    if tezlik:
        tekshiruvlar.append(tezlik)
    if (sorov.radar_turi or sorov.begona_shaxs or sorov.moslama_qarovsiz
            or sorov.norozilik_bildirilgan or sorov.patrul_avtomobili is not None
            or sorov.xodim_formada is not None):
        tekshiruvlar.extend(_radar_tekshiruvi(sorov))
    kamera = _kamera_tekshiruvi(sorov)
    if kamera:
        tekshiruvlar.append(kamera)
        tekshiruvlar.append(_takroriylik_eslatmasi())
    kamera_royxati = _kamera_modda_royxati(sorov)
    if kamera_royxati:
        tekshiruvlar.append(kamera_royxati)
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


# ---------- Qaror rasmidan ma'lumot o'qish ----------
#
# Bu YAGONA joy bo'lib, jarima modulida AI ishlatiladi — va u faqat MATNNI
# O'QIYDI, huquqiy xulosa chiqarmaydi. Rasmdan olingan sanalar va raqamlar
# yuqoridagi arifmetik tekshiruvlarga uzatiladi, xulosani esa qonun matni va
# hisob-kitob beradi. Model xato o'qishi mumkin, shuning uchun o'qilgan
# qiymatlar foydalanuvchiga KO'RSATILADI va u tuzatishi mumkin.

MAX_RASM_HAJMI = 8 * 1024 * 1024
RASM_SOROV_MUDDATI = 90

_RASM_KORSATMASI = """Bu — O'zbekistonda chiqarilgan yo'l harakati jarimasi qarorining tasviri.
Undagi ma'lumotlarni O'QIB, JSON qaytar. O'ylab topma: rasmda ko'rinmagan
maydonni null qoldir.

Maydonlar:
- hodisa_sanasi: qoidabuzarlik sodir etilgan sana, YYYY-MM-DD
- qaror_sanasi: qaror chiqarilgan sana, YYYY-MM-DD
- modda: Ma'muriy javobgarlik kodeksi moddasi, masalan "128-3" (128³ bo'lsa "128-3" deb yoz)
- band: Yo'l harakati qoidalarining bandi, faqat raqam
- summa: jarima summasi matn ko'rinishida
- qaror_raqami: qaror raqami
- qayd_etilgan_tezlik: radar qayd etgan tezlik, faqat butun son
- ruxsat_etilgan_tezlik: o'sha joyda ruxsat etilgan tezlik, faqat butun son
- kamera: qaror foto-video qayd etish vositasi orqali chiqarilganmi (true/false)
- jarima_bhm: jarima bazaviy hisoblash miqdorining (BHM) necha baravari ekani.
  Qarorda "BHMning 5 baravari" kabi yozilgan bo'lsa — 5. Yozilmagan bo'lsa null.

Sanalar rasmda kun.oy.yil ko'rinishida bo'lishi mumkin — YYYY-MM-DD ga o'gir."""

# Matnli qaror (PDF/DOCX) uchun — maydonlar aynan bir xil, faqat manba boshqa.
_MATN_KORSATMASI = _RASM_KORSATMASI.replace(
    "qarorining tasviri", "qarorining matni"
).replace("rasmda ko'rinmagan", "matnda yo'q").replace(
    "Sanalar rasmda", "Sanalar matnda"
)

# Qaror odatda bir betlik. Undan uzun matn kelsa, kerakli maydonlar boshida
# bo'ladi — qolganini yuborish tokenni behuda sarflaydi.
MAX_QAROR_BELGILAR = 12_000

_RASM_SXEMASI = {
    "type": "OBJECT",
    "properties": {
        "hodisa_sanasi": {"type": "STRING", "nullable": True},
        "qaror_sanasi": {"type": "STRING", "nullable": True},
        "modda": {"type": "STRING", "nullable": True},
        "band": {"type": "STRING", "nullable": True},
        "summa": {"type": "STRING", "nullable": True},
        "qaror_raqami": {"type": "STRING", "nullable": True},
        "qayd_etilgan_tezlik": {"type": "INTEGER", "nullable": True},
        "ruxsat_etilgan_tezlik": {"type": "INTEGER", "nullable": True},
        "kamera": {"type": "BOOLEAN", "nullable": True},
        "jarima_bhm": {"type": "NUMBER", "nullable": True},
    },
}


class RasmXato(Exception):
    """Rasmdan ma'lumot o'qib bo'lmadi (foydalanuvchiga ko'rsatiladigan xabar)."""


def rasm_oqish_mavjud() -> bool:
    return bool(GEMINI_API_KEY)


def _sana(qiymat) -> Optional[date]:
    if not qiymat:
        return None
    for shakl in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(str(qiymat).strip(), shakl).date()
        except ValueError:
            continue
    return None


def _butun(qiymat, eng_kop: int) -> Optional[int]:
    """Modeldan kelgan sonni ehtiyotkorlik bilan oladi."""
    if qiymat is None:
        return None
    raqamlar = re.findall(r"\d+", str(qiymat))
    if not raqamlar:
        return None
    son = int(raqamlar[0])
    return son if 0 <= son <= eng_kop else None


def _bhm(qiymat) -> Optional[float]:
    """Jarima necha baravar BHM ekani. Chegaradan tashqarisi tashlanadi."""
    try:
        son = float(qiymat)
    except (TypeError, ValueError):
        return None
    return son if 0 < son <= 100 else None


def rasmdan_oqi(bayt: bytes, mime: str = "image/jpeg") -> JarimaSorov:
    """Jarima qarori rasmidan JarimaSorov to'ldiradi.

    Faqat o'qiydi — huquqiy baho bermaydi. O'qilgan qiymatlar chaqiruvchi
    tomonidan foydalanuvchiga ko'rsatiladi va tuzatilishi mumkin.
    """
    if not bayt:
        raise RasmXato("Rasm bo'sh.")
    if len(bayt) > MAX_RASM_HAJMI:
        raise RasmXato("Rasm hajmi juda katta (8 MB gacha).")
    if not rasm_oqish_mavjud():
        raise RasmXato("Rasmdan o'qish sozlanmagan. Ma'lumotlarni qo'lda kiriting.")

    natija = _gemini_maydonlari(
        [{"text": _RASM_KORSATMASI},
         {"inline_data": {"mime_type": mime, "data": base64.b64encode(bayt).decode()}}],
        "Rasmdan ma'lumotlarni o'qib bo'lmadi. Suratni yorugʻroq oling yoki "
        "ma'lumotlarni qo'lda kiriting.",
    )
    return _sorovga_ogir(natija)


def matndan_oqi(matn: str) -> JarimaSorov:
    """Jarima qarori MATNIDAN (PDF/DOCX dan ajratilgan) JarimaSorov to'ldiradi.

    PDF va DOCX da matn allaqachon mavjud — uni rasmga aylantirib OCR qilish
    ortiqcha. Ko'rsatma va sxema rasm bilan bir xil: ikkalasi ham bir xil
    maydonlarni beradi va bir xil arifmetik tekshiruvga tushadi.
    """
    matn = (matn or "").strip()
    if not matn:
        raise RasmXato("Hujjat bo'sh.")
    if not rasm_oqish_mavjud():
        raise RasmXato(
            "Hujjatdan avtomatik o'qish sozlanmagan. Ma'lumotlarni qo'lda kiriting."
        )

    natija = _gemini_maydonlari(
        [{"text": _MATN_KORSATMASI + "\n\n---\n" + matn[:MAX_QAROR_BELGILAR]}],
        "Hujjatdan ma'lumotlarni o'qib bo'lmadi. Ma'lumotlarni qo'lda kiriting.",
    )
    return _sorovga_ogir(natija)


def _gemini_maydonlari(qismlar: list, xato_matni: str) -> dict:
    """Gemini'dan qat'iy sxema bo'yicha JSON oladi (rasm ham, matn ham)."""
    try:
        javob = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent",
            params={"key": GEMINI_API_KEY},
            json={
                "contents": [{"parts": qismlar}],
                "generationConfig": {
                    "temperature": 0,  # o'qish — ijodkorlik emas
                    "response_mime_type": "application/json",
                    "response_schema": _RASM_SXEMASI,
                    "maxOutputTokens": 1024,
                },
            },
            timeout=RASM_SOROV_MUDDATI,
        )
        javob.raise_for_status()
        return json.loads(javob.json()["candidates"][0]["content"]["parts"][0]["text"])
    except Exception as e:
        log.warning("Qaror maydonlarini o'qib bo'lmadi: %s", e)
        raise RasmXato(xato_matni) from e


def _sorovga_ogir(natija: dict) -> JarimaSorov:
    """Modeldan kelgan xom JSON ni JarimaSorov'ga o'giradi va chegaralaydi."""
    modda = str(natija.get("modda") or "").strip()
    return JarimaSorov(
        hodisa_sanasi=_sana(natija.get("hodisa_sanasi")),
        qaror_sanasi=_sana(natija.get("qaror_sanasi")),
        modda=modda[:40],
        band=str(natija.get("band") or "").strip()[:40],
        summa=str(natija.get("summa") or "").strip()[:60],
        qaror_raqami=str(natija.get("qaror_raqami") or "").strip()[:60],
        qayd_etilgan_tezlik=_butun(natija.get("qayd_etilgan_tezlik"), 400),
        ruxsat_etilgan_tezlik=_butun(natija.get("ruxsat_etilgan_tezlik"), 200),
        kamera=bool(natija.get("kamera")),
        jarima_bhm=_bhm(natija.get("jarima_bhm")),
    )
