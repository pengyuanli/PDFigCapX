""" Utility functions invoking system packages to process PDFs """

from os import system
from os.path import exists, join
from pathlib import Path
from re import split as re_split
from subprocess import check_output
from typing import List

# from numpy import empty_like, dot, array
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

from .models import HtmlPage, TextContainer


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


def launch_chromedriver():
    """Start chromedriver in headless mode"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")

    # service = Service(executable_path=ChromeDriverManager().install())
    service = Service(executable_path="/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver


def extract_page_text_content(
    browser: webdriver.Chrome, html_page_path: str
) -> HtmlPage:
    """Obtains page layout information and returns DIVs with text"""
    html_file = f"file://{html_page_path}"
    browser.get(html_file)

    page_layout = browser.find_element(By.XPATH, "/html/body/img")
    text_elements = browser.find_elements(By.XPATH, "/html/body/div")

    text_lines = []
    for elem in text_elements:
        if len(elem.text) > 0:
            text_lines.append(
                TextContainer(
                    x=elem.location["x"],
                    y=elem.location["y"],
                    width=elem.size["width"],
                    height=elem.size["height"],
                    text=elem.text,
                )
            )
    page = HtmlPage(
        width=page_layout.size["width"],
        height=page_layout.size["height"],
        text_containers=text_lines,
    )
    return page


# def sort_by_most_common_value_desc(arr: List[int]) -> List[CountTuple]:
#     """Count ocurrences of element in arr and return sorted tuples in desc
#     order"""
#     counts_per_value = [CountTuple(value=val, count=arr.count(val)) for val in set(arr)]
#     # counts_per_value = [(val, arr.count(val)) for val in set(arr)]
#     # return sorted(counts_per_value, key=lambda x: x.count, reverse=True)
#     return sorted(counts_per_value, key=lambda x: (x.count, x.value), reverse=True)


# def intersect_two_segments(
#     point_a0: List[int],
#     point_a1: List[int],
#     point_q0: List[int],
#     point_q1: List[int],
# ) -> List[int]:
#     """Find intersection between two segments
#     https://stackoverflow.com/questions/3252194/numpy-and-line-intersections
#     """

#     def perp(a):
#         b = empty_like(a)
#         b[0] = -a[1]
#         b[1] = a[0]
#         return b

#     def seg_intersect(a1, a2, b1, b2):
#         da = a2 - a1
#         db = b2 - b1
#         dp = a1 - b1
#         dap = perp(da)
#         denom = dot(dap, db)
#         num = dot(dap, dp)
#         return (num / denom.astype(float)) * db + b1

#     intersect = seg_intersect(
#         array(point_a0), array(point_a1), array(point_q0), array(point_q1)
#     )
#     intersect.astype(int)
#     return [intersect[0], intersect[1]]
