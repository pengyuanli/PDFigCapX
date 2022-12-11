from src.models import TextBox, Layout, Region, Bbox
from typing import List

NOT_SUPPORTED = (
    "skipping page: calculations do not support PDFs with more than 2 columns"
)


def is_multicol_caption(box: TextBox, layout: Layout):
    ROW_EXTRA = layout.row_width / 5
    x0_2nd_col = layout.col_coords[1]

    if (box.x < x0_2nd_col and box.x1 > x0_2nd_col) or box.x > x0_2nd_col + ROW_EXTRA:
        return True
    return False


def estimate_caption_regions_top(captions: List[TextBox], layout: Layout):
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
                    w = layout.width - layout.col_coords[0]
                    h = caption.y - sweep[1]
                    sweep[1] = caption.y1
            bbox = Bbox(x, y, w, h)
            regions.append(Region(bbox, caption, is_multicol))
    else:
        print(NOT_SUPPORTED)

    return regions


def estimate_caption_regions_bottom(captions: list[TextBox], layout: Layout):
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
        sweep = [layout.content_region.height] * layout.num_cols
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
                    h = sweep[0] - caption.y
                    sweep[0] = caption.y
                else:
                    w = layout.width - layout.col_coords[0]
                    h = sweep[1] - caption.y
                    sweep[1] = caption.y
            bbox = Bbox(x, y, w, h)
            regions.append(Region(bbox, caption, is_multicol))
    else:
        print(NOT_SUPPORTED)

    return regions


def estimate_caption_regions_side(captions: list[TextBox], layout: Layout):
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

    for caption in sorted_captions:
        y = caption.y
        h = vert_sweep - caption.y
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
