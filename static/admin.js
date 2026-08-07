// Admin sahifa mantiqi: parol bilan kirish, moddalarni ko'rish/qo'shish/tahrirlash
(function () {
  let parol = "";

  const parolKarta = document.getElementById("parol-karta");
  const statistikaKarta = document.getElementById("statistika-karta");
  const botKarta = document.getElementById("bot-karta");
  const royxatKarta = document.getElementById("royxat-karta");
  const formaKarta = document.getElementById("forma-karta");
  const royxat = document.getElementById("moddalar-royxati");
  const formaXabar = document.getElementById("forma-xabar");

  document.getElementById("kirish-tugma").addEventListener("click", kirish);
  document.getElementById("parol").addEventListener("keydown", (e) => {
    if (e.key === "Enter") kirish();
  });
  document.getElementById("saqlash-tugma").addEventListener("click", saqlash);
  document.getElementById("bot-yangila-tugma").addEventListener("click", botHolatiYukla);

  async function kirish() {
    parol = document.getElementById("parol").value;
    const j = await fetch("/api/admin/moddalar", { headers: { "X-Admin-Parol": parol } });
    if (!j.ok) {
      document.getElementById("parol-xato").textContent = "Noto'g'ri parol";
      return;
    }
    parolKarta.hidden = true;
    statistikaKarta.hidden = false;
    botKarta.hidden = false;
    royxatKarta.hidden = false;
    formaKarta.hidden = false;
    renderRoyxat(await j.json());
    statistikaYukla();
    botHolatiYukla();
  }

  // ---- Telegram bot holati ----
  //
  // Bot javob bermay qolganda sabab shu yerda ko'rinadi: webhook Telegram'da
  // haqiqatan o'rnatilganmi, navbatda yetkazilmagan savol turibdimi va
  // Telegram oxirgi marta nima xato qaytargan.

  async function botHolatiYukla() {
    const xulosa = document.getElementById("bot-xulosa");
    const idish = document.getElementById("bot-holati");
    xulosa.className = "";
    xulosa.textContent = "Tekshirilmoqda…";
    idish.innerHTML = "";
    try {
      const j = await fetch("/api/admin/telegram", { headers: { "X-Admin-Parol": parol } });
      if (j.status === 404) {
        xulosa.className = "xato-xabar";
        xulosa.textContent = "Bot sozlanmagan — TELEGRAM_BOT_TOKEN berilmagan.";
        return;
      }
      if (!j.ok) {
        const d = await j.json().catch(() => ({}));
        xulosa.className = "xato-xabar";
        xulosa.textContent = d.detail || "Holatni olib bo'lmadi (" + j.status + ").";
        return;
      }
      renderBotHolati(await j.json());
    } catch (e) {
      xulosa.className = "xato-xabar";
      xulosa.textContent = "Serverga ulanib bo'lmadi.";
    }
  }

  function renderBotHolati(d) {
    const xulosa = document.getElementById("bot-xulosa");
    const kutilgan = d.kutilgan_url || "";
    const navbat = d.pending_update_count || 0;

    let matn, sinf;
    if (!d.url) {
      matn = "Webhook o'rnatilmagan — Telegram xabarlarni hech qayerga yubormayapti.";
      sinf = "xato-xabar";
    } else if (kutilgan && d.url !== kutilgan) {
      matn = "Webhook boshqa manzilga o'rnatilgan — xabarlar bu xizmatga kelmayapti.";
      sinf = "xato-xabar";
    } else if (d.last_error_message) {
      matn = "Telegram oxirgi yetkazishda xato oldi: " + d.last_error_message;
      sinf = "xato-xabar";
    } else if (navbat > 0) {
      matn = navbat + " ta savol navbatda — xizmat uyquda yoki band bo'lgan, uyg'onishi bilan javob beriladi.";
      sinf = "";
    } else {
      matn = "Hammasi joyida — webhook o'rnatilgan, navbat bo'sh.";
      sinf = "ok-xabar";
    }
    xulosa.className = sinf;
    xulosa.textContent = matn;

    const idish = document.getElementById("bot-holati");
    const qatorlar = [
      ["Webhook manzili", d.url || "—"],
      ["Kutilgan manzil", kutilgan || "—"],
      ["Navbatdagi savollar", navbat],
      ["Maxfiy sir tekshiruvi", d.sir_yoqilgan ? "yoqilgan" : "o'chiq"],
      ["Oxirgi xato", d.last_error_message || "yo'q"],
      ["Oxirgi xato vaqti", sanaMatni(d.last_error_date)],
    ];
    idish.innerHTML =
      '<div class="manba-nomi">Webhook tafsilotlari</div>' +
      qatorlar
        .map(([n, q]) =>
          '<div class="manba-qator"><span>' + esc(n) + "</span><b>" + esc(String(q)) + "</b></div>")
        .join("");
  }

  // Telegram vaqtni unix soniyada beradi.
  function sanaMatni(unix) {
    if (!unix) return "—";
    return new Date(unix * 1000).toLocaleString("uz-UZ");
  }

  // ---- Statistika ----

  async function statistikaYukla() {
    try {
      const j = await fetch("/api/admin/statistika", { headers: { "X-Admin-Parol": parol } });
      if (!j.ok) return;
      renderStatistika(await j.json());
    } catch (e) { /* statistika yuklanmasa ham panel ishlayveradi */ }
  }

  function renderStatistika(s) {
    // Yuqori kartalar: jami, topildi/topilmadi, oddiy/pro, foydalanuvchilar
    const kartalar = document.getElementById("stat-kartalar");
    kartalar.innerHTML = "";
    const oddiy = (s.rejimlar && s.rejimlar.oddiy) || 0;
    const pro = (s.rejimlar && s.rejimlar.pro) || 0;
    const sayt = (s.manbalar && s.manbalar.sayt) || 0;
    const bot = (s.manbalar && s.manbalar.bot) || 0;
    const foiz = (qism, butun) => (butun ? Math.round((qism / butun) * 100) + "%" : "—");
    const kunlik = s.kunlik_30 || [];
    const bugun = kunlik.length ? kunlik[kunlik.length - 1] : { jami: 0 };
    const oxirgi7 = kunlik.slice(-7);
    const hafta = oxirgi7.reduce((y, k) => y + (k.jami || 0), 0);
    const oy = kunlik.reduce((y, k) => y + (k.jami || 0), 0);
    const engFaol = kunlik.reduce((a, b) => ((b.jami || 0) > (a.jami || 0) ? b : a),
                                  { jami: 0, sana: "—" });
    const jarimalar = s.jarima_tekshiruvlari || 0;

    [
      ["Jami so'rovlar", s.jami_sorovlar],
      ["Javob topilish ulushi", foiz(s.javob_topildi, s.jami_sorovlar)],
      ["Javob topildi / topilmadi", s.javob_topildi + " / " + s.javob_topilmadi],
      ["Bugun", bugun.jami || 0],
      ["Oxirgi 7 kun", hafta],
      ["Kuniga o'rtacha (30 kun)", (oy / 30).toFixed(1)],
      ["Eng faol kun", (engFaol.jami || 0) + " · " + (engFaol.sana || "—")],
      ["Sayt / Telegram bot", sayt + " / " + bot],
      ["🎤 Ovozli savol / 🔊 javob", (s.ovozli_sorovlar || 0) + " / " + (s.ovozli_javoblar || 0)],
      ["📋 Shartnoma tahlillari", s.shartnoma_tahlillari || 0],
      ["🚗 Jarima tekshiruvi", jarimalar],
      [
        "🚗 Asos topilgan jarimalar",
        (s.jarima_asos_topildi || 0) + " (" + foiz(s.jarima_asos_topildi || 0, jarimalar) + ")",
      ],
      ["Oddiy / Pro", oddiy + " / " + pro],
      [
        "Foydalanuvchilar (sayt / bot)",
        (s.sayt_foydalanuvchilar_soni || 0) + " / " + (s.bot_foydalanuvchilar_soni || 0),
      ],
    ].forEach(([nomi, qiymat]) => {
      const k = document.createElement("div");
      k.className = "stat-karta";
      k.innerHTML = '<div class="stat-qiymat">' + esc(String(qiymat)) + '</div><div class="stat-nomi">' + esc(nomi) + "</div>";
      kartalar.appendChild(k);
    });

    // 30 kunlik grafik — oddiy CSS ustunlar, tashqi kutubxonasiz.
    // Ustun ichida bot ulushi alohida rangda: sayt va bot o'sishi bir xil
    // emas va buni bitta umumiy ustundan ko'rib bo'lmaydi.
    const grafik = document.getElementById("stat-grafik");
    grafik.innerHTML = "";
    const maks = Math.max(1, ...s.kunlik_30.map((k) => k.jami));
    s.kunlik_30.forEach((k) => {
      const bot = k.bot || 0;
      const ustun = document.createElement("div");
      ustun.className = "stat-ustun";
      ustun.title =
        k.sana + ": " + k.jami + " so'rov (" + k.topildi + " topildi)" +
        (bot ? " · bot: " + bot : "");
      const bar = document.createElement("div");
      bar.className = "stat-bar";
      bar.style.height = Math.round((k.jami / maks) * 100) + "%";
      if (k.jami === 0) bar.classList.add("bosh");
      if (bot && k.jami) {
        const botUlush = document.createElement("div");
        botUlush.className = "stat-bar-bot";
        botUlush.style.height = Math.round((bot / k.jami) * 100) + "%";
        bar.appendChild(botUlush);
      }
      ustun.appendChild(bar);
      grafik.appendChild(ustun);
    });

    renderManbalar(s);

    // Mavzular kesimi — gorizontal barlar
    const mavzular = document.getElementById("stat-mavzular");
    mavzular.innerHTML = "";
    const juftlar = Object.entries(s.mavzular || {}).sort((a, b) => b[1] - a[1]);
    if (!juftlar.length) mavzular.textContent = "Hozircha ma'lumot yo'q";
    const mavzuMaks = Math.max(1, ...juftlar.map(([, n]) => n));
    juftlar.forEach(([mavzu, n]) => {
      const q = document.createElement("div");
      q.className = "mavzu-qator";
      const nom = document.createElement("span");
      nom.className = "mavzu-nomi";
      nom.textContent = mavzu;
      const bar = document.createElement("span");
      bar.className = "mavzu-bar";
      bar.style.width = Math.round((n / mavzuMaks) * 100) + "%";
      const son = document.createElement("span");
      son.className = "mavzu-son";
      son.textContent = n;
      q.append(nom, bar, son);
      mavzular.appendChild(q);
    });

    // Shartnoma turlari — qaysi shartnoma ko'proq tekshirilayotgani
    const turlar = document.getElementById("stat-shartnomalar");
    turlar.innerHTML = "";
    const turJuftlar = Object.entries(s.shartnoma_turlari || {}).sort((a, b) => b[1] - a[1]);
    if (!turJuftlar.length) {
      turlar.textContent = "Hozircha shartnoma tahlil qilinmagan";
    }
    turJuftlar.forEach(([turi, n]) => {
      const q = document.createElement("div");
      q.className = "manba-qator";
      q.innerHTML = "<span>" + esc(turi) + "</span><b>" + esc(String(n)) + "</b>";
      turlar.appendChild(q);
    });

    // Topilmagan savollar ro'yxati
    const topilmagan = document.getElementById("stat-topilmagan");
    topilmagan.innerHTML = "";
    if (!s.topilmagan_savollar.length) {
      topilmagan.textContent = "Topilmagan savollar yo'q 🎉";
    }
    s.topilmagan_savollar.slice(0, 50).forEach((t) => {
      const q = document.createElement("div");
      q.className = "topilmagan-qator";
      q.innerHTML = '<span class="topilmagan-sana">' + esc(t.sana) + "</span> " + esc(t.savol);
      topilmagan.appendChild(q);
    });
  }

  // Sayt va bot yonma-yon: qaysi kanal ko'proq ishlatilayotgani va qaysi
  // birida javob topilmayotgani darhol ko'rinsin.
  function renderManbalar(s) {
    const idish = document.getElementById("stat-manbalar");
    idish.innerHTML = "";
    const kesim = s.manba_kesimi || {};
    [
      ["🌐 Sayt", kesim.sayt || {}, s.sayt_foydalanuvchilar_soni || 0, null],
      ["🤖 Telegram bot", kesim.bot || {}, s.bot_foydalanuvchilar_soni || 0, s.ovozli_javoblar || 0],
    ].forEach(([nomi, k, foydalanuvchilar, ovozliJavoblar]) => {
      const jami = k.jami || 0;
      const qatorlar = [
        ["So'rovlar", jami],
        ["Javob topildi", (k.topildi || 0) + (jami ? " (" + Math.round(((k.topildi || 0) / jami) * 100) + "%)" : "")],
        ["Foydalanuvchilar", foydalanuvchilar],
        ["Oddiy / Pro", (k.oddiy || 0) + " / " + (k.pro || 0)],
        ["🎤 Ovozli savol", k.ovozli || 0],
      ];
      if (ovozliJavoblar !== null) qatorlar.push(["🔊 Ovozli javob", ovozliJavoblar]);

      const blok = document.createElement("div");
      blok.className = "manba-blok";
      blok.innerHTML =
        '<div class="manba-nomi">' + esc(nomi) + "</div>" +
        qatorlar
          .map(([n, q]) =>
            '<div class="manba-qator"><span>' + esc(n) + "</span><b>" + esc(String(q)) + "</b></div>")
          .join("");
      idish.appendChild(blok);
    });
  }

  function renderRoyxat(moddalar) {
    royxat.innerHTML = "";
    moddalar.forEach((m) => {
      const q = document.createElement("div");
      q.className = "modda-royxat-qator";
      const chap = document.createElement("div");
      chap.innerHTML =
        "<b>" + esc(m.id) + "</b> — " + esc(m.sarlavha || m.modda_raqami) +
        ' <span class="belgi ' + m.holat + '">' +
        (m.holat === "verified" ? "✓ tekshirilgan" : "tekshirilmoqda") + "</span>";
      const tugma = document.createElement("button");
      tugma.className = "tahrir-tugma";
      tugma.textContent = "Tahrirlash";
      tugma.addEventListener("click", () => formagaYukla(m));
      q.append(chap, tugma);
      royxat.appendChild(q);
    });
  }

  function formagaYukla(m) {
    document.getElementById("forma-sarlavha").textContent = "✏️ Moddani tahrirlash: " + m.id;
    document.getElementById("f-id").value = m.id;
    document.getElementById("f-qonun").value = m.qonun_nomi;
    document.getElementById("f-raqam").value = m.modda_raqami;
    document.getElementById("f-sarlavha").value = m.sarlavha || "";
    document.getElementById("f-matn").value = m.matn || "";
    document.getElementById("f-url").value = m.lex_url || "";
    document.getElementById("f-teglar").value = (m.teglar || []).join(", ");
    document.getElementById("f-holat").value = m.holat;
    formaKarta.scrollIntoView({ behavior: "smooth" });
  }

  async function saqlash() {
    formaXabar.textContent = "";
    const modda = {
      id: document.getElementById("f-id").value.trim(),
      qonun_nomi: document.getElementById("f-qonun").value.trim(),
      modda_raqami: document.getElementById("f-raqam").value.trim(),
      sarlavha: document.getElementById("f-sarlavha").value.trim(),
      matn: document.getElementById("f-matn").value.trim(),
      lex_url: document.getElementById("f-url").value.trim(),
      teglar: document.getElementById("f-teglar").value.split(",").map((t) => t.trim()).filter(Boolean),
      holat: document.getElementById("f-holat").value,
    };
    if (!modda.id || !modda.qonun_nomi || !modda.modda_raqami) {
      formaXabar.className = "xato-xabar";
      formaXabar.textContent = "ID, qonun nomi va modda raqami majburiy";
      return;
    }
    const j = await fetch("/api/admin/moddalar", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Admin-Parol": parol },
      body: JSON.stringify(modda),
    });
    if (!j.ok) {
      const d = await j.json().catch(() => ({}));
      formaXabar.className = "xato-xabar";
      formaXabar.textContent = "Xatolik: " + (d.detail || j.status);
      return;
    }
    formaXabar.className = "ok-xabar";
    formaXabar.textContent = "✓ Saqlandi";
    kirishYangila();
  }

  async function kirishYangila() {
    const j = await fetch("/api/admin/moddalar", { headers: { "X-Admin-Parol": parol } });
    if (j.ok) renderRoyxat(await j.json());
  }

  function esc(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }
})();
