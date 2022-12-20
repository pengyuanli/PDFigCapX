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
    RETR_EXTERNAL,
    Mat,
)
from numpy import ones, uint8, zeros, array
from PIL import Image
from copy import copy, deepcopy
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


def get_candidates(
    base_folder_path: str, page: HtmlPage, layout: Layout, captions: List[TextBox]
) -> Tuple[List[Bbox], List[Bbox], List[Bbox]]:
    """Find every contour in the page that could represent a publication figure
    or a section of a publication figure"""
    LAYOUT_MARGIN = 10

    png_path = str((Path(base_folder_path) / page.img_name).resolve())
    page_image = imread(png_path)
    page_image_gray = cvtColor(page_image, COLOR_BGR2GRAY)
    # match PNG and html sizes
    scaling = calc_scaling_factor(page_image, page.width, page.height)
    # scaling = calc_scaling_factor(page_image, layout.width, layout.height)

    _, thresh = threshold(page_image_gray, 240, 255, THRESH_BINARY_INV)
    kernel = ones((5, 5), uint8)
    dilation = dilate(thresh, kernel, iterations=1)
    contours, _ = findContours(dilation, RETR_EXTERNAL, CHAIN_APPROX_SIMPLE)

    # for cnt in contours:
    #     drawContours(canvas, [cnt], 0, 255, -1)
    # contours, _ = findContours(canvas, RETR_EXTERNAL, CHAIN_APPROX_SIMPLE)

    # merge contours based on multicolumn
    cnts = [scaled_bbox(el, scaling) for el in contours]
    cnts = [
        cnt for cnt in cnts if overlap_ratio_based(cnt, layout.content_region) > 0.75
    ]
    orig_cnts = deepcopy(cnts)
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
                        if row_region.intersect_area(cnt_eval) > 0:
                            idxs_merge.append(j)
                if len(idxs_merge) > 1:
                    idxs_groups_merge.append(idxs_merge)

        idxs_not_merge = [x for x in range(len(cnts))]
        affected_ids = [idx for group in idxs_groups_merge for idx in group]
        idxs_not_merge = set(idxs_not_merge).difference(set(affected_ids))

        merged_cnts = [cnts[i] for i in idxs_not_merge]
        for idxs_group in idxs_groups_merge:
            bboxes_to_merge = [cnts[i] for i in idxs_group]
            merged_cnts.append(Bbox.merge_bboxes(bboxes_to_merge))
        cnts = merged_cnts

    # remove scaling here
    candidate_bboxes = []  # for candidate figures or tables
    for cnt in cnts:
        for caption_box in captions:
            intersect_bbox = caption_box.intersect(cnt)
            if intersect_bbox is not None:
                if cnt.x < caption_box.x:
                    cnt.x1 = intersect_bbox.x
                else:
                    cnt.x = intersect_bbox.x1
                cnt.update_width()

        if (
            cnt.y >= layout.content_region.y - LAYOUT_MARGIN
            and cnt.height > layout.row_height
        ):
            candidate_bboxes.append(cnt)

    return candidate_bboxes, cnts, orig_cnts
