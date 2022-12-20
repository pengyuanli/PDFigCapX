"""
pdf_info is to get the basic infomation from pdfs
info={
filename, height, width, page_no, figure_est_no, layout_bbox, text_mask
}
"""
# pylint: disable-all
from selenium import webdriver
from selenium.webdriver.common.by import By
from multiprocessing import Pool, TimeoutError
import time
import os
import json

# Column width, middle gap, Maximum Figure number will be helpful
def pdf_info(html_file_path, pdf):
    # Get the pdf info by parsing html

    info = {}
    # obtain file name
    info["filename"] = pdf
    # obtain page no
    for_counting = []
    for page in os.listdir(html_file_path):
        if page.endswith(".png") & page.startswith("page"):
            for_counting.append(page)
    page_no = len(for_counting)
    for_counting = sorted(for_counting)
    info["page_no"] = page_no
    # Obtain all html information
    list_of_htmls = []
    html_info = []
    html_info_json = html_file_path + "/" + pdf[:-4] + ".json"
    if os.path.isfile(html_info_json):
        with open(html_info_json) as json_data:
            html_info = json.load(json_data)
    else:
        browser = webdriver.Chrome(
            "/home/jtt/Documents/chromedriver_linux64/chromedriver"
        )
        for page_id in range(page_no):
            page = for_counting[page_id]
            html_file = "file://" + html_file_path + "/" + page[:-4] + ".html"
            list_of_htmls.append(html_file)
            browser.get(html_file)
            page_layout = browser.find_element(By.XPATH, "/html/body/img")
            img_size = (page_layout.size["height"], page_layout.size["width"])
            text_elements = browser.find_elements(By.XPATH, "/html/body/div")
            text_boxes = []
            for element in text_elements:
                text = element.text
                if len(text) > 0:
                    text_boxes.append(
                        [
                            [
                                element.location["x"],
                                element.location["y"],
                                element.size["width"],
                                element.size["height"],
                            ],
                            text,
                        ]
                    )
            html_info.append(
                [int(os.path.basename(html_file)[4:-5]), text_boxes, img_size]
            )
        browser.quit()
        # html_info.append(read_each_html(html_file))
        with open(html_file_path + "/" + pdf[:-4] + ".json", "w") as outfile:
            json.dump(html_info, outfile)
    # multithread = Pool(4)
    # html_info = multithread.map(read_each_html, list_of_htmls)
    # multithread.close()
    # multithread.join()
    # obtain text layout
    row_width = []
    row_height = []
    column_no = 1
    columns = [0]
    left_point = []
    top_point = []
    right_point = []

    if page_no > 3:
        list_to_check = range(2, page_no)
    else:
        list_to_check = range(1, page_no + 1)
    for each_page_html in html_info:
        if each_page_html[0] in list_to_check:
            # print each_page_html[0]
            # Obtain page convas region
            info["page_height"] = each_page_html[2][0]
            info["page_width"] = each_page_html[2][1]
            for element in each_page_html[1]:
                if len(element[1]) > 30:
                    row_width.append(element[0][2])
                    row_height.append(element[0][3])
                    left_point.append(element[0][0])
                    right_point.append(element[0][0] + element[0][2])
                    top_point.append(element[0][1])
    point_left = sorted(
        [(i, left_point.count(i)) for i in set(left_point)],
        key=lambda x: x[1],
        reverse=True,
    )
    width_row = sorted(
        [(i, row_width.count(i)) for i in set(row_width)],
        key=lambda x: x[1],
        reverse=True,
    )
    height_row = sorted(
        [(i, row_height.count(i)) for i in set(row_height)],
        key=lambda x: x[1],
        reverse=True,
    )
    info["row_height"] = height_row[0][0]
    info["row_width"] = width_row[0][0]
    info["text_layout"] = (
        max(0, min(top_point)),
        min(info["page_height"], max(top_point)),
    )

    # Compute column no and position for each column
    i = 0
    while i < len(point_left):
        j = i + 1
        while j < len(point_left):
            if abs(point_left[i][0] - point_left[j][0]) <= 10:
                point_left[i] = (point_left[i][0], point_left[i][1] + point_left[j][1])
                del point_left[j]
            else:
                j = j + 1
        i = i + 1
    point_left = sorted(point_left, key=lambda x: x[1], reverse=True)

    if (
        float(point_left[0][1]) / len(left_point) > 0.75
        or float(info["row_width"]) / info["page_width"] > 0.5
    ):
        column_no = 1
        columns = [point_left[0][0]]
    else:  # float(point_left[1][1]) / len(left_point) > 0.2:  # Need to
        # correct, it may cause numbe below 0
        column_no = (
            2  # int(float((info['page_width'] - 2*point_left[0][0]))/info['row_width'])
        )

        for i in range(1, len(point_left)):
            if abs(point_left[i][0] - point_left[0][0]) > info["row_width"]:
                columns = [
                    min(point_left[i][0], point_left[0][0]),
                    max(point_left[i][0], point_left[0][0]),
                ]
                break

    info["column_no"] = column_no
    info["columns"] = columns

    left_bar = min(left_point)
    right_bar = max(right_point)
    # pdf layout
    if left_bar > 0 and left_bar < 20 * info["row_height"]:
        info["left_bbox"] = [0, 0, left_bar, info["page_height"]]
        info["right_bbox"] = [
            min(info["page_width"] - 2 * info["row_height"], right_bar),
            0,
            info["page_width"]
            - min(info["page_width"] - 2 * info["row_height"], right_bar),
            info["page_height"],
        ]
        if (
            info["text_layout"][0] < 15 * info["row_height"]
            and info["text_layout"][1] > 15 * info["row_height"]
        ):
            info["top_bbox"] = [0, 0, info["page_width"], info["text_layout"][0]]
            info["down_bbox"] = [
                0,
                info["text_layout"][1],
                info["page_width"],
                info["page_height"] - info["text_layout"][1],
            ]
        else:
            info["top_bbox"] = [0, 0, info["page_width"], info["row_height"]]
            info["down_bbox"] = [
                0,
                info["page_height"] - info["row_height"],
                info["page_width"],
                info["row_height"],
            ]
    else:
        info["left_bbox"] = [0, 0, info["row_height"], info["page_height"]]
        info["right_bbox"] = [
            info["page_width"] - info["row_height"],
            0,
            info["row_height"],
            info["page_height"],
        ]
        info["top_bbox"] = [0, 0, info["page_width"], info["row_height"]]
        info["down_bbox"] = [
            0,
            info["page_height"] - info["row_height"],
            info["page_width"],
            info["row_height"],
        ]

    # print info['left_bbox']
    # print info['right_bbox']
    # print info['top_bbox']
    # print info['down_bbox']
    info["mess_up"] = False
    info["graph_layout"] = info["text_layout"]

    return info, html_info


def read_each_html(x):
    # browser = webdriver.Chrome('/home/pengyuan/chromedriver')
    # browser = webdriver.Chrome('/usa/pengyuan/Documents/RESEARCH/PDFigCapX/chromedriver/chromedriver')
    # browser.implicitly_wait(2)
    browser.get(x)
    page_layout = browser.find_element_by_xpath("/html/body/img")
    img_size = (page_layout.size["height"], page_layout.size["width"])
    text_elements = browser.find_elements_by_xpath("/html/body/div")
    text_boxes = []
    for element in text_elements:
        text = element.text
        if len(text) > 0:
            text_boxes.append(
                [
                    [
                        element.location["x"],
                        element.location["y"],
                        element.size["width"],
                        element.size["height"],
                    ],
                    text,
                ]
            )

    browser.quit()
    return int(os.path.basename(x)[4:-5]), text_boxes, img_size
