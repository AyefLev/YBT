from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RenderedPage:
    page_no: int
    image_bytes: bytes
    mime_type: str = "image/png"


def render_pdf_pages_for_vision(
    path: Path,
    *,
    max_pages: int = 12,
    zoom: float = 2.0,
) -> list[RenderedPage]:
    try:
        import fitz  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError("PyMuPDF is required to render scanned PDF pages for vision parsing") from exc

    rendered: list[RenderedPage] = []
    with fitz.open(path) as document:
        matrix = fitz.Matrix(zoom, zoom)
        for page_index, page in enumerate(document, start=1):
            if page_index > max_pages:
                break
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            rendered.append(
                RenderedPage(
                    page_no=page_index,
                    image_bytes=pixmap.tobytes("png"),
                    mime_type="image/png",
                )
            )
    return rendered
