from typing import Any, Optional, List

# from pydantic import BaseModel
from dataclasses import dataclass, field


@dataclass()
class Bbox:
    __slot__ = ("x", "y", "width", "height")
    x: int
    y: int
    width: int
    height: int

    def to_bbox(self):
        return [self.x, self.y, self.width, self.height]


@dataclass()
class TextContainer:
    """Represents a div with text in the document page. (x0,y0) is the top left
    corner while (x1,y1) is the bottom right corner.
    """

    __slots__ = ("x0", "y0", "x1", "y1", "width", "height", "text")
    x0: int
    y0: int
    x1: int
    y1: int
    width: int
    height: int
    text: str

    def to_bbox(self):
        return [self.x0, self.y0, self.width, self.height]


@dataclass
class Caption:
    text: str
    x0: int
    y0: int
    width: int
    height: int

    def to_bbox(self):
        return [self.x0, self.y0, self.width, self.height]


@dataclass
class Figure:
    x0: int
    y0: int
    width: int
    height: int
    multicolumn: bool
    identifier: Optional[str]
    type: Optional[str]
    sweep_type: Optional[str]
    caption: Optional[Caption] = None

    def to_bbox(self):
        return [self.x0, self.y0, self.width, self.height]


@dataclass
class HtmlPage:
    """Page in a PDF document converted to HTML
    attributes:
    - name:   File name
    - width:  Width of HTML page which differs from the width of the PNG file
    - height: Height of HTML page which differs from the height of the PNG file
    - text_containers: Every div inside the HTML containing text
    - img_name: Associated PNG filename
    - page_number: Page number in PDF
    - orphan_figure: Figure in page built from remaining contour candidates
        after every other candidates have been matched to captions. This
        situation is common when the caption is on the next page, and the field
        stores the caption-less figure for a posterior validation across
        consecutive pages.
    - orphan_captions: div containing the starting word 'figure' that were
        not matched to any candidate region on the page after sweeping the
        page downwards, upwards and sidewards.
    """

    name: str
    width: int
    height: int
    img_name: str
    page_number: int
    text_containers: List[TextContainer]
    figures: List[Figure] = field(init=False)
    orphan_figure: Figure = field(init=False)
    orphan_captions: List[TextContainer] = field(init=False)

    def __post_init__(self):
        self.figures = []
        self.orphan_captions = []
