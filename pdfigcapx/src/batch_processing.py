import logging
import argparse
import multiprocessing
from multiprocessing import Process
from os import listdir
from pathlib import Path
from src.document import Document

"""
poetry run python src/batch_processing.py /home/jtt/Documents/datasets/gxd /home/jtt/Documents/outputs/xpdf /home/jtt/Documents/outputs/gdx
"""


def process_pdf(pdf_path: str, xpdf_path: str, data_path: str):
    try:
        print(pdf_path)
        document = Document(pdf_path, xpdf_path, data_path, include_first_page=False)
        document.extract_figures()
        document.draw(n_cols=6, txtr=True, save=True)
    except Exception as e:
        logging.error(f"{pdf_path}:", exc_info=True)
        print(pdf_path, e)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="pdffigcapx",
        description="batch_processing",
    )
    parser.add_argument("pdfs_path")
    parser.add_argument("xpdf_path")
    parser.add_argument("data_path")
    args = parser.parse_args()

    input_folder = Path(args.pdfs_path)
    if not input_folder.exists():
        raise Exception(f"Input folder {input_folder} does not exist")

    log_path = Path(args.data_path) / "pdfigcapx.log"
    logging.basicConfig(
        filename=log_path.resolve(),
        filemode="a",
        format="%(asctime)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )

    pool = multiprocessing.Pool()
    pdf_names = [el for el in listdir(input_folder) if el.endswith(".pdf")]

    items = [(input_folder / el, args.xpdf_path, args.data_path) for el in pdf_names]

    with multiprocessing.Pool(10) as pool:
        pool.starmap(process_pdf, items)
