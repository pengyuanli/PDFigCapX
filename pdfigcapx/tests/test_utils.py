""" testing utility functions """

from os import listdir, makedirs, path
from pathlib import Path
from shutil import rmtree

import pytest
from src import utils


@pytest.mark.parametrize(
    "test_input,expected",
    [
        (
            ["file-06.png", "file-20.png", "file-07.png"],
            ["file-06.png", "file-07.png", "file-20.png"],
        ),
        (
            ["1-abc", "2-abc", "11-abc", "21-abc", "2-def"],
            ["1-abc", "2-abc", "2-def", "11-abc", "21-abc"],
        ),
        ([], []),
    ],
)
def test_natural_sort(test_input, expected):
    """Test sort with padding left"""
    actual = utils.natural_sort(test_input)

    assert len(actual) == len(expected)
    assert all([a == b for a, b in zip(actual, expected)])


def test_pdf2images():
    """Images are created on target directory"""
    file_path = Path("./tests/data/pdf-1.pdf")
    output_path = Path("./tests/output/pdf-1")
    makedirs(output_path, exist_ok=True)
    utils.pdf2images(file_path.resolve(), output_path.resolve())

    assert path.isdir(output_path) is True
    # PDF has 6 pages
    print(utils.natural_sort(listdir(output_path)))
    assert len(listdir(output_path)) == 6
    rmtree(output_path)
