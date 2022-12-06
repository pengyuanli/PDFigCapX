""" a """

from os import listdir, makedirs
from pathlib import Path
from shutil import rmtree

import PIL
import utils
from PIL import Image


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


def get_pages(xpdf_path: Path):
    """Read the size and div content for every page"""
    page_names = [
        x for x in listdir(xpdf_path) if x.endswith(".html") and x.startswith("page")
    ]
    browser = utils.launch_chromedriver()

    html_pages = []
    for page_name in page_names:
        html_page = utils.extract_page_text_content(
            browser, (xpdf_path / page_name).resolve()
        )
        html_pages.append(html_page)
    browser.quit()
    return html_pages


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
