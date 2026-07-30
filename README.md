# ⚖️ HuquqiyAI — O'zbekiston uchun huquqiy AI yordamchi

Fuqarolar uchun huquqiy savollariga **qonunning asl moddasi**, **amaliy tavsiya**
va **qayerga murojaat qilish** ma'lumotini beruvchi veb-ilova.
Ro'yxatdan o'tish talab qilinmaydi — ochilgan zahoti ishlatiladi.

President AI Award 2026 tanlovi uchun tayyorlangan prototip.

## Asosiy imkoniyatlar

- **Chat interfeysi** — ikki rejim:
  - *Oddiy odam* — sodda, tushunarli til
  - *Advokat / Pro* — yuridik til, protsessual muddatlar, hujjat turlari
- **Har bir javob qat'iy uch qismdan iborat:**
  1. **Qonun moddasi** — asl matn **o'zgartirilmasdan** (bazadan olinadi, LLM
     qayta yozmaydi), modda raqami, qonun nomi va to'g'ridan-to'g'ri moddaga
     olib boruvchi lex.uz havolasi bilan, iqtibos-karta ko'rinishida
  2. **Umumiy tavsiya** — vaziyatga mos tushuntirish va keyingi qadamlar
  3. **Qayerga murojaat qilish** — davlat organi nomi, manzil, telefon, sayt
- **Hujjat tahlili** — PDF/DOCX/TXT yuklab, hujjatni huquqiy tahlil qildirish
- **Ariza qoralamasi generatori** — asosli javobdan keyin bir tugma bilan
  tayyor ariza/da'vo arizasi tuziladi (LLM'siz: modda va organ bazadan olinadi,
  foydalanuvchi faqat F.I.Sh kiritadi; hujjatda yoziladigan yagona joy — imzo)
- **Uch yozuvda ishlaydi** — o'zbek lotin, o'zbek kirill va rus tilidagi
  savollarga o'sha til/yozuvda javob (kirill uchun transliteratsiyali qidiruv)
- **Admin sahifa** (`/admin`, parol bilan) — qonun moddalarini qo'shish/yangilash

## Arxitektura: asl matn kafolati

RAG oqimi: savol → moddalarni qidirish (kalit so'z + teg skoring) → AI model
faqat **topilgan moddalar asosida** tavsiya yozadi va tegishli moddalar ID'sini
tanlaydi (majburiy structured output, JSON schema). Modda matnining o'zi esa
**hech qachon LLM orqali o'tmaydi** — foydalanuvchiga bevosita bazadan
(`data/qonunlar.json`) yuboriladi. Bu parafraza xavfini texnik jihatdan yo'q qiladi.

Ikki provayderli arxitektura: asosiy AI provayder ishlamay qolsa (kredit
tugashi, limit), tizim avtomatik zaxira provayderga (Google Gemini) o'tadi —
xizmat uzluksiz ishlaydi.

lex.uz'dan olib bo'lmagan matnlar to'qib chiqarilmaydi — ular bazada
`needs_verification` deb belgilanadi va UI'da "matn tekshirilmoqda" ko'rinishida,
faqat lex.uz havolasi bilan chiqadi. Hozirgi bazadagi 42 ta modda matni lex.uz'ning
rasmiy sahifalaridan olingan (`verified`): Mehnat kodeksi (ishdan bo'shatish,
ish haqi, ta'til, sinov muddati, mehnat nizolari), Oila kodeksi (ajrashish,
aliment, er-xotin mulki), Fuqarolik kodeksi (shartnoma, ijara, qarz, meros),
Iste'molchilar huquqlari qonuni (nuqsonli tovar, almashtirish, pul qaytarish).

```
app/
├── main.py              # FastAPI routelar
├── config.py            # .env sozlamalar
├── models.py            # Pydantic sxemalar
├── storage.py           # JSON baza qatlami
└── services/
    ├── retrieval.py     # moddalarni qidirish
    ├── llm.py           # AI integratsiyasi: Anthropic + Gemini zaxira (structured output)
    └── documents.py     # PDF/DOCX matn ajratish
data/
├── qonunlar.json        # 14 modda: Mehnat, Oila, Fuqarolik kodekslari + Iste'molchilar qonuni
└── organlar.json        # organlar va kontaktlar bazasi
static/                  # chat UI + admin sahifa (sof HTML/JS)
```

## O'rnatish

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# .env faylida ANTHROPIC_API_KEY va ADMIN_PASSWORD ni kiriting
```

`.env` o'zgaruvchilari:

| O'zgaruvchi | Tavsif |
|---|---|
| `ANTHROPIC_API_KEY` | Asosiy AI provayder kaliti |
| `MODEL` | Asosiy model (standart: `claude-sonnet-4-5`) |
| `GEMINI_API_KEY` | Zaxira provayder kaliti (ixtiyoriy, [aistudio.google.com](https://aistudio.google.com/apikey)dan bepul olinadi) |
| `GEMINI_MODEL` | Zaxira model (standart: `gemini-2.5-flash`) |
| `ADMIN_PASSWORD` | Admin sahifa paroli |

Kamida bitta provayder kaliti bo'lishi shart; ikkalasi bo'lsa tizim avtomatik
zaxiraga o'tishni qo'llaydi.

## Ishga tushirish

```bash
source venv/bin/activate
uvicorn app.main:app --port 8000
```

So'ng brauzerda: **http://127.0.0.1:8000** (admin: **http://127.0.0.1:8000/admin**)

## Bepul hostingga joylash (Render)

Repo'da `render.yaml` tayyor. Qadamlar:

1. Kodni GitHub'ga push qiling
2. [render.com](https://render.com)da GitHub bilan kiring
3. **New + → Blueprint** → repo'ni tanlang
4. So'ralganda `ANTHROPIC_API_KEY` va `ADMIN_PASSWORD` qiymatlarini kiriting

Bepul tierda xizmat 15 daqiqa harakatsizlikdan keyin uxlaydi (birinchi ochilish
~1 daqiqa). Demo oldidan sahifani bir marta ochib qo'ying.

## Demo uchun 3 ta namunaviy savol

1. **Mehnat** (oddiy rejim): *"Ish beruvchi meni asossiz ishdan bo'shatmoqchi,
   nima qilay?"* → Mehnat kodeksi 161-modda + Mehnat inspeksiyasi (1176)
2. **Iste'molchi** (oddiy rejim): *"Sotib olgan telefonim nuqsonli chiqdi,
   qaytarib bera olamanmi?"* → Iste'molchilar qonuni 14-modda + Raqobat qo'mitasi (1159)
3. **Oila** (pro rejim): *"Ajrashganda bola alimenti qanday undiriladi?"* →
   Oila kodeksi 96-97-moddalar + sud/FHDYo (pro rejimda protsessual tartib bilan)

Bonus: biror mehnat shartnomasini (PDF/DOCX) yuklab, "Bu shartnomada xodim
huquqlari buzilganmi?" deb so'rash mumkin.

## Keyingi bosqichlar

- **Ovozli suhbat** — arxitektura tayyor: `services/llm.py` kirish matnini
  manbasidan mustaqil qabul qiladi, STT/TTS qo'shish faqat yangi endpoint
  talab qiladi
- **To'liq lex.uz sinxronizatsiyasi** — barcha kodekslarni avtomatik yuklab,
  yangilanishlarni kuzatish (hozircha admin panel orqali qo'lda)
- **Semantik qidiruv** — baza kattalashganda embedding asosidagi qidiruv
  (hozirgi leksik qidiruv kichik korpus uchun yetarli)
- Telegram-bot interfeysi, javoblarni streaming qilish, foydalanuvchi fikri (feedback) yig'ish

## Ogohlantirish

HuquqiyAI bergan ma'lumot tanishtiruv xarakteriga ega bo'lib, professional
huquqiy maslahat o'rnini bosmaydi. Rasmiy manba — [lex.uz](https://lex.uz).
