""" Dataclasses for storing content of HTML pages """
from dataclasses import dataclass


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
    text_boxes: list[TextBox]
