# Shartnoma tahlili testlari (LLM chaqirilmaydi).
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import shartnoma

client = TestClient(app)

MEHNAT_SHARTNOMASI = """MEHNAT SHARTNOMASI № 47

1. SHARTNOMA PREDMETI
1.3. Shartnoma muddati: 6 oy, sinov muddati 6 oy.

2. MEHNATGA HAQ TO'LASH
2.1. Xodimning oylik ish haqi 3 000 000 so'mni tashkil etadi.
2.3. Ish beruvchi ish haqini bir tomonlama kamaytirish huquqiga ega.

3. ISH VAQTI
3.1. Ish kuni 09:00 dan 21:00 gacha, haftasiga olti kun.
"""


def _soxta_natija(**kw):
    natija = {
        "shartnoma_turi": "mehnat",
        "umumiy_mazmun": {
            "tomonlar": "MChJ va xodim", "predmet": "Sotuvchi lavozimi",
            "summa": "3 000 000 so'm", "muddat": "6 oy",
        },
        "bandlar_soni": 5,
        "bandlar": [
            {"band": "2.1", "mazmuni": "Ish haqi 3 mln", "xavf": "yashil",
             "izoh": "Odatiy band", "modda_id": ""},
            {"band": "1.3", "mazmuni": "Sinov muddati 6 oy", "xavf": "qizil",
             "izoh": "Qonunga zid", "modda_id": "mehnat-130"},
            {"band": "2.3", "mazmuni": "Bir tomonlama kamaytirish", "xavf": "sariq",
             "izoh": "Xavfli", "modda_id": "mehnat-137"},
        ],
        "xulosa": "1.3-bandni olib tashlashni talab qiling.",
    }
    natija.update(kw)
    return natija


# ---------- Bandlarga ajratish ----------

def test_bandlar_ajratiladi():
    bandlar = shartnoma.bandlarga_ajrat(MEHNAT_SHARTNOMASI)
    raqamlar = [b.split()[0] for b in bandlar]
    assert raqamlar == ["1.3", "2.1", "2.3", "3.1"]


def test_bandsiz_matn_bosh_royxat():
    assert shartnoma.bandlarga_ajrat("Oddiy matn, band raqamlari yo'q.") == []
    assert shartnoma.bandlarga_ajrat("") == []


def test_sarlavha_band_deb_hisoblanmaydi():
    """"1. SHARTNOMA PREDMETI" — bo'lim sarlavhasi, band emas."""
    bandlar = shartnoma.bandlarga_ajrat("1. SHARTNOMA PREDMETI\n1.1. Birinchi band matni.")
    assert len(bandlar) == 1
    assert bandlar[0].startswith("1.1")


# ---------- Turni taxmin qilish ----------

def test_mehnat_shartnomasi_taniladi():
    assert shartnoma.turni_taxmin(MEHNAT_SHARTNOMASI) == "mehnat"


def test_ijara_va_kredit_taniladi():
    assert shartnoma.turni_taxmin("IJARA SHARTNOMASI. Ijaraga beruvchi ...") == "ijara"
    assert shartnoma.turni_taxmin("KREDIT SHARTNOMASI. Qarz oluvchi bankdan ...") == "kredit"


def test_notanish_matn_boshqa():
    assert shartnoma.turni_taxmin("Bugun havo ochiq.") == "boshqa"


# ---------- Nomzod moddalar ----------

def test_imperativ_normalar_doim_qoshiladi():
    """Leksik qidiruv "09:00 dan 21:00 gacha" bandini "ish vaqtining normal
    davomiyligi" moddasi bilan bog'lay olmaydi — shuning uchun mehnat
    shartnomasi uchun bu modda majburan nomzodlarga kiradi."""
    idlar = [m["id"] for m in shartnoma._nomzod_moddalar(MEHNAT_SHARTNOMASI)]
    assert "mehnat-182" in idlar   # ish vaqtining normal davomiyligi
    assert "mehnat-130" in idlar   # sinov muddati
    assert "mehnat-253" in idlar   # ish haqini to'lash muddatlari


def test_nomzodlar_takrorlanmaydi_va_cheklangan():
    nomzodlar = shartnoma._nomzod_moddalar(MEHNAT_SHARTNOMASI)
    idlar = [m["id"] for m in nomzodlar]
    assert len(idlar) == len(set(idlar))
    assert len(idlar) <= shartnoma.MAX_NOMZOD


def test_asosiy_moddalar_bazada_mavjud():
    """Ro'yxatdagi ID o'zgarib ketsa (modda o'chirilsa) jimgina yo'qolmasin."""
    from app import storage

    for tur, idlar in shartnoma.ASOSIY_MODDALAR.items():
        for modda_id in idlar:
            assert storage.modda_top(modda_id), f"{tur}: {modda_id} bazada yo'q"


# ---------- Javobni tuzish ----------

def test_modda_matni_bazadan_olinadi(monkeypatch):
    """Asl matn kafolati: LLM faqat ID tanlaydi, matn bazadan qo'shiladi."""
    monkeypatch.setattr(shartnoma.llm, "shartnoma_tahlil_yarat", lambda *a: _soxta_natija())
    javob = shartnoma.shartnomani_tahlil(MEHNAT_SHARTNOMASI)

    sinov_bandi = next(b for b in javob.bandlar if b.band == "1.3")
    assert sinov_bandi.modda.id == "mehnat-130"
    assert "sinov" in sinov_bandi.modda.sarlavha.lower()
    assert sinov_bandi.modda.matn  # bazadagi asl matn


def test_oylab_topilgan_modda_id_tashlanadi(monkeypatch):
    """Model mavjud bo'lmagan ID qaytarsa — band moddasiz ko'rsatiladi.
    Yolg'on havoladan ko'ra havolasizlik yaxshiroq."""
    natija = _soxta_natija(bandlar=[
        {"band": "9.9", "mazmuni": "Nimadir", "xavf": "qizil",
         "izoh": "Izoh", "modda_id": "mehnat-99999"},
    ])
    monkeypatch.setattr(shartnoma.llm, "shartnoma_tahlil_yarat", lambda *a: natija)
    javob = shartnoma.shartnomani_tahlil(MEHNAT_SHARTNOMASI)
    assert javob.bandlar[0].modda is None


def test_bandlar_xavf_boyicha_saralanadi(monkeypatch):
    """Odam ro'yxatni tepadan o'qiydi — qizil band pastda qolib ketmasin."""
    monkeypatch.setattr(shartnoma.llm, "shartnoma_tahlil_yarat", lambda *a: _soxta_natija())
    javob = shartnoma.shartnomani_tahlil(MEHNAT_SHARTNOMASI)
    assert [b.xavf for b in javob.bandlar] == ["qizil", "sariq", "yashil"]


def test_notogri_xavf_darajasi_sariqqa_tushadi(monkeypatch):
    natija = _soxta_natija(bandlar=[
        {"band": "1.1", "mazmuni": "M", "xavf": "binafsha", "izoh": "I", "modda_id": ""},
    ])
    monkeypatch.setattr(shartnoma.llm, "shartnoma_tahlil_yarat", lambda *a: natija)
    assert shartnoma.shartnomani_tahlil(MEHNAT_SHARTNOMASI).bandlar[0].xavf == "sariq"


def test_bosh_hujjat_rad_etiladi():
    with pytest.raises(shartnoma.AiXato):
        shartnoma.shartnomani_tahlil("   ")


def test_llm_xatosi_ai_xatoga_oraladi(monkeypatch):
    def portla(*a):
        raise RuntimeError("rate limit 429")

    monkeypatch.setattr(shartnoma.llm, "shartnoma_tahlil_yarat", portla)
    with pytest.raises(shartnoma.AiXato) as e:
        shartnoma.shartnomani_tahlil(MEHNAT_SHARTNOMASI)
    assert "So'rovlar ko'payib ketdi" in e.value.foydalanuvchi_matni


# ---------- API endpoint ----------

def test_shartnoma_endpointi(monkeypatch):
    monkeypatch.setattr(shartnoma.llm, "shartnoma_tahlil_yarat", lambda *a: _soxta_natija())
    r = client.post("/api/shartnoma",
                    files={"fayl": ("shartnoma.txt", MEHNAT_SHARTNOMASI.encode(), "text/plain")})
    assert r.status_code == 200
    d = r.json()
    assert d["shartnoma_turi"] == "mehnat"
    assert d["umumiy_mazmun"]["summa"] == "3 000 000 so'm"
    assert d["bandlar"][0]["xavf"] == "qizil"
    assert d["bandlar"][0]["modda"]["id"] == "mehnat-130"
    assert "professional" in d["disclaimer"]


def test_shartnoma_endpointi_katta_fayl_rad_etadi():
    from app.config import MAX_HUJJAT_HAJMI

    r = client.post("/api/shartnoma",
                    files={"fayl": ("katta.txt", b"x" * (MAX_HUJJAT_HAJMI + 1), "text/plain")})
    assert r.status_code == 413


def test_shartnoma_endpointi_notogri_format():
    r = client.post("/api/shartnoma",
                    files={"fayl": ("rasm.png", b"\x89PNG\r\n", "image/png")})
    assert r.status_code == 422


# ---------- Hujjat surati (OCR) ----------

class _SoxtaOcrJavob:
    def __init__(self, malumot, holat=200):
        self._m = malumot
        self.status_code = holat

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"Client error '{self.status_code}'")

    def json(self):
        return self._m


def _ocr_javobi(matn):
    return {"candidates": [{"content": {"parts": [{"text": matn}]}}]}


def test_rasmdan_matn_oqiladi(monkeypatch):
    from app.services import documents

    monkeypatch.setattr(documents, "GEMINI_API_KEY", "kalit")
    monkeypatch.setattr(documents.httpx, "post",
                        lambda *a, **k: _SoxtaOcrJavob(_ocr_javobi("  1.1. Band matni.  ")))
    assert documents.rasm_matni(b"rasm") == "1.1. Band matni."


def test_rasm_kengaytmasi_matn_ajratdan_otadi(monkeypatch):
    """matn_ajrat rasmni ham qabul qilishi kerak — sayt va bot shu funksiyani
    chaqiradi, ikkalasida alohida yo'l yozilmasin."""
    from app.services import documents

    monkeypatch.setattr(documents, "rasm_matni", lambda b, m="": "1.1. Rasmdan.")
    assert documents.matn_ajrat("qaror.jpg", b"x") == "1.1. Rasmdan."
    assert documents.matn_ajrat("hujjat", b"x", "image/png") == "1.1. Rasmdan."


def test_notanish_format_rad_etiladi():
    from app.services import documents

    with pytest.raises(documents.HujjatXato) as e:
        documents.matn_ajrat("fayl.exe", b"x")
    assert "rasm" in str(e.value)


def test_limit_xatosi_rasmga_agdarilmaydi(monkeypatch):
    """429 da "suratni yorug'roq oling" deyish noto'g'ri — odam aybni o'z
    rasmidan qidirib, qayta-qayta suratga oladi."""
    from app.services import documents

    monkeypatch.setattr(documents, "GEMINI_API_KEY", "kalit")
    monkeypatch.setattr(documents.httpx, "post",
                        lambda *a, **k: _SoxtaOcrJavob({}, holat=429))
    with pytest.raises(documents.HujjatXato) as e:
        documents.rasm_matni(b"rasm")
    assert "limiti" in str(e.value)
    assert "yorug'roq" not in str(e.value)


def test_katta_rasm_rad_etiladi():
    from app.services import documents

    with pytest.raises(documents.HujjatXato) as e:
        documents.rasm_matni(b"x" * (documents.MAX_RASM_HAJMI + 1))
    assert "8 MB" in str(e.value)


def test_shartnoma_endpointi_rasm_qabul_qiladi(monkeypatch):
    from app.services import documents

    monkeypatch.setattr(documents, "rasm_matni", lambda b, m="": MEHNAT_SHARTNOMASI)
    monkeypatch.setattr(shartnoma.llm, "shartnoma_tahlil_yarat", lambda *a: _soxta_natija())
    r = client.post("/api/shartnoma",
                    files={"fayl": ("shartnoma.png", b"soxta-rasm", "image/png")})
    assert r.status_code == 200
    assert r.json()["shartnoma_turi"] == "mehnat"
