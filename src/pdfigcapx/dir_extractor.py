from os import listdir, makedirs
from pathlib import Path

from selenium import webdriver
from pdfigcapx.html_content import HtmlPage
from renderer import render_pdf
import utils
from typing import List

MIN_TEXT_LENGTH = 30


class DirExtractor:

    def __init__(self) -> None:
        self.webdriver = self._init_web_driver()

    def _init_web_driver(self):
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--headless')
        return webdriver.Chrome('chromedriver', options=chrome_options)

    def extract(self, input_path: str, output_path: str):
        base_folder = Path(input_path)
        target_folder = Path(output_path)

        pdf_paths = [
            base_folder / f for f in listdir(base_folder)
            if f.endswith(".pdf") and not f.startswith(".")
        ]

        if len(pdf_paths) == 0:
            return
        makedirs(target_folder, exist_ok=True)

        for pdf_path in pdf_paths:
            pdf_name = pdf_path.stem()
            pdf_folder = target_folder / pdf_name

            # load images in memory
            pil_images = render_pdf(pdf_path)
            # extract content to html
            artifacts_folder = utils.pdf2html(pdf_path.resolve(),
                                              pdf_folder.resolve())

    def extract_content(self, pdf_path: Path, html_folder: Path):
        pass

    def sort_by_most_common_value_desc(arr: List[int]) -> List[int]:
        counts_per_value = [(val, arr.count(val)) for val in set(arr)]
        return sorted(counts_per_value, key=lambda x: x[1], reverse=True)

    def get_metadata(self, pdf_path: Path, html_folder: Path):
        """ get textboxes"""

        filename = pdf_path.stem

        htmls = [
            html_folder / f for f in listdir(html_folder)
            if f.endswith(".html")
        ]
        htmls = utils.natural_sort(htmls)

        # pdf_info line 77 checks the number of pages but i'm not sure why
        # i would want to skip the first page
        pages = []
        for html in htmls:
            page = utils.extract_page_text_content(self.webdriver, html)
            pages.append(page)

        x_lefts = []
        row_widths = []
        row_heights = []
        y_tops = []

        page: HtmlPage
        for page in pages:
            for text_box in page.text_boxes:
                if len(text_box.text) > MIN_TEXT_LENGTH:
                    x_lefts.append(text_box.x_top_left)
                    row_widths.append(text_box.width)
                    row_heights.append(text_box.height)
                    y_tops.append(text_box.y_top_left)

        common_x_lefts = self.sort_by_most_common_value_desc(x_lefts)
        common_row_widths = self.sort_by_most_common_value_desc(row_widths)
        common_row_heights = self.sort_by_most_common_value_desc(row_heights)

        max_row_height = row_heights[0][0]
        max_row_widths = row_widths[0][0]
