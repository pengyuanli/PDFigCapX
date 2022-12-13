import numpy as np
from src.models import TextBox, Layout, Region, Bbox, Figure
from src.page import HtmlPage
from src.utils import overlap_ratio_based
from typing import List, Tuple
from copy import copy, deepcopy

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


def merge_candidate_bboxes(bboxes: List[Bbox]) -> Bbox:
    x0 = min([el.x for el in bboxes])
    y0 = min([el.y for el in bboxes])
    x1 = max([el.x1 for el in bboxes])
    y1 = max([el.y1 for el in bboxes])
    return Bbox(x0, y0, x1 - x0, y1 - y0)


CAPTIONS_BELOW_FIGURES = "captions_below_figures"
CAPTIONS_OVER_FIGURES = "captions_over_figures"


def style_cut(bbox: Bbox, caption: TextBox, sweep_type: str, layout: Layout):
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

    if sweep_type == CAPTIONS_BELOW_FIGURES:
        # check if there is anything above
        out_bbox.y1 = max(bbox.y1, caption.y - 1)

        if abs(layout.content_region.y - out_bbox.y) < threshold_top:
            out_bbox.y = layout.content_region.y + layout.row_height
        else:
            out_bbox.y -= layout.row_height
    elif sweep_type == CAPTIONS_OVER_FIGURES:
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
            bbox = merge_candidate_bboxes(bboxes)
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


def expand_captions(
    page: HtmlPage, figures: List[Figure], row_height: int, type="figure"
) -> List[Figure]:
    """Search in the page for the next sentences to complement the caption"""
    for figure in figures:
        figure.identifier = figure.caption.get_caption_identifier(type=type)
        sentences = [
            box
            for box in page.text_boxes
            if box.y > figure.caption.y and abs(figure.caption.x - box.x) < 10
        ]
        sentences = sorted(sentences, key=lambda x: x.y)
        vertical = figure.caption.y1

        for sentence in sentences:
            if abs(sentence.y - vertical) < row_height:
                figure.caption.width = (
                    figure.caption.width
                    if figure.caption.width >= sentence.width
                    else sentence.width
                )
                figure.caption.height += sentence.height
                # TODO: fix - symbols when breaking lines
                figure.caption.text += f" {sentence.text}"
                vertical = sentence.y1
            else:
                break
    return figures


def calc_intersection_area(box1: Bbox, box2: Bbox):
    x = max(box1.x, box2.x)
    y = max(box1.y, box2.y)
    w = min(box1.x + box1.width, box2.x + box2.width) - x
    h = min(box1.y + box1.height, box2.y + box2.height) - y

    if w < 0 or h < 0:
        return 0.0
    else:
        return w * h


# TODO: ignore first page, find why i am not loading the figures without captions
def greedy_swap(caption, candidates, layout):
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
            bboxes[idx] = merge_candidate_bboxes(filtered_candidates)
            overlaps[idx] = calc_intersection_area(region.bbox, bboxes[idx])
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
        print(figure.bbox)
        figure.identifier = regions[max_region_idx].caption.get_caption_identifier()

        if not is_multicol_caption(caption, layout) and max_region_idx != 2:
            if caption.x1 <= layout.col_coords[1]:
                figure.bbox.x = layout.col_coords[0] - layout.col_coords[0] / 4
                figure.bbox.x1 = layout.col_coords[1]
                figure.bbox.update_width()
            else:
                figure.bbox.x = layout.col_coords[1]
                figure.bbox.x1 = layout.content_region.x1 + layout.col_coords[0] / 4
                figure.bbox.update_width()
        else:
            if region.multicolumn and max_region_idx != 2:
                # check versus the expanded caption
                figure.bbox.x = layout.content_region.x
                figure.bbox.x1 = layout.width
                figure.bbox.update_width()
        return figure
    else:
        return None


def get_figures(
    page: HtmlPage,
    candidates: List[Bbox],
    captions: List[TextBox],
    layout: Layout,
    sweep_type: str,
) -> Tuple[List[Figure], List[TextBox], List[Bbox]]:

    print(page.number)
    if len(captions) == 1 and len(candidates) > 0:
        figure = greedy_swap(captions[0], candidates, layout)
        if figure:
            return [figure], [], []
        else:
            return [], captions, candidates

    if sweep_type == "captions_below_figures":
        regions = estimate_caption_regions_top(captions, layout)
    elif sweep_type == "captions_over_figures":
        regions = estimate_caption_regions_bottom(captions, layout)
    elif sweep_type == "captions_next_to_figures":
        regions = estimate_caption_regions_side(captions, layout)
    else:
        raise Exception(f"Sweep {sweep_type} not supported")
    figures, remaining_captions, remaning_candidates = match_figures_with_captions(
        regions, candidates, sweep_type, layout
    )
    # figures = expand_captions(page, figures, layout.row_height)
    return figures, remaining_captions, remaning_candidates


def sweep_regions(
    page: HtmlPage,
    candidates: List[Bbox],
    fig_captions: List[TextBox],
    table_captions: List[TextBox],
    layout: Layout,
):
    sweep_strategy = [
        ("captions_below_figures", "figures"),
        ("captions_over_figures", "figures"),
        ("captions_next_to_figures", "figures"),
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
        orphan_bbox = merge_candidate_bboxes(remaining_candidates)
        page.orphan_figure = Figure(
            bbox=orphan_bbox, sweep_type="orphan", multicolumn=True, caption=None
        )
    if len(remaining_captions) > 0:
        page.orphan_captions += remaining_captions


def match_orphans(pages: List[HtmlPage], layout: Layout):
    for (
        idx,
        page,
    ) in enumerate(pages):
        if page.orphan_figure is not None:
            if idx < len(pages) - 1 and len(pages[idx + 1].orphan_captions) > 0:
                # caption should be the first element in page
                sorted_text_next_page = sorted(
                    pages[idx + 1].text_boxes, key=lambda x: (x.x, x.y)
                )
                sorted_orphans = sorted(
                    pages[idx + 1].orphan_captions, key=lambda x: (x.x, x.y)
                )
                if sorted_text_next_page[0].x == sorted_orphans[0].x:
                    page.orphan_figure.caption = sorted_orphans[0]
                    expanded_orphans = expand_captions(
                        pages[idx + 1], [page.orphan_figure], layout.row_height
                    )
                    page.figures.append(expanded_orphans[0])
                    page.orphan_figure = None
                    # delete orphan caption?
            else:
                if (
                    page.orphan_figure.bbox.x >= layout.content_region.x
                    and page.orphan_figure.bbox.x1 <= layout.content_region.x1
                ):
                    page.figures.append(copy(page.orphan_figure))
                page.orphan_figure = None
