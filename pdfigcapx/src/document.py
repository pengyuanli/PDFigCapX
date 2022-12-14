import logging
from os import listdir, makedirs
from pathlib import Path
from typing import List, Tuple
from math import floor, ceil
from shutil import rmtree
from matplotlib.pyplot import subplots, savefig, close as plt_close
from PIL import Image as PILImage

from src.models import Layout, Bbox, Figure
from src.page import HtmlPage
from src.utils import launch_chromedriver, extract_page_text_content, pdf2html
from src.draw import draw_bboxes, draw_content_region, draw_text_regions, draw_columns
import src.contours as cnt
from src.sweep import sweep_regions
import src.utils as utils


def valid_file(filename: str):
    return filename.endswith(".html") and filename.startswith("page")


def valid_image(filename: str):
    return filename.endswith(".png") and not filename.startswith(".")


def calc_row_size(pages: List[HtmlPage], threshold=30):
    widths = [y.width for x in pages for y in x.text_boxes if y.width > threshold]
    heights = [y.height for x in pages for y in x.text_boxes if y.width > threshold]
    sorted_widths = sorted(
        [(i, widths.count(i)) for i in set(widths)], key=lambda x: x[1], reverse=True
    )
    sorted_heights = sorted(
        [(i, heights.count(i)) for i in set(heights)], key=lambda x: x[1], reverse=True
    )
    width = sorted_widths[0][0]
    height = sorted_heights[0][0]

    return width, height


def merge_left_padded_points(
    sorted_points: list[tuple[int, int]], padding_threshold=10
) -> list[tuple[int, int]]:
    """Update the sorted counts by merging padded text elements"""
    left_points = sorted_points.copy()
    i = 0
    while i < len(left_points):
        j = i + 1
        while j < len(left_points):
            if abs(left_points[i][0] - left_points[j][0]) <= padding_threshold:
                left_points[i] = (
                    left_points[i][0],
                    left_points[i][1] + left_points[j][1],
                )
                del left_points[j]
            else:
                j = j + 1
        i = i + 1
    return sorted(left_points, key=lambda x: x[1], reverse=True)


def find_content_region(
    pages: List[HtmlPage], main_size: Tuple[int, int], threshold=30
):
    """
    There may be a case when there are more rows on the right side, so use page_width to filter
    """
    page_width, page_height = main_size
    x0s = [
        y.x
        for x in pages
        for y in x.text_boxes
        if y.width > threshold and y.x < page_width / 2
    ]
    y0s = [y.y for x in pages for y in x.text_boxes if y.width > threshold]
    x1s = [y.x1 for x in pages for y in x.text_boxes if y.width > threshold]
    sorted_x0s = sorted(
        [(i, x0s.count(i)) for i in set(x0s)], key=lambda x: x[1], reverse=True
    )
    sorted_x0s = merge_left_padded_points(sorted_x0s)

    # content region
    cr_x0 = sorted_x0s[0][0]
    cr_y0 = max(0, min(y0s))
    # The converted html file may have some overflowing divs due to conversion
    # errors. In case of overflow, assume a similar padding like the left side
    cr_x1 = min(page_width - cr_x0, max(x1s))
    cand_y1s = [  # y1s constrained to other three coordinates and page height
        y.y1
        for x in pages
        for y in x.text_boxes
        if y.x >= cr_x0 and y.x1 <= cr_x1 and y.y >= cr_y0 and y.y1 <= page_height
    ]
    cr_y1 = max(cand_y1s)
    cr = {"x": cr_x0, "y": cr_y0, "width": cr_x1 - cr_x0, "height": cr_y1 - cr_y0}
    return Bbox(**cr)


##################################################################################


class Document:
    def __init__(
        self,
        pdf_path: str,
        xpdf_base_path: str,
        data_path: str,
        include_first_page=False,
    ):
        self.pdf_path = Path(pdf_path)
        self.doc_name = self.pdf_path.stem
        self.include_first_page = include_first_page
        self.xpdf_base_path = Path(xpdf_base_path)
        self.data_path = Path(data_path)

        self.pages: List[HtmlPage] = []
        self.layout: Layout = None

        logging.info(f"{self.doc_name} starting process ${self.pdf_path}")

        self.transform_pdf()
        self.fetch_pages()
        self.calculate_layout()
        self.expand_captions()

    def transform_pdf(self) -> None:
        if not self.xpdf_base_path.exists():
            makedirs(self.xpdf_base_path)

        prefixed_name = f"xpdf_{self.doc_name}"
        self.xpdf_path = self.xpdf_base_path / prefixed_name
        if self.xpdf_path.exists():
            logging.debug(f"attempting to reuse xpdf content {self.xpdf_path}")
        else:
            out_path = pdf2html(
                self.pdf_path.resolve(), self.xpdf_base_path.resolve(), prefixed_name
            )
            self.xpdf_path = Path(out_path)

    def fetch_pages(self) -> None:
        names = [name for name in listdir(self.xpdf_path) if valid_file(name)]
        browser = launch_chromedriver()

        try:
            pages = []
            for page_name in names:
                page_path = (self.xpdf_path / page_name).resolve()
                page = extract_page_text_content(browser, page_path)
                pages.append(page)
        except Exception as e:
            logging.error("Error parsing pages", exc_info=True)
            raise Exception(e)
        finally:
            if browser:
                browser.quit()
        self.pages = sorted(pages, key=lambda x: x.number)

    def _calc_main_content_page_size(self) -> Tuple[int, int]:
        sizes = []
        for page in self.pages:
            size = (page.width, page.height)
            if size not in sizes:
                sizes.append(size)
        if len(sizes) == 1:
            # best scenario, most common when supp material not present
            return sizes[0]
        elif len(sizes) == 2:
            # main content + supp material in a different page size
            return sizes[0]
        else:
            # very unusual cases where the publication has a intro page from
            # publisher, the main content and supplementary materials.
            return sizes[1]

    def calculate_layout(self) -> None:
        """Estimates the page size, number of columns, column width and height,
        and coordinates for each column
        """
        # use more common widths and heights to estimate row properties
        row_width, row_height = calc_row_size(self.pages, threshold=30)
        # use most common coordinates to find the publication text region
        main_size = self._calc_main_content_page_size()
        content_region = find_content_region(self.pages, main_size, threshold=30)

        # number of columns
        # using page_width / row_width can fail when the publication has a lot of
        # padding outside of the content region and withing columns
        number_cols = floor(content_region.width / row_width)
        if number_cols == 1:
            col_coords = [content_region.x]
        else:
            x1s = [
                y.x
                for x in self.pages
                for y in x.text_boxes
                if y.x >= content_region.x + row_width
            ]
            x1s = sorted(
                [(i, x1s.count(i)) for i in set(x1s)], key=lambda x: x[1], reverse=True
            )
            col_coords = [content_region.x, x1s[0][0]]

        width, height = main_size
        self.layout = Layout(
            width=width,
            height=height,
            row_width=row_width,
            row_height=row_height,
            content_region=content_region,
            num_cols=number_cols,
            col_coords=col_coords,
        )

    def expand_captions(self):
        """Grab the starting caption, iterate over the text boxes not
        assigned as captions to expand the caption into a paragraph. Finally,
        estimate whether the caption spans over multiple columns or not.
        """
        for page in self.pages:
            page.expand_captions(self.layout)

    def extract_figures(self, min_orphan_size=1000) -> None:
        """Traverse the pages in order and extract every figure by matching captions.
        When a page has captions and candidates, we have to match every caption.
        When a page only has candidates and no captions, the caption may be
          on the next page only if it's on the top of the page. In any other case,
          the candidate has no caption if the candidate size is big enough to
          represent a figure. Figures with no captions are common when the PDF
          includes supplementary material or when we missed to detect a caption
          pattern in a text box.
        """
        pages = []
        pages = self.pages if self.include_first_page else self.pages[1:]

        for idx, page in enumerate(pages):
            candidates, _, _ = cnt.get_candidates(
                str(self.xpdf_path), page, self.layout, page.captions
            )
            # match captions with candidates, assigned captions become figures
            if len(page.captions) > 0:
                if len(candidates) > 0:
                    sweep_regions(page, candidates, page.captions, [], self.layout)
                else:
                    self._log_captions_without_candidates(page)
                if page.orphan_figure is not None:
                    self._log_remaining_orphans_not_match(page)
            else:
                if len(candidates) > 0:
                    candidates = self._match_across_pages(
                        pages, idx, candidates, min_orphan_size
                    )
                    if candidates is not None:
                        # caption not found on next page, save as orphan image
                        bbox = Bbox.merge_bboxes(candidates)
                        figure = Figure(bbox, True, None, "orphan")
                        figure.identifier = ""
                        page.figures.append(figure)

    def _log_captions_without_candidates(self, page):
        logging.info(f"{self.doc_name} - pg.{page.number}: captions have no candidates")

    def _log_remaining_orphans_not_match(self, page):
        logging.info(
            f"{self.doc_name} - pg.{page.number}: remaining orphans not matched with any caption"
        )

    def _match_across_pages(
        self,
        pages: List[HtmlPage],
        page_idx: int,
        candidates: List[Bbox],
        min_orphan_size: int,
    ) -> List[Bbox]:

        if page_idx == len(pages) - 1:
            # last page can't have caption on next page
            return candidates
        bbox = Bbox.merge_bboxes(candidates)
        if bbox.area() < min_orphan_size:
            # candidates too small, discard
            return None
        # grab captions that are just below the content region
        thres = self.layout.content_region.x + self.layout.row_height * 1.5
        captions = [c for c in pages[page_idx + 1].captions if c.x < thres]
        if len(captions) != 1:
            # no captions or too many, which idk how to handle
            return candidates

        orphan_caption = captions[0]
        # update captions on next page by reference
        updated_captions = [
            c for c in pages[page_idx + 1].captions if c.id != orphan_caption.id
        ]
        pages[page_idx + 1].captions = updated_captions
        figure = Figure(bbox, True, orphan_caption, "orphan")
        figure.identifier = captions[0].get_caption_identifier()
        pages[page_idx].figures.append(figure)
        # assigned orphan figure to caption in next page succesfully
        return None

    def draw(
        self,
        n_cols: int,
        cr=True,
        txtr=False,
        colr=False,
        capr=True,
        figr=True,
        save=False,
    ) -> None:
        n_rows = ceil(len(self.pages) / n_cols)
        fig, ax = subplots(n_rows, n_cols, dpi=300)

        for idx, page in enumerate(self.pages):
            col = idx % n_cols
            row = int(idx / n_cols)

            page_name = page.img_name
            png_path = (self.xpdf_path / page_name).resolve()
            page_image = PILImage.open(png_path)
            page_image = page_image.resize((page.width, page.height))

            if cr:
                draw_content_region(ax[row][col], self.layout.content_region)
            if txtr:
                draw_text_regions(ax[row][col], page)
            if colr:
                draw_columns(ax[row][col], self.layout)
            if capr:
                draw_bboxes(ax[row][col], page.captions, "black", "black", 1.0)
            if figr:
                bboxes = [el.bbox for el in page.figures]
                draw_bboxes(ax[row][col], bboxes, "orange", "orange", 0.7)
            ax[row][col].imshow(page_image)
            ax[row][col].set_title(f"pg.{page.number}")
            ax[row][col].axis("off")
        for idx in range(len(self.pages), n_rows * n_cols):
            col = idx % n_cols
            row = int(idx / n_cols)
            ax[row][col].axis("off")
        fig.suptitle(self.pdf_path.stem)
        fig.tight_layout()

        if save:
            if not self.data_path.exists():
                makedirs(self.data_path.resolve())
            output_path = self.data_path / f"{self.doc_name}.png"
            savefig(output_path, dpi=1200)
        plt_close(fig)  # close to avoid memory leak

    def _fetch_pages_as_images(self, dpi=300) -> list[PILImage.Image]:
        """Return PDF pages as PIL Images"""
        output_folder = self.data_path / f"{self.doc_name}_images"
        makedirs(output_folder, exist_ok=True)
        utils.pdf2images(self.pdf_path.resolve(), output_folder.resolve(), dpi=dpi)
        filenames = listdir(output_folder)
        image_names = [x for x in filenames if valid_image]
        image_names = utils.natural_sort(image_names)
        images = []
        for image_name in image_names:
            pil_image = PILImage.open(output_folder / image_name).convert("RGB")
            pil_image.load()  # load into memory (also closes the file associated)
            images.append(pil_image)
        rmtree(output_folder)
        return images

    def save_images(self, dpi=300, prefix=None):
        pil_images = self._fetch_pages_as_images(dpi)
        str_prefix = "" if not prefix else f"{prefix}_"
        for page, pil_image in zip(self.pages, pil_images):
            scale = float(pil_image.size[0]) / self.layout.width

            for idx, fig in enumerate(page.figures):
                crop_box = [
                    fig.bbox.x * scale,
                    fig.bbox.y * scale,
                    fig.bbox.x1 * scale,
                    fig.bbox.y1 * scale,
                ]
                extracted_fig = pil_image.crop(crop_box)
                fig_name = f"{str_prefix}{page.number}_{idx+1}.jpg"
                fig_path = self.data_path / fig_name
                extracted_fig.save(fig_path)
                extracted_fig.close()

    def debug_candidates(self, n_cols=10):
        n_rows = ceil(len(self.pages) / n_cols)
        fig, ax = subplots(n_rows, n_cols, dpi=300)
        pages = []
        pages = self.pages if self.include_first_page else self.pages[1:]

        for idx, page in enumerate(pages):
            candidates, cnts, orig_cnts = cnt.get_candidates(
                str(self.xpdf_path), page, self.layout, page.captions
            )
            col = idx % n_cols
            row = int(idx / n_cols)

            page_name = page.img_name
            png_path = (self.xpdf_path / page_name).resolve()
            page_image = PILImage.open(png_path)
            page_image = page_image.resize((page.width, page.height))

            page_box = Bbox(1, 1, page.width, page.height)
            draw_bboxes(ax[row][col], [page_box], "black", "none", 1.0)
            draw_content_region(ax[row][col], self.layout.content_region)
            draw_bboxes(ax[row][col], page.captions, "black", "black", 0.5)
            draw_bboxes(ax[row][col], candidates, "red", "red", 0.5)
            draw_bboxes(ax[row][col], cnts, "blue", "blue", 0.5)
            draw_bboxes(ax[row][col], orig_cnts, "green", "green", 0.5)
            ax[row][col].imshow(page_image)
            ax[row][col].set_title(f"pg.{page.number}")
            ax[row][col].axis("off")

        for idx in range(len(self.pages), n_rows * n_cols):
            col = idx % n_cols
            row = int(idx / n_cols)
            ax[row][col].axis("off")
