from dataclasses import dataclass, field


@dataclass
class PageMetadata:
    filename: str
    page_number: int
    page_width: float = field(default=0.0)
    page_width: float = field(default=0.0)
    number_columns: int = field(default=0)
    row_height: float = field(default=0.0)
    row_width: float = field(default=0.0)
    text_layout: float = field(default=0.0)
    left_bbox: float = field(default=0.0)
    right_bbox: float = field(default=0.0)
    top_bbox: float = field(default=0.0)
    down_bbox: float = field(default=0.0)
    mess_up: bool = field(default=False)
    graph_layout: float = field(default=0.0)
