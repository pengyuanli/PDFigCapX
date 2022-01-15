from dataclasses import dataclass, field
from typing import List, Tuple
from .utils import sort_by_most_common_value_desc
from .html_content import CountTuple, HtmlPage, PageBoxesCounts, BoundingBox


@dataclass
class PdfLayout:
    """
      TODO: I believe this should be used per page, not passing an array of pages
    """
    pages: List[HtmlPage]
    min_text_length: int

    page_height: int = field(init=False)
    page_width: int = field(init=False)

    text_x_min: int = field(init=False)
    text_x_max: int = field(init=False)
    text_y_min: int = field(init=False)
    text_y_max: int = field(init=False)

    row_width: int = field(init=False)
    row_height: int = field(init=False)

    number_columns: int = field(init=False)
    start_x_cols: List[int] = field(init=False)

    def __post_init__(self):
        txtbox_size_diff = 10
        counts = self._count_elements(txtbox_size_diff)

        self.page_height = self.pages[0].height
        self.page_width = self.pages[0].width
        self.row_width = counts.sorted_width_counts[0].value
        self.row_height = counts.sorted_height_counts[0].value

        self.text_x_min = min(counts.x0s)
        self.text_x_common_min = counts.sorted_x0_counts[0].value
        self.text_x_max = max(counts.x1s)
        self.text_y_min = max(0, min(counts.y0s))
        self.text_y_max = min(self.page_height,
                              max(counts.y0s) + self.row_height)

        # what if there are different page widths
        start_x_columns = self._calc_columns(counts, self.pages[0].width)
        self.number_columns = len(start_x_columns)
        self.start_x_cols = start_x_columns

    def _count_elements(self, txtbox_size_diff: int) -> PageBoxesCounts:
        counts = PageBoxesCounts()
        for page in self.pages:
            for text_line in page.text_lines:
                if len(text_line.text) > self.min_text_length:
                    counts.x0s.append(text_line.x_top_left)
                    counts.y0s.append(text_line.y_top_left)
                    counts.x1s.append(text_line.x_top_right)
                    counts.widths.append(text_line.width)
                    counts.heights.append(text_line.height)
        counts.sorted_x0_counts = sort_by_most_common_value_desc(counts.x0s)
        counts.sorted_width_counts = sort_by_most_common_value_desc(
            counts.widths)
        counts.sorted_height_counts = sort_by_most_common_value_desc(
            counts.heights)

        counts.sorted_x0_counts = self._merge_counts(counts.sorted_x0_counts,
                                                     distance=txtbox_size_diff)
        return counts

    def _merge_counts(self,
                      count_arr: List[CountTuple],
                      distance=10) -> List[CountTuple]:
        new_count_arr = count_arr.copy()

        i = 0
        while i < len(new_count_arr):
            j = i + 1
            while j < len(new_count_arr):
                diff = new_count_arr[i].value - new_count_arr[j].value
                if abs(diff) <= distance:
                    new_count_arr[i] = CountTuple(
                        value=new_count_arr[i].value,
                        count=new_count_arr[i].count + new_count_arr[j].count)
                    del new_count_arr[j]
                else:
                    j = j + 1
            i = i + 1
        new_count_arr = sorted(new_count_arr,
                               key=lambda x: x.count,
                               reverse=True)
        return new_count_arr

    def _calc_columns(self, counts: PageBoxesCounts,
                      page_width: int) -> List[int]:
        most_common_x0 = counts.sorted_x0_counts[0]
        most_common_row_width = counts.sorted_width_counts[0]

        # only one column
        ratio_x0 = float(most_common_x0.count) / len(counts.sorted_x0_counts)
        ratio_width = float(most_common_row_width.value) / page_width
        if ratio_x0 > 0.75 or ratio_width > 0.5:
            return [most_common_x0.value]

        # two columns: find first text box to the right
        for i in range(1, len(counts.sorted_x0_counts)):
            diff = counts.sorted_x0_counts[i].value - most_common_x0.value
            if abs(diff) > most_common_row_width.value:
                return [
                    min(counts.sorted_x0_counts[i].value,
                        most_common_x0.value),
                    max(counts.sorted_x0_counts[i].value, most_common_x0.value)
                ]
        raise Exception("Cannot determine starting points for 2 columns")

    def find_surrounding_bboxes(
            self) -> Tuple[BoundingBox, BoundingBox, BoundingBox, BoundingBox]:
        """ Return left, right, top, bottom bounding boxes """
        left_bbox = BoundingBox(x0=0,
                                y0=0,
                                x1=self.text_x_min,
                                y1=self.page_height)
        right_bbox = BoundingBox(x0=self.text_x_max,
                                 y0=0,
                                 x1=self.page_width,
                                 y1=self.page_height)
        top_bbox = BoundingBox(x0=0,
                               y0=0,
                               x1=self.page_width,
                               y1=self.text_y_min)
        bottom_bbox = BoundingBox(x0=0,
                                  y0=self.text_y_max,
                                  x1=self.page_width,
                                  y1=self.page_height)

        # # why row_height instead of row_width if we are calculating x
        # if self.text_x_min > 0 and self.text_x_min < 20 * self.row_height:
        #     left_bbox = BoundingBox(x0=0,
        #                             y0=0,
        #                             x1=self.text_x_min,
        #                             y1=self.page_height)
        #     right_bbox = BoundingBox(x0=self.text_x_max,
        #                              y0=0,
        #                              x1=self.page_width,
        #                              y1=self.page_height)

        #     # what is 15?
        #     if self.text_y_min < 15 * self.row_height and self.text_y_max > 15 * self.row_height:
        #         top_bbox = BoundingBox(x0=0,
        #                                y0=0,
        #                                x1=self.page_width,
        #                                y1=self.text_y_min)
        #         bottom_bbox = BoundingBox(x0=0,
        #                                   y0=self.text_y_max + self.row_height,
        #                                   x1=self.page_width,
        #                                   y1=self.page_height)
        #     else:
        #         top_bbox = BoundingBox(x0=0,
        #                                y0=0,
        #                                x1=self.page_width,
        #                                y1=self.row_height)
        #         bottom_bbox = BoundingBox(x0=0,
        #                                   y0=self.page_height -
        #                                   self.row_height,
        #                                   x1=self.page_width,
        #                                   y1=self.row_height)
        # else:
        #     left_bbox = BoundingBox(x0=0,
        #                             y0=0,
        #                             x1=self.row_height,
        #                             y1=self.page_height)
        #     right_bbox = BoundingBox(x0=self.page_width - self.row_height,
        #                              y0=0,
        #                              x1=self.row_height,
        #                              y1=self.page_height)
        #     top_bbox = BoundingBox(x0=0,
        #                            y0=0,
        #                            x1=self.page_width,
        #                            y1=self.row_height)
        #     bottom_bbox = BoundingBox(x0=0,
        #                               y0=self.page_height - self.row_height,
        #                               x1=self.page_width,
        #                               y1=self.row_height)

        return (left_bbox, right_bbox, top_bbox, bottom_bbox)
