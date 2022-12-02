from typing import Optional

from pydantic import BaseModel


class TextContainer(BaseModel):
    x: int
    y: int
    width: int
    height: int
    text: str


class HtmlPage(BaseModel):
    width: int
    height: int
    text_containers: Optional[list[TextContainer]] = None
