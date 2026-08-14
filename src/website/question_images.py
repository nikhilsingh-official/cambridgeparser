"""Render a question's on-page image straight from the source PDF.

The website offers two views of a question: the reconstructed-from-position
text layer (see :mod:`question_layout`) and a plain *image* of the original
paper. The image view is the trusted default because the positional
reconstruction can misplace or split tokens.

A layout already carries, per page, the ``page_index`` plus the content
``origin``/``width``/``height`` in the shared 794x1123 image coordinate space.
This module renders each PDF page into that exact space and crops it to the
content box, then stitches multi-page questions vertically into one PNG. It is a
thin wrapper over PyMuPDF/Pillow and degrades to ``None`` when the PDF or those
libraries are unavailable, so callers can fall back to the positional view.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

try:  # optional at runtime: rendering is skipped cleanly if unavailable
    import fitz  # PyMuPDF
    from PIL import Image

    _RENDER_AVAILABLE = True
except Exception:  # pragma: no cover - depends on the environment
    _RENDER_AVAILABLE = False

# The layout coordinate space (matches question_layout / qsplitter word boxes).
PAGE_WIDTH = 794.0
PAGE_HEIGHT = 1123.0
# Vertical gap between stitched page crops, in pixels.
PAGE_GAP = 12


def render_available() -> bool:
    return _RENDER_AVAILABLE


class PdfCache:
    """Lazily opens (and reuses) one PDF per paper code."""

    def __init__(self, pdf_dir: Path) -> None:
        self._pdf_dir = pdf_dir
        self._docs: Dict[str, Any] = {}

    def get(self, paper_code: str) -> Optional[Any]:
        if not _RENDER_AVAILABLE:
            return None
        if paper_code not in self._docs:
            path = self._pdf_dir / f"{paper_code}.pdf"
            self._docs[paper_code] = fitz.open(path) if path.is_file() else None
        return self._docs[paper_code]


def _render_page_crop(doc: Any, page: Dict[str, Any]) -> Optional[Any]:
    page_index = page.get("page_index")
    if not isinstance(page_index, int) or page_index < 0 or page_index >= doc.page_count:
        return None

    pdf_page = doc[page_index]
    rect = pdf_page.rect
    if rect.width <= 0 or rect.height <= 0:
        return None

    matrix = fitz.Matrix(PAGE_WIDTH / rect.width, PAGE_HEIGHT / rect.height)
    pix = pdf_page.get_pixmap(matrix=matrix, alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

    origin = page.get("origin") or [0.0, 0.0]
    left, top = float(origin[0]), float(origin[1])
    box = (
        max(0, int(left)),
        max(0, int(top)),
        min(pix.width, int(left + float(page.get("width") or 0))),
        min(pix.height, int(top + float(page.get("height") or 0))),
    )
    if box[2] <= box[0] or box[3] <= box[1]:
        return None
    return img.crop(box)


def render_layout_image(doc: Optional[Any], layout: Optional[Dict[str, Any]]):
    """Render + stitch a layout's pages into one PIL image, or ``None``."""
    if doc is None or not layout:
        return None
    crops = []
    for page in layout.get("pages") or []:
        crop = _render_page_crop(doc, page)
        if crop is not None:
            crops.append(crop)
    if not crops:
        return None

    total_width = max(crop.width for crop in crops)
    total_height = sum(crop.height for crop in crops) + PAGE_GAP * (len(crops) - 1)
    canvas = Image.new("RGB", (total_width, total_height), "white")
    y = 0
    for crop in crops:
        canvas.paste(crop, (0, y))
        y += crop.height + PAGE_GAP
    return canvas


def save_layout_image(
    doc: Optional[Any],
    layout: Optional[Dict[str, Any]],
    images_dir: Path,
    filename: str,
) -> Optional[Dict[str, Any]]:
    """Render a layout to ``images_dir/filename``; return an image descriptor.

    The returned ``src`` is relative to the resources root so the client can
    resolve it as ``<BASE_URL>resources/<src>``.
    """
    image = render_layout_image(doc, layout)
    if image is None:
        return None
    images_dir.mkdir(parents=True, exist_ok=True)
    image.save(images_dir / filename)
    return {"src": f"images/{filename}", "width": image.width, "height": image.height}
