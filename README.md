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

RAG oqimi: savol → moddalarni qidirish (BM25 uslubidagi leksik qidiruv) → AI model
faqat **topilgan moddalar asosida** tavsiya yozadi va tegishli moddalar ID'sini
tanlaydi (majburiy structured output, JSON schema). Modda matnining o'zi esa
**hech qachon LLM orqali o'tmaydi** — foydalanuvchiga bevosita bazadan
(`data/qonunlar.json`) yuboriladi. Bu parafraza xavfini texnik jihatdan yo'q qiladi.

Ikki provayderli arxitektura: asosiy AI provayder ishlamay qolsa (kredit
tugashi, limit), tizim avtomatik zaxira provayderga (Google Gemini) o'tadi —
xizmat uzluksiz ishlaydi.

lex.uz'dan olib bo'lmagan matnlar to'qib chiqarilmaydi — ular bazada
`needs_verification` deb belgilanadi va UI'da "matn tekshirilmoqda" ko'rinishida,
faqat lex.uz havolasi bilan chiqadi.

### Baza: 348 modda, 13 ta hujjat

Barcha modda matnlari `tools/lex_import.py` orqali lex.uz'dan olingan
(`verified`) — qo'lda ham, AI orqali ham yozilmagan (pastda "Bazani to'ldirish").

| Hujjat | Modda | Nimani qamraydi |
|---|---|---|
| Mehnat kodeksi | 49 | ishdan bo'shatish, ish haqi, ta'til, sinov muddati, mehnat nizolari |
| Fuqarolik kodeksi | 42 | shartnoma, ijara, qarz, meros, zarar qoplash |
| Oila kodeksi | 34 | ajrashish, aliment, er-xotin mulki, bola tarbiyasi |
| Soliq kodeksi | 33 | daromad, mol-mulk va yer solig'i, imtiyozlar, deklaratsiya |
| Yer kodeksi | 31 | tomorqa, uchastka ajratish, olib qo'yish, yer nizolari |
| Fuqarolik protsessual kodeksi | 28 | da'vo arizasi, davlat boji, muddatlar, apellyatsiya |
| Konstitutsiya | 28 | inson huquqlari (mehnat, uy-joy, ta'lim, sud himoyasi) |
| Ma'muriy javobgarlik kodeksi | 23 | jarimalar, yo'l qoidalari, jamoat tartibi |
| Uy-joy kodeksi | 18 | ijara, ko'chirish, kommunal to'lovlar |
| Iste'molchilar huquqlari qonuni | 18 | nuqsonli tovar, almashtirish, pul qaytarish |
| Jinoyat kodeksi | 16 | o'g'rilik, firibgarlik, tan jarohati |
| Murojaatlar to'g'risidagi qonun | 16 | ariza berish, ko'rib chiqish muddatlari, javob |
| Yo'l harakati to'g'risidagi qonun | 12 | guvohnoma, haydovchi huquqlari, texnik holat |

Har kodeksdan butun matn emas, fuqaro savolida eng ko'p uchraydigan moddalar
tanlangan: baza kattaligi javob sifatini emas, faqat qidiruv shovqinini oshiradi.

```
app/
├── main.py              # FastAPI routelar
├── config.py            # .env sozlamalar
├── models.py            # Pydantic sxemalar
├── storage.py           # JSON baza qatlami
└── services/
    ├── retrieval.py     # moddalarni qidirish (BM25 + teskari indeks)
    ├── llm.py           # AI integratsiyasi: Anthropic + Gemini zaxira (structured output)
    └── documents.py     # PDF/DOCX matn ajratish
data/
├── qonunlar.json        # 348 modda, 13 hujjat (hammasi lex.uz'dan)
└── organlar.json        # organlar va kontaktlar bazasi
tools/
└── lex_import.py        # lex.uz'dan modda import qilish
static/                  # chat UI + admin sahifa (sof HTML/JS)
```

## Bazani to'ldirish (lex.uz importeri)

Modda matni **hech qachon qo'lda yozilmaydi va AI orqali generatsiya
qilinmaydi** — faqat `tools/lex_import.py` orqali lex.uz'dan olinadi.

```bash
# Registrdagi hujjatdan tanlangan moddalarni import qilish
python tools/lex_import.py --hujjat soliq --faqat 379,380,381

# Avval ko'rib chiqish (faylga yozmaydi)
python tools/lex_import.py --hujjat yer --quruq

# Bazadagi moddalar lex.uz bilan hamon mos ekanini tekshirish (qonun o'zgargan bo'lishi mumkin)
python tools/lex_import.py --hujjat mehnat --tekshir
```

Yangi hujjat qo'shish: `HUJJATLAR` registriga `(akt id, prefiks, qonun_nomi)`
yozuvini qo'shing. **lex.uz'da kuchini yo'qotgan tahrirlar ham ochilaveradi** —
akt id ni tanlashda hujjat amaldaligiga ishonch hosil qiling (registrda ikkita
bunday tuzoq izohda ko'rsatilgan).

Import avtomatik teg taklif qiladi (sarlavhadan), lekin foydalanuvchi
"tomorqa", "guvohnoma" deb yozadi — bunday jonli so'zlar qo'lda qo'shiladi.
Teglar qidiruvda eng katta vaznga ega, shuning uchun ular
`tests/test_retrieval.py` dagi real savollar testi yiqilganda sozlanadi.

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
- **lex.uz o'zgarishlarini kuzatish** — importerda `--tekshir` rejimi bor,
  lekin u qo'lda ishga tushiriladi; buni jadval bo'yicha avtomatlashtirish kerak
- **Semantik qidiruv** — embedding asosidagi qidiruv. Hozirgi leksik qidiruv
  (BM25 + qo'lda tanlangan teglar) 348 modda uchun yetarli, lekin savol
  moddadagidan butunlay boshqa so'z bilan yozilsa uni topa olmaydi
- Telegram-bot interfeysi, javoblarni streaming qilish, foydalanuvchi fikri (feedback) yig'ish

## Ogohlantirish

HuquqiyAI bergan ma'lumot tanishtiruv xarakteriga ega bo'lib, professional
huquqiy maslahat o'rnini bosmaydi. Rasmiy manba — [lex.uz](https://lex.uz).
