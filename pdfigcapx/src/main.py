""" a """

from os import listdir, makedirs
from pathlib import Path
from shutil import rmtree

from PIL import Image

from .utils import natural_sort, pdf2html, pdf2images


def fetch_pages_as_images(
    pdf_path: Path, base_folder: Path, dpi=300
) -> list[PIL.Image]:
    """Return PDF pages as PIL Images"""
    output_folder = base_folder / "images"
    makedirs(output_folder, exist_ok=True)
    pdf2images(pdf_path.resolve(), output_folder.resolve(), dpi=dpi)
    image_names = [
        x
        for x in listdir(output_folder)
        if x.endswith(".png") and not x.startswith(".")
    ]
    image_names = natural_sort(image_names)
    images = []
    for image_name in image_names:
        pil_image = Image.open(output_folder / image_name).convert("RGB")
        pil_image.load()  # load into memory (also closes the file associated)
        images.append(pil_image)
    rmtree(output_folder)
    return images


def pdf_info(pdf_path: Path, xpdf_path: Path):
    """Figure out what this function pdf_info does"""


def extract_figures(pdf_path: Path, xpdf_path: Path):
    """the figures_caption_list method"""
    pdf_info(pdf_path, xpdf_path)


def process_pdf(pdf_path: Path, base_folder: Path, dpi=300):
    """a, for exception delete all inside folder"""
    pil_images = fetch_pages_as_images(pdf_path, base_folder, dpi)
    xpdf_folder_name = f"xpdf_{pdf_path.stem}"
    xpdf_folder_path = pdf2html(
        pdf_path.resolve(), base_folder.resolve(), xpdf_folder_name
    )
