from os import listdir, makedirs
from pathlib import Path
from renderer import render_pdf
from utils import pdf2images


class DirExtractor:

    def extract(input_path: str, output_path: str):
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

            makedirs(pdf_folder, exist_ok=True)
            pil_images = render_pdf(pdf_path)
            pdf2images(pdf_path.resolve(), pdf_folder.resolve())

    def extract_content(pdf_path: Path, html_folder: Path):
        pass

    def get_metadata(pdf_path: Path, html_folder: Path):
        filename = pdf_path.stem()
        pngs = [f for f in listdir(html_folder) if f.endswith(".png")]
        # thought this was already sorted ?
        pngs = pngs.sorted(pngs)
        number_pages = len(pngs)
