from pathlib import Path
from cv2 import (
    imread,
    cvtColor,
    dilate,
    findContours,
    threshold,
    boundingRect,
    COLOR_BGR2GRAY,
    THRESH_BINARY_INV,
    CHAIN_APPROX_SIMPLE,
    RETR_TREE,
    Mat,
)
from numpy import ones, uint8
from src.page import HtmlPage
from src.models import Bbox, Layout


def overlap_ratio_based(box1: Bbox, box2: Bbox) -> float:
    # overlap ratio based on box1
    SI = max(0, min(box1.x1, box2.x1) - max(box1.x, box2.x)) * max(
        0, min(box1.y1, box2.y1) - max(box1.y, box2.y)
    )
    box1_area = box1.width * box1.height
    if box1_area == 0:
        overlap_ratio = 0
    else:
        overlap_ratio = float(SI) / box1_area
    return overlap_ratio


def calc_scaling_factor(image: Mat, page_width: int, page_height: int) -> float:
    # the PNG may be bigger than the html size
    height, width, _ = image.shape
    if height > width:
        return float(height) / page_height
    else:
        return float(width) / page_width


def get_potential_figure_bboxes(base_folder_path: str, page: HtmlPage, layout: Layout):
    """Process the page image to find potential contours that hold figures"""
    LAYOUT_MARGIN = 10
    figure_boxes, table_boxes = page.find_caption_boxes()

    png_path = str((Path(base_folder_path) / page.img_name).resolve())
    page_image = imread(png_path)
    page_image_gray = cvtColor(page_image, COLOR_BGR2GRAY)
    # match PNG and html sizes
    scaling = calc_scaling_factor(page_image, page.width, page.height)

    _, thresh = threshold(page_image_gray, 240, 255, THRESH_BINARY_INV)
    kernel = ones((5, 5), uint8)
    dilation = dilate(thresh, kernel, iterations=1)
    contours, _ = findContours(dilation, RETR_TREE, CHAIN_APPROX_SIMPLE)
    # canvas_with_contours = np.zeros(thresh.shape, dtype=np.uint8)

    candidate_bboxes = []  # for candidate figures or tables
    for cnt in contours:
        cnt_bbox = boundingRect(cnt)
        scaled_cnt_bbox = Bbox(**[int(float(x) / scaling) for x in cnt_bbox])
        overlap_w_captions = 0
        for caption_box in figure_boxes:
            overlap_w_captions += overlap_ratio_based(caption_box, scaled_cnt_bbox)
        overlap_w_layout = overlap_ratio_based(layout, scaled_cnt_bbox)

        if (
            overlap_w_captions < 0.5
            and overlap_w_layout < 0.2
            and scaled_cnt_bbox.y >= layout.content_region.y - LAYOUT_MARGIN
            and scaled_cnt_bbox.height > layout.row_height
        ):
            # cv2.drawContours(canvas_with_contours, [cnt], 0, 255, -1)
            candidate_bboxes.append(scaled_cnt_bbox)

    return candidate_bboxes, figure_boxes, table_boxes
