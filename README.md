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
- **Telegram bot** — matn va **ovozli xabar** orqali savol berish, hujjat tahlili
- **Admin sahifa** (`/admin`, parol bilan) — qonun moddalarini qo'shish/yangilash
  va statistika: so'rovlar soni, javob topilish ulushi, **sayt/bot kesimi**,
  ovozli so'rovlar, mavzular bo'yicha taqsimot, 30 kunlik grafik va
  javob topilmagan savollar ro'yxati (bazani kengaytirish uchun)

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
├── services/
│   ├── javob.py         # asosiy javob oqimi (sayt va bot shuni chaqiradi)
│   ├── retrieval.py     # moddalarni qidirish (BM25 + teskari indeks)
│   ├── llm.py           # AI integratsiyasi: Anthropic + Gemini zaxira (structured output)
│   └── documents.py     # PDF/DOCX matn ajratish
└── bot/                 # Telegram bot (handlers, formatlash, holat)
data/
├── qonunlar.json        # 348 modda, 13 hujjat (hammasi lex.uz'dan)
└── organlar.json        # organlar va kontaktlar bazasi
tools/
└── lex_import.py        # lex.uz'dan modda import qilish
static/                  # chat UI + admin sahifa (sof HTML/JS)
```

## Telegram bot

Bot saytdagi bilan **aynan bir xil** javob oqimini ishlatadi
(`app/services/javob.py`) — mantiq takrorlanmaydi, kesh ham umumiy.

Imkoniyatlari: savol-javob, **ovozli xabar**, **ovozli javob**, PDF/DOCX hujjat
tahlili, `/rejim` (oddiy/pro), `/ovoz` (ovozli javob sozlamasi), javob ostidan
ariza qoralamasini `.txt` fayl qilib olish.

**Botdagi javob saytdagidan batafsilroq.** Botda ekran cheklovi yo'q, shuning
uchun javob alohida **umumiy xulosa** bilan boshlanadi ("qonun bo'yicha
ahvolingiz qanday") va qadamlar ko'proq hamda to'liqroq bo'ladi
(`batafsil=True` — `services/llm.py`). Buning evaziga javob ~10 soniya
sekinlashadi, shuning uchun saytda yoqilmagan. Kesh kalitida ham shu farq
hisobga olinadi — botning javobi saytga berilmaydi.

**Ovozli xabar.** Telegram ovozni OGG/Opus'da beradi; u provayderga
**o'zgartirilmasdan** yuboriladi, chunki Render bepul tierda ffmpeg yo'q.
Asosiy provayder — Gemini (kaliti loyihada allaqachon bor), `OPENAI_API_KEY`
berilsa Whisper zaxira bo'ladi. Transkript foydalanuvchiga javobdan oldin
ko'rsatiladi: nutq noto'g'ri tanilsa, u buni darhol ko'radi. Cheklov —
60 soniya.

**Ovozli javob (TTS).** `TTS_PROVAYDER=gemini` qo'yilsa yoqiladi; standart
holat — `yoq`. Uch nozik joyi bor:

- **Ovozga faqat tavsiya qismi tushadi.** Modda matnlari uzun va quloqqa quruq —
  ularni o'qib berish audioni bir necha daqiqaga cho'zadi. Matnli javob esa doim
  to'liq yuboriladi: ovoz uning o'rnini emas, qo'shimchasini bajaradi.
- **Format.** Gemini xom PCM qaytaradi (`audio/L16`), Telegram'ning `sendVoice`i
  esa faqat OGG/Opus qabul qiladi va Render'da ffmpeg yo'q. Shuning uchun PCM
  standart `wave` moduli bilan WAV'ga o'raladi va `sendAudio` orqali yuboriladi —
  yangi bog'liqlik ham, konvertatsiya ham talab qilinmaydi.
- **Sozlama foydalanuvchida** (`/ovoz`): `avto` (standart — ovozli savolga
  ovozli javob, matnli savolga faqat matn), `doim`, `o'chiq`.

TTS xatosi javobni yiqitmaydi — ovoz kelmasa ham matnli javob yuboriladi.

O'zbek tilidagi sifat tekshirilgan: hosil qilingan audio qaytadan matnga
o'girilganda asl matnga 96–100% mos tushdi (`gemini-2.5-flash-preview-tts`,
`Kore` va `Charon` ovozlari).

**Lokal ishlab chiqish (polling):**

```bash
# .env ga TELEGRAM_BOT_TOKEN ni qo'ying (@BotFather beradi)
python -m app.bot.polling
```

**Produksiya (webhook):** `TELEGRAM_WEBHOOK_URL` berilgan bo'lsa, ilova ishga
tushganda webhook o'zi o'rnatiladi (`/telegram/webhook`). `TELEGRAM_WEBHOOK_SECRET`
ni ham qo'ying — so'rov haqiqatan Telegram'dan kelganini shu tekshiradi.
Render Blueprint'da uchalasi ham sozlangan.

Bir nechta nozik joy ataylab shunday qilingan:

- **Webhook darhol `200` qaytaradi**, javob esa fon vazifasida tayyorlanadi.
  Javob 10-15 soniya davom etadi; Telegram javobni kutib qolsa o'sha update'ni
  qayta yuboradi va foydalanuvchi bir savolga ikki marta javob olardi.
- **Javob alohida oqimda hisoblanadi** (`asyncio.to_thread`). Aks holda LLM
  so'rovi butun event loop'ni — bot bilan birga saytni ham — qotirib qo'yadi.
- **Javob bitta xabarda keladi.** Ilgari xulosa, har modda va tavsiya alohida
  xabar edi — uch moddali javob 5-6 ta xabarga bo'linib, suhbat emas, hujjat
  oqimiga o'xshardi. Endi odam bitta xabarda xulosa, tavsiya va murojaat
  organini oladi; qonun matnini «📖 Qonun moddalari» tugmasi orqali ochadi.
  Tugmadagi kalit AYNAN o'sha javobga bog'langan, shuning uchun eski xabardagi
  tugma yangi javobning moddalarini ochib yubormaydi.
- **Modda matni qisqartirilmaydi.** Telegram'da xabar 4096 belgi bilan
  cheklangan, shuning uchun uzun modda xatboshi chegarasi bo'yicha bir necha
  xabarga bo'linadi.
- **`parse_mode=HTML`**, MarkdownV2 emas: qonun matni `.`, `-`, `(` belgilariga
  to'la va MarkdownV2 da ularning har biri escape talab qiladi.
- Har foydalanuvchi uchun 10 daqiqada 20 so'rov cheklovi va bir vaqtda bitta
  so'rov qoidasi bor.

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
| `GEMINI_MODEL` | Zaxira model (standart: `gemini-flash-latest`). Aniq versiya nomlarini Google yangi kalitlar uchun yopib qo'yadi — `-latest` xavfsizroq |
| `ADMIN_PASSWORD` | Admin sahifa paroli |
| `TELEGRAM_BOT_TOKEN` | Bot tokeni (@BotFather). Bo'sh bo'lsa bot o'chiq, sayt oldingidek ishlaydi |
| `TELEGRAM_WEBHOOK_URL` | Ilovaning tashqi manzili. Berilsa webhook avtomatik o'rnatiladi |
| `TELEGRAM_WEBHOOK_SECRET` | Webhook so'rovini tekshirish uchun tasodifiy satr |
| `OPENAI_API_KEY` | Ovozni matnga o'girish zaxirasi (ixtiyoriy; asosiysi — Gemini) |
| `TTS_PROVAYDER` | Ovozli javob: `gemini` yoki `yoq` (standart: `yoq`) |
| `GEMINI_TTS_MODEL` | TTS modeli (standart: `gemini-2.5-flash-preview-tts`) |
| `GEMINI_TTS_OVOZ` | Ovoz nomi (standart: `Kore`) |

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
- Javoblarni streaming qilish, foydalanuvchi fikri (feedback) yig'ish

## Ogohlantirish

HuquqiyAI bergan ma'lumot tanishtiruv xarakteriga ega bo'lib, professional
huquqiy maslahat o'rnini bosmaydi. Rasmiy manba — [lex.uz](https://lex.uz).
