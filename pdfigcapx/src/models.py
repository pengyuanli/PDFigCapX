from typing import Any, Optional

from pydantic import BaseModel


class TextContainer(BaseModel):
    """Represents a div with text in the document page. (x0,y0) is the top left
    corner while (x1,y1) is the bottom right corner.
    """

    x0: int
    y0: int
    x1: int
    y1: int
    width: int
    height: int
    text: str

    def to_bbox(self):
        return [self.x0, self.y0, self.width, self.height]


class HtmlPage(BaseModel):
    name: str
    width: int
    height: int
    text_containers: Optional[list[TextContainer]] = None
    img_name: str


class Caption(BaseModel):
    text: str
    x0: int
    y0: int
    width: int
    height: int

    def to_bbox(self):
        return [self.x0, self.y0, self.width, self.height]
