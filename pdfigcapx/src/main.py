""" a """

from os import listdir, makedirs
from pathlib import Path
from shutil import rmtree

import PIL
import math
import utils
from PIL import Image
from typing import List, Union
from src.models import HtmlPage, Layout, Bbox, TextBox


def fetch_pages_as_images(
    pdf_path: Path, base_folder: Path, dpi=300
) -> list[PIL.Image]:
    """Return PDF pages as PIL Images"""
    output_folder = base_folder / "images"
    makedirs(output_folder, exist_ok=True)
    utils.pdf2images(pdf_path.resolve(), output_folder.resolve(), dpi=dpi)
    image_names = [
        x
        for x in listdir(output_folder)
        if x.endswith(".png") and not x.startswith(".")
    ]
    image_names = utils.natural_sort(image_names)
    images = []
    for image_name in image_names:
        pil_image = Image.open(output_folder / image_name).convert("RGB")
        pil_image.load()  # load into memory (also closes the file associated)
        images.append(pil_image)
    rmtree(output_folder)
    return images


def get_pages(xpdf_path: Path) -> List[HtmlPage]:
    """Read the size and div content for every page"""
    page_names = [
        x for x in listdir(xpdf_path) if x.endswith(".html") and x.startswith("page")
    ]
    browser = utils.launch_chromedriver()

    try:
        html_pages = []
        for page_name in page_names:
            html_page = utils.extract_page_text_content(
                browser, (xpdf_path / page_name).resolve()
            )
            html_pages.append(html_page)
    except Exception as e:
        print(e)
        return None
    finally:
        if browser:
            browser.quit()
    html_pages = sorted(html_pages, key=lambda x: x.page_number)
    return html_pages


def merge_left_padded_points(
    sorted_points: list[tuple[int, int]], padding_threshold=10
) -> list[tuple[int, int]]:
    """Update the sorted counts by merging padded text elements"""
    left_points = sorted_points.copy()
    i = 0
    while i < len(left_points):
        j = i + 1
        while j < len(left_points):
            if abs(left_points[i][0] - left_points[j][0]) <= padding_threshold:
                left_points[i] = (
                    left_points[i][0],
                    left_points[i][1] + left_points[j][1],
                )
                del left_points[j]
            else:
                j = j + 1
        i = i + 1
    return sorted(left_points, key=lambda x: x[1], reverse=True)


def calc_row_size(pages: List[HtmlPage], threshold=30):
    widths = [y.width for x in pages for y in x.text_boxes if y.width > threshold]
    heights = [y.height for x in pages for y in x.text_boxes if y.width > threshold]
    sorted_widths = sorted([i for i in set(widths)], key=lambda x: x[1], reverse=True)
    sorted_heights = sorted([i for i in set(heights)], key=lambda x: x[1], reverse=True)
    width = sorted_widths[0]
    height = sorted_heights[0]

    return width, height


def find_content_region(pages: List[HtmlPage], threshold=30):
    x0s = [y.x0 for x in pages for y in x.text_boxes if y.width > threshold]
    y0s = [y.y0 for x in pages for y in x.text_boxes if y.width > threshold]
    x1s = [y.x1 for x in pages for y in x.text_boxes if y.width > threshold]
    sorted_x0s = sorted(
        [(i, x0s.count(i)) for i in set(x0s)], key=lambda x: x[1], reverse=True
    )
    sorted_x0s = merge_left_padded_points(sorted_x0s)

    # content region
    cr_x0 = sorted_x0s[0][0]
    cr_y0 = max(0, min(y0s))
    cr_x1 = max(x1s)
    cand_y1s = [  # y1s constrained to other three coordinates
        y.y1
        for x in pages
        for y in x.text_boxes
        if y.x0 >= cr_x0 and y.x1 <= cr_x1 and y.y0 >= cr_y0
    ]
    cr_y1 = max(cand_y1s)
    cr = {"x": cr_x0, "y": cr_y0, "width": cr_x1 - cr_x0, "height": cr_y1 - cr_y0}
    return Bbox(**cr)


def calc_document_layout(pages: List[HtmlPage], threshold=30) -> Layout:
    """Estimates the page size, number of columns, column width and height,
    and coordinates for each column
    Parameters:
    ----------
    - pages: List[HtmlPage]
    - threshold: int
        To ignore small text boxes detected on figures or on publisher temlates
    """
    # use more common widths and heights to estimate row properties
    row_width, row_height = calc_row_size(pages, threshold)
    # use most common coordinates to find the publication text region
    content_region = find_content_region(pages, threshold)

    # number of columns
    page_width = pages[0].width  # TODO: change to mode width?
    number_cols = math.floor(page_width / row_width)
    if number_cols == 1:
        col_coords = [content_region.x0]
    else:
        candidates = [
            y.x0
            for x in pages
            for y in x.text_boxes
            if y.x0 >= content_region.x0 + row_width
        ]
        col_coords = [content_region.x0, min(candidates)]

    return Layout(
        width=page_width,
        height=pages[0].height,
        row_width=row_width,
        row_height=row_height,
        content_region=Bbox(**content_region),
        num_cols=number_cols,
        col_coords=col_coords,
    )


def extract_figures(pdf_path: Path, xpdf_path: Path):
    """the figures_caption_list method"""
    html_pages = get_pages(xpdf_path)


def process_pdf(pdf_path: Path, base_folder: Path, dpi=300):
    """a, for exception delete all inside folder"""
    pil_images = fetch_pages_as_images(pdf_path, base_folder, dpi)
    xpdf_folder_name = f"xpdf_{pdf_path.stem}"
    xpdf_folder_path = utils.pdf2html(
        pdf_path.resolve(), base_folder.resolve(), xpdf_folder_name
    )
