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

  faylInput.addEventListener("change", () => {
    faylNomi.textContent = faylInput.files.length ? faylInput.files[0].name : "";
  });

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

    userXabarQosh(fayl ? `📎 ${fayl.name}${savol ? " — " + savol : ""}` : savol);
    savolInput.value = "";
    savolInput.style.height = "auto";
    faylInput.value = "";
    faylNomi.textContent = "";

    const kutish = kutishQosh();
    yuborTugma.disabled = true;
    try {
      let javob;
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

    // ARIZA QORALAMASI (faqat asosli javoblar uchun)
    if (data.javob_topildi && data.moddalar && data.moddalar.length) {
      ich.appendChild(arizaBlokYarat(data, savol || ""));
    }

    ich.appendChild(el("div", "disclaimer", data.disclaimer || ""));
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
