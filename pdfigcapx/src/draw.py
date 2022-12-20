import matplotlib.patches as patches
from matplotlib.pyplot import Axes
from typing import Optional, List
from src.models import Bbox, Layout
from src.page import HtmlPage


def draw_content_region(ax: List[List[Axes]], region: Bbox):
    rect = patches.Rectangle(
        (region.x, region.y),
        region.width,
        region.height,
        linewidth=1,
        edgecolor="black",
        facecolor="none",
        alpha=0.5,
    )
    ax.add_patch(rect)


def draw_columns(ax: List[List[Axes]], layout: Layout):
    for col in layout.col_coords:
        ax.vlines(col, 0, layout.height, colors="red", linestyles="dashed")


def draw_text_regions(ax: List[List[Axes]], page: HtmlPage):
    for box in page.text_boxes:
        rect = patches.Rectangle(
            (box.x, box.y),
            box.width,
            box.height,
            linewidth=1,
            edgecolor="none",
            facecolor="blue",
            alpha=0.4,
        )
        ax.add_patch(rect)


def draw_bboxes(
    ax: List[List[Axes]],
    boxes: List[Bbox],
    edgecolor: Optional[str],
    facecolor: Optional[str],
    alpha: float,
):
    for box in boxes:
        rect = patches.Rectangle(
            (box.x, box.y),
            box.width,
            box.height,
            linewidth=1,
            edgecolor=edgecolor,
            facecolor=facecolor if facecolor else "null",
            alpha=alpha,
        )
        ax.add_patch(rect)
