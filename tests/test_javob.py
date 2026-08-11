# Javob xizmati qatlami testlari (LLM'siz).
#
# Bu qatlamning butun mazmuni — sayt va Telegram bot bitta kodni ishlatishi.
# Shuning uchun testlar nafaqat mantiqni, balki qatlamning HTTP'dan
# mustaqilligini ham tekshiradi.
import ast
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import ChatJavob
from app.services import javob as javob_xizmati
from app.services import kesh

client = TestClient(app)


@pytest.fixture(autouse=True)
def _toza():
    kesh.tozala()
    yield
    kesh.tozala()


def _soxta_javob(topildi=True, tavsiya="tavsiya"):
    return ChatJavob(
        javob_topildi=topildi, moddalar=[], tavsiya=tavsiya,
        murojaat=None, murojaat_mavzusi="umumiy",
    )


# ---------- Qatlam mustaqilligi ----------

def test_javob_qatlami_fastapi_ga_boglanmagan():
    """services/javob.py HTTP haqida hech narsa bilmasligi kerak — aks holda
    uni Telegram botdan chaqirib bo'lmaydi."""
    manba = (Path(__file__).resolve().parent.parent / "app" / "services" / "javob.py").read_text(encoding="utf-8")
    for tugun in ast.walk(ast.parse(manba)):
        if isinstance(tugun, ast.Import):
            nomlar = [a.name for a in tugun.names]
        elif isinstance(tugun, ast.ImportFrom):
            nomlar = [tugun.module or ""]
        else:
            continue
        for n in nomlar:
            assert not n.startswith("fastapi"), f"javob.py fastapi'ga bog'landi: {n}"
            assert not n.startswith("starlette"), f"javob.py starlette'ga bog'landi: {n}"


# ---------- Xato turlari ----------

def test_kalit_yoq_bolsa_ai_sozlanmagan(monkeypatch):
    monkeypatch.setattr(javob_xizmati, "ANTHROPIC_API_KEY", "")
    monkeypatch.setattr(javob_xizmati, "GEMINI_API_KEY", "")
    monkeypatch.setattr(javob_xizmati, "OPENAI_API_KEY", "")
    with pytest.raises(javob_xizmati.AiSozlanmagan):
        javob_xizmati.uch_qismli_javob("aliment qancha")


def test_bitta_openai_kaliti_yetarli(monkeypatch):
    """Faqat OpenAI sozlangan bo'lsa ham xizmat ishlashi kerak — u endi
    to'laqonli provayder, faqat ovoz zaxirasi emas."""
    monkeypatch.setattr(javob_xizmati, "ANTHROPIC_API_KEY", "")
    monkeypatch.setattr(javob_xizmati, "GEMINI_API_KEY", "")
    monkeypatch.setattr(javob_xizmati, "OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(
        javob_xizmati.llm, "javob_yarat",
        lambda *a, **k: {"javob_topildi": True, "tegishli_modda_idlari": [],
                         "tavsiya": "test", "murojaat_mavzusi": "umumiy"},
    )
    assert javob_xizmati.uch_qismli_javob("aliment qancha") is not None


@pytest.mark.parametrize(
    "xato_matni,kutilgan_bolak",
    [
        ("Your credit balance is too low", "hisob to'ldirilishi"),
        ("authentication_error: invalid x-api-key", "API kalit noto'g'ri"),
        ("rate limit exceeded (429)", "So'rovlar ko'payib ketdi"),
        ("Server overloaded (529)", "hozir band"),
        ("connection reset by peer", "vaqtinchalik xatolik"),
    ],
)
def test_ai_xato_ozbekcha_xabarga_aylanadi(xato_matni, kutilgan_bolak):
    xato = javob_xizmati.AiXato(RuntimeError(xato_matni))
    assert kutilgan_bolak in xato.foydalanuvchi_matni


def test_ai_xato_asl_istisnoni_saqlaydi():
    asl = RuntimeError("nimadir")
    assert javob_xizmati.AiXato(asl).asl is asl


def test_llm_xatosi_ai_xatoga_oraladi(monkeypatch):
    monkeypatch.setattr(javob_xizmati, "ANTHROPIC_API_KEY", "test")
    monkeypatch.setattr(
        javob_xizmati.llm, "javob_yarat",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("rate limit 429")),
    )
    with pytest.raises(javob_xizmati.AiXato) as e:
        javob_xizmati.uch_qismli_javob("aliment qancha")
    assert "So'rovlar ko'payib ketdi" in e.value.foydalanuvchi_matni


# ---------- Kesh javob_ol ichida ----------

def test_javob_ol_keshdan_qaytaradi(monkeypatch):
    chaqiruvlar = []

    def soxta(savol, rejim="oddiy", tarix=None, hujjat_matni=None, batafsil=False):
        chaqiruvlar.append(savol)
        return _soxta_javob()

    monkeypatch.setattr(javob_xizmati, "uch_qismli_javob", soxta)
    javob_xizmati.javob_ol("aliment qancha")
    javob_xizmati.javob_ol("aliment qancha")
    assert len(chaqiruvlar) == 1


def test_javob_topilmasa_keshlanmaydi(monkeypatch):
    """Baza to'ldirilgach o'sha savol to'g'ri javob berishi kerak."""
    chaqiruvlar = []

    def soxta(savol, rejim="oddiy", tarix=None, hujjat_matni=None, batafsil=False):
        chaqiruvlar.append(savol)
        return _soxta_javob(topildi=False)

    monkeypatch.setattr(javob_xizmati, "uch_qismli_javob", soxta)
    javob_xizmati.javob_ol("javobsiz savol")
    javob_xizmati.javob_ol("javobsiz savol")
    assert len(chaqiruvlar) == 2


def test_suhbat_tarixi_bolsa_keshlanmaydi(monkeypatch):
    """Tarixli javob oldingi xabarlarga bog'liq — boshqa foydalanuvchiga berib bo'lmaydi."""
    chaqiruvlar = []

    def soxta(savol, rejim="oddiy", tarix=None, hujjat_matni=None, batafsil=False):
        chaqiruvlar.append(savol)
        return _soxta_javob()

    monkeypatch.setattr(javob_xizmati, "uch_qismli_javob", soxta)
    tarix = [{"rol": "user", "matn": "salom"}]
    javob_xizmati.javob_ol("davomi", tarix=tarix)
    javob_xizmati.javob_ol("davomi", tarix=tarix)
    assert len(chaqiruvlar) == 2


# ---------- HTTP qatlami xatolarni to'g'ri kodga aylantiradi ----------

def test_sozlanmagan_provayder_503(monkeypatch):
    def soxta(*a, **k):
        raise javob_xizmati.AiSozlanmagan()

    monkeypatch.setattr("app.main.javob_ol", soxta)
    r = client.post("/api/chat", json={"savol": "aliment qancha"})
    assert r.status_code == 503
    assert "ANTHROPIC_API_KEY" in r.json()["detail"]


def test_provayder_xatosi_502(monkeypatch):
    def soxta(*a, **k):
        raise javob_xizmati.AiXato(RuntimeError("overloaded 529"))

    monkeypatch.setattr("app.main.javob_ol", soxta)
    r = client.post("/api/chat", json={"savol": "aliment qancha"})
    assert r.status_code == 502
    assert "band" in r.json()["detail"]


def test_statistika_xatosi_javobni_buzmaydi(monkeypatch):
    """Statistika yozilmasa ham foydalanuvchi javobini yo'qotmasligi kerak."""
    monkeypatch.setattr(
        javob_xizmati.statistika, "sorov_hisobla",
        lambda **k: (_ for _ in ()).throw(OSError("disk to'la")),
    )
    javob_xizmati.statistikani_yoz(_soxta_javob(), "oddiy", None, "savol")


# ---------- Provayder xatolari ----------

from app.services.javob import _ai_xato_matni  # noqa: E402

def test_hisob_xatosi_limit_xatosidan_ustun(monkeypatch):
    """Anthropic krediti tugab, keyin Gemini limitga urilsa: foydalanuvchi
    "bir daqiqadan so'ng urinib ko'ring" deb kutmasligi kerak — hisob
    to'ldirilmaguncha hech narsa o'zgarmaydi."""
    from app.services import llm

    matn = llm._xatolar_matni([
        RuntimeError("Your credit balance is too low to access the Anthropic API"),
        RuntimeError("429 RESOURCE_EXHAUSTED quota exceeded"),
    ])
    # Hisob xatosi birinchi bo'lsa, _ai_xato_matni to'g'ri xabarni tanlaydi
    assert matn.index("credit balance") < matn.index("429")
    assert "hisob to'ldirilishi kerak" in _ai_xato_matni(RuntimeError(matn))


def test_ikkala_provayder_xatosi_ham_saqlanadi():
    from app.services import llm

    matn = llm._xatolar_matni([RuntimeError("anthropic yiqildi"),
                               RuntimeError("gemini yiqildi")])
    assert "anthropic yiqildi" in matn and "gemini yiqildi" in matn


def test_faqat_limit_bolsa_limit_xabari():
    from app.services import llm

    matn = llm._xatolar_matni([RuntimeError("429 rate limit")])
    assert "So'rovlar ko'payib ketdi" in _ai_xato_matni(RuntimeError(matn))
