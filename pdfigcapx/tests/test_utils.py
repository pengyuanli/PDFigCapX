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


def test_pdf2html():
    """HTML files are created on target directory"""
    file_path = Path("./tests/data/pdf-1.pdf")
    output_path = Path("./tests/output/pdf-1-html")
    makedirs(output_path, exist_ok=True)

    new_folder_name = f"{file_path.stem}"
    new_folder_path = utils.pdf2html(
        file_path.resolve(), output_path.resolve(), new_folder_name
    )
    assert path.isdir(new_folder_path) is True
    # PDF has 6 pages
    html_docs = [x for x in listdir(new_folder_path) if ".html" in x]
    png_images = [x for x in listdir(new_folder_path) if ".png" in x]
    # html pages include an index.html extra page
    assert len(html_docs) - 1 == len(png_images)
    assert len(html_docs) - 1 == 6
    rmtree(output_path)


def test_chromedriver():
    """Open an html page an extract layout and divs. Chromedriver should match
    google-chrome binary number"""
    file_path = Path("./tests/data/sample_html_page/page4.html")
    browser = utils.launch_chromedriver()
    page = utils.extract_page_text_content(browser, file_path.resolve())
    # known from the html
    assert page.height == 782
    assert page.width == 595
    assert len(page.text_boxes) > 0
    assert page.name == "page4.html"
    assert page.img_name == "page4.png"
    assert page.number == 4
    # attributes not used in init
    assert len(page.orphan_captions) == 0
    assert len(page.figures) == 0
    assert page.orphan_figure is None
    browser.quit()
