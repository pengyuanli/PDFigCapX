# PdfFigCapx

Python3 implementation of Li et al. [_Figure and caption extraction from biomedical documents_](https://academic.oup.com/bioinformatics/article/35/21/4381/5428177) (2018).
PdfFigCapx extracts figures and captions from PDF documents, and returns the
extracted content and associated metadata.

Following https://mathspp.com/blog/how-to-create-a-python-package-in-2022 to setup the repository structure.

## Dependencies

The project relies on [ChromeDriver](https://chromedriver.chromium.org/downloads) and pdf2html utility from [Xpdf command line tools](https://www.xpdfreader.com/download.html). The library will look by default for ChromDriver at _/usr/bin_ but you can provide a custom path. For pdf2html, make sure the binaries are added to your PATH or in _/usr/bin_.

## Usage

## Contribute

This project uses [Poetry](https://python-poetry.org/) for dependency management. After cloning the repository, install the dependencies using ` poetry install`. For VSCode, you can also add the environment to the project using and then installing the dependencies:

```bash
poetry config virtualenvs.in-project true
peotry install
```

Then you can add the interpreter in your IDE. In case you need to delete and reinstall an environment (.venv), check this [post](https://stackoverflow.com/a/64434542).
