from os import makedirs, path, listdir
from pathlib import Path
from shutil import rmtree
import pytest
from src.pdfigcapx import utils


@pytest.mark.parametrize("test_input,expected", [
    (['file-06.png', 'file-20.png', 'file-07.png'],
     ['file-06.png', 'file-07.png', 'file-20.png']),
    (['1-abc', '2-abc', '11-abc', '21-abc', '2-def'],
     ['1-abc', '2-abc', '2-def', '11-abc', '21-abc']),
    ([], [])
])
def test_natural_sort(test_input, expected):
    actual = utils.natural_sort(test_input)

    assert len(actual) == len(expected)
    assert all([a == b for a, b in zip(actual, expected)])


def test_image2pdf():
    # pdf with 20 pages
    file_path = Path('./tests/data/pdf-1.pdf')
    output_path = Path('./tests/output/pdf-1')
    makedirs(output_path, exist_ok=True)
    utils.pdf2images(file_path.resolve(), output_path.resolve())
    assert path.isdir(output_path) is True
    assert len(listdir(output_path)) == 20
    rmtree(output_path)
