# Ovozni matnga o'girish testlari (tarmoqqa chiqmaydi).
import pytest

from app.services import ovoz


class SoxtaJavob:
    def __init__(self, malumot, holat=200):
        self._malumot = malumot
        self.status_code = holat

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._malumot


def _gemini_javobi(matn):
    return {"candidates": [{"content": {"parts": [{"text": matn}]}}]}


def test_bosh_ovoz_rad_etiladi():
    with pytest.raises(ovoz.OvozXato):
        ovoz.matnga_ogir(b"")


def test_provayder_yoq_bolsa_tushunarli_xato(monkeypatch):
    monkeypatch.setattr(ovoz, "GEMINI_API_KEY", "")
    monkeypatch.setattr(ovoz, "OPENAI_API_KEY", "")
    with pytest.raises(ovoz.OvozXato) as e:
        ovoz.matnga_ogir(b"ovoz")
    assert "matn bilan" in str(e.value)


def test_gemini_transkripti_qaytadi(monkeypatch):
    monkeypatch.setattr(ovoz, "GEMINI_API_KEY", "kalit")
    monkeypatch.setattr(
        ovoz.httpx, "post",
        lambda *a, **k: SoxtaJavob(_gemini_javobi("  Ish haqimni bermayapti  ")),
    )
    assert ovoz.matnga_ogir(b"ovoz") == "Ish haqimni bermayapti"


def test_ogg_ozgartirilmasdan_yuboriladi(monkeypatch):
    """Render bepul tierda ffmpeg yo'q — audio qanday kelsa shunday yuborilishi kerak."""
    yuborilgan = {}
    monkeypatch.setattr(ovoz, "GEMINI_API_KEY", "kalit")

    def soxta_post(*a, **k):
        yuborilgan.update(k.get("json", {}))
        return SoxtaJavob(_gemini_javobi("savol"))

    monkeypatch.setattr(ovoz.httpx, "post", soxta_post)
    ovoz.matnga_ogir(b"xom-opus-baytlar", "audio/ogg")
    qismlar = yuborilgan["contents"][0]["parts"]
    audio = next(q for q in qismlar if "inline_data" in q)
    assert audio["inline_data"]["mime_type"] == "audio/ogg"


def test_gemini_ishlamasa_whisperga_otiladi(monkeypatch):
    monkeypatch.setattr(ovoz, "GEMINI_API_KEY", "kalit")
    monkeypatch.setattr(ovoz, "OPENAI_API_KEY", "openai-kalit")
    chaqiruvlar = []

    def soxta_post(url, *a, **k):
        chaqiruvlar.append(url)
        if "googleapis" in url:
            raise RuntimeError("gemini ishlamadi")
        return SoxtaJavob({"text": "zaxira transkript"})

    monkeypatch.setattr(ovoz.httpx, "post", soxta_post)
    assert ovoz.matnga_ogir(b"ovoz") == "zaxira transkript"
    assert len(chaqiruvlar) == 2


def test_ikkala_provayder_ham_ishlamasa_ozbekcha_xato(monkeypatch):
    monkeypatch.setattr(ovoz, "GEMINI_API_KEY", "kalit")
    monkeypatch.setattr(ovoz, "OPENAI_API_KEY", "openai-kalit")
    monkeypatch.setattr(
        ovoz.httpx, "post",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("tarmoq")),
    )
    with pytest.raises(ovoz.OvozXato) as e:
        ovoz.matnga_ogir(b"ovoz")
    assert "matn bilan" in str(e.value)


def test_nutq_topilmasa_bosh_matn(monkeypatch):
    """Model bo'sh satr qaytarsa — bu xato emas, handler foydalanuvchidan
    qayta yozishni so'raydi."""
    monkeypatch.setattr(ovoz, "GEMINI_API_KEY", "kalit")
    monkeypatch.setattr(ovoz.httpx, "post", lambda *a, **k: SoxtaJavob({"candidates": []}))
    assert ovoz.matnga_ogir(b"jimjitlik") == ""
