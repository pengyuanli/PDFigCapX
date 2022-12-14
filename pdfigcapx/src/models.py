from typing import Optional, List, Union
from dataclasses import dataclass, field
from re import search as re_search
from re import IGNORECASE
from enum import Enum


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

    def __eq__(self, other):
        return (
            self.x == other.x
            and self.y == other.y
            and self.width == other.width
            and self.height == other.height
        )

    def update_width(self):
        self.width = self.x1 - self.x

    def update_height(self):
        self.height = self.y1 - self.y

    def intersect_area(self, other) -> float:
        x = max(self.x, other.x)
        y = max(self.y, other.y)
        w = min(self.x1, other.x1) - x
        h = min(self.y1, other.y1) - y
        return 0.0 if (w < 0 or h < 0) else w * h

    def intersect(self, other):
        x = max(self.x, other.x)
        y = max(self.y, other.y)
        w = min(self.x1, other.x1) - x
        h = min(self.y1, other.y1) - y
        return None if (w < 0 or h < 0) else Bbox(x, y, w, h)

    def area(self):
        return self.width * self.height

    def merge_bboxes(bboxes):
        x0 = min([el.x for el in bboxes])
        y0 = min([el.y for el in bboxes])
        x1 = max([el.x1 for el in bboxes])
        y1 = max([el.y1 for el in bboxes])
        return Bbox(x0, y0, x1 - x0, y1 - y0)


def build_regex_for_caption(type="figure") -> str:
    """Helper to build regular expressions to find figure or table text in sentence.
    We assume that the figure or table names are the first words in a caption.
    """
    if type == "figure":
        return r"^fig*[a-zA-Z.]+ ([a-zA-Z.]+)?\d+(\.)?"  # match also fig. s1.
    elif type == "table":
        return r"^table*\w+ \d+"
    else:
        raise Exception(f"Error in type {type}, we only search for a figure or table")


class AlignmentType(Enum):
    LEFT = 1
    RIGHT = 2
    MULTICOLUMN = 3
    UNKNOWN = 4


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

    def __init__(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        id: int,
        page_number: int,
        text: str,
    ):
        super().__init__(x, y, width, height)
        self.id = id
        self.page_number = page_number
        self.text = text
        self.alignment = AlignmentType.UNKNOWN

    def can_be_caption(self, type="figure") -> bool:
        """Check whether a sentence qualifies as a potential caption
        Parameters:
        ----------
        - text: str
        - type: str, "figure" or "table"
        returns:
        - bool
        """
        reg_exp = build_regex_for_caption(type=type)
        rgx = re_search(reg_exp, self.text, IGNORECASE)
        return rgx is not None

    def get_caption_identifier(self, type="figure") -> Union[str, None]:
        """Find in a text sentence a hint for the figure or table name"""
        reg_exp = build_regex_for_caption(type=type)
        rgx = re_search(reg_exp, self.text, IGNORECASE)
        return rgx.group() if rgx is not None else None


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
    caption: TextBox
    sweep_type: str
    identifier: str = field(init=False)
    type: str = field(init=False)

    def __post_init__(self):
        # TODO: update
        self.type = "temp"
        self.identifier = ""


@dataclass
class Layout:
    width: int
    height: int
    num_cols: int
    row_width: int
    row_height: int
    content_region: Bbox
    col_coords: List[int]


@dataclass
class Region:
    bbox: Bbox
    caption: TextBox
    multicolumn: bool
