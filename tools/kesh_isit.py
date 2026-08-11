"""Kesh isitgich: ehtimolli savollarni oldindan berib, javoblarni keshga to'ldiradi.

Nima uchun kerak. Bepul provayder kvotalari daqiqasiga bir necha savolga
yetadi, demo paytida esa bir vaqtda o'nlab savol kelishi mumkin. Keshdagi
javob provayderga umuman bormaydi — u yerda 5 ta ham, 50 ta ham bir xil tez
va bepul. Ya'ni cho'qqi yuklamani ko'tarishning eng arzon yo'li — savollarni
oldindan berib qo'yish.

Savollar ikki manbadan olinadi:
  1. Har mavzu uchun QO'LDA yozilgan hayotiy savollar — odamlar amalda shunday
     so'raydi ("ish haqi to'lanmayapti", "aliment qancha");
  2. Bazadagi MODDA sarlavhalaridan hosil qilinganlari — 600+ moddaning
     hammasini qamrash uchun.

Ishlatish:
    python -m tools.kesh_isit --quruq            # faqat savollarni ko'rsatadi
    python -m tools.kesh_isit --soni 40          # 40 tasini isitadi
    python -m tools.kesh_isit --moddalar         # modda savollarini ham qo'shadi

Kesh Upstash'da saqlansa (STATISTIKA_KV_URL berilgan bo'lsa), isitilgan javob
Render qayta ishga tushgandan keyin ham joyida qoladi — aks holda xotiradagi
kesh xizmat uxlashi bilan yo'qoladi va bu ish behuda ketadi.
"""
import argparse
import re
import sys
import time

from app import storage
from app.services import kesh
from app.services.javob import AiXato, javob_ol

# Har mavzu uchun hayotiy savollar. Ro'yxat bazadagi moddalarga qarab
# tuzilgan: har biri ortida javob beradigan kamida bitta modda bor.
SAVOLLAR = {
    "mehnat": [
        "Ish haqi 3 oydan beri to'lanmayapti, nima qilay?",
        "Ishdan asossiz bo'shatishdi, qanday tiklanaman?",
        "Dastlabki sinov muddati qancha bo'lishi mumkin?",
        "Mehnat shartnomasini o'z xohishim bilan qanday bekor qilaman?",
        "Ish beruvchi mehnat daftarchamni bermayapti",
        "Ta'til puli to'lanmadi, qayerga murojaat qilaman?",
        "Ish kuni necha soat bo'lishi kerak?",
        "Tungi ishga qanday haq to'lanadi?",
        "Homilador ayolni ishdan bo'shatish mumkinmi?",
        "Ortiqcha ishlagan soatlarim uchun haq olishim kerakmi?",
    ],
    "oila": [
        "Aliment qancha miqdorda to'lanadi?",
        "Ajrashganda mol-mulk qanday bo'linadi?",
        "Bola kim bilan qoladi, qanday hal qilinadi?",
        "Aliment to'lamayotgan otani nima qilish mumkin?",
        "Nikohni sudsiz bekor qilish mumkinmi?",
        "Er va xotinning umumiy mulki nimalar hisoblanadi?",
        "Nikoh shartnomasi tuzish mumkinmi?",
        "Otalikni qanday belgilash mumkin?",
    ],
    "iste'molchi": [
        "Sotib olgan tovarim nuqsonli chiqdi, qaytara olamanmi?",
        "Tovarni almashtirish muddati qancha?",
        "Sifatli tovarni qaytarish mumkinmi?",
        "Do'kon chek bermadi, huquqim bormi?",
        "Kafolat muddati ichida buzilgan texnikani kim ta'mirlaydi?",
        "Onlayn buyurtma kelmadi, pulni qanday qaytaraman?",
        "Xizmat sifatsiz ko'rsatildi, nima qilaman?",
    ],
    "uy-joy": [
        "Ijaraga bergan uyimdan ijarachi chiqmayapti",
        "Ijara depozitim qaytarilmadi, nima qilay?",
        "Kvartira mulkdorining huquqlari qanday?",
        "Qo'shni shovqin qilyapti, qayerga murojaat qilaman?",
        "Ko'p kvartirali uyda umumiy mulk kimga tegishli?",
        "Uyni sotganda qanday hujjat kerak?",
    ],
    "yer": [
        "Yer uchastkasini ijaraga olish shartnomasi qanday tuziladi?",
        "Yerimni davlat ehtiyoji uchun olmoqchi, kompensatsiya bormi?",
        "O'zboshimchalik bilan egallangan yer nima bo'ladi?",
        "Tomorqa yerini sotish mumkinmi?",
        "Yer uchastkasiga bo'lgan huquq qanday rasmiylashtiriladi?",
    ],
    "soliq": [
        "Jismoniy shaxs qanday soliq to'laydi?",
        "Soliq to'lovchining huquqlari qanday?",
        "Soliq qarzi bo'lsa nima bo'ladi?",
        "Mol-mulk solig'i qanday hisoblanadi?",
        "Soliq organi qarorini shikoyat qilish mumkinmi?",
    ],
    "fuqarolik": [
        "Qarz berdim, qaytarmayapti, nima qilaman?",
        "Shartnoma tuzilmagan bo'lsa pulni qaytarib olsam bo'ladimi?",
        "Asossiz boyish nima va qanday qaytariladi?",
        "Shartnomani bir tomonlama bekor qilish mumkinmi?",
        "Zarar yetkazgan shaxsdan qanday undirib olaman?",
        "Da'vo muddati qancha?",
        "Ishonchnoma qanday rasmiylashtiriladi?",
    ],
    "yo'l-harakati": [
        "Tezlikni oshirganim uchun jarima qancha?",
        "Kamera yozib olgan jarimani qanday shikoyat qilaman?",
        "Mast holda haydash uchun qanday javobgarlik bor?",
        "Sug'urtasiz haydasam nima bo'ladi?",
        "Yo'l-transport hodisasida nima qilish kerak?",
        "Haydovchilik guvohnomasi olib qo'yilsa qancha muddatga?",
        "To'xtab turish qoidalarini buzsam jarima bormi?",
        "Jarimani qancha muddatda to'lash kerak?",
    ],
    "ma'muriy": [
        "Ma'muriy huquqbuzarlik nima?",
        "Ma'muriy jarima qarorini qanday shikoyat qilaman?",
        "Jamoat joyida chekkanim uchun jarima bormi?",
        "Ma'muriy javobgarlik necha yoshdan boshlanadi?",
    ],
    "jinoyat": [
        "Jinoyat tushunchasi nima?",
        "Meni aldab pulimni olishdi, bu jinoyatmi?",
        "Firibgarlik uchun qanday jazo bor?",
        "Ariza berganimdan keyin nima bo'ladi?",
    ],
    "umumiy": [
        "Davlat organiga qanday murojaat qilaman?",
        "Murojaatimga necha kunda javob berishlari kerak?",
        "Sudga da'vo arizasi qanday beriladi?",
        "Bepul yuridik yordam olsam bo'ladimi?",
        "Advokat yollash shartmi?",
    ],
}

# Sarlavha oldidagi "130-modda." / "4-band." qismini olib tashlash uchun
_RAQAM = re.compile(r"^\d+[¹²³⁴]?-(modda|band)\.?\s*")


def moddadan_savol(modda: dict) -> str:
    """Modda sarlavhasidan tabiiy savol yasaydi.

    Sarlavha "130-modda. Dastlabki sinov muddati" ko'rinishida bo'ladi;
    raqamli qism olib tashlanadi va savolga aylantiriladi. Bu qo'lda yozilgan
    ro'yxat qamramagan moddalarni ham keshga tushirish uchun.
    """
    mavzu = _RAQAM.sub("", modda.get("sarlavha", "")).strip()
    if not mavzu:
        return ""
    return f"{mavzu[0].upper()}{mavzu[1:]} bo'yicha qonun nima deydi?"


def savollarni_yig(moddalar_ham: bool) -> list:
    savollar = [s for royxat in SAVOLLAR.values() for s in royxat]
    if moddalar_ham:
        korilgan = set(savollar)
        for m in storage.moddalarni_oqi():
            s = moddadan_savol(m)
            if s and s not in korilgan:
                korilgan.add(s)
                savollar.append(s)
    return savollar


def isit(savollar: list, kechikish: float) -> None:
    versiya = storage.versiya()
    jami = len(savollar)
    keshda = yangi = xato = 0

    for i, savol in enumerate(savollar, 1):
        k = kesh.kalit(savol, "oddiy", versiya)
        if kesh.ol(k) is not None:
            keshda += 1
            print(f"[{i}/{jami}] keshda  — {savol[:60]}")
            continue
        try:
            javob = javob_ol(savol, "oddiy")
        except AiXato as e:
            # Provayder qancha kutish kerakligini aytadi — o'shanga bo'ysunamiz.
            kutish = getattr(getattr(e, "asl", None), "kutish", None)
            if kutish and kutish <= 120:
                print(f"[{i}/{jami}] limit   — {kutish}s kutilyapti...")
                time.sleep(kutish)
                try:
                    javob = javob_ol(savol, "oddiy")
                except AiXato as e2:
                    xato += 1
                    print(f"[{i}/{jami}] XATO    — {e2.foydalanuvchi_matni}")
                    continue
            else:
                xato += 1
                print(f"[{i}/{jami}] XATO    — {e.foydalanuvchi_matni}")
                continue
        holat = "yangi   " if javob.javob_topildi else "topilmadi"
        yangi += javob.javob_topildi
        print(f"[{i}/{jami}] {holat}— {savol[:60]}")
        # Kvotani birdan yoqib yubormaslik uchun savollar orasida pauza
        if kechikish:
            time.sleep(kechikish)

    print()
    print(f"Jami: {jami} | keshda bor edi: {keshda} | yangi isitildi: {yangi} | xato: {xato}")
    ombor = "ha" if kesh.tashqi_saqlash() else "yo'q (faqat xotirada, uyg'onishda yo'qoladi)"
    print(f"Tashqi omborda saqlanadimi: {ombor}")


def main() -> int:
    p = argparse.ArgumentParser(description="Javob keshini oldindan to'ldiradi")
    p.add_argument("--quruq", action="store_true", help="savollarni ko'rsatadi, so'rov yubormaydi")
    p.add_argument("--soni", type=int, default=0, help="nechta savol isitilsin (0 = hammasi)")
    p.add_argument("--moddalar", action="store_true", help="modda sarlavhalaridan ham savol yasash")
    p.add_argument("--kechikish", type=float, default=2.0, help="savollar orasidagi pauza (sekund)")
    a = p.parse_args()

    savollar = savollarni_yig(a.moddalar)
    if a.soni:
        savollar = savollar[: a.soni]

    if a.quruq:
        for s in savollar:
            print(s)
        print(f"\nJami {len(savollar)} ta savol")
        return 0

    if not kesh.tashqi_saqlash():
        print("OGOHLANTIRISH: tashqi ombor sozlanmagan — isitilgan kesh xizmat")
        print("qayta ishga tushishi bilan yo'qoladi. STATISTIKA_KV_URL ni bering.")
        print()

    isit(savollar, a.kechikish)
    return 0


if __name__ == "__main__":
    sys.exit(main())
