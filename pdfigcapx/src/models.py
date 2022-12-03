from typing import Optional, Any

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


class HtmlPage(BaseModel):
    width: int
    height: int
    text_containers: Optional[list[TextContainer]] = None
