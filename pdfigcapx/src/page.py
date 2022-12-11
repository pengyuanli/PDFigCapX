from typing import List, Tuple
from src.models import TextBox
from src.utils import can_be_caption


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

    def __init__(
        self,
        name: str,
        width: int,
        height: int,
        img_name: str,
        number: int,
        text_boxes: List[TextBox],
    ):
        self.name = name
        self.width = width
        self.height = height
        self.img_name = img_name
        self.number = number
        self.text_boxes = text_boxes
        self.figures = []
        self.orphan_captions = []
        self.orphan_figure = None

    def find_caption_boxes(self) -> Tuple[List[TextBox], List[TextBox]]:
        """Get text boxes with text matching Table or Fig"""
        table_captions = []
        figure_captions = []
        for text_box in self.text_boxes:
            text = text_box.text.strip()
            if can_be_caption(text, type="figure"):
                figure_captions.append(text_box)
            elif can_be_caption(text, type="table"):
                table_captions.append(text_box)
        return figure_captions, table_captions
