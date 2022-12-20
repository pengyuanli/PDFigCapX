from src.models import Bbox, Layout
from src.page import HtmlPage
from typing import List, Tuple
from math import floor


class LayoutBuilder:
    def build(pages: List[HtmlPage], min_width=30) -> Layout:
        layout = LayoutBuilder._calculate_layout(pages, threshold=min_width)
        return layout

    def _calculate_row_size(pages: List[HtmlPage], threshold=30) -> Tuple[int, int]:
        widths = [y.width for x in pages for y in x.text_boxes if y.width > threshold]
        heights = [y.height for x in pages for y in x.text_boxes if y.width > threshold]
        sorted_widths = sorted(
            [(i, widths.count(i)) for i in set(widths)],
            key=lambda x: (x[1], x[0]),
            reverse=True,
        )
        sorted_heights = sorted(
            [(i, heights.count(i)) for i in set(heights)],
            key=lambda x: x[1],
            reverse=True,
        )
        width = sorted_widths[0][0]
        height = sorted_heights[0][0]

        return width, height

    def _calc_main_content_page_size(pages: List[HtmlPage]) -> Tuple[int, int]:
        sizes = []
        for page in pages:
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

    def _merge_left_padded_points(
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

    def _find_content_region(
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
        sorted_x0s = LayoutBuilder._merge_left_padded_points(sorted_x0s)

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
        if len(cand_y1s) == 0:
            raise Exception("could not find a suitable y1 for content region")

        cr_y1 = max(cand_y1s)
        cr = {"x": cr_x0, "y": cr_y0, "width": cr_x1 - cr_x0, "height": cr_y1 - cr_y0}
        return Bbox(**cr)

    def _calculate_layout(pages: List[HtmlPage], threshold):
        row_width, row_height = LayoutBuilder._calculate_row_size(pages, threshold)
        width, height = LayoutBuilder._calc_main_content_page_size(pages)
        content_region = LayoutBuilder._find_content_region(
            pages, (width, height), threshold
        )

        # number of columns
        # using page_width / row_width can fail when the publication has a lot of
        # padding outside of the content region and withing columns
        number_cols = floor(content_region.width / row_width)
        if number_cols == 1:
            # safety check for one column papers with the column not occupying
            # the whole width -> this is a workaround for PlosOne papers
            if content_region.x > width / 4:
                left_most_x = sorted([el.x for x in pages for el in x.text_boxes])
                right_most_x = sorted(
                    [el.x1 for x in pages for el in x.text_boxes],
                    reverse=True,
                )
                content_region.x = left_most_x[0]
                content_region.x1 = right_most_x[0]
                content_region.update_width()
            col_coords = [content_region.x]
        elif number_cols == 2:
            x1s = [
                y.x
                for x in pages
                for y in x.text_boxes
                if y.x >= content_region.x + row_width
            ]
            x1s = sorted(
                [(i, x1s.count(i)) for i in set(x1s)], key=lambda x: x[1], reverse=True
            )
            col_coords = [content_region.x, x1s[0][0]]
        else:
            raise Exception(
                f"The document has {number_cols} columns. We only support a maximum of two."
            )

        return Layout(
            width=width,
            height=height,
            row_width=row_width,
            row_height=row_height,
            content_region=content_region,
            num_cols=number_cols,
            col_coords=col_coords,
        )
