from os import makedirs, path, listdir
from pathlib import Path
from shutil import rmtree
from subprocess import CalledProcessError
from selenium import webdriver
import pytest
from src.pdfigcapx import utils


@pytest.mark.parametrize("test_input,expected",
                         [(['file-06.png', 'file-20.png', 'file-07.png'
                            ], ['file-06.png', 'file-07.png', 'file-20.png']),
                          (['1-abc', '2-abc', '11-abc', '21-abc', '2-def'],
                           ['1-abc', '2-abc', '2-def', '11-abc', '21-abc']),
                          ([], [])])
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


def test_pdf2html_worked_correctly():
    file_path = './tests/data/pdf-1.pdf'
    output_path = './tests/output'

    artifacts_folder = utils.pdf2html(file_path, output_path)
    assert artifacts_folder == str(Path('./tests/output/xpdf_pdf-1').resolve())
    rmtree(artifacts_folder)


def test_pdf2html_cannot_export_to_existing_folder():
    # pdftohtml error code 2: Target folder already exists
    file_path = './tests/data/pdf-1.pdf'
    output_path = './tests/output'

    artifacts_folder = utils.pdf2html(file_path, output_path)
    assert artifacts_folder == str(Path('./tests/output/xpdf_pdf-1').resolve())

    with pytest.raises(CalledProcessError,
                       match=r".*returned non-zero exit status 2.*"):
        utils.pdf2html(file_path, output_path)
    rmtree(artifacts_folder)


def test_pdf2html_pdf_does_not_exist():
    # pdftohtml error code 1: Error opening PDF
    file_path = './tests/data/NON_EXISTENT.pdf'
    output_path = './tests/output'

    with pytest.raises(CalledProcessError,
                       match=r".*returned non-zero exit status 1.*"):
        utils.pdf2html(file_path, output_path)


def test_chromeExtractPageTextContent():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--headless')
    browser = webdriver.Chrome('chromedriver', options=chrome_options)

    html_path_path = str(Path('./tests/data/htmls/page1.html').resolve())

    try:
        page = utils.extract_page_text_content(browser, html_path_path)
        assert isinstance(page.width, int)
        assert isinstance(page.height, int)
        assert len(page.text_boxes) > 0
    finally:
        browser.quit()


def test_intersectionBetweeTwoSegments():
    point_a0 = [2, 2]
    point_a1 = [4, 3]
    point_b0 = [6, 0]
    point_b1 = [6, 3]

    intersect = utils.intersect_two_segments(point_a0, point_a1, point_b0,
                                             point_b1)
    assert intersect == [6, 4]


# use to test the sort by common objects
# [CountTuple(count=31, value=167),
#  CountTuple(count=13, value=36),
#  CountTuple(count=5, value=35),
#  CountTuple(count=4, value=166),
#  CountTuple(count=1, value=421),
#  CountTuple(count=1, value=180),
#  CountTuple(count=1, value=188)]