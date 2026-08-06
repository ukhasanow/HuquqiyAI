# Radar surati tekshiruvi.
#
# Bu yerdagi eng muhim test — test_trenoga_ozi_asos_bermaydi (test_jarima.py da)
# bilan juftlikda ishlaydi: surat "trenoga" ko'rsatgani bilan asos bermaydi,
# asos faqat atrofdagi DALILDAN (patrul avtomobili yo'q, xodim formada emas)
# kelib chiqadi.
import json
import struct

import pytest

from app.models import RadarKuzatuv
from app.services import jarima, radar

# ---------- Kuzatuvni JarimaSorov'ga o'girish ----------


def _kuzatuv(**qoshimcha) -> RadarKuzatuv:
    asos = {"radar_bormi": True, "ornatilish": "trenoga"}
    asos.update(qoshimcha)
    return RadarKuzatuv(**asos)


def test_ornatilish_radar_turiga_ogiriladi():
    juftlar = {"trenoga": "trenoga", "avtomobilda": "patrul",
               "ustunda": "statsionar", "qolda": "", "noanik": ""}
    for korilgan, kutilgan in juftlar.items():
        sorov = radar.kuzatuvni_sorovga(_kuzatuv(ornatilish=korilgan))
        assert sorov.radar_turi == kutilgan


def test_qolda_kiritilgan_malumot_suratdan_ustun():
    """Odam o'zi aytgan narsa modelning taxminidan ustun turadi."""
    asl = jarima.JarimaSorov(radar_turi="patrul", patrul_avtomobili=True)
    sorov = radar.kuzatuvni_sorovga(
        _kuzatuv(ornatilish="trenoga", patrul_avtomobili=False), asl)
    assert sorov.radar_turi == "patrul"
    assert sorov.patrul_avtomobili is True


def test_asl_sorov_ozgartirilmaydi():
    asl = jarima.JarimaSorov()
    radar.kuzatuvni_sorovga(_kuzatuv(patrul_avtomobili=False), asl)
    assert asl.patrul_avtomobili is None


def test_noanik_patrul_avtomobili_asos_bermaydi():
    """null (kadr tor) va False (aniq yo'q edi) bir xil emas."""
    sorov = radar.kuzatuvni_sorovga(_kuzatuv(patrul_avtomobili=None))
    javob = jarima.jarimani_tekshir(sorov)
    t = next(t for t in javob.tekshiruvlar
             if t.nomi.startswith("Radar belgilangan tartibda"))
    assert t.holat == "diqqat"


def test_odam_bor_bolsa_qarovsiz_deb_hisoblanmaydi():
    """Odam bor, lekin formada emas — bu 32-band, 35-band emas.

    Ikkalasi ham berilsa, bitta holat ikki marta asos bo'lib ko'rinadi.
    """
    sorov = radar.kuzatuvni_sorovga(
        _kuzatuv(odam_bormi=True, xodim_formada=False, moslama_qarovsiz=True))
    assert sorov.moslama_qarovsiz is False
    javob = jarima.jarimani_tekshir(sorov)
    assert not any(t.nomi.startswith("Moslama qarovsiz") for t in javob.tekshiruvlar)


def test_haqiqiy_qarovsiz_moslama_asos_beradi():
    sorov = radar.kuzatuvni_sorovga(
        _kuzatuv(odam_bormi=False, moslama_qarovsiz=True))
    javob = jarima.jarimani_tekshir(sorov)
    t = next(t for t in javob.tekshiruvlar if t.nomi.startswith("Moslama qarovsiz"))
    assert t.holat == "asos"
    assert t.modda.id == "ypx-35"


def test_dislokatsiya_sorovi_joy_va_vaqtni_yigadi():
    matn = radar.dislokatsiya_sorovi(_kuzatuv(
        sana="2026-08-06 14:31", gps=(41.2995, 69.2401),
        joy_belgilari=["Toshkent, Amir Temur ko'chasi 12"],
        moslama_rusumi="Vizir",
    ))
    assert "2026-08-06 14:31" in matn
    assert "41.29950" in matn and "69.24010" in matn
    assert "Amir Temur" in matn
    assert "Vizir" in matn


def test_dislokatsiya_sorovi_malumotsiz_bosh_boladi():
    assert radar.dislokatsiya_sorovi(_kuzatuv()) == ""


# ---------- Model javobini o'qish ----------


def test_json_blok_ichidan_ajratiladi():
    xom = '```json\n{"radar_bormi": true, "ornatilish": "trenoga"}\n```'
    kuzatuv = radar._json_ajrat(xom)
    assert kuzatuv.radar_bormi is True
    assert kuzatuv.ornatilish == "trenoga"


def test_json_atrofidagi_matn_tashlanadi():
    xom = 'Mana natija:\n{"radar_bormi": false}\nUmid qilamanki foydali.'
    assert radar._json_ajrat(xom).radar_bormi is False


def test_buzuq_json_tushunarli_xato_beradi():
    with pytest.raises(radar.RadarXato, match="qaytadan urinib"):
        radar._json_ajrat("javob bera olmayman")


# ---------- Gemini oqimi (tarmoqsiz) ----------


class _SoxtaJavob:
    def __init__(self, matn):
        self._matn = matn
        self.status_code = 200

    def raise_for_status(self):
        pass

    def json(self):
        return {"candidates": [{"content": {"parts": [{"text": self._matn}]}}]}


def _soxta_post(monkeypatch, matn):
    monkeypatch.setattr(radar, "GEMINI_API_KEY", "test-kalit")
    monkeypatch.setattr(radar.httpx, "post", lambda *a, **k: _SoxtaJavob(matn))


def test_suratdan_kuzat_toliq_oqim(monkeypatch):
    _soxta_post(monkeypatch, json.dumps({
        "radar_bormi": True, "ornatilish": "trenoga",
        "patrul_avtomobili": False, "avtomobil_tavsifi": "oq Nexia, yozuvsiz",
        "odam_bormi": True, "xodim_formada": False,
        "moslama_rusumi": "Vizir", "tezlik_belgisi": 70,
    }))
    kuzatuv = radar.suratdan_kuzat(b"soxta-rasm")
    assert kuzatuv.patrul_avtomobili is False
    assert kuzatuv.tezlik_belgisi == 70

    javob = jarima.jarimani_tekshir(radar.kuzatuvni_sorovga(kuzatuv))
    t = next(t for t in javob.tekshiruvlar
             if t.nomi.startswith("Radar belgilangan tartibda"))
    assert t.holat == "asos"
    assert t.modda.id == "ypx-32"


def test_radar_korinmasa_tushunarli_xato(monkeypatch):
    _soxta_post(monkeypatch, json.dumps({"radar_bormi": False}))
    with pytest.raises(radar.RadarXato, match="moslamasi ko'rinmadi"):
        radar.suratdan_kuzat(b"soxta-rasm")


def test_kalitsiz_serverda_tushunarli_xato(monkeypatch):
    monkeypatch.setattr(radar, "GEMINI_API_KEY", "")
    with pytest.raises(radar.RadarXato, match="sozlanmagan"):
        radar.suratdan_kuzat(b"soxta-rasm")


def test_juda_katta_rasm_rad_etiladi():
    with pytest.raises(radar.RadarXato, match="8 MB"):
        radar.suratdan_kuzat(b"x" * (radar.MAX_RASM_HAJMI + 1))


# ---------- EXIF ----------
#
# EXIF o'quvchisi qo'lda yozilgan (Pillow qo'shilmadi), shuning uchun u
# haqiqiy baytlar bilan tekshiriladi: quyida to'liq JPEG+EXIF yasaladi.


def _rational(payi: int, maxraji: int) -> bytes:
    return struct.pack("<II", payi, maxraji)


def _exifli_jpeg(sana=b"2026:08:06 14:31:02\x00", kenglik_yonalishi=b"N\x00",
                 uzunlik_yonalishi=b"E\x00") -> bytes:
    """Bitta sana va bitta koordinata yozilgan eng kichik JPEG.

    Joylashuv (TIFF boshidan): 8 IFD0 | 38 Exif IFD | 55 GPS IFD |
    109 sana | 129 kenglik | 153 uzunlik
    """
    SANA_OFS, KENGLIK_OFS, UZUNLIK_OFS = 109, 129, 153

    def yozuv(teg, tip, sanoq, qiymat: bytes) -> bytes:
        return struct.pack("<HHI", teg, tip, sanoq) + qiymat.ljust(4, b"\x00")[:4]

    ifd0 = (struct.pack("<H", 2)
            + yozuv(0x8769, 4, 1, struct.pack("<I", 38))    # Exif IFD ko'rsatkichi
            + yozuv(0x8825, 4, 1, struct.pack("<I", 55))    # GPS IFD ko'rsatkichi
            + struct.pack("<I", 0))
    exif_ifd = (struct.pack("<H", 1)
                + yozuv(0x9003, 2, len(sana), struct.pack("<I", SANA_OFS))
                + struct.pack("<I", 0))
    gps_ifd = (struct.pack("<H", 4)
               + yozuv(1, 2, 2, kenglik_yonalishi)
               + yozuv(2, 5, 3, struct.pack("<I", KENGLIK_OFS))
               + yozuv(3, 2, 2, uzunlik_yonalishi)
               + yozuv(4, 5, 3, struct.pack("<I", UZUNLIK_OFS))
               + struct.pack("<I", 0))

    # 41°17'58.2"N, 69°14'24.36"E — Toshkent markazi
    kenglik = _rational(41, 1) + _rational(17, 1) + _rational(582, 10)
    uzunlik = _rational(69, 1) + _rational(14, 1) + _rational(2436, 100)

    tiff = bytearray(b"II" + struct.pack("<HI", 42, 8))
    for ofset, bolak in ((8, ifd0), (38, exif_ifd), (55, gps_ifd),
                         (SANA_OFS, sana), (KENGLIK_OFS, kenglik),
                         (UZUNLIK_OFS, uzunlik)):
        if len(tiff) < ofset:
            tiff.extend(b"\x00" * (ofset - len(tiff)))
        tiff[ofset:ofset + len(bolak)] = bolak

    app1 = b"Exif\x00\x00" + bytes(tiff)
    return (b"\xff\xd8\xff\xe1" + struct.pack(">H", len(app1) + 2) + app1
            + b"\xff\xd9")


def test_exif_sana_va_koordinata_oqiladi():
    sana, gps = radar._exif_sana_va_gps(_exifli_jpeg())
    assert sana == "2026-08-06 14:31"
    assert gps is not None
    kenglik, uzunlik = gps
    assert kenglik == pytest.approx(41.2995, abs=1e-4)
    assert uzunlik == pytest.approx(69.2401, abs=1e-4)


def test_janubiy_va_gorbiy_yarim_shar_manfiy():
    _, gps = radar._exif_sana_va_gps(
        _exifli_jpeg(kenglik_yonalishi=b"S\x00", uzunlik_yonalishi=b"W\x00"))
    assert gps[0] < 0 and gps[1] < 0


def test_exifsiz_rasm_xato_bermaydi():
    """EXIF yo'qligi normal hol — surat baribir tekshiriladi."""
    assert radar._exif_sana_va_gps(b"\xff\xd8\xff\xdb" + b"\x00" * 40) == ("", None)


def test_buzuq_exif_butun_tekshiruvni_toxtatmaydi():
    buzuq = _exifli_jpeg()[:60] + b"\xff" * 30
    assert radar._exif_sana_va_gps(buzuq) == ("", None)


def test_jpeg_bolmagan_fayl_xato_bermaydi():
    assert radar._exif_sana_va_gps(b"\x89PNG\r\n\x1a\n" + b"\x00" * 20) == ("", None)


def test_suratdan_kuzat_exifni_qoshadi(monkeypatch):
    _soxta_post(monkeypatch, json.dumps(
        {"radar_bormi": True, "ornatilish": "trenoga"}))
    kuzatuv = radar.suratdan_kuzat(_exifli_jpeg())
    assert kuzatuv.sana == "2026-08-06 14:31"
    assert kuzatuv.gps is not None


# ---------- API endpointi ----------

from fastapi.testclient import TestClient  # noqa: E402

from app import main  # noqa: E402

client = TestClient(main.app)


def _endpoint_javobi(monkeypatch, **kuzatuv):
    monkeypatch.setattr(main.radar_xizmati, "suratdan_kuzat",
                        lambda *a, **k: _kuzatuv(**kuzatuv))
    return client.post("/api/jarima/radar",
                       files={"fayl": ("radar.jpg", b"soxta", "image/jpeg")})


def test_endpoint_kuzatuv_va_tekshiruvni_qaytaradi(monkeypatch):
    r = _endpoint_javobi(monkeypatch, patrul_avtomobili=False,
                         odam_bormi=True, xodim_formada=False,
                         sana="2026-08-06 14:31", gps=(41.2995, 69.2401))
    assert r.status_code == 200
    d = r.json()
    assert d["kuzatuv"]["patrul_avtomobili"] is False
    assert d["tekshiruv"]["asoslar_soni"] >= 1
    assert "41.29950" in d["dislokatsiya_sorovi"]


def test_endpoint_dalilsiz_asos_bermaydi(monkeypatch):
    r = _endpoint_javobi(monkeypatch, patrul_avtomobili=True, odam_bormi=True,
                         xodim_formada=True)
    assert r.status_code == 200
    tekshiruv = r.json()["tekshiruv"]
    nomlar = [t["nomi"] for t in tekshiruv["tekshiruvlar"] if t["holat"] == "asos"]
    assert "Radar belgilangan tartibda ishlatilganmi" not in nomlar


def test_endpoint_xatoni_422_bilan_qaytaradi(monkeypatch):
    def portla(*a, **k):
        raise radar.RadarXato("Suratda moslama ko'rinmadi.")

    monkeypatch.setattr(main.radar_xizmati, "suratdan_kuzat", portla)
    r = client.post("/api/jarima/radar",
                    files={"fayl": ("radar.jpg", b"x", "image/jpeg")})
    assert r.status_code == 422
    assert "ko'rinmadi" in r.json()["detail"]
