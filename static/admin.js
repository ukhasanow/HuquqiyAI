// Admin sahifa mantiqi: parol bilan kirish, moddalarni ko'rish/qo'shish/tahrirlash
(function () {
  let parol = "";

  const parolKarta = document.getElementById("parol-karta");
  const royxatKarta = document.getElementById("royxat-karta");
  const formaKarta = document.getElementById("forma-karta");
  const royxat = document.getElementById("moddalar-royxati");
  const formaXabar = document.getElementById("forma-xabar");

  document.getElementById("kirish-tugma").addEventListener("click", kirish);
  document.getElementById("parol").addEventListener("keydown", (e) => {
    if (e.key === "Enter") kirish();
  });
  document.getElementById("saqlash-tugma").addEventListener("click", saqlash);

  async function kirish() {
    parol = document.getElementById("parol").value;
    const j = await fetch("/api/admin/moddalar", { headers: { "X-Admin-Parol": parol } });
    if (!j.ok) {
      document.getElementById("parol-xato").textContent = "Noto'g'ri parol";
      return;
    }
    parolKarta.hidden = true;
    royxatKarta.hidden = false;
    formaKarta.hidden = false;
    renderRoyxat(await j.json());
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
