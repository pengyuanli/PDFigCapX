""" Utility functions invoking system packages to process PDFs """

from os import system
from os.path import exists, join
from pathlib import Path
from re import split as re_split
from subprocess import check_output
from typing import List, Union
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup

from src.models import TextBox, Bbox
from src.page import HtmlPage


def natural_sort(arr: List[str]) -> List[str]:
    """Sorts list in ascending order considering numpad for numbers"""

    def convert(text):
        return int(text) if text.isdigit() else text.lower()

    # pylint: disable=unnecessary-lambda-assignment
    alphanum_key = lambda key: [convert(c) for c in re_split("([0-9]+)", key)]
    return sorted(arr, key=alphanum_key)


def pdf2images(file_path: str, output_path: str, dpi=300) -> None:
    """convert PDF to images and save them on output location"""
    gs_cmd = f"gs -q -sDEVICE=png16m \
        -o {join(output_path, 'file-%02d.png')} -r{dpi} {file_path}"
    # TODO: how to capture an error from the ghostscript command?
    system(gs_cmd)


def pdf2html(file_path: str, output_base_path: str, new_folder_name: str) -> str:
    """Converts PDF pages to HTML and stores it inside the output_base_path/new_folder_name
    Parameters
    ----------
    file_path : str
        Full path to the PDF document
    output_base_path: str
        Where to create the output folder with the HTML artifacts
    new_folder_name: str
        Folder to create inside output_base_path to store artifacts
    Returns
    -------
    str
        Location of the newly created folder with the artifacts
    Raises
    ------
    CalledProcessError
        If the xpdf binary pdftohtml fails to execute:
        - Error code 1 for errors opening a PDF
        - Error code 2 for using an existing folder as output folder
        - Error code 3 for PDF permissions
        - Error code 99 for anything else (e.g. missing fonts)
    Exception
        If the output_base_path does not exist
    """
    pdftohtml = "pdftohtml"

    if not exists(output_base_path):
        raise Exception(f"output_base_path ${output_base_path} does not exist")

    document_path = Path(file_path)
    output_name = new_folder_name
    output_folder = Path(output_base_path) / output_name

    check_output(
        [pdftohtml, str(document_path.resolve()), str(output_folder.resolve())]
    )
    return str(output_folder.resolve())


def launch_chromedriver() -> webdriver.Chrome:
    """Start chromedriver in headless mode"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    # chrome_options.add_argument("--no-sandbox")
    # service = Service(executable_path=ChromeDriverManager().install())
    service = Service(executable_path="/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver


def extract_page_text_content(
    browser: webdriver.Chrome, html_page_path: str
) -> HtmlPage:
    """Reads an html page, calculates the page size and extracts the text boxes.
    This method assumes that the PDF content stored in html_page_path as html
    files was produced by xpdftools pdf2html. The input html files contain
    a background image in the unique img tag with the page size. The text
    content is stored in divs of class 'txt', which also provide the location
    in the page as left and top style attributes. However, as we need to use
    the div box size in later calculations, we use Selenium's webdriver to
    compute the width and height. Each resulting web component also provides
    the text content but accessing elem.text is very slow. Instead, we read
    the html content and parse it with bs4. Using Selenium for text can be
    2.5X slower.
    Parameters:
    ----------
    - browser: webdriver.Chrome
        chromedriver instance running headless
    - html_page_path: str
        folder path containing the html files
    Returns:
    - HtmlPage
        Page object holding the parsed raw data
    """
    # read with webchromedriver to get the computed sizes
    html_file = f"file://{html_page_path}"
    browser.get(html_file)
    html_path = Path(html_page_path)
    page_number = int(html_path.stem[4:])  # prefix is page (e.g. page1)
    page_layout = browser.find_element(By.XPATH, "/html/body/img")
    div_components = browser.find_elements(By.CLASS_NAME, "txt")

    text_boxes = []
    captions = []
    # read with bs4 to read the text faster than div_comps[i].text
    try:
        with open(html_path.resolve(), "r") as f:
            html_content = f.read()
        soup = BeautifulSoup(html_content, "html.parser")
        divs = soup.find_all("div", class_="txt")
        for idx, (comp, div) in enumerate(zip(div_components, divs)):
            args = {
                **comp.rect,
                "id": idx,
                "page_number": page_number,
                "text": div.get_text(),
            }
            text_box = TextBox(**args)
            if text_box.can_be_caption(type="figure"):
                captions.append(text_box)
            else:
                text_boxes.append(text_box)
    except UnicodeDecodeError:
        # some html files may have conflicting characters with utf-8, in those
        # cases try to read with the text from the web components
        text_boxes = []
        for idx, comp in enumerate(div_components):
            args = {
                **comp.rect,
                "id": idx,
                "page_number": page_number,
                "text": comp.text,
            }
            text_box = TextBox(**args)
            if text_box.can_be_caption(type="figure"):
                captions.append(text_box)
            else:
                text_boxes.append(text_box)
            text_boxes.append(TextBox(**args))

    return HtmlPage(
        name=html_path.name,
        img_name=f"{html_path.stem}.png",
        width=page_layout.size["width"],
        height=page_layout.size["height"],
        text_boxes=text_boxes,
        captions=captions,
        number=page_number,
    )


def overlap_ratio_based(box1: Bbox, box2: Bbox) -> float:
    # overlap ratio based on box1
    SI = max(0, min(box1.x1, box2.x1) - max(box1.x, box2.x)) * max(
        0, min(box1.y1, box2.y1) - max(box1.y, box2.y)
    )
    box1_area = box1.width * box1.height
    if box1_area == 0:
        overlap_ratio = 0
    else:
        overlap_ratio = float(SI) / box1_area
    return overlap_ratio
