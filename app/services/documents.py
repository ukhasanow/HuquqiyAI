# Yuklangan hujjatdan (PDF/DOCX) matn ajratish
import io

from ..config import MAX_HUJJAT_BELGILAR


class HujjatXato(Exception):
    """Hujjatni o'qib bo'lmaganda ko'tariladi."""


def matn_ajrat(fayl_nomi: str, bayt: bytes) -> str:
    nomi = fayl_nomi.lower()
    if nomi.endswith(".pdf"):
        matn = _pdf_matn(bayt)
    elif nomi.endswith(".docx"):
        matn = _docx_matn(bayt)
    elif nomi.endswith(".txt"):
        matn = bayt.decode("utf-8", errors="replace")
    else:
        raise HujjatXato("Faqat PDF, DOCX yoki TXT fayllar qabul qilinadi.")

    matn = matn.strip()
    if not matn:
        raise HujjatXato(
            "Hujjatdan matn ajratib bo'lmadi. Ehtimol bu skanerlangan rasm — "
            "matnli hujjat yuklang."
        )
    return matn[:MAX_HUJJAT_BELGILAR]


def _pdf_matn(bayt: bytes) -> str:
    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(bayt))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as e:
        raise HujjatXato(f"PDF faylni o'qib bo'lmadi: {e}")


def _docx_matn(bayt: bytes) -> str:
    import docx

    try:
        d = docx.Document(io.BytesIO(bayt))
        qismlar = [p.text for p in d.paragraphs]
        for jadval in d.tables:
            for qator in jadval.rows:
                qismlar.extend(katak.text for katak in qator.cells)
        return "\n".join(qismlar)
    except Exception as e:
        raise HujjatXato(f"DOCX faylni o'qib bo'lmadi: {e}")
