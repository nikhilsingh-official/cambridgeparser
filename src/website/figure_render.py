"""Render a sub-region of a question-paper page straight from the PDF.

Figures, diagrams and tables are never reconstructed as text; they are shown as
crisp crops taken from the source PDF. Region coordinates arrive in the shared
image space (e.g. 794x1123 for A4 at 96 DPI); this module maps them back to PDF
points and rasterises just that clip at a higher zoom for a sharp image.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence, Tuple

import fitz

# Fallback A4-at-96-DPI page size, used only when the real image page size is
# unknown. The renderer prefers the caller-supplied page size.
DEFAULT_IMAGE_PAGE = (794.0, 1123.0)


def render_region_png(
    pdf_path: Path,
    page_index: int,
    bbox_image_space: Sequence[float],
    image_page_size: Tuple[float, float] = DEFAULT_IMAGE_PAGE,
    zoom: float = 2.0,
) -> bytes:
    """Rasterise ``bbox_image_space`` from ``page_index`` of the PDF as PNG bytes."""

    document = fitz.open(pdf_path)
    try:
        page = document.load_page(page_index)
        image_w, image_h = image_page_size
        scale_x = page.rect.width / image_w if image_w else 1.0
        scale_y = page.rect.height / image_h if image_h else 1.0

        x0, y0, x1, y1 = bbox_image_space
        clip = fitz.Rect(
            x0 * scale_x, y0 * scale_y, x1 * scale_x, y1 * scale_y
        ) & page.rect
        # Output pixels = image-space units * zoom (matrix cancels the pt scale).
        matrix = fitz.Matrix(zoom / scale_x, zoom / scale_y)
        pixmap = page.get_pixmap(matrix=matrix, clip=clip, alpha=False)
        return pixmap.tobytes("png")
    finally:
        document.close()
