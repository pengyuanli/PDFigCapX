""" Dataclasses for storing content of HTML pages """
from dataclasses import dataclass


@dataclass
class TextBox:
    """ Represents a div container inside an HTML page """
    x: int
    y: int
    width: int
    height: int


@dataclass
class HtmlPage:
    """ Page layout and location of all text boxes in an HTML page """
    width: int
    height: int
    text_boxes: list[TextBox]
