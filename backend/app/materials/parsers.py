from dataclasses import dataclass
from pathlib import Path

from docx import Document
from pptx import Presentation
from pypdf import PdfReader


@dataclass(frozen=True)
class ParsedText:
    content: str
    page_no: int | None = None
    slide_no: int | None = None


SUPPORTED_SUFFIXES = {".txt", ".md", ".docx", ".pdf", ".pptx"}


def parse_material(path: Path, suffix: str) -> list[ParsedText]:
    if suffix in {".txt", ".md"}:
        return _parse_text(path)
    if suffix == ".docx":
        return _parse_docx(path)
    if suffix == ".pdf":
        return _parse_pdf(path)
    if suffix == ".pptx":
        return _parse_pptx(path)
    return []


def _parse_text(path: Path) -> list[ParsedText]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8", errors="ignore")
    return [ParsedText(text)] if text.strip() else []


def _parse_docx(path: Path) -> list[ParsedText]:
    document = Document(path)
    parts: list[str] = []
    parts.extend(paragraph.text for paragraph in document.paragraphs if paragraph.text.strip())
    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                parts.append(" ".join(cells))
    text = "\n".join(parts)
    return [ParsedText(text)] if text.strip() else []


def _parse_pdf(path: Path) -> list[ParsedText]:
    reader = PdfReader(path)
    parsed: list[ParsedText] = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            parsed.append(ParsedText(text, page_no=index))
    return parsed


def _parse_pptx(path: Path) -> list[ParsedText]:
    presentation = Presentation(path)
    parsed: list[ParsedText] = []
    for index, slide in enumerate(presentation.slides, start=1):
        parts: list[str] = []
        for shape in slide.shapes:
            if hasattr(shape, "text") and shape.text.strip():
                parts.append(shape.text.strip())
        text = "\n".join(parts)
        if text.strip():
            parsed.append(ParsedText(text, slide_no=index))
    return parsed
