""" Dataclasses for storing content of HTML pages """
from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass
class BoundingBox:
    """ Bounding box in image where y augments from top to bottom.
        (x0,y0) -------------|
        |                    |
        |______________(x1,y1)
    """
    x0: int
    y0: int
    x1: int
    y1: int
    width: int = field(init=False)
    height: int = field(init=False)

    def __post_init__(self):
        self.width = self.x1 - self.x0
        self.height = self.y1 - self.y0

    def to_cv2_bbox(self):
        """ Return the cv2 format for bounding boxes """
        return [self.x0, self.y0, self.width, self.height]


@dataclass
class TextLine(BoundingBox):
    """ Represents a div container inside an HTML page """
    text: str


@dataclass
class HtmlPage:
    """ Page layout and location of all text boxes in an HTML page """
    width: int
    height: int
    text_lines: List[TextLine]


@dataclass
class CountTuple:
    """ Stored the number of times value appears """
    count: int
    value: int


@dataclass
class PageBoxesCounts:
    x0s: List[int] = field(default_factory=list)
    y0s: List[int] = field(default_factory=list)
    heights: List[int] = field(default_factory=list)
    widths: List[int] = field(default_factory=list)
    x1s: List[int] = field(default_factory=list)
    sorted_x0_counts: List[CountTuple] = field(default_factory=list)
    sorted_width_counts: List[CountTuple] = field(default_factory=list)
    sorted_height_counts: List[CountTuple] = field(default_factory=list)

    # MISSING OUTPUT
    def calc_y_range(self, page_height: int) -> Tuple[int, int]:
        return (max(0, min(self.y0s)), min(page_height, max(self.y0s)))
