from typing import Any, List

BBox = List[float]


def combine_bboxes(bboxes: List[BBox]) -> BBox:
    xs = [bbox[0] for bbox in bboxes] + [bbox[2] for bbox in bboxes]
    ys = [bbox[1] for bbox in bboxes] + [bbox[3] for bbox in bboxes]
    return [min(xs), min(ys), max(xs), max(ys)]


def bbox_intersects(left: BBox, right: BBox) -> bool:
    return not (
        left[2] <= right[0]
        or left[0] >= right[2]
        or left[3] <= right[1]
        or left[1] >= right[3]
    )


def scale_pdf_bbox(pdf_bbox: List[float], pdf_rect: Any, image_bbox: BBox) -> BBox:
    x_scale = (image_bbox[2] - image_bbox[0]) / pdf_rect.width
    y_scale = (image_bbox[3] - image_bbox[1]) / pdf_rect.height
    return [
        pdf_bbox[0] * x_scale,
        pdf_bbox[1] * y_scale,
        pdf_bbox[2] * x_scale,
        pdf_bbox[3] * y_scale,
    ]
