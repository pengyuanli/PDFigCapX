import numpy as np
from src.models import TextBox, Layout, Region, Bbox, Figure, AlignmentType
from src.page import HtmlPage
from src.utils import overlap_ratio_based
from typing import List, Tuple
from copy import copy, deepcopy
import logging

from enum import Enum


class SweepType(Enum):
    CAPTIONS_OVER_FIGURES = 1
    CAPTIONS_BELOW_FIGURES = 2
    CAPTIONS_NEXT_TO_FIGURES = 3


NOT_SUPPORTED = (
    "skipping page: calculations do not support PDFs with more than 2 columns"
)


def is_multicol_caption(box: TextBox, layout: Layout):
    ROW_EXTRA = layout.row_width / 5
    x0_2nd_col = layout.col_coords[1]

    if (
        box.x < x0_2nd_col and box.x1 > x0_2nd_col
    ):  # or box.x > x0_2nd_col:  + ROW_EXTRA:
        return True
    return False


def estimate_caption_regions_top(
    captions: List[TextBox], layout: Layout
) -> List[Region]:
    """Estimate the regions on top of a potential caption sentence. These
    regions serve to indicate the potential locations of figures assuming
    that these captions appear below the figure.
    The estimations are performed using a vertical sweep from top to bottom
    such that regions are assigned only to one caption box.
    """
    if len(captions) == 0:
        return []

    regions = []
    if layout.num_cols == 1:
        vert_sweep = 1  # sweep through the whole row
        sorted_captions = sorted(captions, key=lambda x: x.y)
        for caption in sorted_captions:
            bbox = Bbox(1, 1, layout.width - 2, caption.y - vert_sweep)
            regions.append(Region(bbox, caption, False))
            vert_sweep = caption.y1
    elif layout.num_cols == 2:
        sweep = [layout.content_region.y] * layout.num_cols
        sorted_captions = sorted(captions, key=lambda x: (x.y, x.x))
        for caption in sorted_captions:
            is_multicol = is_multicol_caption(caption, layout)
            if is_multicol:
                x = layout.content_region.x
                y = sweep[0]
                w = layout.content_region.width
                h = caption.y - sweep[0]
                sweep[0] = caption.y1
                sweep[1] = caption.y1
            else:
                x = caption.x
                if caption.x < layout.col_coords[1]:
                    y = sweep[0]
                    w = layout.col_coords[1] - layout.col_coords[0]
                    h = caption.y - sweep[0]
                    sweep[0] = caption.y1
                else:
                    y = sweep[1]
                    w = layout.content_region.x1 - caption.x
                    h = caption.y - sweep[1]
                    sweep[1] = caption.y1
            bbox = Bbox(x, y, w, h)
            regions.append(Region(bbox, caption, is_multicol))
    else:
        logging.info(f"{NOT_SUPPORTED}")
        print(NOT_SUPPORTED)

    return regions


def estimate_caption_regions_bottom(
    captions: list[TextBox], layout: Layout
) -> List[Region]:
    """Estimate the regions below a potential caption sentence. The sweep is
    done from bottom to top to avoid issues with multicolumn and single
    column figures in a same page.
    """
    if len(captions) == 0:
        return []

    regions = []
    if layout.num_cols == 1:
        vert_sweep = layout.content_region.y1  # bottom
        sorted_captions = sorted(captions, key=lambda x: x.y, reverse=True)
        for caption in sorted_captions:
            bbox = Bbox(
                layout.col_coords[0], caption.y1, layout.width, vert_sweep - caption.y
            )
            regions.append(Region(bbox, caption, False))
            vert_sweep = caption.y
    elif layout.num_cols == 2:
        sweep = [layout.content_region.y1] * layout.num_cols
        sorted_captions = sorted(captions, key=lambda x: (x.y, x.x), reverse=True)
        for caption in sorted_captions:
            is_multicol = is_multicol_caption(caption, layout)
            if is_multicol:
                x = layout.col_coords[0]
                y = caption.y1
                w = layout.width
                h = sweep[0] - caption.y
                sweep[0] = caption.y
                sweep[1] = caption.y
            else:
                x = caption.x
                y = caption.y1
                if caption.x < layout.col_coords[1]:
                    w = layout.col_coords[1] - layout.col_coords[0]
                    h = sweep[0] - caption.y1
                    sweep[0] = caption.y
                else:
                    w = layout.content_region.x1 - caption.x
                    h = sweep[1] - caption.y1
                    sweep[1] = caption.y
            bbox = Bbox(x, y, w, h)
            regions.append(Region(bbox, caption, is_multicol))
    else:
        logging.info(f"{NOT_SUPPORTED}")
        print(NOT_SUPPORTED)

    return regions


def estimate_caption_regions_side(
    captions: list[TextBox], layout: Layout, greedy=False
) -> List[Region]:
    """Estimate the regions when the caption is to the right or left of the
    figure. These cases contemplate only multi-column figures because
    side captions on a single column may be unfeasible due to space
    contraints.
    """
    if len(captions) == 0:
        return []
    regions = []
    # start at bottom to sweep bottom - up
    vert_sweep = layout.content_region.y1  # bottom
    sorted_captions = sorted(captions, key=lambda x: (x.y, x.x), reverse=True)
    mid_point = (
        layout.col_coords[0] + layout.row_width / 2
        if layout.num_cols == 1
        else layout.col_coords[1]
    )

    for idx, caption in enumerate(sorted_captions):
        if idx == len(sorted_captions) - 1:
            # check all the way up for the last caption
            y = layout.content_region.y
        else:
            if greedy:
                y = layout.y
            else:
                y = caption.y
        h = vert_sweep - y
        if caption.x < mid_point:  # caption on the left
            x = caption.x1
            w = layout.content_region.width - caption.width
        else:
            x = layout.content_region.x
            w = caption.x - layout.content_region.x
        vert_sweep = caption.y
        bbox = Bbox(x, y, w, h)
        regions.append(Region(bbox, caption, True))

    return regions


def style_cut(bbox: Bbox, caption: TextBox, sweep_type: SweepType, layout: Layout):
    """Adjust the borders of the figure box in an attempt to avoid losing
    labels not captured by the contours.
    TODO: Use the y value from text components to check if there is anything
    over the figure and below the top content region margin
    """
    out_bbox = deepcopy(bbox)
    threshold_top = 40
    x_padding = 5

    x0 = bbox.x - x_padding if bbox.x - x_padding >= 0 else layout.content_region.x
    x1 = (
        bbox.x1 + x_padding
        if bbox.x1 + x_padding <= layout.content_region.x1
        else layout.content_region.x1
    )

    if sweep_type == SweepType.CAPTIONS_BELOW_FIGURES:
        # check if there is anything above
        out_bbox.y1 = max(bbox.y1, caption.y - 1)

        if abs(layout.content_region.y - out_bbox.y) < threshold_top:
            out_bbox.y = layout.content_region.y + layout.row_height
        else:
            out_bbox.y -= layout.row_height
    elif sweep_type == SweepType.CAPTIONS_OVER_FIGURES:
        out_bbox.y = min(bbox.y, caption.y - layout.row_height)
        out_bbox.y1 += layout.row_height
    else:
        out_bbox.y1 = max(out_bbox.y1, caption.y1)

    out_bbox.x = x0
    out_bbox.x1 = x1
    out_bbox.update_width()
    out_bbox.update_height()
    return out_bbox


def match_figures_with_captions(
    regions: List[Region], candidates: List[Bbox], sweep_type: str, layout: Layout
) -> Tuple[List[Figure], List[TextBox], List[Bbox]]:
    """Match candidate regions for captions to candidate figures per page"""
    # change the logic here. Every candidate figure inside the region can be
    # merged and be considered a figure.
    figures = []
    unmatched_caption_boxes = []
    idxs_to_remove = []
    for region in regions:
        # keep index for easy removal
        sparse_figures = [
            (idx, x)
            for idx, x in enumerate(candidates)
            if overlap_ratio_based(x, region.bbox) > 0.5
            or overlap_ratio_based(region.bbox, x) > 0.5
        ]
        bboxes = [x[1] for x in sparse_figures]

        if len(sparse_figures) > 1:
            # check whether region is single column, but image is multicolumn
            bbox = Bbox.merge_bboxes(bboxes)
            bbox = style_cut(bbox, region.caption, sweep_type, layout)

            is_multicol = region.multicolumn
            if (
                not is_multicol
                and layout.num_cols == 2
                and bbox.x1 > layout.col_coords[1]
            ):
                is_multicol = True

            figure = Figure(
                bbox=bbox,
                caption=region.caption,
                multicolumn=is_multicol,
                sweep_type=sweep_type,
            )
            figures.append(figure)
            idxs_to_remove += [x[0] for x in sparse_figures]
        else:
            unmatched_caption_boxes.append(region.caption)

    remaining_candidates = [
        x for idx, x in enumerate(candidates) if idx not in idxs_to_remove
    ]
    return figures, unmatched_caption_boxes, remaining_candidates


def greedy_swap(
    page: HtmlPage, caption: TextBox, candidates: List[Bbox], layout: Layout
):
    """Match the caption with the region with the highest overlap between the
    region and the candidate bounding boxes.
    """
    regions_top = estimate_caption_regions_top([caption], layout)
    regions_bottom = estimate_caption_regions_bottom([caption], layout)
    regions_side = estimate_caption_regions_side([caption], layout, greedy=True)
    overlaps = np.array([0, 0, 0])
    regions = [regions_top[0], regions_bottom[0], regions_side[0]]

    bboxes = [None, None, None]
    for idx, region in enumerate(regions):
        filtered_candidates = [
            c for c in candidates if overlap_ratio_based(c, region.bbox) > 0.1
        ]
        if len(filtered_candidates) > 0:
            bboxes[idx] = Bbox.merge_bboxes(filtered_candidates)
            overlaps[idx] = region.bbox.intersect_area(bboxes[idx])
        else:
            overlaps[idx] = 0

    max_region_idx = overlaps.argmax()

    if bboxes[max_region_idx] is not None:
        caption = regions[max_region_idx].caption

        figure = Figure(
            bboxes[max_region_idx],
            region.multicolumn,
            caption,
            f"unique_{max_region_idx}",
        )
        figure.identifier = regions[max_region_idx].caption.get_caption_identifier()

        if max_region_idx == 0:  # image on top
            # sometimes text between figure and text is not captured by
            # the bounding box because it's not graphical content but text
            figure.bbox.y1 = max(caption.y - layout.row_height, figure.bbox.y1)
            # move y a bit up in case we are missing any text
            figure.bbox.y = _max_any_text_above(page, figure.bbox, layout, caption)
        elif max_region_idx == 2:
            figure.bbox.y = min(figure.bbox.y, caption.y - layout.row_height)
            figure.bbox.update_height()
            return figure

        if caption.alignment == AlignmentType.LEFT:
            figure.bbox.x = layout.content_region.x
            figure.bbox.x1 = layout.col_coords[1]
        elif caption.alignment == AlignmentType.RIGHT:
            figure.bbox.x = layout.col_coords[1]
            figure.bbox.x1 = max(layout.content_region.x1, figure.bbox.x1)
        else:  # AlignmentType.MULTICOLUMN
            figure.bbox.x = max(layout.content_region.x, min(figure.bbox.x, caption.x))
            figure.bbox.x1 = _min_any_text_to_the_right(page, figure.bbox, caption)
        figure.bbox.update_height()
        figure.bbox.update_width()
        return figure
    else:
        return None


def _max_any_text_above(
    page: HtmlPage, bbox: Bbox, layout: Layout, caption: TextBox
) -> int:
    if caption.alignment == AlignmentType.RIGHT:
        min_x = layout.col_coords[1]
        max_x = layout.content_region.x1
    elif caption.alignment == AlignmentType.LEFT:
        min_x = layout.content_region.x
        max_x = layout.col_coords[1]
    else:
        min_x = layout.content_region.x
        max_x = layout.content_region.x1

    text_boxes = [
        tb
        for tb in page.text_boxes
        if tb.y1 < bbox.y - 2 * layout.row_height and tb.x >= min_x and tb.x1 <= max_x
        # this last option can be better optimized, probably I need to label
        # the text to know if it's part of a paragraph or a title to avoid them
        and tb.width > bbox.width / 2
    ]
    max_y1 = None
    if len(text_boxes) > 0:
        text_boxes = sorted(text_boxes, key=lambda el: el.y1, reverse=True)
        max_y1 = text_boxes[0].y1 + 1
    else:
        max_y1 = max(bbox.y - 5 * layout.row_height, layout.content_region.y)
    return max_y1


def _min_any_text_to_the_right(page: HtmlPage, bbox: Bbox, caption: TextBox) -> int:
    """For multicolumn figures, check if there is any idented text to the right.
    It's not usual but some publications ident text with a row width smaller than
    the regular column width
    return:
    right margin for the figure
    """
    text_boxes = [
        tb
        for tb in page.text_boxes
        if tb.x > bbox.x1 and tb.y > bbox.y and tb.y1 < bbox.y1
    ]
    min_x1 = None
    if len(text_boxes) > 0:
        text_boxes = sorted(text_boxes, key=lambda el: el.x)
        min_x1 = text_boxes[0].x
    else:
        min_x1 = bbox.x1
    # but always consider the caption length
    return max(caption.x1, min_x1)


def get_figures(
    page: HtmlPage,
    candidates: List[Bbox],
    captions: List[TextBox],
    layout: Layout,
    sweep_type: str,
) -> Tuple[List[Figure], List[TextBox], List[Bbox]]:

    if len(captions) == 1 and len(candidates) > 0:
        figure = greedy_swap(page, captions[0], candidates, layout)
        if figure:
            return [figure], [], []
        else:
            return [], captions, candidates

    if sweep_type == SweepType.CAPTIONS_BELOW_FIGURES:
        regions = estimate_caption_regions_top(captions, layout)
    elif sweep_type == SweepType.CAPTIONS_OVER_FIGURES:
        regions = estimate_caption_regions_bottom(captions, layout)
    elif sweep_type == SweepType.CAPTIONS_NEXT_TO_FIGURES:
        regions = estimate_caption_regions_side(captions, layout)
    else:
        raise Exception(f"Sweep {sweep_type} not supported")
    figures, remaining_captions, remaning_candidates = match_figures_with_captions(
        regions, candidates, sweep_type, layout
    )
    return figures, remaining_captions, remaning_candidates


def sweep_regions(
    page: HtmlPage,
    candidates: List[Bbox],
    fig_captions: List[TextBox],
    table_captions: List[TextBox],
    layout: Layout,
):
    sweep_strategy: List[Tuple[SweepType, str]] = [
        (SweepType.CAPTIONS_BELOW_FIGURES, "figures"),
        (SweepType.CAPTIONS_OVER_FIGURES, "figures"),
        (SweepType.CAPTIONS_NEXT_TO_FIGURES, "figures"),
    ]

    remaining_candidates = deepcopy(candidates)
    remaining_captions = deepcopy(fig_captions)
    for strategy, _ in sweep_strategy:
        figures, remaining_captions, remaining_candidates = get_figures(
            page, remaining_candidates, remaining_captions, layout, strategy
        )
        if figures and len(figures) > 0:
            page.figures += figures
        if len(remaining_captions) == 0:
            break

    # saving orphans
    if len(remaining_candidates) > 0:
        orphan_bbox = Bbox.merge_bboxes(remaining_candidates)
        page.orphan_figure = Figure(
            bbox=orphan_bbox, sweep_type="orphan", multicolumn=True, caption=None
        )
    if len(remaining_captions) > 0:
        page.orphan_captions += remaining_captions
