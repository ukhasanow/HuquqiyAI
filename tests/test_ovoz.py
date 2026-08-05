# Ovoz xizmatlari testlari: matnga o'girish (STT) va ovozga o'girish (TTS).
# Tarmoqqa chiqmaydi.
import base64
import io
import wave

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


# ---------- Matnni ovozga o'girish (TTS) ----------

def _tts_javobi(pcm: bytes, mime: str = "audio/L16;codec=pcm;rate=24000"):
    return {"candidates": [{"content": {"parts": [
        {"inlineData": {"mimeType": mime, "data": base64.b64encode(pcm).decode()}}
    ]}}]}


def _tts_yoq(monkeypatch, model="gemini"):
    monkeypatch.setattr(ovoz, "TTS_PROVAYDER", model)
    monkeypatch.setattr(ovoz, "GEMINI_API_KEY", "kalit")


def test_tts_ochiq_bolsa_mavjud_emas(monkeypatch):
    """Standart holat — TTS o'chiq: sozlanmagan serverda bot faqat matn yozadi."""
    monkeypatch.setattr(ovoz, "TTS_PROVAYDER", "yoq")
    monkeypatch.setattr(ovoz, "GEMINI_API_KEY", "kalit")
    assert not ovoz.tts_mavjud()
    with pytest.raises(ovoz.OvozXato):
        ovoz.ovozga_ogir("Sudga murojaat qiling.")


def test_tts_kalitsiz_mavjud_emas(monkeypatch):
    monkeypatch.setattr(ovoz, "TTS_PROVAYDER", "gemini")
    monkeypatch.setattr(ovoz, "GEMINI_API_KEY", "")
    assert not ovoz.tts_mavjud()


def test_pcm_wav_ga_oraladi(monkeypatch):
    """Gemini xom PCM qaytaradi; Telegram'ga yuborish uchun WAV sarlavhasi kerak
    (ffmpeg yo'q, shuning uchun standart `wave` moduli bilan o'raladi)."""
    _tts_yoq(monkeypatch)
    pcm = b"\x01\x02" * 1000
    monkeypatch.setattr(ovoz.httpx, "post", lambda *a, **k: SoxtaJavob(_tts_javobi(pcm)))

    bayt, mime = ovoz.ovozga_ogir("Sudga murojaat qiling.")
    assert mime == "audio/wav"
    assert bayt[:4] == b"RIFF" and bayt[8:12] == b"WAVE"
    with wave.open(io.BytesIO(bayt)) as w:
        assert w.getframerate() == 24000
        assert w.getnchannels() == 1
        assert w.getsampwidth() == 2
        assert w.readframes(w.getnframes()) == pcm


def test_chastota_mime_dan_oqiladi(monkeypatch):
    """Gemini format satrini ikki xil yozadi — qat'iy 24000 deb yozib bo'lmaydi."""
    _tts_yoq(monkeypatch)
    monkeypatch.setattr(
        ovoz.httpx, "post",
        lambda *a, **k: SoxtaJavob(_tts_javobi(b"\x00\x00" * 10, "audio/l16; rate=16000; channels=1")),
    )
    bayt, _ = ovoz.ovozga_ogir("matn")
    with wave.open(io.BytesIO(bayt)) as w:
        assert w.getframerate() == 16000


def test_uzun_matn_gap_chegarasida_qisqaradi(monkeypatch):
    _tts_yoq(monkeypatch)
    yuborilgan = {}

    def soxta_post(*a, **k):
        yuborilgan.update(k.get("json", {}))
        return SoxtaJavob(_tts_javobi(b"\x00\x00"))

    monkeypatch.setattr(ovoz.httpx, "post", soxta_post)
    uzun = "Sudga murojaat qiling. " * 200
    ovoz.ovozga_ogir(uzun)

    oqilgan = yuborilgan["contents"][0]["parts"][0]["text"]
    assert len(oqilgan) < len(uzun)
    assert oqilgan.rstrip().endswith(".")  # so'z o'rtasidan kesilmagan


def test_bosh_matn_ovozga_ogirilmaydi(monkeypatch):
    _tts_yoq(monkeypatch)
    with pytest.raises(ovoz.OvozXato):
        ovoz.ovozga_ogir("   ")


def test_audio_qaytmasa_xato(monkeypatch):
    """Model matn qaytarib qo'ysa (audio o'rniga) — bu xato, jim qolinmaydi."""
    _tts_yoq(monkeypatch)
    monkeypatch.setattr(
        ovoz.httpx, "post",
        lambda *a, **k: SoxtaJavob({"candidates": [{"content": {"parts": [{"text": "salom"}]}}]}),
    )
    with pytest.raises(ovoz.OvozXato):
        ovoz.ovozga_ogir("matn")
