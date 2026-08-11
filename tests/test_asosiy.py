# LLM'siz ishlaydigan qismlar uchun testlar:
# baza yaxlitligi, qidiruv (lotin + kirill), ariza generatori, API endpointlar.
import pytest
from fastapi.testclient import TestClient

from app import storage
from app.main import app
from app.services import retrieval
from app.services.ariza import ariza_tuz

client = TestClient(app)


# ---------- Baza yaxlitligi ----------

def test_baza_toliq():
    moddalar = storage.moddalarni_oqi()
    assert len(moddalar) >= 42
    for m in moddalar:
        assert m["id"] and m["qonun_nomi"] and m["modda_raqami"]
        assert m["lex_url"].startswith("https://lex.uz/")
        assert m["holat"] in ("verified", "needs_verification")
        if m["holat"] == "verified":
            assert len(m["matn"]) > 50, f"{m['id']} matni juda qisqa"


def test_organlar_toliq():
    organlar = storage.organlarni_oqi()
    mavzular = {o["mavzu"] for o in organlar}
    assert "umumiy" in mavzular  # fallback organ bo'lishi shart
    for o in organlar:
        assert o["nomi"] and o["manzil"]


def test_mavzular_organlar_bilan_mos():
    """LLM tanlaydigan har bir mavzu uchun bazada organ bo'lishi shart.
    Aks holda model to'g'ri mavzu qaytarsa ham foydalanuvchi "umumiy"ga tushadi."""
    from app.services.llm import MUROJAAT_MAVZULARI

    organ_mavzulari = {o["mavzu"] for o in storage.organlarni_oqi()}
    yetishmayotgan = set(MUROJAAT_MAVZULARI) - organ_mavzulari
    assert not yetishmayotgan, f"organlar.json da yo'q mavzular: {yetishmayotgan}"


def test_har_bir_kodeks_qidiruvda_topiladi():
    """Har bir qonun uchun hayotiy savol top-3 da to'g'ri kodeksni chiqarishi kerak."""
    moddalar = storage.moddalarni_oqi()
    tekshiruv = [
        ("Ish haqimni 2 oydan beri to'lashmayapti", "mehnat-"),
        ("Ajrashmoqchiman, aliment to'lamayapti", "oila-"),
        ("Muzlatgich buzuq chiqdi, pulini qaytarishadimi?", "istemol-"),
        ("Ijara shartnomam bor, uydan chiqarib yubormoqchi", "uyjoy-"),
        ("Tezlikni oshirganim uchun kamera jarima yozdi", "mjk-"),
        ("Telefonimni o'g'irlab ketishdi", "jk-"),
    ]
    for savol, prefiks in tekshiruv:
        idlar = [m["id"] for m in retrieval.moddalarni_qidir(savol, moddalar)]
        assert any(i.startswith(prefiks) for i in idlar[:3]), f"{savol!r} -> {idlar}"


def test_kundalik_murojaatlar_javobsiz_qolmaydi():
    """Jonli sinovda javobsiz qolgan, lekin juda ko'p uchraydigan savollar."""
    moddalar = storage.moddalarni_oqi()
    for savol, kutilgan in [
        ("Qo'shnim tunda juda shovqin qilyapti, nima qilsam bo'ladi?", "mjk-192"),
        ("Uy egasi garov pulimni qaytarmadi", "fuqarolik-1023"),
    ]:
        idlar = [m["id"] for m in retrieval.moddalarni_qidir(savol, moddalar)]
        assert kutilgan in idlar[:3], f"{savol!r} -> {idlar}"


def test_qidiruv_apostrofsiz_va_kirill():
    """Foydalanuvchilar apostrofsiz ("ogirlab") va kirillda yozadi —
    ikkalasi ham teglardagi apostrofli shakl bilan mos tushishi kerak."""
    moddalar = storage.moddalarni_oqi()
    for savol, kutilgan in [
        ("Telefonimni ogirlab ketishdi", "jk-169"),
        ("Иш ҳақимни тўламаяпти", "mehnat-"),
        ("Квартирадан кўчириб юборишмоқчи", "uyjoy-"),
    ]:
        idlar = [m["id"] for m in retrieval.moddalarni_qidir(savol, moddalar)]
        assert any(i.startswith(kutilgan) for i in idlar[:3]), f"{savol!r} -> {idlar}"


# ---------- Qidiruv ----------

def test_qidiruv_lotin():
    moddalar = storage.moddalarni_oqi()
    natija = retrieval.moddalarni_qidir("aliment miqdori qancha", moddalar)
    assert natija[0]["id"].startswith("oila-")


def test_qidiruv_kirill():
    moddalar = storage.moddalarni_oqi()
    natija = retrieval.moddalarni_qidir("Иш ҳақимни тўламаяпти, нима қилай?", moddalar)
    idlar = [m["id"] for m in natija]
    assert any(i.startswith("mehnat-") for i in idlar[:3])


def test_qidiruv_topilmasa_cheklangan():
    """Mos modda topilmasa butun baza emas, cheklangan namuna qaytadi —
    aks holda baza o'sgani sayin LLM so'rovi va javob vaqti o'sib boradi.

    Namuna har hujjatdan bittadan olinadi: fayldagi birinchi N yozuv bitta-ikkita
    kodeksga tiqilib qolar va savol mavzusiga umuman aloqasi bo'lmasligi mumkin edi."""
    moddalar = storage.moddalarni_oqi()
    natija = retrieval.moddalarni_qidir("xxxyyyzzz", moddalar)
    hujjatlar = {m["id"].split("-")[0] for m in moddalar}
    assert len(natija) == min(retrieval.FALLBACK_CHEGARA, len(hujjatlar))
    assert len({m["id"].split("-")[0] for m in natija}) == len(natija)


def test_qidiruv_indeksi_baza_ozgarsa_yangilanadi():
    """Kesh eskirib qolmasligi kerak: yangi ro'yxatga yangi indeks quriladi."""
    moddalar = storage.moddalarni_oqi()
    retrieval.moddalarni_qidir("aliment", moddalar)
    soxta = [dict(moddalar[0], id="test-x", teglar=["xyzqwe"], sarlavha="", matn="")]
    natija = retrieval.moddalarni_qidir("xyzqwe", soxta)
    assert natija and natija[0]["id"] == "test-x"


# ---------- Ariza generatori ----------

def _namuna_modda():
    return storage.modda_top("mehnat-253")


def _namuna_organ():
    return storage.organ_top("mehnat")


def test_ariza_tuziladi():
    matn = ariza_tuz(
        fish="Aliyev Alisher",
        vaziyat="Ish haqim 2 oydan beri to'lanmayapti.",
        moddalar=[_namuna_modda()],
        organ=_namuna_organ(),
        telefon="+998901234567",
    )
    assert "ARIZA" in matn
    assert "Aliyev Alisher" in matn
    assert "253-moddasi" in matn
    assert "_____________ (imzo)" in matn


def test_ariza_shahar_va_sanasiz():
    """Hujjatda shahar va sana bo'lmasligi kerak — yoziladigan yagona joy imzo."""
    matn = ariza_tuz(
        fish="Test Testov",
        vaziyat="Vaziyat",
        moddalar=[_namuna_modda()],
        organ=_namuna_organ(),
    )
    import datetime
    bugun = datetime.date.today()
    assert str(bugun.year) not in matn  # sana yo'q
    assert matn.count("(imzo)") == 1  # yoziladigan bitta joy — imzo
    assert "[" not in matn  # boshqa to'ldiriladigan joy yo'q


def test_ariza_fishsiz_xato():
    with pytest.raises(ValueError):
        ariza_tuz(fish="  ", vaziyat="", moddalar=[_namuna_modda()], organ=_namuna_organ())


def test_ariza_moddasiz_xato():
    with pytest.raises(ValueError):
        ariza_tuz(fish="Test", vaziyat="", moddalar=[], organ=_namuna_organ())


def test_sud_uchun_davo_arizasi():
    organ = storage.organ_top("fuqarolik")
    matn = ariza_tuz(fish="Test", vaziyat="", moddalar=[_namuna_modda()], organ=organ)
    assert "DA'VO ARIZASI" in matn


# ---------- API endpointlar ----------

def test_bosh_sahifa():
    r = client.get("/")
    assert r.status_code == 200
    assert "HuquqiyAI" in r.text


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["moddalar_soni"] >= 42


def test_ariza_endpoint():
    r = client.post("/api/ariza", json={
        "fish": "Aliyev Alisher",
        "vaziyat": "Test vaziyat",
        "modda_idlari": ["mehnat-253", "mehnat-269"],
        "murojaat_mavzusi": "mehnat",
    })
    assert r.status_code == 200
    assert "253-, 269-moddalari" in r.json()["matn"]


def test_ariza_endpoint_notogri_modda():
    r = client.post("/api/ariza", json={"fish": "Test", "modda_idlari": ["yoq-id"]})
    assert r.status_code == 422


def test_ovoz_endpointi_transkript_qaytaradi(monkeypatch):
    """Saytdagi mikrofon botdagi AYNAN shu xizmatni ishlatadi."""
    from app.services import ovoz

    monkeypatch.setattr(ovoz, "mavjud", lambda: True)
    monkeypatch.setattr(ovoz, "matnga_ogir", lambda *a, **k: "  Ish haqim berilmayapti  ")
    r = client.post("/api/ovoz", files={"fayl": ("ovoz.ogg", b"opus", "audio/ogg")})
    assert r.status_code == 200
    assert r.json() == {"matn": "Ish haqim berilmayapti"}


def test_ovoz_endpointi_sozlanmagan_bolsa_503(monkeypatch):
    from app.services import ovoz

    monkeypatch.setattr(ovoz, "mavjud", lambda: False)
    r = client.post("/api/ovoz", files={"fayl": ("ovoz.ogg", b"opus", "audio/ogg")})
    assert r.status_code == 503


def test_ovoz_endpointi_katta_fayl_rad_etadi(monkeypatch):
    from app.config import MAX_OVOZ_HAJMI
    from app.services import ovoz

    monkeypatch.setattr(ovoz, "mavjud", lambda: True)
    r = client.post("/api/ovoz",
                    files={"fayl": ("ovoz.ogg", b"x" * (MAX_OVOZ_HAJMI + 1), "audio/ogg")})
    assert r.status_code == 413


def test_ovoz_endpointi_xatoni_tushunarli_qaytaradi(monkeypatch):
    from app.services import ovoz

    monkeypatch.setattr(ovoz, "mavjud", lambda: True)
    monkeypatch.setattr(ovoz, "matnga_ogir",
                        lambda *a, **k: (_ for _ in ()).throw(ovoz.OvozXato("Matn bilan yozing.")))
    r = client.post("/api/ovoz", files={"fayl": ("ovoz.ogg", b"opus", "audio/ogg")})
    assert r.status_code == 422
    assert "Matn bilan yozing." in r.json()["detail"]


def test_admin_parolsiz_yopiq():
    assert client.get("/api/admin/moddalar").status_code == 401
    assert client.get("/api/admin/moddalar", headers={"X-Admin-Parol": "xato"}).status_code == 401


def test_health_sozlash_holatini_korsatadi():
    """Render'da disk vaqtinchalik — "fayl" qiymati statistika
    saqlanmasligini anglatadi va buni darhol ko'rish kerak."""
    d = client.get("/health").json()
    assert d["statistika_saqlash"] in ("tashqi", "fayl")
    assert d["bot"] in ("yoqilgan", "o'chiq")


def test_health_provayder_holati():
    p = client.get("/health").json()["provayderlar"]
    assert isinstance(p, list) and p, "navbat tartibi saqlanishi uchun ro'yxat bo'lishi kerak"
    for bosqich in p:
        nom, holat = bosqich["nom"], bosqich["holat"]
        assert "/" in nom, f"bosqich nomida model bo'lishi kerak: {nom}"
        assert holat in (
            "ishlayapti", "sozlanmagan", "noma'lum",
            "hisob", "kalit", "limit", "model", "band", "uzildi", "xato",
        )
    # Pulli provayder oxirida turishi shart — aks holda har savol pul yeydi
    assert p[-1]["nom"].startswith("openai/")
    assert p[0]["nom"].startswith("anthropic/")


def test_health_provayder_xatosini_eslab_qoladi():
    """Zaxira jimgina o'lib qolmasligi kerak: Anthropic krediti tugab,
    Gemini ham yiqilsa, /health ikkalasining sababini ko'rsatishi shart."""
    from app.services import llm

    asl, asl_blok = llm._holat.copy(), llm._bloklangan.copy()
    try:
        llm._holat.clear()
        llm._bloklangan.clear()
        # Haqiqiy bosqich nomlari olinadi — holat va navbat bir xil kalitni
        # ishlatishi shart, aks holda /health hech qachon to'lmaydi
        nomlar = [n for n, _, _ in llm._bosqichlar()]
        anth = next(n for n in nomlar if n.startswith("anthropic/"))
        gem = next(n for n in nomlar if n.startswith("gemini/"))

        xatolar = []
        llm._urin(anth, _yiqiluvchi("Your credit balance is too low"), xatolar)
        llm._urin(gem, _yiqiluvchi("429 RESOURCE_EXHAUSTED: quota"), xatolar)
        holat = {b["nom"]: b["holat"] for b in llm.provayderlar_holati()}
        assert holat[anth] == "hisob"
        assert holat[gem] == "limit"
        assert len(xatolar) == 2
        # Muvaffaqiyat holatni tozalaydi
        assert llm._urin(gem, lambda: {"ok": True}, xatolar) == {"ok": True}
        yangi = {b["nom"]: b["holat"] for b in llm.provayderlar_holati()}
        assert yangi[gem] == "ishlayapti"
    finally:
        llm._holat.clear(); llm._holat.update(asl)
        llm._bloklangan.clear(); llm._bloklangan.update(asl_blok)


def test_openai_sxemasi_strict_talablariga_javob_beradi():
    """OpenAI strict rejimi: har obyektda additionalProperties=false va BARCHA
    xossalar required ichida. Sxema qo'lda emas, mavjudidan o'giriladi —
    shuning uchun yangi maydon qo'shilsa ham shart buzilmasligi kerak."""
    from app.services import llm

    def tekshir(s):
        if s.get("type") == "object" or "properties" in s:
            assert s["additionalProperties"] is False
            assert set(s["required"]) == set(s["properties"])
            for ichki in s["properties"].values():
                tekshir(ichki)
        if "items" in s:
            tekshir(s["items"])
        # Strict rejim uzunlik cheklovlarini qabul qilmaydi
        assert "maxLength" not in s and "maxItems" not in s

    for sxema in (
        llm._openai_sxemaga(llm._javob_tool()["input_schema"]),
        llm._openai_sxemaga(llm._javob_tool(batafsil=True)["input_schema"]),
        llm._openai_sxemaga(llm._shartnoma_tool()["input_schema"]),
    ):
        tekshir(sxema)

    # Batafsil rejimda qo'shiladigan maydon o'girishdan keyin ham saqlanadi
    assert "xulosa" in llm._openai_sxemaga(
        llm._javob_tool(batafsil=True)["input_schema"]
    )["properties"]


def test_openai_hisob_xatosi_limitdan_ajratiladi():
    """OpenAI hisob tugaganini 429 + "quota" bilan qaytaradi. Limit deb
    tasniflansa, odam bekorga "bir daqiqadan so'ng urining" deb kutadi."""
    from app.services import llm
    from app.services.javob import _ai_xato_matni

    xato = RuntimeError("Error code: 429 - insufficient_quota: You exceeded your current quota")
    assert llm._xato_sababi(xato) == "hisob"
    assert "Administratorga" in _ai_xato_matni(xato)
    # Haqiqiy tezlik limiti esa limit bo'lib qolishi kerak
    assert llm._xato_sababi(RuntimeError("429 rate limit exceeded")) == "limit"


def test_qisqa_limitda_avtomatik_qayta_uriniladi(monkeypatch):
    """Groq bepul tierda "3 soniyadan keyin qayting" deydi — shu qisqa
    kutishda taslim bo'lish javobni bekorga yo'qotadi. Uzoq kutishda esa
    kutmasdan keyingi provayderga o'tish kerak."""
    from app.services import llm

    uxlagan = []
    monkeypatch.setattr(llm.time, "sleep", uxlagan.append)

    qisqa = ['HTTP 429 retry-after: 4 — {"code":"rate_limit_exceeded"}']

    def bir_marta_yiqiladi():
        if qisqa:
            raise RuntimeError(qisqa.pop())
        return {"ok": True}

    xatolar = []
    assert llm._urin("groq", bir_marta_yiqiladi, xatolar) == {"ok": True}
    # 4 emas 5: muddat ataylab bir soniyaga ko'paytiriladi, aks holda
    # yaxlitlash tufayli limit oynasi hali yangilanmagan bo'lishi mumkin
    assert uxlagan == [5], "provayder aytgan muddat kutilmadi"
    assert xatolar == []

    # Uzoq kutishda kutilmaydi — navbat keyingisiga o'tishi kerak
    uxlagan.clear()
    xatolar = []
    uzoq = 'HTTP 429 — Rate limit reached. Please try again in 28m48s.'
    assert llm._urin("groq", lambda: (_ for _ in ()).throw(RuntimeError(uzoq)), xatolar) is None
    assert uxlagan == []
    assert len(xatolar) == 1


def test_groq_openai_bilan_bir_xil_yoldan_boradi():
    """Groq OpenAI-mos API ishlatadi — alohida nusxa emas, o'sha chaqiruvchi.
    Faqat manzil, kalit va model farq qilishi kerak."""
    from app.services import llm

    g, o = llm._groq_provayder("test-model"), llm._openai_provayder()
    assert g.model == "test-model", "model parametr bo'lishi kerak"
    assert g.nom == "groq" and o.nom == "openai"
    assert "groq.com" in g.manzil and "openai.com" in o.manzil
    assert g.manzil.endswith("/chat/completions") and o.manzil.endswith("/chat/completions")
    assert g.model and o.model and g.model != o.model


def test_har_model_alohida_bosqich_va_bepullar_oldinda():
    """Ikki narsa bir vaqtda: har model alohida bosqich (limit model bo'yicha
    hisoblanadi, shuning uchun ro'yxat bepul sig'imni oshiradi) va pulli
    provayder oxirida (aks holda har savol bekorga pul yeydi)."""
    from app import config
    from app.services import llm

    nomlar = [n for n, _, _ in llm._bosqichlar()]
    assert nomlar[0].startswith("anthropic/")
    assert nomlar[-1].startswith("openai/")

    # Har sozlangan model o'z bosqichini olishi kerak
    for model in config.GEMINI_MODELLAR:
        assert f"gemini/{model}" in nomlar
    for model in config.GROQ_MODELLAR:
        assert f"groq/{model}" in nomlar

    # Bepullar pullidan oldin
    oxirgi_bepul = max(i for i, n in enumerate(nomlar)
                       if n.startswith(("gemini/", "groq/")))
    assert oxirgi_bepul < nomlar.index(nomlar[-1])


def test_krediti_tugagan_provayder_chetlab_otiladi():
    """Krediti tugagan provayder har savolda qayta chaqirilmasligi kerak:
    bu bekorga kechikish qo'shadi va uning xatosi boshqalarnikini bosib
    ketadi. Muddat o'tgach yana bir marta sinaladi (hisob to'ldirilgan
    bo'lishi mumkin)."""
    from app.services import llm

    asl_blok, asl_holat = llm._bloklangan.copy(), llm._holat.copy()
    try:
        llm._bloklangan.clear()
        llm._holat.clear()
        chaqiruvlar = []

        def olik():
            chaqiruvlar.append(1)
            raise RuntimeError("Your credit balance is too low")

        natija = llm._navbat([
            ("anthropic", True, olik),
            ("gemini", True, lambda: {"ok": 1}),
        ])
        assert natija == {"ok": 1}
        assert len(chaqiruvlar) == 1

        # Ikkinchi savolda o'lik provayder umuman chaqirilmaydi
        llm._navbat([("anthropic", True, olik), ("gemini", True, lambda: {"ok": 2})])
        assert len(chaqiruvlar) == 1, "bloklangan provayder qayta chaqirildi"

        # Muddat o'tgach yana sinaladi
        llm._bloklangan["anthropic"] = 0
        llm._navbat([("anthropic", True, olik), ("gemini", True, lambda: {"ok": 3})])
        assert len(chaqiruvlar) == 2
    finally:
        llm._bloklangan.clear(); llm._bloklangan.update(asl_blok)
        llm._holat.clear(); llm._holat.update(asl_holat)


def test_hamma_provayder_bloklansa_tushunarli_xato():
    """Hammasi chetlangan bo'lsa "API kalit yo'q" deyish chalg'itadi —
    kalit bor, u ishlamayapti."""
    from app.services import llm

    asl_blok, asl_holat = llm._bloklangan.copy(), llm._holat.copy()
    try:
        llm._bloklangan.clear()
        llm._holat.clear()
        llm._holat["gemini"] = "hisob"
        llm._bloklangan["gemini"] = float("inf")
        with pytest.raises(RuntimeError) as xato:
            llm._navbat([("gemini", True, lambda: {"ok": 1})])
        assert "chetlangan" in str(xato.value)
        assert xato.value.sabablar == ["hisob"]
    finally:
        llm._bloklangan.clear(); llm._bloklangan.update(asl_blok)
        llm._holat.clear(); llm._holat.update(asl_holat)


def test_gemini_uzilgan_javob_ochiq_xato_beradi():
    """Chegaraga urilganda Gemini `parts` ni umuman qaytarmaydi. Tekshiruvsiz
    bu KeyError bo'lib chiqadi va zaxira nega o'lgani noma'lum qoladi."""
    from app.services import llm

    class SoxtaJavob:
        def __init__(self, malumot):
            self._m = malumot

        def json(self):
            return self._m

    with pytest.raises(RuntimeError, match="uzildi"):
        llm._gemini_matni(SoxtaJavob({"candidates": [{"finishReason": "MAX_TOKENS"}]}))

    with pytest.raises(RuntimeError, match="bo'sh javob"):
        llm._gemini_matni(SoxtaJavob({"candidates": [{"content": {"parts": []}}]}))

    # O'ylash qismi javob emas — u tashlab ketilishi kerak
    matn = llm._gemini_matni(SoxtaJavob({"candidates": [{"content": {"parts": [
        {"text": "o'ylash", "thought": True},
        {"text": '{"javob": 1}'},
    ]}}]}))
    assert matn == '{"javob": 1}'

    assert llm._xato_sababi(RuntimeError("Unterminated string at char 411")) == "uzildi"


def _yiqiluvchi(xabar: str):
    def ish():
        raise RuntimeError(xabar)
    return ish


def test_health_sir_oshkor_qilmaydi():
    matn = client.get("/health").text
    for sir in ("sk-ant", "sk-proj", "gsk_", "AQ.", "upstash.io", "AAGnz"):
        assert sir not in matn


def test_health_kesh_holati():
    """Isitilgan kesh saqlanadimi — demo oldidan buni ko'rish shart.
    "xotira" bo'lsa Render uyg'onishi bilan yo'qoladi va isitish behuda."""
    k = client.get("/health").json()["kesh"]
    assert k["saqlash"] in ("tashqi", "xotira")
    assert isinstance(k["yozuvlar"], int)


def test_isitgich_savollari_bazaga_mos():
    """Isitgich ro'yxatidagi har savolga qidiruv nomzod topishi kerak —
    aks holda isitish "javob topilmadi" ni keshlab, kvotani behuda yeydi."""
    from tools.kesh_isit import SAVOLLAR, savollarni_yig

    from app import storage
    from app.services import retrieval

    moddalar = storage.moddalarni_oqi()
    nomzodsiz = [s for royxat in SAVOLLAR.values() for s in royxat
                 if not retrieval.moddalarni_qidir(s, moddalar)]
    assert not nomzodsiz, f"bazada javobi yo'q savollar: {nomzodsiz}"
    assert len(savollarni_yig(False)) >= 50
