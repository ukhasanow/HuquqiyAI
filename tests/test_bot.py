# Telegram bot testlari (Telegram'ga chiqmaydi).
#
# Handler'lar soxta Message obyekti bilan chaqiriladi: maqsad — aloqa emas,
# oqim mantiqi (cheklovlar, xato yo'llari, xabar shakli).
import asyncio

import pytest
from fastapi.testclient import TestClient

from app import bot as telegram_bot
from app import main
from app.bot import formatlash, holat
from app.models import ChatJavob, ModdaJavob, OrganJavob
from app.services import javob as javob_xizmati

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def _toza():
    holat.tozala()
    yield
    holat.tozala()


def _modda(matn="Modda matni.", mid="oila-41"):
    return ModdaJavob(
        id=mid, qonun_nomi="O'zbekiston Respublikasining Oila kodeksi",
        modda_raqami="41-modda", sarlavha="41-modda. Sudning nikohdan ajratish asoslari",
        matn=matn, lex_url="https://lex.uz/acts/-104720#-158843", holat="verified",
    )


def _javob(topildi=True, moddalar=None, tavsiya="Sudga murojaat qiling."):
    return ChatJavob(
        javob_topildi=topildi,
        moddalar=moddalar if moddalar is not None else [_modda()],
        tavsiya=tavsiya,
        murojaat=OrganJavob(
            nomi="Fuqarolik ishlari bo'yicha sud", tavsif="Nizolar",
            manzil="Toshkent", telefon="1008", sayt="https://sud.uz",
            kontakt_holati="verified",
        ),
        murojaat_mavzusi="oila",
    )


# ---------- Formatlash ----------

def test_uzun_matn_telegram_chegarasiga_boliadi():
    matn = "\n".join(f"{i}-xatboshi. " + "so'z " * 60 for i in range(60))
    bolaklar = formatlash.bolaklarga_bol(matn)
    assert len(bolaklar) > 1
    assert all(len(b) <= formatlash.XABAR_CHEGARASI for b in bolaklar)


def test_bolish_soz_ortasidan_kesmaydi():
    matn = "so'z " * 3000
    for bolak in formatlash.bolaklarga_bol(matn):
        assert bolak.endswith("so'z") or bolak.endswith("so'z ")


def test_qisqa_matn_bolinmaydi():
    assert formatlash.bolaklarga_bol("qisqa matn") == ["qisqa matn"]
    assert formatlash.bolaklarga_bol("   ") == []


def test_html_belgilari_ekranlanadi():
    """Modda matnidagi < va & Telegram HTML'ini buzmasligi kerak."""
    bolaklar = formatlash.modda_xabari(_modda(matn="Shartnoma <buzilishi> & oqibatlari").model_dump())
    matn = "\n".join(bolaklar)
    assert "&lt;buzilishi&gt;" in matn and "&amp;" in matn


def test_juda_uzun_modda_qisqartirilmaydi():
    """Qonunning asl matni loyihaning asosiy va'dasi — kesib tashlab bo'lmaydi."""
    uzun = "Modda matni. " * 2000
    bolaklar = formatlash.modda_xabari(_modda(matn=uzun).model_dump())
    yigilgan = " ".join(bolaklar)
    assert len(bolaklar) > 1
    # Bo'laklardagi belgilar soni asl matnnikidan kam bo'lmasligi kerak
    assert yigilgan.count("Modda matni.") == 2000


def test_tavsiya_xabarida_organ_va_disclaimer_bor():
    matn = "\n".join(formatlash.tavsiya_xabari(_javob()))
    assert "Sudga murojaat qiling." in matn
    assert "1008" in matn
    assert "professional" in matn  # disclaimer


def test_topilmadi_xabari_halol():
    matn = "\n".join(formatlash.topilmadi_xabari(_javob(topildi=False, moddalar=[])))
    assert "topilmadi" in matn.lower()


# ---------- Holat va cheklovlar ----------

def test_rejim_saqlanadi():
    assert holat.rejim(1) == "oddiy"
    assert holat.rejim_belgila(1, "pro") == "pro"
    assert holat.rejim(1) == "pro"
    assert holat.rejim_belgila(1, "notogri") == "oddiy"


def test_cheklov_chegaradan_keyin_toxtatadi():
    for _ in range(holat.CHEKLOV_CHEGARASI):
        ruxsat, _ = holat.cheklovdan_otdi(7)
        assert ruxsat
    ruxsat, kutish = holat.cheklovdan_otdi(7)
    assert not ruxsat and kutish > 0


def test_cheklov_foydalanuvchilar_orasida_alohida():
    for _ in range(holat.CHEKLOV_CHEGARASI):
        holat.cheklovdan_otdi(1)
    assert holat.cheklovdan_otdi(2)[0]


def test_band_ikkinchi_sorovni_toxtatadi():
    assert holat.band_qil(5)
    assert not holat.band_qil(5)
    holat.bandni_bosat(5)
    assert holat.band_qil(5)


def test_oxirgi_javob_ariza_uchun_saqlanadi():
    holat.javobni_saqla(3, "nikohdan ajrashaman", _javob())
    saqlangan = holat.oxirgi_javob(3)
    assert saqlangan["modda_idlari"] == ["oila-41"]
    assert saqlangan["murojaat_mavzusi"] == "oila"


# ---------- Webhook ----------

def test_webhook_token_yoq_bolsa_404(monkeypatch):
    monkeypatch.setattr(telegram_bot, "mavjud", lambda: False)
    r = client.post(main.WEBHOOK_YOLI, json={"update_id": 1})
    assert r.status_code == 404


def test_webhook_notogri_sir_rad_etiladi(monkeypatch):
    monkeypatch.setattr(telegram_bot, "mavjud", lambda: True)
    monkeypatch.setattr(main, "TELEGRAM_WEBHOOK_SECRET", "maxfiy")
    r = client.post(main.WEBHOOK_YOLI, json={"update_id": 1},
                    headers={"X-Telegram-Bot-Api-Secret-Token": "notogri"})
    assert r.status_code == 403
    r = client.post(main.WEBHOOK_YOLI, json={"update_id": 1})
    assert r.status_code == 403


def test_webhook_darhol_javob_qaytaradi(monkeypatch):
    """Javob tayyorlash 10-15s davom etadi; Telegram kutib qolsa update'ni
    qayta yuboradi va foydalanuvchi bir savolga ikki javob oladi."""
    ishga_tushdi = []
    monkeypatch.setattr(telegram_bot, "mavjud", lambda: True)
    monkeypatch.setattr(main, "TELEGRAM_WEBHOOK_SECRET", "")

    async def soxta(malumot):
        ishga_tushdi.append(malumot)

    monkeypatch.setattr(main, "_updateni_qayta_ishla", soxta)
    r = client.post(main.WEBHOOK_YOLI, json={"update_id": 42, "message": {}})
    assert r.status_code == 200 and r.json() == {"ok": True}


def test_takroriy_update_bir_marta_qayta_ishlanadi():
    telegram_bot._korilgan_update_idlar.clear()
    assert not telegram_bot.takroriy_update(100)
    assert telegram_bot.takroriy_update(100)
    assert not telegram_bot.takroriy_update(101)


# ---------- Handler oqimi ----------

class SoxtaBot:
    def __init__(self):
        self.harakatlar = []

    async def send_chat_action(self, **kw):
        self.harakatlar.append(kw)


class SoxtaXabar:
    """Message'ning handler'lar ishlatadigan qismi."""

    def __init__(self, matn="", chat_id=99):
        self.text = matn
        self.caption = None
        self.chat = type("Chat", (), {"id": chat_id})()
        self.bot = SoxtaBot()
        self.yuborilgan = []
        self.yuborilgan_audio = []

    async def answer(self, matn, reply_markup=None, disable_web_page_preview=None):
        self.yuborilgan.append(matn)
        return self

    async def answer_audio(self, fayl, title=None, caption=None):
        self.yuborilgan_audio.append(fayl)
        return self

    async def delete(self):
        return True


def _ishga_tushir(korutina):
    return asyncio.run(korutina)


def test_savolga_javob_oqimi(monkeypatch):
    from app.bot import handlers

    monkeypatch.setattr(handlers, "javob_ol", lambda *a, **k: _javob())
    monkeypatch.setattr(handlers, "statistikani_yoz", lambda *a, **k: None)
    xabar = SoxtaXabar("Nikohdan qanday ajrashaman?")
    _ishga_tushir(handlers._savolga_javob_ber(xabar, xabar.text))

    matn = "\n".join(xabar.yuborilgan)
    assert "41-modda" in matn          # modda
    assert "Sudga murojaat qiling." in matn  # tavsiya
    assert "1008" in matn              # organ
    assert holat.oxirgi_javob(99)      # ariza uchun saqlandi
    assert holat.band_qil(99)          # band belgisi bo'shatilgan


def test_ai_xatosi_foydalanuvchiga_ozbekcha_yetadi(monkeypatch):
    from app.bot import handlers

    def portla(*a, **k):
        raise javob_xizmati.AiXato(RuntimeError("rate limit 429"))

    monkeypatch.setattr(handlers, "javob_ol", portla)
    xabar = SoxtaXabar("savol")
    _ishga_tushir(handlers._savolga_javob_ber(xabar, "savol"))
    assert any("So'rovlar ko'payib ketdi" in x for x in xabar.yuborilgan)


def test_kutilmagan_xato_botni_jim_qoldirmaydi(monkeypatch):
    from app.bot import handlers

    def portla(*a, **k):
        raise ZeroDivisionError("kutilmagan")

    monkeypatch.setattr(handlers, "javob_ol", portla)
    xabar = SoxtaXabar("savol")
    _ishga_tushir(handlers._savolga_javob_ber(xabar, "savol"))
    assert any("Kutilmagan xatolik" in x for x in xabar.yuborilgan)


def test_xato_bolsa_ham_band_belgisi_bosatiladi(monkeypatch):
    from app.bot import handlers

    monkeypatch.setattr(handlers, "javob_ol", lambda *a, **k: 1 / 0)
    xabar = SoxtaXabar("savol", chat_id=55)
    _ishga_tushir(handlers._savolga_javob_ber(xabar, "savol"))
    assert holat.band_qil(55), "band belgisi bo'shatilmagan — foydalanuvchi bloklanib qoladi"


def test_cheklovdan_otmagan_sorov_llm_ga_bormaydi(monkeypatch):
    from app.bot import handlers

    chaqirildi = []
    monkeypatch.setattr(handlers, "javob_ol", lambda *a, **k: chaqirildi.append(1) or _javob())
    monkeypatch.setattr(handlers, "statistikani_yoz", lambda *a, **k: None)
    for _ in range(holat.CHEKLOV_CHEGARASI):
        holat.cheklovdan_otdi(77)
    xabar = SoxtaXabar("savol", chat_id=77)
    _ishga_tushir(handlers._savolga_javob_ber(xabar, "savol"))
    assert not chaqirildi
    assert any("ko'p so'rov" in x for x in xabar.yuborilgan)


# ---------- Batafsil rejim va xulosa ----------

def test_batafsil_sxemada_xulosa_maydoni_bor():
    from app.services import llm

    oddiy = llm._javob_tool(batafsil=False)["input_schema"]
    batafsil = llm._javob_tool(batafsil=True)["input_schema"]
    assert "xulosa" not in oddiy["properties"]
    assert "xulosa" in batafsil["properties"]
    assert "xulosa" in batafsil["required"]
    assert "xulosa" in llm._gemini_sxema(batafsil=True)["properties"]


def test_batafsil_rejimda_qadamlar_kopayadi():
    from app.services import llm

    oddiy = llm._javob_tool(False)["input_schema"]["properties"]["tavsiya"]
    batafsil = llm._javob_tool(True)["input_schema"]["properties"]["tavsiya"]
    assert batafsil["maxItems"] > oddiy["maxItems"]
    assert batafsil["items"]["maxLength"] > oddiy["items"]["maxLength"]


def test_kesh_kaliti_batafsilni_ajratadi():
    """Botning batafsil javobi saytga (va aksincha) berilmasligi kerak."""
    from app.services import kesh

    qisqa = kesh.kalit("aliment qancha", "oddiy", "v1", batafsil=False)
    uzun = kesh.kalit("aliment qancha", "oddiy", "v1", batafsil=True)
    assert qisqa != uzun


def test_xulosa_javobning_boshida_yuboriladi(monkeypatch):
    from app.bot import handlers

    javob = _javob()
    javob.xulosa = "Qonun bo'yicha siz haqsiz."
    monkeypatch.setattr(handlers, "javob_ol", lambda *a, **k: javob)
    monkeypatch.setattr(handlers, "statistikani_yoz", lambda *a, **k: None)
    xabar = SoxtaXabar("savol", chat_id=101)
    _ishga_tushir(handlers._savolga_javob_ber(xabar, "savol"))

    # Kutish xabaridan keyingi birinchi mazmunli xabar — xulosa
    mazmunli = [x for x in xabar.yuborilgan if x != handlers.KUTING]
    assert "Qonun bo'yicha siz haqsiz." in mazmunli[0]
    assert "41-modda" in mazmunli[1]


def test_xulosa_bosh_bolsa_xabar_yuborilmaydi():
    assert formatlash.xulosa_xabari(_javob()) == []


def test_bot_batafsil_javob_soraydi(monkeypatch):
    """Botda javob har doim batafsil rejimda olinadi."""
    from app.bot import handlers

    chaqiruvlar = []

    def soxta(savol, rejim="oddiy", tarix=None, batafsil=False):
        chaqiruvlar.append(batafsil)
        return _javob()

    monkeypatch.setattr(handlers, "javob_ol", soxta)
    monkeypatch.setattr(handlers, "statistikani_yoz", lambda *a, **k: None)
    _ishga_tushir(handlers._savolga_javob_ber(SoxtaXabar("savol", chat_id=102), "savol"))
    assert chaqiruvlar == [True]


def test_bot_statistikaga_manba_yozadi(monkeypatch):
    from app.bot import handlers

    yozilgan = []
    monkeypatch.setattr(handlers, "javob_ol", lambda *a, **k: _javob())
    monkeypatch.setattr(handlers, "statistikani_yoz", lambda *a: yozilgan.append(a))
    _ishga_tushir(handlers._savolga_javob_ber(SoxtaXabar("savol", chat_id=103), "savol"))
    assert yozilgan[0][4] == "bot"
    assert yozilgan[0][5] is False


# ---------- Ovozli xabar ----------

class SoxtaOvoz:
    def __init__(self, duration=10, file_size=1000, mime_type="audio/ogg"):
        self.duration = duration
        self.file_size = file_size
        self.mime_type = mime_type


class SoxtaOvozliXabar(SoxtaXabar):
    def __init__(self, ovoz_fayl, chat_id=99):
        super().__init__("", chat_id)
        self.voice = ovoz_fayl
        self.audio = None
        self.bot = SoxtaOvozliBot()


class SoxtaOvozliBot(SoxtaBot):
    async def download(self, fayl):
        import io

        return io.BytesIO(b"soxta-opus")


def test_uzun_ovoz_rad_etiladi(monkeypatch):
    from app.bot import handlers

    monkeypatch.setattr(handlers.ovoz, "mavjud", lambda: True)
    xabar = SoxtaOvozliXabar(SoxtaOvoz(duration=300))
    _ishga_tushir(handlers.ovozli_xabar(xabar))
    assert any("juda uzun" in x for x in xabar.yuborilgan)


def test_ovoz_sozlanmagan_bolsa_tushuntiriladi(monkeypatch):
    from app.bot import handlers

    monkeypatch.setattr(handlers.ovoz, "mavjud", lambda: False)
    xabar = SoxtaOvozliXabar(SoxtaOvoz())
    _ishga_tushir(handlers.ovozli_xabar(xabar))
    assert any("matn bilan yozing" in x for x in xabar.yuborilgan)


def test_transkript_foydalanuvchiga_korsatiladi(monkeypatch):
    """Nutq noto'g'ri tanilsa, odam buni javobdan oldin ko'rishi kerak."""
    from app.bot import handlers

    monkeypatch.setattr(handlers.ovoz, "mavjud", lambda: True)
    monkeypatch.setattr(handlers.ovoz, "matnga_ogir", lambda *a, **k: "Ish haqimni bermayapti")
    monkeypatch.setattr(handlers, "javob_ol", lambda *a, **k: _javob())
    monkeypatch.setattr(handlers, "statistikani_yoz", lambda *a: None)
    xabar = SoxtaOvozliXabar(SoxtaOvoz(), chat_id=104)
    _ishga_tushir(handlers.ovozli_xabar(xabar))
    assert any("Ish haqimni bermayapti" in x for x in xabar.yuborilgan)


def test_bosh_transkript_qayta_yozishni_soraydi(monkeypatch):
    from app.bot import handlers

    monkeypatch.setattr(handlers.ovoz, "mavjud", lambda: True)
    monkeypatch.setattr(handlers.ovoz, "matnga_ogir", lambda *a, **k: "")
    chaqirildi = []
    monkeypatch.setattr(handlers, "javob_ol", lambda *a, **k: chaqirildi.append(1))
    xabar = SoxtaOvozliXabar(SoxtaOvoz(), chat_id=105)
    _ishga_tushir(handlers.ovozli_xabar(xabar))
    assert not chaqirildi, "bo'sh transkript bilan LLM'ga borilmasligi kerak"
    assert any("qaytadan" in x for x in xabar.yuborilgan)


def test_ovozli_sorov_statistikada_belgilanadi(monkeypatch):
    from app.bot import handlers

    yozilgan = []
    monkeypatch.setattr(handlers.ovoz, "mavjud", lambda: True)
    monkeypatch.setattr(handlers.ovoz, "matnga_ogir", lambda *a, **k: "Aliment qancha")
    monkeypatch.setattr(handlers, "javob_ol", lambda *a, **k: _javob())
    monkeypatch.setattr(handlers, "statistikani_yoz", lambda *a: yozilgan.append(a))
    _ishga_tushir(handlers.ovozli_xabar(SoxtaOvozliXabar(SoxtaOvoz(), chat_id=106)))
    assert yozilgan[0][5] is True


# ---------- Ovozli javob (TTS) ----------

def _tts_yoq(monkeypatch, handlers, bayt=b"WAV-baytlar"):
    """TTS'ni yoqadi va soxta audio qaytaradi."""
    monkeypatch.setattr(handlers.ovoz, "tts_mavjud", lambda: True)
    monkeypatch.setattr(handlers.ovoz, "ovozga_ogir", lambda matn: (bayt, "audio/wav"))
    monkeypatch.setattr(handlers, "ovozli_javobni_yoz", lambda: None)


def test_ovoz_sozlamasi_uch_holatli():
    assert holat.ovoz_sozlamasi(1) == "avto"
    assert holat.ovoz_belgila(1, "doim") == "doim"
    assert holat.ovoz_sozlamasi(1) == "doim"
    assert holat.ovoz_belgila(1, "notogri") == "avto"


def test_avto_holatda_faqat_ovozli_savolga_ovoz():
    """Matn yozgan odam kutilmagan ovozli xabardan bezovta bo'ladi."""
    assert holat.ovoz_kerakmi(2, ovozli_savol=True)
    assert not holat.ovoz_kerakmi(2, ovozli_savol=False)


def test_doim_holatida_matnli_savolga_ham_ovoz():
    holat.ovoz_belgila(3, "doim")
    assert holat.ovoz_kerakmi(3, ovozli_savol=False)


def test_yoq_holatida_ovozli_savolga_ham_ovoz_yubormaydi():
    holat.ovoz_belgila(4, "yoq")
    assert not holat.ovoz_kerakmi(4, ovozli_savol=True)


def test_ovozli_savolga_ovozli_javob_qoshiladi(monkeypatch):
    from app.bot import handlers

    _tts_yoq(monkeypatch, handlers)
    monkeypatch.setattr(handlers.ovoz, "mavjud", lambda: True)
    monkeypatch.setattr(handlers.ovoz, "matnga_ogir", lambda *a, **k: "Aliment qancha")
    monkeypatch.setattr(handlers, "javob_ol", lambda *a, **k: _javob())
    monkeypatch.setattr(handlers, "statistikani_yoz", lambda *a: None)
    xabar = SoxtaOvozliXabar(SoxtaOvoz(), chat_id=110)
    _ishga_tushir(handlers.ovozli_xabar(xabar))
    assert len(xabar.yuborilgan_audio) == 1


def test_matnli_savolga_ovoz_yuborilmaydi(monkeypatch):
    from app.bot import handlers

    _tts_yoq(monkeypatch, handlers)
    monkeypatch.setattr(handlers, "javob_ol", lambda *a, **k: _javob())
    monkeypatch.setattr(handlers, "statistikani_yoz", lambda *a, **k: None)
    xabar = SoxtaXabar("savol", chat_id=111)
    _ishga_tushir(handlers._savolga_javob_ber(xabar, "savol"))
    assert xabar.yuborilgan_audio == []


def test_tts_xatosi_matnli_javobni_yiqitmaydi(monkeypatch):
    """Ovoz — qo'shimcha. U ishlamasa ham odam javobini olishi shart."""
    from app.bot import handlers

    monkeypatch.setattr(handlers.ovoz, "tts_mavjud", lambda: True)
    monkeypatch.setattr(handlers.ovoz, "ovozga_ogir",
                        lambda matn: (_ for _ in ()).throw(RuntimeError("TTS yiqildi")))
    monkeypatch.setattr(handlers, "javob_ol", lambda *a, **k: _javob())
    monkeypatch.setattr(handlers, "statistikani_yoz", lambda *a, **k: None)
    holat.ovoz_belgila(112, "doim")
    xabar = SoxtaXabar("savol", chat_id=112)
    _ishga_tushir(handlers._savolga_javob_ber(xabar, "savol"))

    matn = "\n".join(xabar.yuborilgan)
    assert "Sudga murojaat qiling." in matn  # matnli javob yetib bordi
    assert xabar.yuborilgan_audio == []


def test_ovozga_faqat_tavsiya_ogiriladi(monkeypatch):
    """Modda matnlari uzun va quruq — audio'ga tushmasligi kerak."""
    from app.bot import handlers

    ogirilgan = []
    monkeypatch.setattr(handlers.ovoz, "tts_mavjud", lambda: True)
    monkeypatch.setattr(handlers.ovoz, "ovozga_ogir",
                        lambda matn: ogirilgan.append(matn) or (b"wav", "audio/wav"))
    monkeypatch.setattr(handlers, "ovozli_javobni_yoz", lambda: None)
    monkeypatch.setattr(handlers, "javob_ol",
                        lambda *a, **k: _javob(moddalar=[_modda(matn="Juda uzun modda matni.")]))
    monkeypatch.setattr(handlers, "statistikani_yoz", lambda *a, **k: None)
    holat.ovoz_belgila(113, "doim")
    _ishga_tushir(handlers._savolga_javob_ber(SoxtaXabar("savol", chat_id=113), "savol"))

    assert ogirilgan == ["Sudga murojaat qiling."]
    assert "Juda uzun modda matni." not in ogirilgan[0]


def test_javob_topilmasa_ovoz_yuborilmaydi(monkeypatch):
    from app.bot import handlers

    _tts_yoq(monkeypatch, handlers)
    monkeypatch.setattr(handlers, "javob_ol", lambda *a, **k: _javob(topildi=False, moddalar=[]))
    monkeypatch.setattr(handlers, "statistikani_yoz", lambda *a, **k: None)
    holat.ovoz_belgila(114, "doim")
    xabar = SoxtaXabar("savol", chat_id=114)
    _ishga_tushir(handlers._savolga_javob_ber(xabar, "savol"))
    assert xabar.yuborilgan_audio == []


def test_ovoz_buyrugi_sozlanmagan_bolsa_tushuntiradi(monkeypatch):
    from app.bot import handlers

    monkeypatch.setattr(handlers.ovoz, "tts_mavjud", lambda: False)
    xabar = SoxtaXabar("/ovoz", chat_id=115)
    _ishga_tushir(handlers.ovoz_buyrugi(xabar))
    assert any("sozlanmagan" in x for x in xabar.yuborilgan)


# ---------- Noma'lum buyruq ----------

def test_notanish_buyruq_llm_ga_bormaydi(monkeypatch):
    """"/ovozz" kabi xato buyruq huquqiy savol sifatida AI'ga yuborilmasin."""
    from app.bot import handlers

    chaqirildi = []
    monkeypatch.setattr(handlers, "javob_ol", lambda *a, **k: chaqirildi.append(1))
    xabar = SoxtaXabar("/ovozz", chat_id=116)
    _ishga_tushir(handlers.notanish_buyruq(xabar))
    assert not chaqirildi
    assert any("Bunday buyruq yo'q" in x for x in xabar.yuborilgan)
