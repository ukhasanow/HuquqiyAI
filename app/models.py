# So'rov/javob sxemalari (Pydantic)
from typing import List, Optional

from pydantic import BaseModel, Field


class TarixXabar(BaseModel):
    rol: str  # "user" yoki "assistant"
    matn: str


class ChatSorov(BaseModel):
    savol: str = Field(min_length=1, max_length=4000)
    rejim: str = "oddiy"  # "oddiy" | "pro"
    tarix: Optional[List[TarixXabar]] = None


class ModdaJavob(BaseModel):
    id: str
    qonun_nomi: str
    modda_raqami: str
    sarlavha: str
    matn: str
    lex_url: str
    holat: str


class OrganJavob(BaseModel):
    nomi: str
    tavsif: str
    manzil: str
    ish_vaqti: Optional[str] = None
    telefon: str
    sayt: str
    onlayn_murojaat: Optional[str] = None
    hududiy_havola: Optional[str] = None
    kontakt_holati: str


class ChatJavob(BaseModel):
    javob_topildi: bool
    moddalar: List[ModdaJavob]  # 1-qism: asl matn (bazadan, o'zgartirilmagan)
    xulosa: str = ""            # umumiy baho (faqat batafsil rejimda — Telegram bot)
    tavsiya: str                # 2-qism: LLM tavsiyasi
    murojaat: Optional[OrganJavob] = None  # 3-qism: bazadagi kontakt
    murojaat_mavzusi: str = "umumiy"  # ariza generatori uchun
    disclaimer: str = (
        "Diqqat: bu ma'lumot tanishtiruv xarakteriga ega bo'lib, professional "
        "huquqiy maslahat o'rnini bosmaydi."
    )


class ArizaSorov(BaseModel):
    fish: str = Field(min_length=1, max_length=200)
    vaziyat: str = Field(default="", max_length=4000)  # foydalanuvchi savoli/bayoni
    modda_idlari: List[str] = Field(min_length=1, max_length=3)
    murojaat_mavzusi: str = "umumiy"
    manzil: str = Field(default="", max_length=300)
    telefon: str = Field(default="", max_length=50)


class ArizaJavob(BaseModel):
    matn: str
    fayl_nomi: str = "ariza.txt"


class OvozJavob(BaseModel):
    """Ovozli xabar transkripti.

    Javob emas, savol: transkript foydalanuvchiga ko'rsatiladi va u tasdiqlab
    (yoki tuzatib) o'zi yuboradi — nutq noto'g'ri tanilsa bilinib qolsin.
    """
    matn: str


class ModdaKiritish(BaseModel):
    id: str = Field(min_length=1)
    qonun_nomi: str
    modda_raqami: str
    sarlavha: str = ""
    matn: str = ""
    lex_url: str = ""
    teglar: List[str] = []
    holat: str = "needs_verification"  # "verified" | "needs_verification"
