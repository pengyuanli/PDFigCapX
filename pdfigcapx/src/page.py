from typing import List, Tuple
from src.models import TextBox, Layout, AlignmentType
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
        captions: List[TextBox],
    ):
        self.name = name
        self.width = width
        self.height = height
        self.img_name = img_name
        self.number = number
        self.text_boxes = text_boxes
        self.captions = captions
        self.figures = []
        self.orphan_captions = []
        self.orphan_figure = None

    def expand_captions(self, layout: Layout):
        updated_captions = []
        for caption in self.captions:
            updated_caption = self._expand_caption(caption, layout)
            updated_captions.append(updated_caption)
        self.captions = updated_captions

    def _expand_caption(self, caption: TextBox, layout: Layout) -> TextBox:
        ids_to_remove = []

        if caption.x < layout.width / 2 and caption.x1 > layout.width / 2:
            alignment = AlignmentType.MULTICOLUMN
            sentences = [
                box
                for box in self.text_boxes
                if box.y > caption.y and abs(caption.x - box.x) < layout.row_width / 2
            ]
        elif caption.x1 < layout.width / 2:
            alignment = AlignmentType.LEFT
            sentences = [
                box
                for box in self.text_boxes
                if box.y > caption.y and abs(caption.x - box.x) < layout.row_width / 2
            ]
        else:
            alignment = AlignmentType.RIGHT
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
                new_caption.update_height()
                new_caption.text += f" {sentence.text}"
                sweep_y = sentence.y

                ids_to_remove.append(sentence.id)
            else:
                break

        self.text_boxes = [tb for tb in self.text_boxes if tb.id not in ids_to_remove]
        new_caption.alignment = alignment
        return new_caption
