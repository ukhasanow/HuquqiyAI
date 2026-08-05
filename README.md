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
- **Jarima qonuniyligini tekshirish** — yo'l jarimasi qarorini muddatlar va
  rasmiylashtirish bo'yicha tekshiradi (AI'siz, aniq arifmetika bilan)
- **Shartnoma tahlili** — mehnat, ijara, kredit yoki oldi-sotdi shartnomasini
  yuklang: har band xavf darajasi (🔴 qonunga zid · 🟡 noqulay · 🟢 e'tibor bering)
  va tegishli qonun moddasi bilan ko'rsatiladi
- **Ovozli savol** — saytda ham, Telegram botda ham mikrofon orqali
- **Telegram bot** — matn, **ovozli xabar** va hujjat orqali savol; javob
  ovozli ham yuborilishi mumkin
- **Admin sahifa** (`/admin`, parol bilan) — qonun moddalarini qo'shish/yangilash
  va statistika: so'rovlar soni, javob topilish ulushi, **sayt va bot uchun
  alohida kesim** (so'rovlar, topilish ulushi, foydalanuvchilar, oddiy/pro,
  ovozli savol va javob), mavzular bo'yicha taqsimot, manba bo'yicha
  ajratilgan 30 kunlik grafik va javob topilmagan savollar ro'yxati
  (bazani kengaytirish uchun)

## Jarima qonuniyligini tekshirish

`POST /api/jarima` (saytda tugma, botda `/jarima`) yo'l jarimasi qarorini
tekshiruv ro'yxati bo'yicha baholaydi.

**Bu yerda AI yo'q va bu ataylab.** Jarimaning taqdirini muddatlar hal qiladi,
muddat esa sanalar ayirmasi. Model bir kun xato hisoblasa, odam asossiz shikoyat
beradi yoki haqiqiy asosdan voz kechadi. Shuning uchun tekshiruvlar oddiy
arifmetika bilan bajariladi, izohlar bazadagi asl modda matniga havola qiladi.
Javob **0,04 soniyada** qaytadi va AI provayder ishlamay qolganda ham ishlaydi.

Tekshiruvlar (muddatlar MJK matnidan olingan):

| Modda | Nima tekshiriladi |
|---|---|
| **36** + 271(7) | javobgarlikka tortish muddati: hodisadan **1 yil**, kamera orqali qayd etilganda **1 oy**. O'tgan bo'lsa ish tugatilishi lozim — eng kuchli asos |
| **316** | shikoyat muddati: qaror **nusxasi olingan** kundan 10 kun |
| **330** | qaror 3 oy ijroga qaratilmasa, ijro etilmaydi |
| **309¹** | kamera jarimasi mashina egasiga yoziladi — boshqa shaxs boshqargan bo'lsa asos bor |
| **281**, **311** | bayonnoma mazmuni va qaror nusxasi topshirilishi |
| **128³** | tezlik jarimasida **5 km/soat chegirmasi** (pastda) |
| **17¹** | kamera orqali qayd etiladigan moddalarning **yopiq ro'yxati** |

### Tezlik jarimasi: 5 km/soat chegirmasi

128³-moddaning oxirgi qismi o'lchash xatosi uchun **qayd etilgan tezlikdan
soatiga 5 kilometr chegirib tashlashni** talab qiladi. Bu eng ko'p e'tibordan
chetda qoladigan qoida va ikki xil asos beradi:

- **Jarima umuman o'rinsiz.** 70 km/soat zonada radar 74 qayd etsa: 74 − 5 = 69,
  ya'ni hisobga olinadigan oshirish yo'q.
- **Jarima qismi noto'g'ri.** 70 zonada 95: chegirmasiz 25 km/soat (5 BHM),
  chegirma bilan 20 km/soat (1 BHM) — summa besh baravar ortiqcha.

Tizim ikkalasini ham hisoblab beradi (128³ qismlari: 20 gacha 1 BHM, 40 gacha 5,
60 gacha 9, undan ortiq 15 BHM).

**17¹-modda** kamera orqali qayd etiladigan huquqbuzarliklarning yopiq ro'yxatini
belgilaydi. Ro'yxatda bo'lmagan modda bo'yicha kamera jarimasi solingan bo'lsa —
bu mustaqil asos. Shu moddaga ko'ra kamera jarimasida **takroriylik hisobga
olinmaydi**.

### Noqonuniy radar (YPX nizomi, VM 975-son)

Nizomning ikki bandi jarima qarorini shunchaki "bekor qilinadigan" emas, balki
**yuridik kuchga ega bo'lmagan** qilib qo'yadi:

- **28-band** — sertifikatga ega bo'lmagan, sertifikat muddati tugagan yoki
  ichki ishlar organlari hisobida bo'lmagan tezlik o'lchash vositasi asosida
  chiqarilgan qarorlar *«yuridik kuchga ega bo'lmaydi va huquqiy oqibatlar
  keltirib chiqarmaydi»*.
- **32-band** — radarni patrul avtomobilidan **o'zboshimchalik bilan yechib
  olish**, begona transport vositalariga o'rnatish va xizmatga aloqasi
  bo'lmagan fuqarolarni jalb qilish **qat'iyan taqiqlanadi**; bunday holda
  chiqarilgan qarorlar ham yuridik kuchga ega bo'lmaydi.

Aynan shu — "uch oyoqli radar" (trenoga) holati. Tekshiruvda radar turi
so'raladi va `trenoga` tanlansa 32-band bo'yicha asos ko'rsatiladi. Qo'shimcha:
**33 va 34-bandlar** kameralar va ko'chma radarlar joyi tasdiqlangan
dislokatsiya bilan belgilanishini talab qiladi — shikoyatda o'sha kungi
dislokatsiya nusxasini so'rash mumkin.

### Qaror rasmini yuklash

`POST /api/jarima/rasm` (saytda tugma, botda oddiy surat yuborish) qaror
suratidan sana, modda, band, tezlik va summani o'qiydi. **AI faqat matnni
o'qiydi** — huquqiy xulosani baribir arifmetik tekshiruvlar beradi. O'qilgan
qiymatlar javobda qaytariladi va foydalanuvchiga ko'rsatiladi: model sanani
xato o'qisa, butun xulosa noto'g'ri bo'lardi, shuning uchun uni tuzatish
imkoni bo'lishi shart. Chegaradan tashqari qiymatlar (masalan 900 km/soat)
tashlab yuboriladi.

### Gemini bepul tier kvotasi

Ovozli xabar (STT), ovozli javob (TTS), rasm o'qish va shartnoma OCR — hammasi
Gemini orqali ishlaydi. **Bepul tierda kvota kalitga emas, Google loyihasiga
bog'langan:** `GenerateRequestsPerDayPerProjectPerModel-FreeTier` — har model
uchun **kuniga 20 ta so'rov**. Ya'ni yangi kalit yasash kvotani tiklamaydi —
o'sha loyihaning kvotasi bo'lgani uchun yangi kalit ham darhol 429 beradi.

Chegara **har model uchun alohida** hisoblanadi, shuning uchun kvota tugasa
`GEMINI_MODEL` ni boshqa modelga o'tkazish vaqtincha yechim beradi. Doimiy
yechim — Google Cloud'da billing yoqish.

Matnli savol-javob bunga bog'liq emas: u Anthropic orqali ishlaydi.

### Eskirgan argument ataylab ishlatilmaydi

Vazirlar Mahkamasining 2018-yil 1-dekabrdagi 975-son qarori (31-band) ko'chma
radarda inspektordan ko'rsatkich va sertifikatni ko'rsatishni talab qilardi —
Oliy sud 2023-yilda aynan shunga tayanib jarimani bekor qilgan. **Lekin bu talab
2024-yil iyulda bekor qilindi** va endi mobil radarlar bayonnomasiz, 37-band
tartibida rasmiylashtiriladi. Shu sababli tizim bu argumentni tavsiya qilmaydi
va foydalanuvchini bundan ogohlantiradi — aks holda behuda shikoyatlar yozilardi.
Buni test qo'riqlaydi.

**Qaror qaysi holatda bekor qilinadi** — 321-modda to'rt asosni belgilaydi va
ular tekshiruv ro'yxatiga kiritilgan: ishning bir tomonlama ko'rib chiqilishi;
qo'llanilgan norma ishning faktik holatlariga mos kelmasligi; ish yuritish
qoidalarining jiddiy buzilishi; jazoning adolatsizligi. 307-modda bo'yicha
aybdorlik aniqlanishi shart.

**Shikoyat qayerga beriladi** (315-modda): yuqori turuvchi organga yoki
**jinoyat ishlari bo'yicha tuman (shahar) sudiga**, qarorni chiqargan organ
orqali yoki bevosita sudga. **Davlat boji to'lanmaydi.** Muddatida berilgan
shikoyat qaror ijrosini to'xtatib turadi (318-modda), qaror bekor qilinsa
undirib olingan pul qaytariladi (324-modda).

**Shikoyat qoralamasi** (`POST /api/jarima/shikoyat`) — topilgan asoslar
avtomatik kiritiladi, odam faqat F.I.Sh yozadi. `ariza.py` dagi `ariza_tuz()`
bunga mos kelmaydi: u "vaziyatimni ko'rib chiqishingizni so'rayman" deb
tugaydi, shikoyatda esa aniq talab bo'lishi kerak — qarorni bekor qilish va
ish yuritishni tugatish. Shu sababli alohida `shikoyat_tuz()` yozilgan.

**Tizim hech qachon "jarima noqonuniy, to'lamang" demaydi** — faqat "shu asos
tekshirishga arziydi" deydi va shikoyat muddatini eslatadi. Yakuniy bahoni sud
yoki vakolatli organ beradi. Bu qoida testda qayd etilgan.

Muddat konstantalari qonun matniga test orqali bog'langan: qonun o'zgarib,
`--tekshir` bilan baza yangilanganda test yiqiladi va konstantalarni eslatadi.
Kalendar oy arifmetikasi 30 kun emas — 31-yanvar + 1 oy = 28-fevral.

## Shartnoma tahlili

Oddiy savol-javob uch qismli javob beradi (modda → tavsiya → organ). Shartnomaga
bu shakl to'g'ri kelmaydi: odam "qaysi bandi menga zarar keltiradi?" deb so'raydi,
shartnomada esa 8-10 ta muammoli band bo'lishi mumkin va ular uch qadamli
tavsiyaga sig'maydi. Shuning uchun `POST /api/shartnoma` alohida javob shaklini
qaytaradi: **umumiy mazmun → bandlar ro'yxati (xavf bo'yicha saralangan) → xulosa**.

Har band uchun: band raqami, oddiy tildagi mazmuni, xavf darajasi va **bazadagi
asl modda**. Asl matn kafolati bu yerda ham kuchda — LLM faqat modda ID'sini
tanlaydi, mavjud bo'lmagan ID qaytarsa band moddasiz ko'rsatiladi.

**Imperativ normalar majburan qo'shiladi.** Leksik qidiruv "Ish kuni 09:00 dan
21:00 gacha" bandini "Ish vaqtining normal davomiyligi" moddasi bilan bog'lay
olmaydi — umumiy so'z yo'q. Shuning uchun shartnoma turi aniqlanadi va o'sha
turga xos majburiy normalar (`services/shartnoma.py` dagi `ASOSIY_MODDALAR`)
nomzodlarga doim kiritiladi. Test bu ro'yxatdagi har bir ID bazada mavjudligini
tekshiradi.

Telegram botda hujjat yuborilsa, shartnoma ekani avtomatik aniqlanadi
(raqamlangan bandlar + turga xos so'zlar) va band-band tahlil ishga tushadi.
Tahlil oddiy javobdan sekinroq (~40 soniya): har band alohida tekshiriladi.

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

### Baza: 602 modda/band, 15 ta hujjat

Barcha modda matnlari `tools/lex_import.py` orqali lex.uz'dan olingan
(`verified`) — qo'lda ham, AI orqali ham yozilmagan (pastda "Bazani to'ldirish").

| Hujjat | Modda | Nimani qamraydi |
|---|---|---|
| **Yo'l harakati qoidalari** | **186** | to'liq matn: tezlik, quvib o'tish, to'xtash, chorraha, temir yo'l kesishmasi |
| **Ma'muriy javobgarlik kodeksi** | **76** | jarimalar, yo'l qoidabuzarliklari **va jarima protsedurasi** (bayonnoma, qaror, shikoyat, ijro muddatlari) |
| Mehnat kodeksi | 49 | ishdan bo'shatish, ish haqi, ta'til, sinov muddati, mehnat nizolari |
| Fuqarolik kodeksi | 42 | shartnoma, ijara, qarz, meros, zarar qoplash |
| Oila kodeksi | 34 | ajrashish, aliment, er-xotin mulki, bola tarbiyasi |
| Soliq kodeksi | 33 | daromad, mol-mulk va yer solig'i, imtiyozlar, deklaratsiya |
| Yer kodeksi | 31 | tomorqa, uchastka ajratish, olib qo'yish, yer nizolari |
| Fuqarolik protsessual kodeksi | 28 | da'vo arizasi, davlat boji, muddatlar, apellyatsiya |
| Konstitutsiya | 28 | inson huquqlari (mehnat, uy-joy, ta'lim, sud himoyasi) |
| Uy-joy kodeksi | 18 | ijara, ko'chirish, kommunal to'lovlar |
| Iste'molchilar huquqlari qonuni | 18 | nuqsonli tovar, almashtirish, pul qaytarish |
| Jinoyat kodeksi | 16 | o'g'rilik, firibgarlik, tan jarohati |
| Murojaatlar to'g'risidagi qonun | 16 | ariza berish, ko'rib chiqish muddatlari, javob |
| Yo'l harakati to'g'risidagi qonun | 12 | guvohnoma, haydovchi huquqlari, texnik holat |

Har kodeksdan butun matn emas, fuqaro savolida eng ko'p uchraydigan moddalar
tanlangan: baza kattaligi javob sifatini emas, faqat qidiruv shovqinini oshiradi.
Istisno — **Yo'l harakati qoidalari to'liq olingan** (186 band): jarima qarorida
istalgan band ko'rsatilishi mumkin va yarim baza bilan "band topilmadi" javobi
juda ko'p chiqar edi.

**Jarima qonuniyligini tekshirish uchun ikki hujjat kerak.** Jarima qarorida
doim ikkalasi ko'rsatiladi: **MJK moddasi** (javobgarlik va jarima miqdori) va
**Qoidalar bandi** (aynan nima buzilgan). Shu sababli MJK'dan qoidabuzarlik
moddalaridan tashqari protsessual moddalar ham olingan — jarima ko'pincha
mazmuni emas, tartibi buzilgani uchun bekor qilinadi: bayonnoma noto'g'ri
tuzilgan (281-modda), qaror nusxasi topshirilmagan (311-modda), javobgarlikka
tortish muddati o'tgan (36-modda), ijro muhlati tugagan (330-modda).

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
├── qonunlar.json        # 602 modda/band, 15 hujjat (hammasi lex.uz'dan)
└── organlar.json        # organlar va kontaktlar bazasi
tools/
└── lex_import.py        # lex.uz'dan modda import qilish
static/                  # chat UI + admin sahifa (sof HTML/JS)
```

## Telegram bot

Bot saytdagi bilan **aynan bir xil** javob oqimini ishlatadi
(`app/services/javob.py`) — mantiq takrorlanmaydi, kesh ham umumiy.

**Bot:** [@HuquqiyAIbot](https://t.me/HuquqiyAIbot) — saytning bosh sahifasida
ham havolasi bor.

Imkoniyatlari: savol-javob, **ovozli xabar** va **ovozli javob**, PDF/DOCX/surat
tahlili, **shartnoma tahlili**, **jarima tekshiruvi** (`/jarima` yoki qaror
surati), `/rejim` (oddiy/pro), `/ovoz`, javob ostidan ariza yoki shikoyat
qoralamasini `.txt` fayl qilib olish.

**Admin statistikasi.** `TELEGRAM_ADMIN_IDLAR` ga qo'shilgan chat ID
`/statistika` buyrug'i orqali bot va sayt ko'rsatkichlarini ko'radi: so'rovlar,
javob topilish ulushi, manba kesimi, ovozli savol/javob, shartnoma va jarima
vositalari, eng ko'p mavzular, oxirgi 7 kun va javob topilmagan savollar.
Parol emas, **chat ID** ishlatiladi: Telegram'da yozilgan parol suhbat
tarixida ochiq qoladi, chat ID ni esa foydalanuvchi soxtalashtira olmaydi.
Admin bo'lmaganga buyruq borligi ham oshkor qilinmaydi. O'z ID ingizni bilish
uchun botga `/id` yozing.

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

**Saytda ovozli savol.** Sayt ham botdagi aynan shu xizmatni ishlatadi
(`POST /api/ovoz` → `services/ovoz.py`). Brauzer `MediaRecorder` bilan yozadi;
format brauzerga qarab farq qiladi, shuning uchun `audio/ogg;codecs=opus` →
`audio/mp4` → `audio/webm` tartibida qo'llab-quvvatlanadigani tanlanadi.
Gemini mime yorlig'ini qat'iy tekshirmaydi (mazmunni o'zi aniqlaydi), WAV va
m4a to'liq sinovdan o'tgan. Transkript **yuborilmaydi**, matn maydoniga
qo'yiladi — odam nutq noto'g'ri tanilganini ko'rib tuzata olsin.

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

Yangi hujjat qo'shish: `HUJJATLAR` registriga
`(akt id, prefiks, qonun_nomi, tuzilma)` yozuvini qo'shing.
**lex.uz'da kuchini yo'qotgan tahrirlar ham ochilaveradi** — akt id ni tanlashda
hujjat amaldaligiga ishonch hosil qiling (registrda uchta bunday tuzoq izohda
ko'rsatilgan).

**Ikki xil tuzilma.** Kodeks va qonunlar `"modda"` tuzilmasida
(`13-modda. Sarlavha`). Hukumat qarori ilovalari — masalan Yo'l harakati
qoidalari — `"band"` tuzilmasida: sarlavhasiz, faqat raqamlangan bandlar
(`116. Transport vositalarining haydovchilari...`). Band parseri uchta tuzoqni
hisobga oladi va ularning har biri testda qayd etilgan:

- hujjat **qarordan** boshlanadi va uning "1.", "2." punktlari band emas —
  bandlar faqat ilovadagi Qoidalarda;
- Qoidalardan **keyin yana ilovalar** keladi ("Yo'l belgilari") va raqamlashni
  birdan boshlaydi — chegara qo'yilmasa 1-band butun ilovani yutib yuboradi;
- lex.uz matnida `117.Temir yoʻl...` — nuqtadan keyin bo'sh joy yo'q. Bo'sh
  joyni majburiy qilsak bu band yo'qoladi, raqamga ruxsat bersak `5.1. yoʻl
  belgisi` band bo'lib ketadi.

Import avtomatik teg taklif qiladi (sarlavhadan), lekin foydalanuvchi
"tomorqa", "guvohnoma" deb yozadi — bunday jonli so'zlar qo'lda qo'shiladi.
Teglar qidiruvda eng katta vaznga ega, shuning uchun ular
`tests/test_retrieval.py` dagi real savollar testi yiqilganda sozlanadi.

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
