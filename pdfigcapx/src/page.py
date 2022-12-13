from typing import List, Tuple
from src.models import TextBox, Layout
from copy import deepcopy


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
            if text_box.can_be_caption(type="figure"):
                figure_captions.append(text_box)
            elif text_box.can_be_caption(type="table"):
                table_captions.append(text_box)
        return figure_captions, table_captions

    def expand_caption(self, caption: TextBox, layout: Layout) -> TextBox:
        if caption.x < layout.width / 2 and caption.x1 > layout.width / 2:
            alignment = "multicolumn"
            sentences = [
                box
                for box in self.text_boxes
                if box.y > caption.y and abs(caption.x - box.x) < layout.row_width / 2
            ]
        elif caption.x1 < layout.width / 2:
            alignment = "left"
            sentences = [
                box
                for box in self.text_boxes
                if box.y > caption.y and abs(caption.x - box.x) < layout.row_width / 2
            ]
        else:
            alignment = "right"
            sentences = [
                box
                for box in self.text_boxes
                if box.y > caption.y and abs(caption.x1 - box.x1) < layout.row_width / 2
            ]

        # the filtering is dropping the last sentence by mistake because the length
        # is smaller than row_width / 2
        sentences = sorted(sentences, key=lambda el: el.y)
        sweep_y = caption.y1

        new_caption = deepcopy(caption)
        for sentence in sentences:
            if abs(sentence.y - sweep_y) < layout.row_height * 1.5:
                # could modify width but it would be not convenient for captions
                # surrounding images
                new_caption.y1 = sentence.y1
                new_caption.height = new_caption.y1 - new_caption.y
                new_caption.text += f" {sentence.text}"
                sweep_y = sentence.y
            else:
                break
        return new_caption
