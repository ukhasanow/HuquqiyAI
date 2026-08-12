# ⚖️ HuquqiyAI — O'zbekiston uchun huquqiy AI yordamchi

Fuqarolar uchun huquqiy savollariga **qonunning asl moddasi**, **amaliy tavsiya**
va **qayerga murojaat qilish** ma'lumotini beruvchi veb-ilova.
Ro'yxatdan o'tish talab qilinmaydi — ochilgan zahoti ishlatiladi.

President AI Award 2026 tanlovi uchun tayyorlangan prototip.

🌐 **Jonli sayt:** https://huquqiyai-kjpa.onrender.com
🤖 **Telegram bot:** saytdagi havola orqali
📄 **English:** [README.en.md](README.en.md)

---

## Bir qarashda

| | |
|---|---|
| **Muammo** | Fuqaro huquqiy savoliga javob izlaganda ikki narsaga duch keladi: qonun tili tushunarsiz, internetdagi maslahat esa manbasiz. |
| **Yechim** | Har javob uch qismdan: qonunning **asl matni**, sodda tavsiya va **aniq organ** manzili bilan. |
| **Asosiy kafolat** | Modda matni AI orqali **umuman o'tmaydi** — u bazadan bevosita chiqadi. Ya'ni qonunni "qayta yozib yuborish" texnik jihatdan mumkin emas. |
| **Baza** | 602 modda/band, 15 ta hujjat — hammasi [lex.uz](https://lex.uz)dan olingan, har biriga to'g'ridan-to'g'ri havola bilan |
| **Til** | O'zbek lotin, o'zbek kirill va rus — savol qaysi yozuvda bo'lsa, javob ham o'shanda |
| **Sifat nazorati** | 427 avtomatik test; ular tarmoqqa umuman chiqmaydi |

### Nega bu ishonchli

Huquqiy AI'da eng katta xavf — modelning qonun matnini o'zicha "tushuntirib"
yuborishi. Bu yerda buni oldini olish uchun **arxitektura darajasida** chora
ko'rilgan:

- Model faqat **qaysi modda mos kelishini tanlaydi** (ID sifatida), matnni
  yozmaydi. Modda matni foydalanuvchiga `data/qonunlar.json` dan chiqadi.
- Model bazada yo'q ID qaytarsa, u **tashlab yuboriladi** — o'ylab topilgan
  modda foydalanuvchiga yetib bormaydi.
- lex.uz'dan olinmagan matnlar to'qib chiqarilmaydi: ular `needs_verification`
  deb belgilanadi va faqat havola bilan ko'rsatiladi.
- Ariza qoralamasi **AI'siz** tuziladi, jarima arifmetikasi ham — u yerda
  taxminga o'rin yo'q.

### Uzluksizlik

Xizmat **8 bosqichli provayder navbati** ustida ishlaydi: biri limitga urilsa
yoki yiqilsa, keyingisi javob beradi va foydalanuvchi buni sezmaydi. Tartib
narx bo'yicha — avval bepul zaxiralar, pulli provayder eng oxirida.

Holatni ochiq ko'rish mumkin: [`/health`](https://huquqiyai-kjpa.onrender.com/health)
har bosqichning holatini va javob keshi saqlanishini ko'rsatadi.

---

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
- **Hujjat tahlili** — PDF/DOCX/TXT yuklab, hujjatni huquqiy tahlil qildirish.
  Tahlildan tashqari **hujjatda nimani tekshirish kerakligi** va **uni qanday
  bekor qildirish mumkinligi** ko'rsatiladi: muddat, qayerga murojaat qilish
  va tartib — turiga qarab (sud qarori, jarima, ishdan bo'shatish buyrug'i,
  shartnoma, davlat organi javobi)
- **Ariza qoralamasi generatori** — asosli javobdan keyin bir tugma bilan
  tayyor ariza/da'vo arizasi tuziladi (LLM'siz: modda va organ bazadan olinadi,
  foydalanuvchi faqat F.I.Sh kiritadi; hujjatda yoziladigan yagona joy — imzo)
- **Uch yozuvda ishlaydi** — o'zbek lotin, o'zbek kirill va rus tilidagi
  savollarga o'sha til/yozuvda javob (kirill uchun transliteratsiyali qidiruv)
- **Jarima qonuniyligini tekshirish** — yo'l jarimasi qarorini muddatlar va
  rasmiylashtirish bo'yicha tekshiradi (AI'siz, aniq arifmetika bilan)
- **Radar o'rnatilishini surat bo'yicha tekshirish** — moslama suratini
  yuklang: yonida patrul avtomobili bormi, uni formadagi xodim boshqarganmi,
  qarovsiz qoldirilganmi — YPX nizomining 28–36-bandlari bo'yicha baholanadi
  (AI faqat suratni tasvirlaydi, huquqiy xulosani qat'iy mantiq chiqaradi)
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

**Trenoganing o'zi qonunbuzarlik EMAS.** Bu eng ko'p uchraydigan yanglish
tushuncha va tizim unga ataylab qo'shilmaydi. Nizomda "trenoga", "uch oyoqli"
degan so'z umuman yo'q, **30, 31 va 34-bandlar** esa ko'chma fotoradarni ochiq
nazarda tutadi. Ya'ni qarorni kuchsiz qiladigan narsa moslamaning **turi** emas:

| Nima buzilgan | Band | Oqibat |
| --- | --- | --- |
| Moslamani patrul avtomobilidan yechib olish, begona TV ga o'rnatish, begona shaxsni jalb qilish | 32 | Yuridik kuchga ega emas |
| Sertifikat yo'q / muddati o'tgan / IIB hisobida yo'q | 28 | Yuridik kuchga ega emas |
| Moslama qarovsiz — xodim uni qabul qilib, ishlatilishiga mas'ul bo'lmagan | 35 | Bekor qilish asosi |
| Dislokatsiyada ko'rsatilmagan joy yoki vaqt | 33 (statsionar), 34 (ko'chma) | Bekor qilish asosi |
| Xotiraga o'rnatilgan joy va harakat yo'nalishi kiritilmagan | 36 | Bekor qilish asosi |
| Ko'rsatkichga e'tiroz bildirilgan, lekin xolislar jalb qilinmagan | 29 | Bekor qilish asosi |

Shuning uchun `trenoga` tanlangani **hech qachon** «asos» bermaydi — u faqat
«diqqat» beradi va hal qiluvchi savolni so'raydi: *radar yonida patrul
avtomobili bormidi, uni formadagi xodim boshqarganmi?* «Asos» aynan shu
javobdan chiqadi. Asossiz shikoyat foydalanuvchini ham, tizimga ishonchni ham
yo'qotadi — buni testlar qo'riqlaydi (`test_trenoga_ozi_asos_bermaydi`).

### Radar suratini yuklash

`POST /api/jarima/radar` (saytda tugma, botda `/radar`) — moslama o'rnatilishi
suratini YPX nizomi bo'yicha tekshiradi. Yuqoridagi jadval nega muhimligi shu
yerda ko'rinadi: **32-band bo'yicha dalilni aynan surat beradi** — odam
"patrul avtomobili bormidi" degan savolga bir yil o'tib javob bera olmaydi,
surat esa uni ko'rsatib turadi.

Ish taqsimoti `jarima.py` dagidek: **AI faqat KUZATADI, xulosani Python
chiqaradi.** Modeldan "bu qonuniymi?" deb so'ralmaydi — bunday so'roqda model
rozi bo'lishga moyil bo'lib, har suratda buzilish "topadi". Undan faqat
tavsif olinadi (yonida patrul avtomobili bormi, odam formadami, moslama
qarovsizmi, rusumi nima), keyin `services/radar.py` uni `JarimaSorov`
maydonlariga o'giradi va odatdagi tekshiruv ishlaydi.

Ikkita nozik joy:

- **`null` va `false` farq qiladi.** "Kadr tor, aniqlab bo'lmadi" — bu "patrul
  avtomobili yo'q edi" degani emas. Faqat `false` asos beradi, `null` bermaydi.
- **EXIF dan sana va koordinata** olinadi (JPEG uchun; Pillow qo'shilmadi, kichik
  o'quvchi `radar.py` ichida). Bu tekshiruv natijasiga ta'sir qilmaydi — EXIF ni
  o'zgartirish mumkin — faqat **34-band bo'yicha dislokatsiya so'rovini**
  aniqlashtiradi: dislokatsiya aynan joy va vaqt bo'yicha tekshiriladi.

Kuzatuv javobda qaytariladi va foydalanuvchiga ko'rsatiladi: model oq
"Malibu"ni patrul avtomobili deb bilishi mumkin va odam buni ko'rib tuzata
olishi kerak.

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

## Hujjat: nimani tekshirish va qanday bekor qildirish

PDF, DOCX, TXT yoki hujjat surati yuklanganda tahlildan tashqari yana ikki
narsa qaytadi: **hujjatning o'zidan tekshirib ko'riladigan ro'yxat** va **uni
qanday bekor qildirish mumkinligi** — muddat, murojaat qilinadigan joy,
rasmiylashtirish tartibi. `services/hujjat.py`.

Sabab oddiy: odam hujjatni "tushunish" uchun emas, u bilan **nima qilishni**
bilish uchun yuklaydi. Tahlil "bu ishdan bo'shatish buyrug'i" deb aytadi, lekin
"sizni ikki oy oldin ogohlantirishlari shart edi" degan gapni aytmaydi — aynan
shu gap odamga kerak.

### Nega bu yerda ham AI yo'q

Hujjat turi uning **muddatini** belgilaydi, muddat esa qaytarib bo'lmaydigan
narsa. Model turni xato aniqlasa, odam noto'g'ri muddatga ishonib haqiqiysini
o'tkazib yuboradi. Shuning uchun tur kalit so'zlar bo'yicha (ball tizimi bilan)
aniqlanadi, muddatlar bazadagi asl modda matniga havola qiladi va testlar
ularni modda matni bilan solishtiradi — qonun o'zgarsa test yiqiladi.

| Hujjat turi | Muddat | Qayerga | Asosiy modda |
| --- | --- | --- | --- |
| Sud hal qiluv qarori (fuqarolik) | **1 oy** qaror qabul qilingan kundan (soddalashtirilgan tartibda 10 kun) | Apellyatsiya instansiyasi sudi | FPK 383, 385¹, 386 |
| Sudning MJK qarori | **10 sutka** qaror o'qib eshittirilgan yoki nusxasi olingan kundan | Apellyatsiya tartibida | MJK 324¹, 324³ |
| Ma'muriy jarima qarori (organ) | **10 kun** nusxa olingan kundan | Yuqori organ yoki jinoyat ishlari bo'yicha tuman sudi | MJK 315, 316, 319, 324 |
| Ishdan bo'shatish buyrug'i | nizo turiga qarab — taxmin qilinmaydi | Ish beruvchi yoki sud | MK 165, 174, 254, 408, 564 |
| Shartnoma | shartnomaning o'zida | Kelishuv yoki sud | FK 382 |
| Davlat organi javobi | **1 yil** qaror ma'lum bo'lgan paytdan | Bo'ysunuv tartibida yuqori organ | Murojaatlar qonuni 16, 17, 21, 26 |

Ishdan bo'shatish qatoriga e'tibor bering: mehnat nizosi muddati bazada yo'q va
u **o'ylab topilmaydi** — javobda "muddat nizo turiga qarab farq qiladi,
buyruq nusxasini olgan sanani belgilab qo'ying" deyiladi. Bo'sh joyni to'ldirish
uchun taxminiy raqam yozish bu yerda eng yomon xato bo'lardi.

### Chalkashadigan juftlik

Sud chiqargan jarima qarori bilan YHXX chiqargan jarima qarorini ajratish
qiyin: ikkalasida ham "jarima", "ma'muriy", "sud" so'zlari bor. Farqni
**"sudya"** so'zi qiladi — organ qarorida u bo'lmaydi.

Lekin bu yetarli emas, chunki xato narxi yuqori: ikkalasida muddat 10 kun
bo'lsa ham, biriga **apellyatsiya**, ikkinchisiga **shikoyat** beriladi.
Noto'g'ri yo'l bilan berilgan hujjat qaytariladi va odam shu orada muddatni
boy beradi. Shuning uchun bu ikkisi «chalkash juftlik» deb belgilangan: ball
farqi qanchalik katta bo'lsa ham, ikkalasi ham ball to'plagan bo'lsa natija
**"taxmin"** deb ko'rsatiladi va foydalanuvchidan hujjatni o'zi tekshirish
so'raladi.

### Jarima qarori PDF ko'rinishida

Ilgari qaror faqat **rasmdan** o'qilardi va PDF yuborilsa umumiy savol-javobga
tushib ketardi. Endi `jarima.matndan_oqi()` bor: PDF va DOCX da matn allaqachon
mavjud, uni rasmga aylantirib OCR qilish ortiqcha. Ko'rsatma va sxema rasm
bilan bir xil, ya'ni ikkala yo'l ham aynan bir xil arifmetik tekshiruvga
tushadi. Maydonlarning hech biri o'qilmasa, hujjat qaror emas deb hisoblanadi
va odam hech bo'lmasa umumiy javob oladi.

### Qalin matn `**` bilan yoziladi

Xizmat modullaridagi izohlar HTML emas, `**qalin**` bilan yoziladi. Ilgari
ularda `<b>` ishlatilgan edi va u **ikkala joyda ham buzilgan**: saytda `el()`
`textContent` orqali yozadi, botda esa `html.escape()` qo'llanadi — natijada
foydalanuvchi qalin matn o'rniga `<b>` teglarini o'qirdi. Endi bitta manbadan
ikki xil chiqish: saytda `qalinFormat()`, botda `_urgu()`.

Botdagi tartib muhim — **avval escape, keyin qalin**: izohga foydalanuvchi
kiritgan qiymat qo'shiladi (masalan qarordagi modda raqami) va undagi `<`
xabarni Telegram uchun butunlay yuborilmaydigan qilib qo'yardi.

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

### Provayder navbati (8 bosqich)

Biri ishlamay qolsa (kredit tugashi, daqiqalik limit, tarmoq xatosi) tizim
avtomatik keyingisiga o'tadi. Tartib ikki mezon bo'yicha: avval **bepul**
zaxiralar, eng oxirida **pulli** provayder — ya'ni pul faqat bepul kvotalar
tugagach sarflanadi.

| # | Bosqich | Roli |
|---|---|---|
| 1 | Anthropic `claude-sonnet-4-5` | asosiy, eng sifatli |
| 2-3 | Google Gemini (2 model) | bepul zaxira |
| 4-5 | Groq `gpt-oss-120b` / `20b` | bepul, kunlik kvotasi katta |
| 6 | OpenRouter `nemotron-3-super` | bepul, **20 so'rov/daqiqa** — cho'qqi uchun |
| 7 | BazaarLink `auto:free` | bepul, 10 so'rov/daqiqa |
| 8 | OpenAI `gpt-5.4-mini` | pulli, faqat oxirgi chora |

Nozik joyi: **har model alohida bosqich**, chunki limitlar model bo'yicha
hisoblanadi (o'lchandi: Groq'da bir model qoldig'i 4323 ga tushganda
ikkinchisi hamon 7924 edi). Shu sababli ro'yxatga model qo'shish bepul
sig'imni shuncha barobar oshiradi — `GEMINI_MODEL` va `GROQ_MODEL` vergul
bilan bir necha model qabul qiladi.

Kunlik kvotasi kichik, lekin daqiqalik limiti keng bo'lganlar (6 va 7)
ataylab **oxirida** turadi: oddiy kunda ularga navbat yetmaydi, cho'qqi
paytda esa aynan o'shalar ushlab qoladi.

### Foydalanuvchiga nima ko'rinadi

Provayder vaqtincha limitga ursa, xabar aniq bo'ladi: *"So'rovlar ko'payib
ketdi. 47 soniyadan so'ng qaytadan urinib ko'ring"* — muddat provayderning
o'z javobidan olinadi, taxmin qilinmaydi. Limit qisqa bo'lsa (8 soniyagacha)
tizim o'zi kutib qayta uriniladi va foydalanuvchi xatoni umuman ko'rmaydi.

Kredit tugashi kabi **doimiy** nosozlikda provayder 10 daqiqaga chetlanadi —
bu bekorga kechikish qo'shmaslik va uning xatosi boshqalarning vaqtinchalik
xatosini bosib ketmasligi uchun.

### Javob keshi

Bir xil savol qayta so'ralsa AI'ga umuman murojaat qilinmaydi. Kesh ikki
qavatli: xotira (tarmoqsiz, ~0 ms) va Upstash (qayta ishga tushishdan omon
qoladi). Jonli o'lchov: **11.07s → 0.128s**.

Demo oldidan keshni oldindan to'ldirish mumkin:

```bash
python -m tools.kesh_isit          # 69 ta hayotiy savol
python -m tools.kesh_isit --moddalar   # + modda sarlavhalaridan 400+
```

Keshdagi javob provayderga bormaydi — u yerda limit ham, xarajat ham,
kutish ham yo'q.

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

## Statistikani saqlash

Render bepul tierda **disk vaqtinchalik**: har deploy'da va xizmat uxlab
uyg'onganda faylga yozilgan hamma narsa yo'qoladi. Ya'ni `data/statistika.json`
ga tayanilsa, ko'rsatkichlar 15 daqiqada bir noldan boshlanadi.

Shu sababli statistika ikki joyda saqlanishi mumkin:

- **Lokal ishlab chiqish** — `data/statistika.json` (hech narsa sozlash shart emas)
- **Produksiya** — tashqi kalit-qiymat ombori, `STATISTIKA_KV_URL` va
  `STATISTIKA_KV_TOKEN` berilganda

Ombor sifatida **Upstash Redis** ishlatiladi: u oddiy HTTP REST API beradi,
shuning uchun yangi paket kerak emas — mavjud `httpx` yetadi.

Ikki himoya qo'yilgan va ikkalasi testda qayd etilgan:

- **Ombor javob bermasa ilova to'xtamaydi** — statistika yozilmaydi, xolos.
- **Ombor javob bermasa faylga tushilmaydi.** Aks holda eski lokal fayl
  o'qilib, keyingi yozuvda tashqi ombordagi haqiqiy ma'lumot ustiga
  yozilib ketardi.

## Keyingi bosqichlar

- **lex.uz o'zgarishlarini kuzatish** — importerda `--tekshir` rejimi bor,
  lekin u qo'lda ishga tushiriladi; buni jadval bo'yicha avtomatlashtirish kerak
- **Semantik qidiruv** — embedding asosidagi qidiruv. Hozirgi leksik qidiruv
  (BM25 + qo'lda tanlangan teglar) hozirgi baza uchun yetarli, lekin savol
  moddadagidan butunlay boshqa so'z bilan yozilsa uni topa olmaydi
- Javoblarni streaming qilish, foydalanuvchi fikri (feedback) yig'ish

## Ogohlantirish

HuquqiyAI bergan ma'lumot tanishtiruv xarakteriga ega bo'lib, professional
huquqiy maslahat o'rnini bosmaydi. Rasmiy manba — [lex.uz](https://lex.uz).
