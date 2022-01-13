""" Dataclasses for storing content of HTML pages """
from dataclasses import dataclass, field
from typing import List


@dataclass
class TextBox:
    """ Represents a div container inside an HTML page """
    x_top_left: int
    y_top_left: int
    x_top_right: int
    width: int
    height: int
    text: str


@dataclass
class HtmlPage:
    """ Page layout and location of all text boxes in an HTML page """
    width: int
    height: int
    text_boxes: List[TextBox]


@dataclass
class CountTuple:
    """ Stored the number of times value appears """
    count: int
    value: int


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
