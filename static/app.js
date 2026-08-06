// HuquqiyAI — chat interfeysi mantiqi
(function () {
  const chat = document.getElementById("chat");
  const forma = document.getElementById("forma");
  const savolInput = document.getElementById("savol");
  const yuborTugma = document.getElementById("yubor");
  const faylInput = document.getElementById("fayl");
  const faylNomi = document.getElementById("fayl-nomi");

  let rejim = "oddiy";
  const tarix = []; // {rol, matn} — serverga kontekst sifatida yuboriladi

  // Anonim foydalanuvchi ID (statistika uchun, shaxsiy ma'lumotsiz)
  let foydalanuvchiId = "";
  try {
    foydalanuvchiId = localStorage.getItem("huquqiyai_id") || "";
    if (!foydalanuvchiId) {
      foydalanuvchiId = "anon-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 10);
      localStorage.setItem("huquqiyai_id", foydalanuvchiId);
    }
  } catch (e) { /* localStorage yopiq bo'lsa ID yuborilmaydi */ }

  // Rejim almashtirish
  document.querySelectorAll(".rejim-tugma").forEach((t) => {
    t.addEventListener("click", () => {
      document.querySelectorAll(".rejim-tugma").forEach((b) => b.classList.remove("faol"));
      t.classList.add("faol");
      rejim = t.dataset.rejim;
    });
  });

  // Namuna savollar
  document.querySelectorAll(".misol").forEach((t) => {
    t.addEventListener("click", () => {
      savolInput.value = t.textContent;
      savolInput.focus();
    });
  });

  // Shartnoma tahlili tanlovi faqat fayl biriktirilganda ko'rinadi
  const shartnomaTanlov = document.getElementById("shartnoma-tanlov");
  const shartnomaBelgi = document.getElementById("shartnoma-belgi");

  faylInput.addEventListener("change", () => {
    const bor = faylInput.files.length > 0;
    faylNomi.textContent = bor ? faylInput.files[0].name : "";
    shartnomaTanlov.hidden = !bor;
    if (!bor) shartnomaBelgi.checked = false;
  });

  // ---- Jarima tekshiruvi ----
  // Sanalar forma orqali so'raladi, erkin matndan taxmin qilinmaydi: jarimaning
  // taqdirini aynan muddat hal qiladi va bir kunlik xato natijani teskari
  // qilib qo'yadi. Tekshiruvning o'zi serverda AI'siz, arifmetika bilan.
  document.getElementById("jarima-och").addEventListener("click", jarimaFormasiniOch);

  const JARIMA_HOLAT = {
    asos: ["🔴", "Bekor qilish uchun asos"],
    diqqat: ["🟡", "Tekshirib ko'ring"],
    joyida: ["🟢", "Muammo ko'rinmayapti"],
    "noma'lum": ["⚪️", "Ma'lumot yetarli emas"],
  };

  function jarimaFormasiniOch() {
    const x = el("div", "xabar bot");
    x.appendChild(avatarYarat());
    const ich = el("div", "xabar-ich");
    ich.appendChild(el("div", "qism-sarlavha", "🚗 Jarima qonuniyligini tekshirish"));
    ich.appendChild(
      el("p", "", "Qarordagi ma'lumotlarni kiriting. Sanalar eng muhimi — " +
        "jarimaning qonuniyligi ko'pincha muddatga bog'liq.")
    );

    // Rasm yuklash: qarorni qo'lda ko'chirib yozishdan ko'ra tez va xatosizroq
    const rasmBlok = el("div", "jarima-rasm");
    const rasmYorliq = el("label", "vosita-tugma", "📷 Qaror rasmini yuklash");
    const rasmKirish = el("input");
    rasmKirish.type = "file";
    rasmKirish.accept = "image/*";
    rasmKirish.hidden = true;
    rasmYorliq.appendChild(rasmKirish);
    const rasmHolati = el("span", "ovoz-holati");
    rasmBlok.append(rasmYorliq, rasmHolati);
    ich.appendChild(rasmBlok);

    // Radar surati — qarordan butunlay boshqa narsa. Qarorda MATN o'qiladi,
    // bu yerda esa HOLAT ko'riladi: yonida patrul avtomobili bormi, moslamani
    // formadagi xodim boshqaryaptimi. Aynan shu ikkisi 32-band bo'yicha asos
    // beradi — trenoganing o'zi hali qonunbuzarlik emas.
    const radarBlok = el("div", "jarima-rasm");
    const radarYorliq = el("label", "vosita-tugma", "📡 Radar suratini yuklash");
    const radarKirish = el("input");
    radarKirish.type = "file";
    radarKirish.accept = "image/*";
    radarKirish.hidden = true;
    radarYorliq.appendChild(radarKirish);
    const radarHolati = el("span", "ovoz-holati");
    radarBlok.append(radarYorliq, radarHolati);
    ich.appendChild(radarBlok);
    ich.appendChild(el("p", "jarima-eslatma",
      "Radar suratida uning atrofi ko'rinsin — yonidagi avtomobil va odam. " +
      "Faqat moslamaning o'zi tushgan yaqin surat kam narsa beradi."));

    const forma = el("form", "jarima-forma");
    const maydonlar = [
      ["hodisa_sanasi", "Qoidabuzarlik sodir bo'lgan sana", "date"],
      ["qaror_sanasi", "Qaror chiqarilgan sana", "date"],
      ["qaror_olingan_sanasi", "Qaror nusxasini olgan sana", "date"],
      ["modda", "MJK moddasi (masalan 128-3)", "text"],
      ["band", "Qoidalar bandi (masalan 116)", "text"],
      ["summa", "Jarima summasi", "text"],
      ["qayd_etilgan_tezlik", "Radar qayd etgan tezlik, km/soat", "number"],
      ["ruxsat_etilgan_tezlik", "Ruxsat etilgan tezlik, km/soat", "number"],
      ["jarima_bhm", "Jarima necha baravar BHM (bilsangiz)", "number"],
    ];
    const kiritishlar = {};
    maydonlar.forEach(([nomi, yorliq, turi]) => {
      const qator = el("label", "jarima-maydon");
      qator.appendChild(el("span", "", yorliq));
      const kiritish = el("input");
      kiritish.type = turi;
      if (turi === "text") kiritish.maxLength = 60;
      kiritishlar[nomi] = kiritish;
      qator.appendChild(kiritish);
      forma.appendChild(qator);
    });

    const tanlovlar = {};
    [
      ["radar_turi", "Radar qanday edi", [
        ["", "bilmayman"],
        ["trenoga", "uch oyoqli tagliksa (trenoga)"],
        ["patrul", "patrul avtomobilida"],
        ["statsionar", "doimiy o'rnatilgan kamera"],
      ]],
      // Trenogada hal qiluvchi savol — atrofi. Javob "patrul avtomobili
      // yo'q edi" bo'lsa, 32-band bo'yicha asos chiqadi.
      ["radar_atrofi", "Radar yonida nima bor edi", [
        ["", "eslay olmayman"],
        ["patrul", "YPX patrul avtomobili va formadagi xodim"],
        ["begona", "oddiy avtomobil yoki fuqarolik kiyimidagi odam"],
        ["qarovsiz", "hech kim yo'q edi, radar qarovsiz turardi"],
      ]],
    ].forEach(([nomi, yorliq, variantlar]) => {
      const qator = el("label", "jarima-maydon");
      qator.appendChild(el("span", "", yorliq));
      const tanlov = el("select");
      variantlar.forEach(([qiymat, matn]) => {
        const variant = el("option", "", matn);
        variant.value = qiymat;
        tanlov.appendChild(variant);
      });
      tanlovlar[nomi] = tanlov;
      qator.appendChild(tanlov);
      forma.appendChild(qator);
    });

    const kameraQator = el("label", "jarima-maydon jarima-belgi");
    const kamera = el("input");
    kamera.type = "checkbox";
    kameraQator.append(kamera, el("span", "", "Kamera (foto-video) orqali qayd etilgan"));
    forma.appendChild(kameraQator);

    const norozilikQator = el("label", "jarima-maydon jarima-belgi");
    const norozilik = el("input");
    norozilik.type = "checkbox";
    norozilikQator.append(norozilik, el("span", "",
      "Radar ko'rsatkichiga o'sha joyda e'tiroz bildirganman"));
    forma.appendChild(norozilikQator);

    const tugma = el("button", "jarima-tekshir", "Tekshirish");
    tugma.type = "submit";
    forma.appendChild(tugma);
    ich.appendChild(forma);
    x.appendChild(ich);
    chat.appendChild(x);
    pastgaSur();

    // Rasm o'qilgach maydonlar to'ldiriladi — foydalanuvchi ularni ko'rib,
    // tuzatib, keyin o'zi "Tekshirish" bosadi. Model xato o'qishi mumkin.
    rasmKirish.addEventListener("change", async () => {
      const fayl = rasmKirish.files[0];
      if (!fayl) return;
      rasmHolati.textContent = "Qaror o'qilmoqda...";
      try {
        const fd = new FormData();
        fd.append("fayl", fayl);
        const javob = await fetch("/api/jarima/rasm", { method: "POST", body: fd });
        const d = await javob.json();
        if (!javob.ok) {
          rasmHolati.textContent = d.detail || "Rasmni o'qib bo'lmadi";
          return;
        }
        const o = d.oqilgan;
        Object.entries(kiritishlar).forEach(([nomi, kiritish]) => {
          if (o[nomi] !== null && o[nomi] !== undefined && o[nomi] !== "") {
            kiritish.value = o[nomi];
          }
        });
        kamera.checked = Boolean(o.kamera);
        rasmHolati.textContent = "✓ O'qildi — tekshirib, kerak bo'lsa tuzating";
        jarimaJavobQosh(d.tekshiruv, o);
      } catch (err) {
        rasmHolati.textContent = "Server bilan bog'lanib bo'lmadi";
      } finally {
        rasmKirish.value = "";
      }
    });

    // Radar surati: kuzatuvlar ko'rsatiladi va formadagi tanlovlar to'ldiriladi.
    // Model xato ko'rishi mumkin — shuning uchun natija tugmaga emas, odam
    // ko'rib tuzata oladigan maydonlarga tushadi.
    radarKirish.addEventListener("change", async () => {
      const fayl = radarKirish.files[0];
      if (!fayl) return;
      radarHolati.textContent = "Surat ko'rilmoqda...";
      try {
        const fd = new FormData();
        fd.append("fayl", fayl);
        const javob = await fetch("/api/jarima/radar", { method: "POST", body: fd });
        const d = await javob.json();
        if (!javob.ok) {
          radarHolati.textContent = d.detail || "Suratni ko'rib bo'lmadi";
          return;
        }
        const k = d.kuzatuv;
        const turlar = { trenoga: "trenoga", avtomobilda: "patrul", ustunda: "statsionar" };
        if (turlar[k.ornatilish]) tanlovlar.radar_turi.value = turlar[k.ornatilish];
        if (k.patrul_avtomobili === true) tanlovlar.radar_atrofi.value = "patrul";
        else if (k.xodim_formada === false || k.patrul_avtomobili === false) {
          tanlovlar.radar_atrofi.value = k.odam_bormi ? "begona" : "qarovsiz";
        }
        if (k.tezlik_belgisi && !kiritishlar.ruxsat_etilgan_tezlik.value) {
          kiritishlar.ruxsat_etilgan_tezlik.value = k.tezlik_belgisi;
        }
        radarHolati.textContent = "✓ Ko'rildi — tekshirib, kerak bo'lsa tuzating";
        radarKuzatuviQosh(k, d.dislokatsiya_sorovi);
        jarimaJavobQosh(d.tekshiruv, {});
      } catch (err) {
        radarHolati.textContent = "Server bilan bog'lanib bo'lmadi";
      } finally {
        radarKirish.value = "";
      }
    });

    forma.addEventListener("submit", async (e) => {
      e.preventDefault();
      tugma.disabled = true;
      const sorov = {
        kamera: kamera.checked,
        norozilik_bildirilgan: norozilik.checked,
        radar_turi: tanlovlar.radar_turi.value,
      };
      // "Eslay olmayman" — bu "yo'q edi" degani EMAS. Bo'sh qoldirilsa
      // maydon null bo'lib qoladi va 32-band bo'yicha asos berilmaydi.
      const atrof = tanlovlar.radar_atrofi.value;
      if (atrof === "patrul") {
        sorov.patrul_avtomobili = true;
        sorov.xodim_formada = true;
      } else if (atrof === "begona") {
        sorov.patrul_avtomobili = false;
        sorov.xodim_formada = false;
      } else if (atrof === "qarovsiz") {
        sorov.patrul_avtomobili = false;
        sorov.moslama_qarovsiz = true;
      }
      Object.entries(kiritishlar).forEach(([nomi, kiritish]) => {
        if (!kiritish.value) return;
        sorov[nomi] = kiritish.type === "number" ? Number(kiritish.value) : kiritish.value;
      });
      try {
        const javob = await fetch("/api/jarima", {
          method: "POST",
          headers: Object.assign(
            { "Content-Type": "application/json" },
            foydalanuvchiId ? { "X-Foydalanuvchi-Id": foydalanuvchiId } : {}
          ),
          body: JSON.stringify(sorov),
        });
        const d = await javob.json();
        if (!javob.ok) {
          botXatoQosh(d.detail || "Tekshirib bo'lmadi.");
          return;
        }
        jarimaJavobQosh(d, sorov);
      } catch (err) {
        botXatoQosh("Server bilan bog'lanib bo'lmadi: " + err.message);
      } finally {
        tugma.disabled = false;
      }
    });
  }

  // Suratdan nima ko'rilgani — huquqiy xulosadan ALOHIDA ko'rsatiladi.
  // Model oq "Malibu"ni patrul avtomobili deb bilishi mumkin va odam buni
  // ko'rib turishi kerak: butun xulosa shu kuzatuvga tayanadi.
  function radarKuzatuviQosh(k, dislokatsiya) {
    const UCHLIK = { true: "ha", false: "yo'q", null: "aniqlab bo'lmadi" };
    const ORNATILISH = {
      trenoga: "uch oyoqli tagliksa (trenoga)",
      avtomobilda: "avtomobilda",
      ustunda: "doimiy ustunda",
      qolda: "xodim qo'lida",
      noanik: "aniqlab bo'lmadi",
    };

    const x = el("div", "xabar bot");
    x.appendChild(avatarYarat());
    const ich = el("div", "xabar-ich");
    ich.appendChild(el("div", "qism-sarlavha", "📡 Suratda ko'rganim"));

    const royxat = el("dl", "radar-kuzatuv");
    [
      ["O'rnatilishi", ORNATILISH[k.ornatilish] || k.ornatilish],
      ["Yonida patrul avtomobili", UCHLIK[k.patrul_avtomobili]],
      ["Avtomobil", k.avtomobil_tavsifi],
      ["Odam bor", k.odam_bormi ? "ha" : "yo'q"],
      ["Formadagi xodim", UCHLIK[k.xodim_formada]],
      ["Moslama qarovsiz", k.moslama_qarovsiz ? "ha" : ""],
      ["Yashiringan", k.yashiringan ? (k.yashirish_tavsifi || "ha") : ""],
      ["Moslama rusumi", k.moslama_rusumi],
      ["Tezlik belgisi", k.tezlik_belgisi ? k.tezlik_belgisi + " km/soat" : ""],
      ["Mo'ljal", (k.joy_belgilari || []).join(", ")],
      ["Suratga olingan", k.sana],
    ].forEach(([nomi, qiymat]) => {
      if (!qiymat) return;
      royxat.appendChild(el("dt", "", nomi));
      royxat.appendChild(el("dd", "", String(qiymat)));
    });
    ich.appendChild(royxat);

    if (dislokatsiya) {
      ich.appendChild(el("p", "", "📍 Dislokatsiya so'rovi uchun (34-band " +
        "bo'yicha murojaatingizga shu ma'lumotni kiriting):"));
      ich.appendChild(el("pre", "radar-dislokatsiya", dislokatsiya));
    }
    ich.appendChild(el("p", "jarima-eslatma",
      "Bu — suratdan ko'rilgan holat, huquqiy xulosa emas. Noto'g'ri ko'rilgan " +
      "bo'lsa, formadagi tanlovlarni qo'lda tuzating."));

    x.appendChild(ich);
    chat.appendChild(x);
    pastgaSur();
  }

  function jarimaJavobQosh(d, sorov) {
    const x = el("div", "xabar bot");
    x.appendChild(avatarYarat());
    const ich = el("div", "xabar-ich");

    const bosh = d.asoslar_soni
      ? `⚠️ Bekor qilishni so'rashga ${d.asoslar_soni} ta asos topildi`
      : "Muddatlar bo'yicha aniq asos topilmadi";
    ich.appendChild(el("div", "qism-sarlavha", bosh));

    if (d.shikoyat_kunlari !== null && d.shikoyat_kunlari >= 0) {
      ich.appendChild(
        el("div", "shikoyat-muddat", `⏳ Shikoyat berishga ${d.shikoyat_kunlari} kun qoldi`)
      );
    }

    d.tekshiruvlar.forEach((t) => {
      const [belgi, daraja] = JARIMA_HOLAT[t.holat] || ["⚪️", ""];
      const karta = el("div", "band-karta " + t.holat);
      const sarlavha = el("div", "band-bosh");
      sarlavha.append(el("span", "band-belgi", belgi), el("span", "band-mazmun", t.nomi));
      karta.appendChild(sarlavha);
      karta.appendChild(el("div", "band-daraja", daraja));
      karta.appendChild(el("div", "band-izoh", t.izoh));
      if (t.modda) {
        const modda = el("details", "band-modda");
        modda.appendChild(el("summary", "", "📖 " + t.modda.qonun_nomi + ", " + t.modda.modda_raqami));
        modda.appendChild(el("div", "modda-matn", t.modda.matn));
        const havola = el("a", "", "lex.uz'da ochish ↗");
        havola.href = t.modda.lex_url;
        havola.target = "_blank";
        havola.rel = "noopener";
        modda.appendChild(havola);
        karta.appendChild(modda);
      }
      ich.appendChild(karta);
    });

    // Shikoyat qayerga beriladi (315, 318, 324-moddalar)
    if (d.shikoyat_yoli && d.shikoyat_yoli.length) {
      ich.appendChild(el("div", "qism-sarlavha", "📮 Shikoyat qayerga va qanday beriladi"));
      const royxat = el("ul", "shikoyat-yoli");
      d.shikoyat_yoli.forEach((q) => {
        const qator = document.createElement("li");
        // Matnda faqat <b> ishlatiladi — u serverdagi qat'iy shablondan keladi
        qator.innerHTML = q;
        royxat.appendChild(qator);
      });
      ich.appendChild(royxat);
    }

    ich.appendChild(el("div", "qism-sarlavha", "✅ Xulosa"));
    ich.appendChild(el("div", "tavsiya", d.xulosa));
    ich.appendChild(shikoyatBlokYarat(sorov));
    ich.appendChild(el("div", "disclaimer", d.disclaimer || ""));
    x.appendChild(ich);
    chat.appendChild(x);
    pastgaSur();
  }

  // Shikoyat qoralamasi: asoslar tekshiruvdan avtomatik olinadi, odam faqat
  // F.I.Sh va qaror ma'lumotlarini kiritadi (ariza blokidagi kabi).
  function shikoyatBlokYarat(jarimaSorov) {
    const blok = el("div", "ariza-blok");
    const ochTugma = el("button", "ariza-och", "📄 Shikoyat qoralamasini tuzish");
    ochTugma.type = "button";
    blok.appendChild(ochTugma);

    const forma = el("form", "ariza-forma yashirin");
    const fish = el("input");
    fish.placeholder = "F.I.Sh (majburiy)";
    fish.required = true;
    fish.maxLength = 200;
    const organ = el("input");
    organ.placeholder = "Qarorni chiqargan organ (ixtiyoriy)";
    organ.maxLength = 200;
    const raqam = el("input");
    raqam.placeholder = "Qaror raqami (ixtiyoriy)";
    raqam.maxLength = 60;
    const manzil = el("input");
    manzil.placeholder = "Manzilingiz (ixtiyoriy)";
    manzil.maxLength = 300;
    const telefon = el("input");
    telefon.placeholder = "Telefon (ixtiyoriy)";
    telefon.maxLength = 50;
    const tolangan = el("label", "jarima-maydon jarima-belgi");
    const tolanganBelgi = el("input");
    tolanganBelgi.type = "checkbox";
    tolangan.append(tolanganBelgi, el("span", "", "Jarimani allaqachon to'laganman"));
    const tuz = el("button", "ariza-tuz", "Tuzish");
    tuz.type = "submit";
    forma.append(fish, organ, raqam, manzil, telefon, tolangan, tuz);
    blok.appendChild(forma);

    const natija = el("div", "ariza-natija yashirin");
    blok.appendChild(natija);

    ochTugma.addEventListener("click", () => {
      forma.classList.toggle("yashirin");
      if (!forma.classList.contains("yashirin")) fish.focus();
    });

    forma.addEventListener("submit", async (e) => {
      e.preventDefault();
      tuz.disabled = true;
      try {
        const jarima = Object.assign({}, jarimaSorov, {
          qaror_raqami: raqam.value.trim(),
          tolangan: tolanganBelgi.checked,
        });
        const javob = await fetch("/api/jarima/shikoyat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            fish: fish.value.trim(),
            jarima,
            qaror_organi: organ.value.trim(),
            manzil: manzil.value.trim(),
            telefon: telefon.value.trim(),
          }),
        });
        const j = await javob.json();
        natija.textContent = "";
        if (!javob.ok) {
          natija.appendChild(el("p", "xato-xabar", j.detail || "Shikoyat tuzishda xatolik"));
        } else {
          const maydon = el("textarea", "ariza-matn");
          maydon.value = j.matn;
          maydon.rows = 18;
          maydon.readOnly = true;
          const yuklab = el("button", "ariza-yuklab", "⬇ Yuklab olish (.txt)");
          yuklab.type = "button";
          yuklab.addEventListener("click", () => {
            const blob = new Blob([maydon.value], { type: "text/plain;charset=utf-8" });
            const a = document.createElement("a");
            a.href = URL.createObjectURL(blob);
            a.download = j.fayl_nomi || "shikoyat.txt";
            a.click();
            URL.revokeObjectURL(a.href);
          });
          natija.append(maydon, yuklab);
        }
        natija.classList.remove("yashirin");
        pastgaSur();
      } catch (err) {
        natija.textContent = "";
        natija.appendChild(el("p", "xato-xabar", "Server bilan bog'lanib bo'lmadi: " + err.message));
        natija.classList.remove("yashirin");
      } finally {
        tuz.disabled = false;
      }
    });
    return blok;
  }

  // ---- Ovozli savol ----
  // Transkript to'g'ridan-to'g'ri YUBORILMAYDI, matn maydoniga qo'yiladi: nutq
  // noto'g'ri tanilsa, odam buni javobdan oldin ko'rib tuzatadi (Telegram
  // botdagi "Savolingiz: ..." shaffofligi bilan bir xil).
  const mikrofon = document.getElementById("mikrofon");
  const ovozHolati = document.getElementById("ovoz-holati");
  const MAX_OVOZ_SONIYA = 60;

  let yozuvchi = null;
  let bolaklar = [];
  let taymer = null;
  let toxtatishTaymeri = null;

  // MediaRecorder formatlari brauzerga qarab farq qiladi. Gemini ogg/mp4/wav
  // ni ishonchli qabul qiladi, shuning uchun avval o'sha formatlar sinaladi.
  function formatTanla() {
    const nomzodlar = [
      "audio/ogg;codecs=opus",
      "audio/mp4",
      "audio/webm;codecs=opus",
      "audio/webm",
    ];
    if (!window.MediaRecorder || !MediaRecorder.isTypeSupported) return "";
    return nomzodlar.find((t) => MediaRecorder.isTypeSupported(t)) || "";
  }

  if (!navigator.mediaDevices || !window.MediaRecorder) {
    mikrofon.disabled = true;
    mikrofon.title = "Brauzeringiz ovoz yozishni qo'llamaydi";
  } else {
    mikrofon.addEventListener("click", () => {
      if (yozuvchi && yozuvchi.state === "recording") toxtat();
      else boshla();
    });
  }

  async function boshla() {
    let oqim;
    try {
      oqim = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (e) {
      ovozHolati.textContent = "Mikrofonga ruxsat berilmadi";
      return;
    }
    const tur = formatTanla();
    yozuvchi = new MediaRecorder(oqim, tur ? { mimeType: tur } : undefined);
    bolaklar = [];
    yozuvchi.addEventListener("dataavailable", (e) => {
      if (e.data.size) bolaklar.push(e.data);
    });
    yozuvchi.addEventListener("stop", () => {
      oqim.getTracks().forEach((t) => t.stop());
      yubor(new Blob(bolaklar, { type: yozuvchi.mimeType || "audio/webm" }));
    });
    yozuvchi.start();

    mikrofon.classList.add("yozilmoqda");
    mikrofon.title = "To'xtatish";
    ovozHolati.classList.add("yozilmoqda");
    let soniya = 0;
    ovozHolati.textContent = "● 0:00 — to'xtatish uchun bosing";
    taymer = setInterval(() => {
      soniya++;
      const m = Math.floor(soniya / 60);
      const s = String(soniya % 60).padStart(2, "0");
      ovozHolati.textContent = `● ${m}:${s} — to'xtatish uchun bosing`;
    }, 1000);
    // Cheklovdan oshgan yozuvni serverga yubormaymiz — o'zi to'xtaydi
    toxtatishTaymeri = setTimeout(toxtat, MAX_OVOZ_SONIYA * 1000);
  }

  function toxtat() {
    clearInterval(taymer);
    clearTimeout(toxtatishTaymeri);
    mikrofon.classList.remove("yozilmoqda");
    mikrofon.title = "Savolni ovoz bilan ayting";
    ovozHolati.classList.remove("yozilmoqda");
    if (yozuvchi && yozuvchi.state === "recording") yozuvchi.stop();
  }

  async function yubor(blob) {
    if (!blob.size) {
      ovozHolati.textContent = "";
      return;
    }
    ovozHolati.textContent = "Tinglanmoqda...";
    mikrofon.disabled = true;
    try {
      const fd = new FormData();
      fd.append("fayl", blob, "ovoz." + (blob.type.includes("ogg") ? "ogg" : blob.type.includes("mp4") ? "m4a" : "webm"));
      const javob = await fetch("/api/ovoz", { method: "POST", body: fd });
      const d = await javob.json();
      if (!javob.ok) {
        ovozHolati.textContent = d.detail || "Ovozni o'girib bo'lmadi";
        return;
      }
      if (!d.matn) {
        ovozHolati.textContent = "Nutq eshitilmadi — qaytadan urinib ko'ring";
        return;
      }
      ovozHolati.textContent = "";
      savolInput.value = savolInput.value ? savolInput.value + " " + d.matn : d.matn;
      savolInput.dispatchEvent(new Event("input"));
      savolInput.focus();
    } catch (err) {
      ovozHolati.textContent = "Server bilan bog'lanib bo'lmadi";
    } finally {
      mikrofon.disabled = false;
    }
  }

  // Header chip: bazadagi moddalar soni + ochiq hisoblagich
  fetch("/health")
    .then((r) => r.json())
    .then((d) => {
      const chip = document.getElementById("baza-chip");
      if (chip && d.moddalar_soni) chip.textContent = d.moddalar_soni + " modda · lex.uz";
      const hisob = document.getElementById("hisoblagich");
      if (hisob && d.javoblar_soni > 0) {
        hisob.textContent = "📊 Shu paytgacha " + d.javoblar_soni + " ta savolga javob berildi";
      }
    })
    .catch(() => {});

  savolInput.addEventListener("input", () => {
    savolInput.style.height = "auto";
    savolInput.style.height = Math.min(savolInput.scrollHeight, 140) + "px";
  });
  savolInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      forma.requestSubmit();
    }
  });

  forma.addEventListener("submit", async (e) => {
    e.preventDefault();
    const savol = savolInput.value.trim();
    const fayl = faylInput.files[0] || null;
    if (!savol && !fayl) return;

    const shartnomaRejimi = fayl && shartnomaBelgi.checked;
    userXabarQosh(
      fayl
        ? `${shartnomaRejimi ? "📋" : "📎"} ${fayl.name}${savol ? " — " + savol : ""}`
        : savol
    );
    savolInput.value = "";
    savolInput.style.height = "auto";
    faylInput.value = "";
    faylNomi.textContent = "";
    shartnomaTanlov.hidden = true;
    shartnomaBelgi.checked = false;

    const kutish = kutishQosh();
    yuborTugma.disabled = true;
    try {
      let javob;
      if (shartnomaRejimi) {
        const fd = new FormData();
        fd.append("fayl", fayl);
        javob = await fetch("/api/shartnoma", {
          method: "POST",
          headers: foydalanuvchiId ? { "X-Foydalanuvchi-Id": foydalanuvchiId } : {},
          body: fd,
        });
        const d = await javob.json();
        kutish.remove();
        if (!javob.ok) {
          botXatoQosh(d.detail || "Shartnomani tahlil qilib bo'lmadi.");
          return;
        }
        shartnomaJavobQosh(d);
        return;
      }
      if (fayl) {
        const fd = new FormData();
        fd.append("fayl", fayl);
        fd.append("savol", savol);
        fd.append("rejim", rejim);
        javob = await fetch("/api/hujjat", {
          method: "POST",
          headers: foydalanuvchiId ? { "X-Foydalanuvchi-Id": foydalanuvchiId } : {},
          body: fd,
        });
      } else {
        const headers = { "Content-Type": "application/json" };
        if (foydalanuvchiId) headers["X-Foydalanuvchi-Id"] = foydalanuvchiId;
        javob = await fetch("/api/chat", {
          method: "POST",
          headers,
          body: JSON.stringify({ savol, rejim, tarix: tarix.slice(-6) }),
        });
      }
      const data = await javob.json();
      kutish.remove();
      if (!javob.ok) {
        botXatoQosh(data.detail || "Xatolik yuz berdi. Qaytadan urinib ko'ring.");
        return;
      }
      botJavobQosh(data, savol);
      tarix.push({ rol: "user", matn: savol || (fayl ? "Hujjat yuklandi: " + fayl.name : "") });
      tarix.push({ rol: "assistant", matn: data.tavsiya || "" });
    } catch (err) {
      kutish.remove();
      botXatoQosh("Server bilan bog'lanib bo'lmadi: " + err.message);
    } finally {
      yuborTugma.disabled = false;
      savolInput.focus();
    }
  });

  // ---- Render funksiyalari ----

  function avatarYarat() {
    const a = el("div", "avatar");
    const img = document.createElement("img");
    img.src = "/static/logo-192.png";
    img.alt = "";
    a.appendChild(img);
    return a;
  }

  function el(tag, cls, matn) {
    const d = document.createElement(tag);
    if (cls) d.className = cls;
    if (matn !== undefined) d.textContent = matn;
    return d;
  }

  // "**qalin**" belgilarini xavfsiz render qilish (faqat textContent orqali,
  // HTML kiritilmaydi). Ro'yxat qatorlari uchun "- " prefiksi saqlanadi.
  function qalinFormat(matn) {
    const p = el("p");
    const qismlar = matn.split("**");
    qismlar.forEach((qism, i) => {
      if (!qism) return;
      if (i % 2 === 1) p.appendChild(el("b", "", qism));
      else p.appendChild(document.createTextNode(qism));
    });
    return p;
  }

  function userXabarQosh(matn) {
    const x = el("div", "xabar user");
    const ich = el("div", "xabar-ich");
    ich.appendChild(el("p", "", matn));
    x.appendChild(ich);
    chat.appendChild(x);
    pastgaSur();
  }

  function kutishQosh() {
    const x = el("div", "xabar bot");
    x.appendChild(avatarYarat());
    const ich = el("div", "xabar-ich");
    const k = el("span", "kutish");
    for (let i = 0; i < 3; i++) k.appendChild(el("span"));
    ich.appendChild(k);
    x.appendChild(ich);
    chat.appendChild(x);
    pastgaSur();
    return x;
  }

  function botXatoQosh(matn) {
    const x = el("div", "xabar bot");
    x.appendChild(avatarYarat());
    const ich = el("div", "xabar-ich");
    ich.appendChild(el("p", "xato-xabar", "⚠️ " + matn));
    x.appendChild(ich);
    chat.appendChild(x);
    pastgaSur();
  }

  // Uch qismli javobni render qilish.
  // MUHIM: modda matni serverdan (bazadan) kelganicha ko'rsatiladi — textContent
  // orqali, hech qanday o'zgartirishsiz.
  function botJavobQosh(data, savol) {
    const x = el("div", "xabar bot");
    x.appendChild(avatarYarat());
    const ich = el("div", "xabar-ich");

    // 1-QISM: QONUN MODDASI
    if (data.moddalar && data.moddalar.length) {
      ich.appendChild(el("div", "qism-sarlavha", "1 · Qonun moddasi"));
      data.moddalar.forEach((m) => {
        const karta = el("div", "modda-karta");
        karta.appendChild(el("div", "qonun-nomi", m.qonun_nomi));
        karta.appendChild(el("div", "modda-sarlavha", m.sarlavha || m.modda_raqami));
        if (m.holat === "verified" && m.matn) {
          karta.appendChild(el("div", "modda-matn", m.matn));
        } else {
          karta.appendChild(
            el("div", "modda-matn", "Modda matni hali tekshirilmoqda — rasmiy matnni lex.uz'da ko'ring.")
          );
        }
        const past = el("div", "modda-past");
        const havola = el("a", "", "lex.uz'da ochish ↗");
        havola.href = m.lex_url;
        havola.target = "_blank";
        havola.rel = "noopener";
        past.appendChild(havola);
        past.appendChild(
          el("span", "belgi " + m.holat, m.holat === "verified" ? "✓ tekshirilgan" : "tekshirilmoqda")
        );
        karta.appendChild(past);
        ich.appendChild(karta);
      });
    }

    // 2-QISM: UMUMIY TAVSIYA
    ich.appendChild(el("div", "qism-sarlavha", (data.moddalar && data.moddalar.length ? "2" : "•") + " · Umumiy tavsiya"));
    const tavsiya = el("div", "tavsiya");
    (data.tavsiya || "").split(/\n+/).forEach((p) => {
      if (p.trim()) tavsiya.appendChild(qalinFormat(p.trim()));
    });
    ich.appendChild(tavsiya);

    // 3-QISM: QAYERGA MUROJAAT QILISH
    if (data.murojaat) {
      ich.appendChild(el("div", "qism-sarlavha", (data.moddalar && data.moddalar.length ? "3" : "•") + " · Qayerga murojaat qilish"));
      const o = data.murojaat;
      const karta = el("div", "organ-karta");
      karta.appendChild(el("div", "organ-nomi", "🏛 " + o.nomi));
      if (o.tavsif) karta.appendChild(el("div", "organ-qator", o.tavsif));
      karta.appendChild(el("div", "organ-qator", "📍 " + o.manzil));
      if (o.ish_vaqti) karta.appendChild(el("div", "organ-qator", "🕒 " + o.ish_vaqti));
      karta.appendChild(el("div", "organ-qator", "📞 " + o.telefon));
      const saytQator = el("div", "organ-qator");
      const sayt = el("a", "", o.sayt.replace(/^https?:\/\//, ""));
      sayt.href = o.sayt;
      sayt.target = "_blank";
      sayt.rel = "noopener";
      saytQator.append("🌐 ", sayt);
      if (o.onlayn_murojaat && o.onlayn_murojaat !== o.sayt) {
        const onlayn = el("a", "", "onlayn murojaat");
        onlayn.href = o.onlayn_murojaat;
        onlayn.target = "_blank";
        onlayn.rel = "noopener";
        saytQator.append(" · ", onlayn);
      }
      if (o.hududiy_havola && o.hududiy_havola !== o.sayt) {
        const hududiy = el("a", "", "hududiy bo'linmalar");
        hududiy.href = o.hududiy_havola;
        hududiy.target = "_blank";
        hududiy.rel = "noopener";
        saytQator.append(" · ", hududiy);
      }
      karta.appendChild(saytQator);
      if (o.kontakt_holati !== "verified") {
        karta.appendChild(el("div", "organ-qator xato-xabar", "ℹ️ Kontakt ma'lumotlari tekshirilmoqda"));
      }
      ich.appendChild(karta);
    }

    // HUJJAT YO'LI — fayl yuklanganda: nimani tekshirish va qanday bekor qildirish
    if (data.hujjat_yoli) hujjatYoliQosh(ich, data.hujjat_yoli);

    // ARIZA QORALAMASI (faqat asosli javoblar uchun)
    if (data.javob_topildi && data.moddalar && data.moddalar.length) {
      ich.appendChild(arizaBlokYarat(data, savol || ""));
    }

    ich.appendChild(el("div", "disclaimer", data.disclaimer || ""));
    x.appendChild(ich);
    chat.appendChild(x);
    pastgaSur();
  }

  // Hujjat bilan NIMA QILISH kerakligi: turi, muddat, tekshirish ro'yxati va
  // bekor qildirish yo'li. AI'siz — hammasi qonun matnidan.
  //
  // Muddat eng tepada: odam avval "menda qancha vaqt bor?" degan savolga
  // javob oladi. Tur taxminiy bo'lsa buni yashirmaymiz — noto'g'ri tur
  // noto'g'ri muddat degani va bu qaytarib bo'lmaydigan zarar.
  function hujjatYoliQosh(ich, y) {
    ich.appendChild(el("div", "qism-sarlavha", "📑 " + y.turi_nomi));
    if (y.ishonch === "taxmin" && y.turi !== "boshqa") {
      ich.appendChild(el("div", "hujjat-taxmin",
        "Turi taxminan aniqlandi — quyidagi muddat sizga tegishli ekanini " +
        "hujjatning o'zidan tekshiring."));
    }

    if (y.muddat) {
      const m = el("div", "hujjat-muddat");
      m.appendChild(el("strong", "", "⏳ Shikoyat muddati: " + y.muddat));
      if (y.muddat_izohi) m.appendChild(el("div", "hujjat-muddat-izoh", y.muddat_izohi));
      ich.appendChild(m);
    } else if (y.muddat_izohi) {
      ich.appendChild(el("div", "hujjat-muddat-izoh", "⏳ " + y.muddat_izohi));
    }

    // Ikkala ro'yxat bir xil tuzilishda — faqat sarlavhasi va raqamlash uslubi farqli
    [
      ["🔍 Hujjatda nimani tekshirish kerak", y.tekshiruvlar, true],
      ["⚖️ Qanday bekor qildiriladi", y.bekor_yoli, false],
    ].forEach(([sarlavha, qatorlar, nomlimi]) => {
      if (!qatorlar || !qatorlar.length) return;
      ich.appendChild(el("div", "qism-sarlavha kichik", sarlavha));
      const royxat = el("ol", "hujjat-royxat");
      qatorlar.forEach((q) => {
        const li = el("li");
        if (nomlimi) li.appendChild(el("div", "hujjat-nom", q.nomi));
        li.appendChild(qalinFormat(nomlimi ? q.izoh : q.matn));
        if (q.modda) {
          const havola = el("a", "hujjat-modda",
            "📖 " + q.modda.modda_raqami + " — " + q.modda.qonun_nomi);
          havola.href = q.modda.lex_url;
          havola.target = "_blank";
          havola.rel = "noopener";
          li.appendChild(havola);
        }
        royxat.appendChild(li);
      });
      ich.appendChild(royxat);
    });

    if (y.ogohlantirish) ich.appendChild(el("div", "disclaimer", "⚠️ " + y.ogohlantirish));
  }

  // Shartnoma tahlili: umumiy mazmun -> bandlar (xavf bo'yicha) -> xulosa.
  // Uch qismli javobdan farqli tuzilma: odam shartnomadan "qaysi bandi menga
  // zarar keltiradi?" degan savolga javob kutadi.
  const XAVF_BELGI = { qizil: "🔴", sariq: "🟡", yashil: "🟢" };
  const XAVF_NOMI = {
    qizil: "Qonunga zid",
    sariq: "Siz uchun noqulay",
    yashil: "E'tibor bering",
  };
  const TUR_NOMI = {
    mehnat: "Mehnat shartnomasi",
    ijara: "Ijara shartnomasi",
    kredit: "Kredit / qarz shartnomasi",
    "oldi-sotdi": "Oldi-sotdi shartnomasi",
    xizmat: "Xizmat ko'rsatish shartnomasi",
    boshqa: "Shartnoma",
  };

  function shartnomaJavobQosh(d) {
    const x = el("div", "xabar bot");
    x.appendChild(avatarYarat());
    const ich = el("div", "xabar-ich");

    // Umumiy mazmun
    ich.appendChild(el("div", "qism-sarlavha", "📋 " + (TUR_NOMI[d.shartnoma_turi] || TUR_NOMI.boshqa)));
    const mazmun = el("div", "shartnoma-mazmun");
    [
      ["Tomonlar", d.umumiy_mazmun.tomonlar],
      ["Predmet", d.umumiy_mazmun.predmet],
      ["Summa", d.umumiy_mazmun.summa],
      ["Muddat", d.umumiy_mazmun.muddat],
    ].forEach(([nomi, qiymat]) => {
      if (!qiymat) return;
      const q = el("div", "mazmun-qator");
      q.append(el("span", "mazmun-nomi", nomi), el("span", "", qiymat));
      mazmun.appendChild(q);
    });
    ich.appendChild(mazmun);

    // Bandlar
    if (d.bandlar.length) {
      const qizil = d.bandlar.filter((b) => b.xavf === "qizil").length;
      const sarlavha =
        "⚠️ Diqqat qiling — " + d.bandlar.length + " ta band" +
        (d.bandlar_soni ? " (jami " + d.bandlar_soni + " tadan)" : "") +
        (qizil ? ", shundan " + qizil + " tasi qonunga zid" : "");
      ich.appendChild(el("div", "qism-sarlavha", sarlavha));

      d.bandlar.forEach((b) => {
        const karta = el("div", "band-karta " + b.xavf);
        const bosh = el("div", "band-bosh");
        bosh.append(
          el("span", "band-belgi", XAVF_BELGI[b.xavf] || "🟡"),
          el("span", "band-raqam", b.band),
          el("span", "band-mazmun", b.mazmuni)
        );
        karta.appendChild(bosh);
        karta.appendChild(el("div", "band-daraja", XAVF_NOMI[b.xavf] || ""));
        karta.appendChild(el("div", "band-izoh", b.izoh));

        // Modda — bazadagi ASL matn, o'zgartirilmagan
        if (b.modda) {
          const modda = el("details", "band-modda");
          const sarl = el("summary", "", "📖 " + b.modda.qonun_nomi + ", " + b.modda.modda_raqami);
          modda.appendChild(sarl);
          modda.appendChild(el("div", "modda-matn", b.modda.matn));
          const havola = el("a", "", "lex.uz'da ochish ↗");
          havola.href = b.modda.lex_url;
          havola.target = "_blank";
          havola.rel = "noopener";
          modda.appendChild(havola);
          karta.appendChild(modda);
        }
        ich.appendChild(karta);
      });
    } else {
      ich.appendChild(el("div", "tavsiya", "Diqqat talab qiladigan band topilmadi."));
    }

    // Xulosa
    if (d.xulosa) {
      ich.appendChild(el("div", "qism-sarlavha", "✅ Xulosa"));
      const xulosa = el("div", "tavsiya");
      d.xulosa.split(/\n+/).forEach((p) => {
        if (p.trim()) xulosa.appendChild(qalinFormat(p.trim()));
      });
      ich.appendChild(xulosa);
    }

    ich.appendChild(el("div", "disclaimer", d.disclaimer || ""));
    x.appendChild(ich);
    chat.appendChild(x);
    pastgaSur();
  }

  // Ariza qoralamasi bloki: tugma -> forma (faqat F.I.Sh majburiy) -> tayyor matn
  function arizaBlokYarat(data, savol) {
    const blok = el("div", "ariza-blok");
    const ochTugma = el("button", "ariza-och", "📄 Ariza qoralamasini tuzish");
    ochTugma.type = "button";
    blok.appendChild(ochTugma);

    const forma = el("form", "ariza-forma yashirin");
    const fishInput = el("input");
    fishInput.placeholder = "F.I.Sh (majburiy)";
    fishInput.required = true;
    fishInput.maxLength = 200;
    const manzilInput = el("input");
    manzilInput.placeholder = "Manzilingiz (ixtiyoriy)";
    manzilInput.maxLength = 300;
    const telefonInput = el("input");
    telefonInput.placeholder = "Telefon (ixtiyoriy)";
    telefonInput.maxLength = 50;
    const tuzTugma = el("button", "ariza-tuz", "Tuzish");
    tuzTugma.type = "submit";
    forma.append(fishInput, manzilInput, telefonInput, tuzTugma);
    blok.appendChild(forma);

    const natija = el("div", "ariza-natija yashirin");
    blok.appendChild(natija);

    ochTugma.addEventListener("click", () => {
      forma.classList.toggle("yashirin");
      if (!forma.classList.contains("yashirin")) fishInput.focus();
    });

    forma.addEventListener("submit", async (e) => {
      e.preventDefault();
      tuzTugma.disabled = true;
      try {
        const javob = await fetch("/api/ariza", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            fish: fishInput.value.trim(),
            vaziyat: savol,
            modda_idlari: data.moddalar.map((m) => m.id),
            murojaat_mavzusi: data.murojaat_mavzusi || "umumiy",
            manzil: manzilInput.value.trim(),
            telefon: telefonInput.value.trim(),
          }),
        });
        const j = await javob.json();
        natija.textContent = "";
        if (!javob.ok) {
          natija.appendChild(el("p", "xato-xabar", j.detail || "Ariza tuzishda xatolik"));
        } else {
          const matnMaydon = el("textarea", "ariza-matn");
          matnMaydon.value = j.matn;
          matnMaydon.rows = 14;
          matnMaydon.readOnly = true;
          const yuklab = el("button", "ariza-yuklab", "⬇ Yuklab olish (.txt)");
          yuklab.type = "button";
          yuklab.addEventListener("click", () => {
            const blob = new Blob([matnMaydon.value], { type: "text/plain;charset=utf-8" });
            const a = document.createElement("a");
            a.href = URL.createObjectURL(blob);
            a.download = j.fayl_nomi || "ariza.txt";
            a.click();
            URL.revokeObjectURL(a.href);
          });
          natija.append(matnMaydon, yuklab);
        }
        natija.classList.remove("yashirin");
        pastgaSur();
      } catch (err) {
        natija.textContent = "";
        natija.appendChild(el("p", "xato-xabar", "Server bilan bog'lanib bo'lmadi: " + err.message));
        natija.classList.remove("yashirin");
      } finally {
        tuzTugma.disabled = false;
      }
    });

    return blok;
  }

  function pastgaSur() {
    window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
  }
})();
