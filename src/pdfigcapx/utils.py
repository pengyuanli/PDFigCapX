""" Utility functions invoking system packages to process PDFs """

from re import split as re_split
from os import system
from os.path import join
from subprocess import check_output
from typing import List
from pathlib import Path


def natural_sort(arr: List[str]) -> List[str]:
    """ Sorts list in ascending order considering numpad for numbers """
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanum_key = lambda key: [convert(c) for c in re_split('([0-9]+)', key)]
    return sorted(arr, key=alphanum_key)


def pdf2images(file_path: str, output_path: str, dpi=300) -> None:
    """ convert PDF to images and save them on output location """
    gs_cmd = f"gs -q -sDEVICE=png16m \
        -o {join(output_path, 'file-%02d.png')} -r{dpi} {file_path}"

    # TODO: how to capture an error from the ghostscript command?
    system(gs_cmd)


def pdf2html(file_path: str, output_base_path: str) -> str:
    """ Converts PDF pages to HTML. Stores output content on a new folder
        with name xpdf_{file_path name} at output_base_path.

        Parameters
        ----------
        file_path : str
            Full path to the PDF document
        output_base_path: str
            Where to create the output folder with the HTML artifacts

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

    """
    pdftohtml = "pdftohtml"

    document_path = Path(file_path)
    output_name = f"xpdf_{document_path.stem}"
    output_folder = Path(output_base_path) / output_name

    check_output([
        pdftohtml,
        str(document_path.resolve()),
        str(output_folder.resolve())
    ])
    return str(output_folder.resolve())
