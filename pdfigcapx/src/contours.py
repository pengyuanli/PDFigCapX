from pathlib import Path
from typing import Tuple, List
from cv2 import (
    imread,
    cvtColor,
    dilate,
    findContours,
    threshold,
    boundingRect,
    drawContours,
    COLOR_BGR2GRAY,
    THRESH_BINARY_INV,
    CHAIN_APPROX_SIMPLE,
    RETR_TREE,
    FILLED,
    Mat,
)
from numpy import ones, uint8, zeros, array
from PIL import Image
from copy import copy
from src.page import HtmlPage
from src.models import Bbox, Layout, TextBox
from src.utils import overlap_ratio_based


def calc_scaling_factor(image: Mat, page_width: int, page_height: int) -> float:
    # the PNG may be bigger than the html size
    height, width, _ = image.shape
    if height > width:
        return float(height) / page_height
    else:
        return float(width) / page_width


def scaled_bbox(cnt, scaling) -> Bbox:
    cnt_bbox = boundingRect(cnt)
    return Bbox(*[int(float(x) / scaling) for x in cnt_bbox])


def merge_candidate_bboxes(bboxes: List[Bbox]) -> Bbox:
    x0 = min([el.x for el in bboxes])
    y0 = min([el.y for el in bboxes])
    x1 = max([el.x1 for el in bboxes])
    y1 = max([el.y1 for el in bboxes])
    return Bbox(x0, y0, x1 - x0, y1 - y0)


def get_potential_contours(
    base_folder_path: str, page: HtmlPage, layout: Layout, captions: List[TextBox]
) -> Tuple[List[Bbox], Image.Image]:
    """Find every contour in the page that could represent a publication figure
    or a section of a publication figure"""
    LAYOUT_MARGIN = 10

    png_path = str((Path(base_folder_path) / page.img_name).resolve())
    page_image = imread(png_path)
    page_image_gray = cvtColor(page_image, COLOR_BGR2GRAY)
    # match PNG and html sizes
    scaling = calc_scaling_factor(page_image, page.width, page.height)

    _, thresh = threshold(page_image_gray, 240, 255, THRESH_BINARY_INV)
    kernel = ones((5, 5), uint8)
    dilation = dilate(thresh, kernel, iterations=1)
    contours, _ = findContours(dilation, RETR_TREE, CHAIN_APPROX_SIMPLE)

    # merge contours based on multicolumn
    cnts = [scaled_bbox(el, scaling) for el in contours]
    if layout.num_cols == 2:
        idxs_groups_merge = []
        x_cross = layout.col_coords[1]
        cr_width = layout.content_region.width
        cr_x = layout.content_region.x

        for i, cnt in enumerate(cnts):
            if cnt.x < x_cross and cnt.x1 > x_cross:
                idxs_merge = [i]
                for j, cnt_eval in enumerate(cnts):
                    if cnt != cnt_eval:
                        row_region = Bbox(cr_x, cnt.y, cr_width, cnt.height)
                        if (
                            overlap_ratio_based(cnt_eval, row_region) > 0
                            or overlap_ratio_based(row_region, cnt_eval) > 0
                        ):
                            idxs_merge.append(j)
                if len(idxs_merge) > 1:
                    idxs_groups_merge.append(idxs_merge)

        idxs_not_merge = [x for x in range(len(cnts))]
        affected_ids = [idx for group in idxs_groups_merge for idx in group]
        idxs_not_merge = set(idxs_not_merge).difference(set(affected_ids))

        merged_cnts = [cnts[i] for i in idxs_not_merge]
        for idxs_group in idxs_groups_merge:
            bboxes_to_merge = [cnts[i] for i in idxs_group]
            merged_cnts.append(merge_candidate_bboxes(bboxes_to_merge))
        cnts = merged_cnts

    # remove scaling here
    candidate_bboxes = []  # for candidate figures or tables
    for cnt in cnts:
        overlap_w_captions = 0
        for caption_box in captions:
            overlap_w_captions += overlap_ratio_based(caption_box, cnt)
        overlap_w_layout = overlap_ratio_based(layout.content_region, cnt)

        if (
            overlap_w_captions < 0.5
            # and overlap_w_layout < 0.2
            and cnt.y >= layout.content_region.y - LAYOUT_MARGIN
            and cnt.height > layout.row_height
        ):
            candidate_bboxes.append(cnt)

    return candidate_bboxes, cnts
