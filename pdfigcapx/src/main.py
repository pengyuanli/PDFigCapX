""" a """

from os import listdir, makedirs
from pathlib import Path
from shutil import rmtree

import traceback
import PIL
import math
import utils
import argparse
from PIL import Image
from typing import List, Union
from src.models import Layout, Bbox, TextBox
from src.page import HtmlPage

from src.contours import get_potential_contours
from src.sweep import sweep_regions, match_orphans


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
        traceback.print_exc()
        return None
    finally:
        if browser:
            browser.quit()
    html_pages = sorted(html_pages, key=lambda x: x.number)
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
    sorted_widths = sorted(
        [(i, widths.count(i)) for i in set(widths)], key=lambda x: x[1], reverse=True
    )
    sorted_heights = sorted(
        [(i, heights.count(i)) for i in set(heights)], key=lambda x: x[1], reverse=True
    )
    width = sorted_widths[0][0]
    height = sorted_heights[0][0]

    return width, height


def find_content_region(pages: List[HtmlPage], page_width: int, threshold=30):
    """
    There may be a case when there are more rows on the right side, so use page_width to filter
    """
    x0s = [
        y.x
        for x in pages
        for y in x.text_boxes
        if y.width > threshold and y.x < page_width / 2
    ]
    y0s = [y.y for x in pages for y in x.text_boxes if y.width > threshold]
    x1s = [y.x1 for x in pages for y in x.text_boxes if y.width > threshold]
    sorted_x0s = sorted(
        [(i, x0s.count(i)) for i in set(x0s)], key=lambda x: x[1], reverse=True
    )
    sorted_x0s = merge_left_padded_points(sorted_x0s)

    # content region
    cr_x0 = sorted_x0s[0][0]
    cr_y0 = max(0, min(y0s))
    # The converted html file may have some overflowing divs due to conversion
    # errors. In case of overflow, assume a similar padding like the left side
    cr_x1 = min(page_width - cr_x0, max(x1s))
    cand_y1s = [  # y1s constrained to other three coordinates
        y.y1
        for x in pages
        for y in x.text_boxes
        if y.x >= cr_x0 and y.x1 <= cr_x1 and y.y >= cr_y0
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
    page_width = pages[0].width  # TODO: change to mode width?
    content_region = find_content_region(pages, page_width, threshold)

    # number of columns
    # using page_width / row_width can fail when the publication has a lot of
    # padding outside of the content region and withing columns
    number_cols = math.floor(content_region.width / row_width)
    if number_cols == 1:
        col_coords = [content_region.x]
    else:
        x1s = [
            y.x
            for x in pages
            for y in x.text_boxes
            if y.x >= content_region.x + row_width
        ]
        x1s = sorted(
            [(i, x1s.count(i)) for i in set(x1s)], key=lambda x: x[1], reverse=True
        )
        col_coords = [content_region.x, x1s[0][0]]

    return Layout(
        width=page_width,
        height=pages[0].height,
        row_width=row_width,
        row_height=row_height,
        content_region=content_region,
        num_cols=number_cols,
        col_coords=col_coords,
    )


def extract(pdf_path: str, base_folder: str, size_threshold=1000):
    full_pdf_path = Path(pdf_path)
    full_base_path = Path(base_folder)

    xpdf_folder_name = f"xpdf_{full_pdf_path.stem}"
    xpdf_folder_path = utils.pdf2html(
        full_pdf_path.resolve(), full_base_path.resolve(), xpdf_folder_name
    )
    pages = get_pages(Path(xpdf_folder_path))
    layout = calc_document_layout(pages)

    for page in pages:
        fig_captions, table_captions = page.find_caption_boxes()
        fig_captions = [
            page.expand_caption(caption, layout) for caption in fig_captions
        ]
        candidates, _ = get_potential_contours(
            xpdf_folder_path, page, layout, fig_captions
        )
        if len(fig_captions) > 0 and len(candidates) > 0:
            sweep_regions(page, candidates, fig_captions, table_captions, layout)
    match_orphans(pages, layout)
    # TODO: if orphan inside other image, then delete
    page.figures = [
        f for f in page.figures if f.bbox.width * f.bbox.height > size_threshold
    ]
    return pages, layout, xpdf_folder_path


def save(
    pdf_path: str,
    pages: List[HtmlPage],
    base_folder: str,
    layout: Layout,
    dpi=300,
    prefix=None,
):
    output_path = Path(base_folder)
    full_pdf_path = Path(pdf_path)
    pil_images = fetch_pages_as_images(full_pdf_path, output_path, dpi)

    str_prefix = "" if not prefix else f"{prefix}_"
    for page, pil_image in zip(pages, pil_images):
        scale = float(pil_image.size[0]) / layout.width

        for idx, fig in enumerate(page.figures):
            crop_box = [
                fig.bbox.x * scale,
                fig.bbox.y * scale,
                fig.bbox.x1 * scale,
                fig.bbox.y1 * scale,
            ]
            extracted_fig = pil_image.crop(crop_box)
            fig_name = f"{str_prefix}{page.number}_{idx+1}.jpg"
            fig_path = output_path / fig_name
            extracted_fig.save(fig_path)


def process_pdf(pdf_path: str, output_img_path: str, add_prefix=False):
    full_pdf_path = Path(pdf_path)
    target_folder_name = full_pdf_path.stem
    # target_img_folder = Path(output_img_path) / target_folder_name
    target_img_folder = Path(output_img_path) / "samples"
    makedirs(target_img_folder, exist_ok=True)

    pages, layout, xpdf_folder_path = extract(
        full_pdf_path.resolve(), target_img_folder.resolve()
    )

    prefix = target_folder_name if add_prefix else None
    save(pdf_path, pages, target_img_folder, layout, prefix=prefix)


if __name__ == "__main__":
    # parser = argparse.ArgumentParser(
    #     prog="pdffigcapx",
    #     description="extract document figures",
    # )
    # parser.add_argument("filename")
    # parser.add_argument("out_data_path")
    # args = parser.parse_args()
    # base_folder = Path("/home/jtt/Documents/test_pdfigcapx")
    base_folder = Path("/home/jtt/pdfs/sample_wormbase")
    pdfs = [base_folder / x for x in listdir(base_folder)]

    for d in pdfs:
        # d = Path("/home/jtt/Documents/test_pdfigcapx/pmid18430929.pdf")
        print(d.stem)
        process_pdf(d, "/home/jtt/Documents/outputs/tests/", add_prefix=True)
