from typing import Any, Optional, List
from dataclasses import dataclass, field


@dataclass()
class Bbox:
    """Bounding box that surrounds text or images
    Parameters:
    ----------
    - x: int
        left-most x coordinate (i.e., x0)
    - y: int
        top-most y coordinate (i.e., y0)
    - width: int
    - height: int
    """

    __slot__ = ("x", "y", "width", "height", "x1", "y1")
    x: int
    y: int
    width: int
    height: int
    x1: int = field(init=False)  # right-most x coordinate
    y1: int = field(init=False)  # bottom-most y coordinate

    def __post_init__(self):
        # save values for clarity during processing
        self.x1 = self.x + self.width
        self.y1 = self.y + self.height

    def to_arr(self):
        """Convert bounding box to array [x,y,w,h]"""
        return [self.x, self.y, self.width, self.height]


@dataclass()
class TextBox(Bbox):
    """Represents a div with text in the document page. (x0,y0) is the top left
    corner while (x1,y1) is the bottom right corner.
    Parameters:
    ----------
    - bbox: Bbox
    - page_number: int
        Page where the content is located. Useful for matching images and captions
        located in consecutive pages
    - text: str
    """

    __slots__ = ("page_number", "text")
    page_number: int
    text: str


# TODO: delete and replace by TextBox
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
    """Extracted figure from a document page.
    Parameters:
    ----------
    bbox: Bbox
    multicolumn: bool
        Whether the figure spans across multiple columns. True for 1-column papers
    identifier: str
        Extracted figure or table name if any
    type: str
        figure or table
    sweep_type: str
        Sweeping strategy used for finding the figure. Bookkeeping for debugging.
    caption: TextBox
    """

    bbox: Bbox
    multicolumn: bool
    identifier: Optional[str]
    type: Optional[str]
    sweep_type: Optional[str]
    caption: Optional[TextBox] = None


@dataclass
class HtmlPage:
    """Page in a PDF document converted to HTML
    attributes:
    - name:   File name
    - width:  Width of HTML page which differs from the width of the PNG file
    - height: Height of HTML page which differs from the height of the PNG file
    - text_boxes: Every div inside the HTML containing text
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
    number: int
    text_boxes: List[TextBox]
    figures: List[Figure] = field(init=False)
    orphan_figure: Figure = field(init=False)
    orphan_captions: List[TextBox] = field(init=False)

    def __post_init__(self):
        self.figures = []
        self.orphan_captions = []
        self.orphan_figure = None
