# Hujjat turini aniqlash, tekshirish ro'yxati va bekor qilish yo'li.
#
# NEGA BU YERDA AI YO'Q. Hujjatning turi uning MUDDATINI belgilaydi: sud
# hal qiluv qarori uchun bir oy, sudning MJK qarori uchun o'n sutka, jarima
# qarori uchun o'n kun. Model turni xato aniqlasa, odamga noto'g'ri muddat
# aytiladi va u haqiqiy muddatni o'tkazib yuboradi — bu qaytarib bo'lmaydigan
# zarar. Shuning uchun tur kalit so'zlar bo'yicha aniqlanadi, muddatlar esa
# bazadagi asl modda matniga havola qiladi.
#
# Ishonch darajasi doim ko'rsatiladi: tur "taxmin" bo'lsa, foydalanuvchi buni
# bilishi va muddatni hujjatning o'zidan tekshirishi kerak.
from typing import List, Optional

from .. import storage
from ..models import BekorQadam, HujjatJavob, HujjatTekshiruv, ModdaJavob
from .retrieval import normallashtir

# Hujjat turlari. "boshqa" — aniqlanmagani, unda umumiy tavsiya beriladi.
TURLAR = (
    "jarima", "sud_mjk", "sud_fuqarolik", "ishdan_bosatish",
    "shartnoma", "organ_javobi", "boshqa",
)

TUR_NOMLARI = {
    "jarima": "Ma'muriy jarima qarori (organ chiqargan)",
    "sud_mjk": "Sudning ma'muriy huquqbuzarlik to'g'risidagi qarori",
    "sud_fuqarolik": "Sudning fuqarolik ishi bo'yicha hal qiluv qarori",
    "ishdan_bosatish": "Mehnat shartnomasini bekor qilish (ishdan bo'shatish) buyrug'i",
    "shartnoma": "Shartnoma",
    "organ_javobi": "Davlat organining murojaatga javobi yoki qarori",
    "boshqa": "Turi aniqlanmagan hujjat",
}

# Kalit so'zlar normallashtirilgan shaklda yoziladi (apostrofsiz, lotinda) —
# hujjat kirillda yozilgan bo'lsa ham topiladi. Har tur uchun:
#   majburiy — shulardan KAMIDA BITTASI bo'lishi shart
#   kuchli   — bittasi topilsa tur deyarli aniq
#   qollab   — qo'shimcha dalil, har biri ball qo'shadi
_QOIDALAR = {
    "sud_mjk": {
        "majburiy": ["sud"],
        # "sudya" va "sud qarori" — hujjatni SUD chiqarganining belgisi. Oddiy
        # YHXX qarorida ham "sudga shikoyat berish mumkin" deb yoziladi, lekin
        # "sudya" so'zi bo'lmaydi: farqni aynan shu ajratadi.
        "kuchli": ["mamuriy huquqbuzarlik togrisidagi ish", "mjtk",
                   "mamuriy javobgarlik", "sudya", "sud qarori"],
        "qollab": ["mamuriy jazo", "protokol", "bayonnoma", "sud majlisi"],
    },
    "sud_fuqarolik": {
        "majburiy": ["sud"],
        "kuchli": ["hal qiluv qarori", "hal qiluv qaror", "fuqarolik ishi",
                   "davo arizasi", "davogar", "javobgar"],
        "qollab": ["sudya", "undirilsin", "qanoatlantirilsin", "rad etilsin",
                   "apellyatsiya", "sud majlisi"],
    },
    "jarima": {
        "majburiy": ["jarima", "mamuriy"],
        "kuchli": ["jarima solish togrisidagi qaror", "mamuriy jarima",
                   "bazaviy hisoblash miqdori"],
        "qollab": ["yhxx", "dyhxx", "yol harakati", "tezlik", "modda",
                   "qaror raqami", "bhm", "davlat raqam belgisi"],
    },
    "ishdan_bosatish": {
        "majburiy": ["buyruq", "mehnat shartnomasi", "bosatilsin", "ozod etilsin"],
        "kuchli": ["mehnat shartnomasini bekor qilish", "ishdan bosatish",
                   "lavozimidan ozod", "mehnat kodeksining"],
        "qollab": ["xodim", "ish beruvchi", "lavozim", "hisob kitob",
                   "mehnat daftarchasi", "tashkilot rahbari"],
    },
    "organ_javobi": {
        "majburiy": ["murojaat", "ariza", "shikoyat"],
        "kuchli": ["murojaatingiz korib chiqildi", "murojaatingizga javob",
                   "korib chiqish natijasida", "asossiz deb topildi"],
        "qollab": ["hokimlik", "vazirlik", "inspeksiya", "qomita", "boshqarma",
                   "rad etildi", "qanoatlantirilmadi"],
    },
}

# Shartnoma alohida aniqlanadi: unda bandlar tuzilishi asosiy belgi bo'ladi
# va buni services/shartnoma.py allaqachon biladi.


def turni_aniqla(matn: str) -> tuple:
    """Hujjat turini va ishonch darajasini qaytaradi: (turi, "aniq"|"taxmin").

    Ball tizimi ataylab oddiy: kuchli belgi 3 ball, qo'llab-quvvatlovchi 1 ball.
    Eng ko'p ball to'plagan tur tanlanadi, lekin majburiy so'zsiz tur umuman
    ko'rib chiqilmaydi — "sud" so'zi yo'q hujjat sud qarori bo'la olmaydi.
    """
    n = normallashtir(matn or "")
    if not n.strip():
        return "boshqa", "taxmin"

    ballar = {}
    for turi, qoida in _QOIDALAR.items():
        if not any(s in n for s in qoida["majburiy"]):
            continue
        ball = sum(3 for s in qoida["kuchli"] if s in n)
        ball += sum(1 for s in qoida["qollab"] if s in n)
        if ball:
            ballar[turi] = ball

    if not ballar:
        return "boshqa", "taxmin"

    turi = max(ballar, key=ballar.get)
    eng_kop = ballar[turi]
    # Ikkinchi o'rindagi tur yaqin bo'lsa, tanlov ishonchli emas.
    qolgan = sorted((b for t, b in ballar.items() if t != turi), reverse=True)
    aniqmi = eng_kop >= 4 and (not qolgan or eng_kop - qolgan[0] >= 3)

    # Chalkashadigan juftliklar: ikkalasi ham ball to'plagan bo'lsa, ball
    # farqi qanchalik katta bo'lishidan qat'i nazar "taxmin" deyiladi.
    #
    # Sababi — bu juftliklarda XATO NARXI yuqori. Jarima qarori ustidan
    # yuqori organga yoki sudga SHIKOYAT beriladi, sud chiqargan qaror
    # ustidan esa APELLYATSIYA. Ikkalasi 10 kun bo'lsa ham, tartib va
    # murojaat qilinadigan joy boshqa: noto'g'ri yo'l bilan berilgan hujjat
    # qaytariladi va odam muddatni shu orada boy beradi.
    for juft in _CHALKASH_JUFTLAR:
        if len(juft & ballar.keys()) > 1:
            aniqmi = False
            break

    return turi, ("aniq" if aniqmi else "taxmin")


# Ball farqi katta bo'lsa ham "aniq" deb aytilmaydigan turlar
_CHALKASH_JUFTLAR = ({"jarima", "sud_mjk"},)


def _modda(modda_id: str) -> Optional[ModdaJavob]:
    m = storage.modda_top(modda_id)
    return ModdaJavob(**m) if m else None


def _t(nomi: str, izoh: str, modda_id: str = "") -> HujjatTekshiruv:
    return HujjatTekshiruv(nomi=nomi, izoh=izoh,
                           modda=_modda(modda_id) if modda_id else None)


def _q(matn: str, modda_id: str = "") -> BekorQadam:
    return BekorQadam(matn=matn, modda=_modda(modda_id) if modda_id else None)


# ---------- Tekshirish ro'yxatlari ----------
#
# Har bir band hujjatning o'zidan tekshirib ko'riladigan aniq narsa bo'lishi
# kerak. "Huquqlaringizni biling" kabi umumiy maslahat bu yerga kirmaydi:
# odam ro'yxatni qo'lida hujjat bilan o'qiydi.

def _tekshiruvlar(turi: str) -> List[HujjatTekshiruv]:
    if turi == "sud_fuqarolik":
        return [
            _t("Hal qiluv qarori qachon qabul qilingan",
               "Apellyatsiya muddati aynan shu sanadan boshlanadi — qarorni "
               "olgan kundan emas. Sanani hujjatning boshidan toping.",
               "fpk-385-1"),
            _t("Siz ishda ishtirok etganmisiz",
               "Ishda ishtirok etishga jalb qilinmagan, ammo huquq va "
               "majburiyatlari haqidagi masala hal etilgan shaxs ham "
               "apellyatsiya shikoyati bera oladi. Sud majlisi haqida "
               "xabardor qilinmagan bo'lsangiz, buni shikoyatda ko'rsating.",
               "fpk-383"),
            _t("Ish soddalashtirilgan tartibda ko'rilganmi",
               "Soddalashtirilgan ish yuritish tartibida, shuningdek "
               "o'zboshimchalik bilan egallangan yer va o'zboshimchalik bilan "
               "qurilgan imorat bo'yicha ishlarda muddat bir oy emas, "
               "**o'n kun**. Qarorda shu tartib ko'rsatilganini tekshiring.",
               "fpk-385-1"),
            _t("Qaror rezolyutiv qismi talabga mos keladimi",
               "Kim, kimdan, qancha miqdorda — bularning hammasi aniq "
               "yozilganini tekshiring. Noaniqlik ijro bosqichida muammo "
               "keltirib chiqaradi."),
            _t("Qaysi dalillar asos qilib olingan",
               "Qarorda ko'rsatilgan dalillarni ish materiallari bilan "
               "solishtiring. Siz taqdim etgan dalil e'tiborga olinmagan "
               "bo'lsa, bu apellyatsiya uchun asosiy vaj bo'ladi."),
        ]

    if turi == "sud_mjk":
        return [
            _t("Qaror qachon o'qib eshittirilgan yoki nusxasi qachon olingan",
               "O'n sutkalik muddat shu sanadan boshlanadi. Sizga nisbatan "
               "qaror chiqarilgan bo'lsa, muddat qaror **nusxasi topshirilgan "
               "yoki siz uni olgan** kundan hisoblanadi.",
               "mjk-324-3"),
            _t("Javobgarlikka tortish muddati o'tmaganmi",
               "Ma'muriy jazo huquqbuzarlik sodir etilgan kundan bir yildan "
               "kechiktirmay, kamera orqali qayd etilganda esa bir oydan "
               "kechiktirmay qo'llaniladi. Muddat o'tgan bo'lsa ish tugatilishi "
               "lozim — bu eng kuchli asos.",
               "mjk-36"),
            _t("Ish sizning ishtirokingizda ko'rilganmi",
               "Ishning bir tomonlama yoki to'liq bo'lmagan holda ko'rib "
               "chiqilishi qarorni bekor qilish uchun mustaqil asos.",
               "mjk-321"),
            _t("Aybdorligingiz aniqlanganmi",
               "Ish ko'rib chiqilayotganda aybdorlik aniqlanishi shart. "
               "Qarorda ayb qanday dalil bilan tasdiqlangani yozilmagan "
               "bo'lsa, buni shikoyatda ko'rsating.",
               "mjk-307"),
            _t("Modda va uning qismi to'g'ri ko'rsatilganmi",
               "Qo'llanilgan norma ishning faktik holatlariga mos kelmasligi "
               "qarorni bekor qilish yoki o'zgartirish uchun asos.",
               "mjk-321"),
        ]

    if turi == "jarima":
        return [
            _t("Qaror nusxasini qachon olgansiz",
               "Shikoyat muddati — qaror **nusxasi olingan** kundan o'n kun. "
               "Qaror chiqarilgan sanadan emas; bu ikkisi ko'pincha bir necha "
               "hafta farq qiladi.",
               "mjk-316"),
            _t("Javobgarlikka tortish muddati",
               "Hodisadan bir yil, kamera orqali qayd etilganda bir oy. "
               "Muddat o'tgan bo'lsa ish tugatilishi lozim.",
               "mjk-36"),
            _t("Qarorda majburiy ma'lumotlar bormi",
               "Qaror chiqarilgan sana va joy, organ nomi va mansabdor shaxs, "
               "huquqbuzarlik holatlari, modda va uning qismi, jarimani to'lash "
               "tartibi hamda shikoyat berish tartibi — bularning yo'qligi "
               "rasmiylashtirish buzilishi hisoblanadi.",
               "mjk-311"),
            _t("Jarima summasi moddaga to'g'ri keladimi",
               "Summani BHM ga bo'lib, moddaning tegishli qismida ko'rsatilgan "
               "baravar bilan solishtiring. Farq bo'lsa — bu aniq asos."),
            _t("To'liqroq tekshirish",
               "Muddatlar, tezlik hisobi (5 km/soat chegirmasi) va radar "
               "qonuniyligi bo'yicha to'liq tekshiruv uchun jarima moduliga "
               "o'ting — u sanalarni arifmetik hisoblab beradi."),
        ]

    if turi == "ishdan_bosatish":
        return [
            _t("Sizni oldindan ogohlantirishganmi",
               "Ish beruvchi **yozma shaklda, imzo qo'ydirib** ogohlantirishi "
               "shart: tashkilot tugatilishi yoki shtat qisqarishida kamida "
               "**ikki oy**, malaka yetarli emasligida kamida **ikki "
               "hafta**, aybli harakatlar uchun kamida **uch kun** oldin. "
               "Ogohlantirish bo'lmagan yoki muddati kam bo'lsa, tartib "
               "buzilgan.",
               "mehnat-165"),
            _t("Buyruqda asos va modda ko'rsatilganmi",
               "Mehnat shartnomasi qaysi modda va qaysi asosga ko'ra bekor "
               "qilinayotgani buyruqda aniq yozilishi kerak. \"Ishga yaramaydi\" "
               "kabi umumiy ibora asos bo'la olmaydi."),
            _t("Sizga kafolat tegishli emasmi",
               "Homilador ayollar va uch yoshgacha bolasi bor xodimlar bilan "
               "mehnat shartnomasini bekor qilish alohida cheklangan. Shu "
               "toifaga kirsangiz, bo'shatish qonunga xilof bo'lishi mumkin.",
               "mehnat-408"),
            _t("Hisob-kitob qilinganmi",
               "Mehnat shartnomasi bekor qilinganda barcha to'lovlar "
               "belgilangan muddatda amalga oshirilishi shart. Ish haqi, "
               "foydalanilmagan ta'til kompensatsiyasi va nafaqa to'lanmagan "
               "bo'lsa, buni talabingizga qo'shing.",
               "mehnat-254"),
            _t("Mehnat daftarchasi berilganmi",
               "Mehnat daftarchasi va bo'shatish to'g'risidagi buyruq nusxasi "
               "sizga berilishi kerak. Berilmagan bo'lsa, buni yozma talab "
               "qiling — bu keyinchalik muddatni hisoblashda ham ahamiyatli.",
               "mehnat-125"),
        ]

    if turi == "shartnoma":
        return [
            _t("Shartnomani bekor qilish sharti nima deyilgan",
               "Shartnomaning o'zida bekor qilish tartibi yozilgan bo'lishi "
               "mumkin — avval shuni o'qing. Qonun \"shartnomada boshqacha "
               "tartib nazarda tutilmagan bo'lsa\" deb boshlanadi.",
               "fuqarolik-382"),
            _t("Ikkinchi taraf shartnomani jiddiy buzganmi",
               "Sudga bir tomonlama murojaat qilish uchun buzilish "
               "**jiddiy** bo'lishi kerak: siz shartnoma tuzishda umid "
               "qilishga haqli bo'lgan narsadan ko'p darajada mahrum "
               "bo'lganingiz. Buni dalil bilan ko'rsatish kerak.",
               "fuqarolik-382"),
            _t("Bir tomonlama bosh tortish nazarda tutilganmi",
               "Qonun yoki shartnomaning o'zi ruxsat bergan bo'lsa, sudsiz "
               "ham bosh tortish mumkin — bunda shartnoma o'z-o'zidan bekor "
               "qilingan hisoblanadi.",
               "fuqarolik-382"),
            _t("Band-band tahlil",
               "Har bandning qonunga mosligini ko'rish uchun shartnomani "
               "tahlil moduliga yuboring — u xavf darajasi va tegishli modda "
               "bilan chiqadi."),
        ]

    if turi == "organ_javobi":
        return [
            _t("Javob mohiyati bo'yicha berilganmi",
               "Siz qo'ygan har bir masalaga javob berilganini tekshiring. "
               "Savolning bir qismi javobsiz qolgan bo'lsa, bu mustaqil "
               "shikoyat asosi."),
            _t("Rad etish sababi asoslanganmi",
               "Javobda qaysi norma asos qilib olingani ko'rsatilishi kerak. "
               "Modda keltirilmagan yoki keltirilgani mazmunga mos kelmasa, "
               "buni yuqori organga bildiring."),
            _t("Materiallar bilan tanishtirishganmi",
               "Sizda murojaatni tekshirish materiallari va uni ko'rib chiqish "
               "natijalari bilan tanishish, qo'shimcha material taqdim etish "
               "va advokat yordamidan foydalanish huquqi bor.",
               "murojaat-21"),
            _t("Javob muddatida kelganmi",
               "Muddat buzilgan bo'lsa, buni yuqori organga bildiring — "
               "murojaatni ko'rib chiqish tartibining buzilishi alohida "
               "e'tiroz mavzusi."),
        ]

    return [
        _t("Hujjatni kim va qachon chiqargan",
           "Chiqargan organ nomi, mansabdor shaxs lavozimi va sana — "
           "muddat aynan shu sanadan hisoblanadi."),
        _t("Qaysi qonun moddasiga asoslangan",
           "Hujjatda keltirilgan moddani lex.uz dan ochib, mazmuni "
           "vaziyatingizga mos kelishini tekshiring. Modda umuman "
           "ko'rsatilmagan bo'lsa, bu asoslanmaganlik belgisi."),
        _t("Shikoyat tartibi yozilganmi",
           "Ko'p hujjatlarda oxirida shikoyat qayerga va qancha muddatda "
           "berilishi yoziladi. Shu qatorni toping — u eng ishonchli manba."),
        _t("Nusxani qachon olganingiz qayd etilganmi",
           "Muddat ko'pincha nusxa olingan kundan boshlanadi. Pochta konverti, "
           "ilova xati yoki imzo qo'ygan jurnalni saqlang."),
    ]


# ---------- Bekor qilish yo'llari ----------

def _bekor_yoli(turi: str) -> List[BekorQadam]:
    if turi == "sud_fuqarolik":
        return [
            _q("**Apellyatsiya shikoyati** beriladi — sudning qonuniy kuchga "
               "kirmagan hal qiluv qarori, ajrimi yoki qarori ustidan.",
               "fpk-383"),
            _q("**Muddat: hal qiluv qarori qabul qilingan kundan bir oy.** "
               "Soddalashtirilgan tartibda ko'rilgan ishlar hamda "
               "o'zboshimchalik bilan egallangan yer va qurilgan imorat "
               "bo'yicha ishlarda — o'n kun.",
               "fpk-385-1"),
            _q("Muddat o'tib ketgan bo'lsa: sabab uzrli deb topilsa, u "
               "tiklanishi mumkin. Iltimosnoma hal qiluv qarori qabul "
               "qilingan kundan **uch oydan kechiktirmay** berilishi shart — "
               "bu chegaradan keyin tiklash imkoni yo'q.",
               "fpk-385-1"),
            _q("Shikoyatda ko'rsatiladi: sud nomi; sizning F.I.Sh va manzilingiz; "
               "ish raqami, qaror sanasi va uni qabul qilgan sud; **qaror "
               "nimasi bilan noto'g'ri ekani**; iltimosingiz; ilova qilingan "
               "materiallar ro'yxati. Shikoyatni o'zingiz yoki vakilingiz "
               "imzolaydi.",
               "fpk-386"),
        ]

    if turi == "sud_mjk":
        return [
            _q("**Apellyatsiya shikoyati** beriladi — birinchi instansiya "
               "sudining ma'muriy huquqbuzarlik to'g'risidagi qarori ustidan.",
               "mjk-324-1"),
            _q("**Muddat: o'n sutka.** Qaror o'qib eshittirilgan kundan; "
               "o'ziga nisbatan qaror chiqarilgan shaxs va jabrlanuvchi uchun "
               "esa **qaror nusxasi topshirilgan yoki olingan** kundan.",
               "mjk-324-3"),
            _q("Muddat o'tkazib yuborilgan bo'lsa, iltimosnoma bering: sabab "
               "uzrli deb topilsa, qarorni chiqargan sud muddatni tiklaydi va "
               "bu haqda ajrim chiqaradi. Rad etilsa, ajrim ustidan xususiy "
               "shikoyat berish mumkin.",
               "mjk-324-3"),
            _q("Shikoyatni ko'rib chiqishda qaror o'zgarishsiz qoldirilishi, "
               "bekor qilinib ish qayta ko'rishga yuborilishi, bekor qilinib "
               "ish yuritish to'xtatilishi yoki jazo **kuchaytirilmagan holda** "
               "o'zgartirilishi mumkin — ya'ni shikoyat berish jazoni "
               "og'irlashtirmaydi.",
               "mjk-321"),
        ]

    if turi == "jarima":
        return [
            _q("Shikoyat **yuqori turuvchi organga (mansabdor shaxsga)** yoki "
               "**jinoyat ishlari bo'yicha tuman (shahar) sudiga** beriladi.",
               "mjk-315"),
            _q("**Muddat: qaror nusxasi olingan kundan o'n kun.**",
               "mjk-316"),
            _q("Shikoyat qarorni chiqargan organ orqali yoki bevosita sudga "
               "yuboriladi; organ uni uch sutka ichida ish bilan birga tegishli "
               "joyga jo'natadi. **Davlat boji to'lanmaydi.**",
               "mjk-315"),
            _q("Muddatida berilgan shikoyat qaror **ijrosini to'xtatib "
               "turadi** — ko'rib chiqilgunga qadar jarimani to'lash talab "
               "qilinmaydi.",
               "mjk-319"),
            _q("Qaror bekor qilinib ish tugatilsa, **undirib olingan pul "
               "qaytariladi** — jarimani allaqachon to'lagan bo'lsangiz ham "
               "shikoyat bering.",
               "mjk-324"),
        ]

    if turi == "ishdan_bosatish":
        return [
            _q("Ikki yo'l bor va ular bir-birini istisno qilmaydi: **bevosita "
               "ish beruvchiga murojaat qilish** yoki **sudga shikoyat "
               "berish**.",
               "mehnat-174"),
            _q("Talabingiz: **avvalgi ishga (lavozimga) tiklash**, "
               "**moddiy zararni qoplash** va — qonunga xilof bo'shatish "
               "natijasida ma'naviy yoki jismoniy azob yetkazilgan bo'lsa — "
               "**ma'naviy ziyonni kompensatsiya qilish**.",
               "mehnat-174"),
            _q("Ish beruvchining o'zi bo'shatishni qonunga xilof deb tan olsa, "
               "u sizni tiklashi va talablaringizni qanoatlantirishi **shart** — "
               "buning uchun sudga borish majburiy emas.",
               "mehnat-174"),
            _q("Sud yetkazilgan zararni qoplash majburiyatini **aybdor "
               "mansabdor shaxs zimmasiga** yuklashi mumkin (uning uch "
               "oylik maoshidan ortiq bo'lmagan miqdorda). Bu ish beruvchi "
               "tashkilotdan alohida javobgarlik.",
               "mehnat-564"),
            _q("⚠️ **Muddatni hujjatdan tekshiring.** Mehnat nizolari uchun "
               "sudga murojaat muddati bu yerda hisoblanmaydi — u nizo turiga "
               "qarab farq qiladi. Buyruq nusxasini olgan sanani aniq belgilab "
               "qo'ying va kechiktirmang."),
        ]

    if turi == "shartnoma":
        return [
            _q("Eng oddiy yo'l — **taraflarning kelishuvi**. Kelishuv yozma "
               "shaklda, shartnoma tuzilgan shakl bilan bir xil "
               "rasmiylashtiriladi.",
               "fuqarolik-382"),
            _q("Kelishuv bo'lmasa, **sud orqali**: ikkinchi taraf "
               "shartnomani **jiddiy ravishda buzgan** bo'lsa yoki Fuqarolik "
               "kodeksi, boshqa qonun hamda shartnomada nazarda tutilgan "
               "hollarda.",
               "fuqarolik-382"),
            _q("Qonun yoki shartnomaning o'zi ruxsat bergan bo'lsa, taraf "
               "shartnomani bajarishdan **to'liq yoki qisman bosh tortishi** "
               "mumkin — bunda shartnoma sudsiz bekor qilingan hisoblanadi.",
               "fuqarolik-382"),
            _q("Sudga murojaatdan oldin ikkinchi tarafga **yozma taklif** "
               "yuboring va javob muddatini ko'rsating — bu keyinchalik "
               "sudda sizning foydangizga ishlaydi."),
        ]

    if turi == "organ_javobi":
        return [
            _q("Javob ustidan **bo'ysunuv tartibida yuqori turuvchi organga** "
               "shikoyat beriladi.",
               "murojaat-16"),
            _q("**Muddat: bir yil** — huquqlaringizni buzuvchi harakat "
               "(harakatsizlik) sodir etilgani yoxud qaror qabul qilingani "
               "sizga ma'lum bo'lgan paytdan.",
               "murojaat-17"),
            _q("Shikoyatga oldin qabul qilingan qarorlar yoki ularning ko'chirma "
               "nusxalari hamda ko'rib chiqish uchun zarur boshqa hujjatlarni "
               "ilova qiling.",
               "murojaat-16"),
            _q("Shikoyatingiz qanoatlantirilsa, ariza berish va uni ko'rib "
               "chiqish bilan bog'liq **xarajatlar hamda yo'qotilgan ish "
               "haqi** sud tartibida qoplanadi; ma'naviy ziyon ham "
               "kompensatsiya qilinishi mumkin.",
               "murojaat-26"),
            _q("Bu yo'l sudga murojaat qilishga to'sqinlik qilmaydi — ikkalasini "
               "ketma-ket yoki mustaqil ravishda ishlatish mumkin."),
        ]

    return [
        _q("Hujjatning o'zida shikoyat tartibi yozilganini qarang — odatda u "
           "oxirgi xatboshida bo'ladi va eng ishonchli manba hisoblanadi."),
        _q("Umumiy qoida: davlat organi qarori ustidan **bo'ysunuv tartibida "
           "yuqori turuvchi organga** murojaat qilish mumkin, muddat — "
           "qaror sizga ma'lum bo'lgan paytdan bir yil.",
           "murojaat-17"),
        _q("Sud qarorlari uchun muddatlar ancha qisqa: fuqarolik ishida bir oy, "
           "ma'muriy huquqbuzarlik ishida o'n sutka. Hujjatingiz sud qarori "
           "bo'lsa, kechiktirmang."),
        _q("Hujjat turini aniq ayta olsangiz (masalan «bu sud hal qiluv qarori»), "
           "aniq muddat va tartibni ko'rsataman."),
    ]


# ---------- Muddat sarlavhasi ----------
#
# Ro'yxatning tepasida bitta qator bilan ko'rsatiladi: odam avval "menda
# qancha vaqt bor?" degan savolga javob oladi, tafsilotni keyin o'qiydi.

_MUDDATLAR = {
    "sud_fuqarolik": ("1 oy", "hal qiluv qarori qabul qilingan kundan "
                              "(soddalashtirilgan tartibda — 10 kun)"),
    "sud_mjk": ("10 sutka", "qaror o'qib eshittirilgan yoki nusxasi "
                            "topshirilgan kundan"),
    "jarima": ("10 kun", "qaror nusxasi olingan kundan"),
    "organ_javobi": ("1 yil", "qaror sizga ma'lum bo'lgan paytdan"),
    "ishdan_bosatish": ("", "muddat nizo turiga qarab farq qiladi — "
                            "buyruq nusxasini olgan sanani belgilab qo'ying"),
    "shartnoma": ("", "muddat shartnomaning o'zida belgilanadi"),
    "boshqa": ("", "hujjat turi aniqlanmadi — muddatni hujjatning o'zidan qarang"),
}


def tahlil(matn: str, turi: str = "") -> HujjatJavob:
    """Hujjat matnidan tur, tekshiruv ro'yxati va bekor qilish yo'lini beradi.

    `turi` berilsa aniqlash o'tkazib yuboriladi — chaqiruvchi turni allaqachon
    bilgan holatlar uchun (masalan shartnoma tahlili moduli).
    """
    if turi:
        ishonch = "aniq"
    else:
        turi, ishonch = turni_aniqla(matn)

    muddat, muddat_izohi = _MUDDATLAR.get(turi, _MUDDATLAR["boshqa"])
    return HujjatJavob(
        turi=turi,
        turi_nomi=TUR_NOMLARI.get(turi, TUR_NOMLARI["boshqa"]),
        ishonch=ishonch,
        muddat=muddat,
        muddat_izohi=muddat_izohi,
        tekshiruvlar=_tekshiruvlar(turi),
        bekor_yoli=_bekor_yoli(turi),
    )
