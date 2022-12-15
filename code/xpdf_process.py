"""
The main code for figure and caption extraction (figures_captions_list)
1. Read pdfs from input folder  (pdf_info)
2. Figure and caption pair detection

    2.1. graphical content detection
    2.2 page segmentation
    2.3 figure detetion
    2.4 caption association

3. Mess up pdf processing

"""

import codecs
import os
import re
import subprocess
import sys

import cv2
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
from lxml import etree
from pdf_info import pdf_info
from selenium import webdriver


def figures_captions_list(input_path, pdf, output_path):
    # input: single pdf file
    # output: bounding box list of figures and captions
    pdf_filename = input_path + pdf
    html_file_path = output_path + pdf[:-4]
    # 1. Read pdfs from input folder  (pdf_info)
    info, html_boxes = pdf_info(html_file_path, pdf)
    #  2.1. graphical content detection
    cap_box, fig_box, info, table_box, text_box = box_detection(
        html_file_path, info, html_boxes
    )
    pre_figures, cap_regions = fig_cap_matching(
        cap_box, fig_box, info, table_box, text_box
    )
    figures, captions = evaluation(
        pre_figures, cap_regions, html_file_path, info, html_boxes
    )  # Remove figure_table and figure caption in one box
    figures, captions = check_region(info, figures, captions)
    no_of_figures = sum([len(figures[x]) for x in figures])
    no_of_caps = sum([len(cap_box[x]) for x in cap_box])
    no_of_figs = sum([len(fig_box[x]) for x in fig_box])
    # print info['filename']
    # print info['mess_up']
    # print info['fig_no_est']

    #
    # print no_of_figures
    # if no_of_figures == no_of_caps:
    #     figures, cap_regions = same_no_caps_est(cap_box, fig_box, info, table_box, text_box)
    #
    r = info["png_ratio"]
    # plt.close("all")
    # for i in range(info['page_no']):
    #     page = 'page' + str(i + 1) + '.png'
    #     img = cv2.imread(html_file_path + '/' + page)
    #     fig, ax = plt.subplots(1)
    #     ax.imshow(img)
    #     for each_caption in cap_box[page]:
    #         rect = patches.Rectangle((each_caption[0]*r, each_caption[1]*r), each_caption[2]*r, each_caption[3]*r,
    #                                  linewidth=1, edgecolor='g',
    #                                  facecolor='none')
    #         ax.add_patch(rect)
    #
    #     for each_fig in fig_box[page]:
    #         #each_fig = each_fig[0]
    #         rect = patches.Rectangle((each_fig[0]*r, each_fig[1]*r), each_fig[2]*r, each_fig[3]*r,
    #                                  linewidth=2, edgecolor='b',
    #                                  facecolor='none')
    #         ax.add_patch(rect)
    #     for each_cap_region in cap_regions[page]:
    #         rect = patches.Rectangle((each_cap_region[1][0]*r, each_cap_region[1][1]*r), each_cap_region[1][2]*r, each_cap_region[1][3]*r,
    #                                  linewidth=1, edgecolor='y',
    #                                  facecolor='none')
    #         ax.add_patch(rect)
    #     for each_result in figures[page]:
    #         each_result = each_result[0]
    #         rect = patches.Rectangle((each_result[0]*r, each_result[1]*r), each_result[2]*r, each_result[3]*r,
    #                                  linewidth=1, edgecolor='r',
    #                                  facecolor='none')
    #         ax.add_patch(rect)
    #     plt.show()
    return figures, info


def box_detection(html_file_path, info, html_boxes):
    fig_box = {}
    cap_box = {}
    word_box = {}
    cap_no_clue = []
    table_box = {}
    # browser = webdriver.Chrome('/home/pengyuan/Documents/FC_extraction/chromedriver')

    for page in sorted(os.listdir(html_file_path)):
        if page.endswith(".png") and page.startswith("page"):

            page_no = int(page[4:-4])
            img = cv2.imread(html_file_path + "/" + page)
            # plt.imshow(img)
            png_size = img.shape
            if png_size[0] > png_size[1]:
                png_ratio = float(png_size[0]) / info["page_height"]
            else:
                png_ratio = (
                    float(png_size[0]) / info["page_width"]
                )  # TODO: this is probably wrong, png_size[1]

            # Read each page html find "Fig"
            # f = codecs.open(html_file_path + '/' + page[:-4] + '.html', 'r')
            # text = f.readline()
            # html_file = 'file://' + html_file_path + '/' + page[:-4] + '.html'
            # browser.get(html_file)

            text = ""
            text_box = []
            page_word_box = []
            table_cap_box = []
            div_no = 1
            for page_html in html_boxes:
                if page_html[0] == page_no:
                    text_elements = page_html[1]

            for e in text_elements:
                text = e[1]
                # if e.size['width'] > info['row_width']-100:
                # TODO: not sure why i need these boxes again
                page_word_box.append(
                    [
                        max(e[0][0] - info["row_height"], 0),
                        e[0][1],
                        e[0][2] + 2 * info["row_height"],
                        e[0][3],
                    ]
                )
                if (
                    text.startswith("Table")
                    or text.startswith("table")
                    or text.startswith("Box")
                ):
                    table_cap_box.append([e[0][0], e[0][1], e[0][2], e[0][3]])
                if (
                    text.startswith("Fig")
                    or text.startswith("fig")
                    or text.startswith("FIG")
                ):
                    # print text
                    text_box.append([e[0][0], e[0][1], e[0][2], e[0][3]])
                    cap_no_clue.append(text)
                elif "Fig" not in text and len(text) > 6:
                    text = text[:6]
                    idx1 = text.find("F")
                    idx2 = text.find("i")
                    idx3 = text.find("g")
                    if (
                        idx1 >= 0
                        and idx2 >= 0
                        and idx3 >= 0
                        and idx2 > idx1
                        and idx3 > idx2
                    ):
                        # print text
                        text_box.append([e[0][0], e[0][1], e[0][2], e[0][3]])
                    # rect = patches.Rectangle((e.location['x'] * png_ratio, e.location['y'] * png_ratio),
                    #                          e.size['width'] * png_ratio,
                    #                          e.size['height'] * png_ratio,
                    #                          linewidth=1, edgecolor='b',
                    #                          facecolor='none')
                    # ax.add_patch(rect)

            cap_box[page] = text_box
            table_box[page] = table_cap_box
            word_box[page] = page_word_box  # NOT BEING USED

            imgray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            ret, thresh = cv2.threshold(imgray, 240, 255, cv2.THRESH_BINARY_INV)
            kernel = np.ones((5, 5), np.uint8)
            dilation = cv2.dilate(thresh, kernel, iterations=1)
            contours, hierarchy = cv2.findContours(
                dilation, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
            )
            new_thresh = np.zeros(thresh.shape, dtype=np.uint8)

            for cnt in contours:
                bbox = cv2.boundingRect(cnt)
                p_bbox = [int(float(x) / png_ratio) for x in bbox]
                box_image = 0
                for caption_box in text_box:
                    box_image = box_image + overlap_ratio_based(caption_box, p_bbox)
                if box_image < 0.5:
                    cv2.drawContours(new_thresh, [cnt], 0, 255, -1)

            contours, hierarchy = cv2.findContours(
                new_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            potential_bbox = []
            # fig, ax = plt.subplots(1)
            # ax.imshow(img)
            for cnt in contours:
                bbox = cv2.boundingRect(cnt)
                thresh_for_figure = (
                    info["row_height"] * png_ratio * 1.5
                )  # / 2  modified on 0318
                if (
                    bbox[3] > thresh_for_figure and bbox[2] > thresh_for_figure
                ):  # Important to set, FIg threshold

                    p_bbox = [int(float(x) / png_ratio) for x in bbox]
                    # Format checking, to filter box that at top, down, left or right
                    ol_left = overlap_ratio_based(p_bbox, info["left_bbox"])
                    ol_right = overlap_ratio_based(p_bbox, info["right_bbox"])
                    # Add filter for first page top sign 0110
                    if page == "page1.png":
                        ol_top = overlap_ratio_based(
                            p_bbox, [0, 0, info["page_width"], info["page_height"] / 4]
                        )  # First page box
                    else:
                        ol_top = overlap_ratio_based(p_bbox, info["top_bbox"])

                    ol_down = overlap_ratio_based(p_bbox, info["down_bbox"])
                    ol_sum = 0
                    ol_sum = ol_down + ol_left + ol_right + ol_top
                    if ol_sum < 0.1:
                        potential_bbox.append(p_bbox)
                        # rect = patches.Rectangle((bbox[0], bbox[1]), bbox[2],bbox[3],
                        #                         linewidth=1, edgecolor='r',
                        #                        facecolor='none')
                        # ax.add_patch(rect)

            fig_box[page] = potential_bbox

            # To check if the pdf is mess up
            if len(potential_bbox) > 1:
                obj_heights = np.array(potential_bbox)[:, 3]
                no_of_all = len(obj_heights)
                no_of_small = len(
                    [
                        1
                        for obj_height in obj_heights
                        if obj_height < 13 and obj_height > 4
                    ]
                )
                small_percent = float(no_of_small) / no_of_all
                if no_of_all > 300 and small_percent > 0.8:
                    info["mess_up"] = True

            count = 0

            if info["mess_up"] == False:  # Need to set carefully
                while count < len(potential_bbox):  # ###Need to think about it.....
                    flag = 0
                    for (
                        each_text_box
                    ) in page_word_box:  # Remove fig box that cross the text box
                        overlap = overlap_ratio_based(
                            potential_bbox[count], each_text_box
                        )
                        if overlap > 0.3:
                            flag = 1
                            del potential_bbox[count]
                            break
                    if flag == 0:
                        count = count + 1
            else:
                while count < len(potential_bbox):  # ###Need to think about it.....
                    flag = 0
                    if potential_bbox[count][3] > 12:
                        for (
                            each_text_box
                        ) in page_word_box:  # Remove fig box that cross the text box
                            overlap = overlap_ratio_based(
                                potential_bbox[count], each_text_box
                            )
                            if overlap > 0.1:
                                flag = 1
                                del potential_bbox[count]
                                break
                        if flag == 0:
                            count = count + 1
                    else:
                        del potential_bbox[count]

            fig_box[page] = potential_bbox

    info["fig_no_est"] = fig_no_estimation(cap_no_clue)
    info["png_ratio"] = png_ratio
    return cap_box, fig_box, info, table_box, page_word_box


def fig_no_estimation(fig_info):
    # print fig_info
    fig_no = 0
    temp_max = 0
    for clue in fig_info:
        if re.search(r"\d+", clue) is not None:
            temp_max = max(int(re.search(r"\d+", clue).group()), temp_max)
    fig_no = temp_max
    # print fig_no
    return fig_no


# cap_box, fig_box, info, table_box, text_box = box_detection(html_file_path, info, html_boxes)
# pre_figures, cap_regions = fig_cap_matching(cap_box, fig_box, info, table_box, text_box)


def fig_cap_matching(cap_box, fig_box, info, table_box, text_box):
    # cap_box
    # fig_box
    # info
    figures = {}
    captions = {}
    fig_size_thresh = 30
    for i in range(info["page_no"]):
        page = "page" + str(i + 1) + ".png"
        table_caps = table_box[page]

        p_captions = cap_box[page]
        p_figures = fig_box[page]
        for table_cap in table_caps:  # To remove the table
            table_cap_box = [
                table_cap[0],
                table_cap[1] + table_cap[3],
                table_cap[2],
                4 * info["row_height"],
            ]  # Remove the table below
            p_figure_id = 0
            while p_figure_id < len(p_figures):
                p_figure = p_figures[p_figure_id]

                overlap = overlap_ratio_based(table_cap_box, p_figure)
                if overlap > 0.1:
                    del p_figures[p_figure_id]
                else:
                    p_figure_id = p_figure_id + 1
            table_cap_box = [
                table_cap[0],
                table_cap[1] - 4 * info["row_height"],
                table_cap[2],
                4 * info["row_height"],
            ]  # Remove the table below
            p_figure_id = 0
            while p_figure_id < len(p_figures):
                p_figure = p_figures[p_figure_id]

                overlap = overlap_ratio_based(table_cap_box, p_figure)
                if overlap > 0.1:
                    del p_figures[p_figure_id]
                else:
                    p_figure_id = p_figure_id + 1

        if len(p_figures) > 0:
            if len(p_figures) == 1 and len(p_captions) == 1:
                if (
                    p_figures[0][2] > fig_size_thresh
                    and p_figures[0][3] > fig_size_thresh
                ):  # size
                    if bbox_distance(p_figures[0], p_captions[0]) < 50:  # distance
                        figures[page] = [[p_figures[0], p_captions[0]]]
                        captions[page] = [
                            [
                                p_captions[0],
                                [1, 1, info["page_width"] - 2, info["page_height"] - 2],
                            ]
                        ]
                if page not in figures.keys():
                    cap_regions = caption_regions(p_captions, p_figures, info)
                    captions[page] = cap_regions
                    figures[page] = label_subfig(
                        info, p_figures, cap_regions, table_box
                    )

            else:
                # sort captions by horizontal
                cap_regions = caption_regions(p_captions, p_figures, info)

                # Calculate the overlap of figures and cpations, the figures
                # belong to the same caption should have same label
                # print cap_regions
                # For the figures have the same label, compute their bounding
                #  box
                captions[page] = cap_regions
                figures[page] = label_subfig(info, p_figures, cap_regions, table_box)
            if len(p_captions) == 0:  # No caption situation
                sum_area = 0
                for p_object in p_figures:
                    sum_area = sum_area + p_object[2] * p_object[3]

                page_width = (
                    info["page_width"] - info["left_bbox"][2] - info["right_bbox"][2]
                )
                page_height = (
                    info["page_height"] - info["top_bbox"][3] - info["down_bbox"][3]
                )
                if float(sum_area) / (page_width * page_height) > 0.2 and i > 1:
                    captions[page] = [
                        [
                            info["down_bbox"],
                            [1, 1, info["page_width"] - 2, info["page_height"] - 2],
                        ]
                    ]
                    figures[page] = label_subfig(
                        info, p_figures, captions[page], table_box
                    )
        else:
            captions[page] = []
            figures[page] = []

    return figures, captions


def same_no_caps_est(cap_box, fig_box, info, table_box, text_box):

    cap_regions = {}
    figures = {}
    for page in cap_box:
        cap_regions[page] = []
        if len(cap_box[page]) == 1:
            cap_regions[page].append(
                [cap_box[page][0], [0, 0, info["page_width"], info["page_height"]]]
            )
        if len(cap_box[page]) > 1:
            p_figures = fig_box[page]
            p_captions = cap_box[page]
            cap_regions[page] = caption_regions(p_captions, p_figures, info)
    # Calculate the overlap of figures and cpations, the figures
    # belong to the same caption should have same label
    # print cap_regions
    # For the figures have the same label, compute their bounding
    #  box
    for page in cap_regions:
        p_figures = fig_box[page]
        p_cap_regions = cap_regions[page]
        figures[page] = label_subfig(info, p_figures, p_cap_regions, table_box)

    return figures, cap_regions


def caption_regions(cap_box, fig_box, info):
    # sort captions by horizontal
    # print cap_box
    # whole_page = [1, 1, info['page_width'], info['page_height']]
    column_no = info["column_no"]
    columns = info["columns"]
    columns_point = [1] * column_no
    cap_regions = []
    if len(cap_box) == 1:
        cap_regions.append(
            [
                cap_box[0],
                [
                    1,
                    1,
                    info["page_width"] - 2 * info["row_height"],
                    info["page_height"] - 2 * info["row_height"],
                ],
            ]
        )
        # comment on 0318 for gxd
        """
        if column_no == 1:
            cap_regions.append([cap_box[0], [1, 1, info['page_width']-2, cap_box[0][1]]])
            cap_regions.append([cap_box[0], [1, cap_box[0][1]+2*info['row_height'], info['page_width']-2, info['page_height']-cap_box[0][1]-3*info['row_height']]])
        else:
            if cap_box[0][2] > info['row_width'] + 50 or (cap_box[0][0] < info['page_width'] / 2 and
                                                                (cap_box[0][0] + cap_box[0][2]) > info['page_width'] / 2):
                cap_regions.append([cap_box[0], [1, 1, info['page_width'] - 2, cap_box[0][1]]])
                cap_regions.append([cap_box[0], [1, cap_box[0][1] + 2 * info['row_height'], info['page_width'] - 2,
                                                 info['page_height'] - cap_box[0][1] - 3 * info['row_height']]])
            else:
                if cap_box[0][0]< columns[0] + 100 or cap_box[0][0] < columns[0] + info['row_width'] -100:
                    cap_regions.append([cap_box[0], [1, 1, columns[0] + info['row_width'], cap_box[0][1]]])
                    cap_regions.append([cap_box[0], [1, cap_box[0][1] + 2 * info['row_height'], columns[0] + info['row_width'],
                                                     info['page_height'] - cap_box[0][1] - 3 * info['row_height']]])
                else:
                    cap_regions.append([cap_box[0], [min(cap_box[0][0], columns[0] + info['row_width']+50), 1, columns[0] + info['row_width'], cap_box[0][1]]])
                    cap_regions.append([cap_box[0], [min(cap_box[0][0], columns[0] + info['row_width']+50), cap_box[0][1] + 2 * info['row_height'], columns[0] + info['row_width'],
                                      info['page_height'] - cap_box[0][1] - 3 * info['row_height']]])
        """
    elif len(cap_box) > 1:
        if column_no == 1:
            cap_sorted = sorted(cap_box, key=lambda x: x[1])
            for cap_item in cap_sorted:
                region = [
                    1,
                    columns_point[0],  # vertical sweep
                    info["page_width"] - 2,
                    cap_item[1] - columns_point[0],
                ]
                cap_regions.append([cap_item, region])
                columns_point[0] = cap_item[1] + cap_item[3]
            cap_regions.append(  # not sure about this one, cap_item may not be defined?
                [
                    cap_item,
                    [
                        1,
                        columns_point[0],
                        info["page_width"] - 2,
                        info["page_height"] - columns_point[0],
                    ],
                ]
            )
        else:
            cap_sorted = sorted(cap_box, key=lambda x: (x[1], x[0]))
            # caption parallel
            for cap_item in cap_sorted:
                no_cross_fig = 1
                if cap_item[2] > info["row_width"] + 50 or (  # width >
                    cap_item[0] < info["page_width"] / 2  # x0
                    and (cap_item[0] + cap_item[2]) > info["page_width"] / 2
                ):
                    no_cross_fig = 0
                    region = [
                        1,
                        max(columns_point),
                        info["page_width"] - 2,
                        cap_item[1] - max(columns_point),
                    ]
                    columns_point = [cap_item[1] + cap_item[3]] * column_no
                    cap_regions.append([cap_item, region])
                else:
                    cap_y = cap_item[1]
                    cap_x = cap_item[0]
                    # for fig_item in fig_box:# To check if there are fig cross this caption
                    #     if (fig_item[1] < cap_y) & (fig_item[1] + fig_item[3] > cap_y):
                    #         no_cross_fig = 1
                    # for other_cap in cap_sorted:# Caption parallel
                    #     if (abs(other_cap[1] - cap_y)<info['row_height']) & (abs(other_cap[0] - cap_x) > 5* info['row_height']):
                    #         no_cross_fig = 1
                    # no_cross_fig = 1
                    # if (cap_item[0] + cap_item[2] > columns[0]+ info['row_width']+100) and (cap_item[0] < columns[0]+ info['row_width'] - 50):
                    #     no_cross_fig = 0
                    #
                    # if no_cross_fig == 0:
                    #     region = [1, max(columns_point), info['page_width']-2, cap_y - max(columns_point)]
                    #     columns_point = [cap_item[1] + cap_item[3]] * column_no
                    #
                    if no_cross_fig == 1:
                        if cap_x < columns[0] + 100:
                            region = [
                                cap_x,
                                columns_point[0],  # is this not 1?
                                info["row_width"],
                                cap_y - columns_point[0],
                            ]
                            columns_point[0] = cap_y + cap_item[3]
                        elif cap_x < columns[0] + info["row_width"] - 100:
                            region = [
                                1,
                                columns_point[0],  # 1?
                                columns[0] + info["row_width"],
                                cap_y - columns_point[0],  # 1?
                            ]
                            columns_point[0] = cap_y + cap_item[3]
                        else:
                            region = [
                                min(cap_x, columns[0] + info["row_width"] + 50),
                                columns_point[1],
                                info["page_width"]
                                - min(cap_x, columns[0] + info["row_width"] + 50),
                                cap_y - columns_point[1],
                            ]
                            columns_point[1] = cap_y + cap_item[3]

                    cap_regions.append([cap_item, region])
            # Added to cover all area, for image below captions
            # ## this may noy be correct, the variable is defined in the loop for every instance
            if no_cross_fig == 0:
                region = [
                    1,
                    max(columns_point),
                    info["page_width"] - 2,
                    info["page_height"] - max(columns_point),
                ]
                cap_regions.append([cap_item, region])
            else:
                cap_regions.append(
                    [
                        cap_item,
                        [
                            0,
                            columns_point[0],
                            info["page_width"] / 2,
                            info["page_height"] - columns_point[0] - 1,
                        ],
                    ]
                )
                cap_regions.append(
                    [
                        cap_item,
                        [
                            info["page_width"] / 2,
                            columns_point[1],
                            info["page_width"] / 2,
                            info["page_height"] - columns_point[1] - 1,
                        ],
                    ]
                )
    return cap_regions


def label_subfig(info, figures, cap_regions, table_box):
    # region overlap
    # distance between all objects, thresh in 4 lines
    # objects under table box
    label = range(len(cap_regions))
    labeled_figures = {}
    fig_merged = []
    for i in range(len(cap_regions)):
        labeled_figures[str(i)] = []

    # Changed order, it may affect
    for figure in figures:
        for i in range(len(cap_regions)):
            overlap = overlap_ratio_based(figure, cap_regions[i][1])
            cover = overlap_ratio_based(
                cap_regions[i][0], figure
            )  # to check if the caption in in the figure
            if overlap > 0.2 and cover < 0.5:  # The overlap need to set carefully
                labeled_figures[str(i)].append(figure)

        # check distance, to remove far objects
        # if cap_regions[i][0][1] < info['down_bbox'][1]:
        #    cap_box = [cap_regions[i][0]]
        #    fig_objects = labeled_figures[str(i)]
        #    for_tr_graph = [0]*len(fig_objects)
        #    increase = -1
        #    while increase != 0:
        #        increase = 0
        #        for fig_no in range(len(fig_objects)):
        #            if for_tr_graph[fig_no]==0:
        #                for cap in cap_box:
        #                    dis = bbox_distance(fig_objects[fig_no], cap)
        #                    if dis < 6 * info['row_height']:
        #                        cap_box.append(fig_objects[fig_no])
        #                        for_tr_graph[fig_no] = 1
        #                        increase = increase +1
        #                        break
        #    del cap_box[0]
        #    labeled_figures[str(i)]= cap_box

    for i in range(len(cap_regions)):
        if len(labeled_figures[str(i)]) > 0:
            if len(labeled_figures[str(i)]) < 2:
                if (
                    labeled_figures[str(i)][0][2] > 20
                    and labeled_figures[str(i)][0][2] > 20
                ):  # Fig Thresh
                    fig_merged.append([labeled_figures[str(i)][0], cap_regions[i][0]])
            else:
                x0 = []
                x1 = []
                y0 = []
                y1 = []
                sum_figure_area = 0
                for each_figure in labeled_figures[str(i)]:
                    x0.append(each_figure[0])
                    y0.append(each_figure[1])
                    x1.append(each_figure[0] + each_figure[2])
                    y1.append(each_figure[1] + each_figure[3])
                    sum_figure_area = each_figure[2] * each_figure[3] + sum_figure_area
                new_fig = [min(x0), min(y0), max(x1) - min(x0), max(y1) - min(y0)]
                # if new_fig[2] > 2*info['row_height'] and new_fig[3] > 2*info['row_height']:
                #     fig_merged.append(new_fig)

                if new_fig[2] > 20 and new_fig[3] > 20:  # Fig Threshold
                    # Check overlap ratio
                    overlap_fig = float(sum_figure_area) / (new_fig[2] * new_fig[3])
                    if overlap_fig > 0.1:
                        fig_merged.append([new_fig, cap_regions[i][0]])
    # fileter small one

    return fig_merged


def evaluation(prefigures, cap_regions, html_file_path, info, html_boxes):

    fig_cap_pair = prefigures
    figures = {}
    captions = {}
    for page in fig_cap_pair:
        figures[page] = []
        captions[page] = []
        for each_figcap in fig_cap_pair[page]:
            new_fig = each_figcap[0]
            caption_flag = overlap_ratio_based(info["down_bbox"], each_figcap[1])
            if caption_flag > 0.8:
                figcap = each_figcap[0]
                if info["mess_up"] == False:
                    for each_page_html in html_boxes:
                        if each_page_html[0] == int(page[4:-4]):
                            for element in each_page_html[1]:
                                in_or_not = overlap_ratio_based(element[0], figcap)
                                if in_or_not > 0.05:
                                    new_fig = merge_two_boxes(new_fig, element[0])

                            for element in each_page_html[1]:
                                in_or_not = bbox_distance(element[0], each_figcap[0])
                                if in_or_not < info["row_height"] / 4:
                                    new_fig = merge_two_boxes(new_fig, element[0])
                    figures[page].append([new_fig, []])
                    captions[page].append([])
                else:
                    figures[page].append([each_figcap[0], []])
                    captions[page].append([])
            else:

                x0 = min(each_figcap[0][0], each_figcap[1][0])
                y0 = min(each_figcap[0][1], each_figcap[1][1])
                x1 = max(
                    each_figcap[0][0] + each_figcap[0][2],
                    each_figcap[1][0] + each_figcap[1][2],
                )
                y1 = max(each_figcap[0][1] + each_figcap[0][3], each_figcap[1][1])
                figcap = [x0, y0, x1 - x0, y1 - y0]
                cap_box = each_figcap[1]

                # print fig_cap_pair[page]
                if info["mess_up"] == False:
                    for each_page_html in html_boxes:
                        if each_page_html[0] == int(page[4:-4]):

                            for element in each_page_html[1]:
                                in_or_not = overlap_ratio_based(element[0], figcap)
                                if in_or_not > 0.05:
                                    new_fig = merge_two_boxes(new_fig, element[0])

                            for element in each_page_html[1]:
                                in_or_not = bbox_distance(element[0], each_figcap[0])
                                if in_or_not < info["row_height"] / 4:
                                    new_fig = merge_two_boxes(new_fig, element[0])
                            # for caption detection ~~~~~~~~~~~~~~~~~~~~~~~~
                            cap_detection_flag = 0
                            cap_text = []
                            cap_gap = 0.5 * info["row_height"]  # modify to 0.75 0.5
                            for element in each_page_html[1]:
                                if element[0] == cap_box or cap_detection_flag == 1:
                                    if element[0] == cap_box:
                                        cap_detection_flag = 1
                                        cap_text.append(element[1])
                                        first_line_box = cap_box
                                        moving_box = cap_box
                                    else:
                                        cap_gap = max(
                                            min(
                                                element[0][1]
                                                - first_line_box[1]
                                                - first_line_box[3],
                                                cap_gap,
                                            ),
                                            3,
                                        )
                                        current_gap = (
                                            element[0][1]
                                            - moving_box[1]
                                            - moving_box[3]
                                        )
                                        # print current_gap
                                        # print moving_box
                                        # print element[0]
                                        if current_gap >= max(
                                            0.5 * info["row_height"], cap_gap
                                        ):  # 0.75*info['row_height']
                                            cap_detection_flag = 0
                                        elif (
                                            element[0][2] - first_line_box[2]
                                            > 5 * info["row_height"]
                                            or element[0][3] - first_line_box[3] > 1
                                        ) and current_gap - cap_gap > 3:
                                            cap_detection_flag = 0

                                        if (
                                            abs(first_line_box[0] - element[0][0])
                                            > 10 * info["row_height"]
                                            and cap_detection_flag == 0
                                        ):
                                            cap_detection_flag = 1
                                        elif (
                                            abs(first_line_box[0] - element[0][0])
                                            > 10 * info["row_height"]
                                            and cap_detection_flag == 1
                                        ):
                                            cap_detection_flag = 1

                                        elif cap_detection_flag == 1:
                                            moving_box = element[0]
                                            cap_box = merge_two_boxes(
                                                cap_box, element[0]
                                            )
                                            cap_text.append(element[1])

                                    # To determine where to stop
                            # Finding separate captions
                            if (
                                len(cap_text) == 1
                                and (
                                    cap_text[0][-1].isdigit()
                                    or cap_text[-1][-1].isdigit()
                                )
                                and len(cap_text[0]) < 15
                            ):
                                cap_detection_flag = 0
                                cap_text_cp = cap_text
                                cap_box_cp = cap_box
                                cap_text = []
                                cap_gap = 0.5 * info["row_height"]  # modify to 0.75 0.5
                                next = 0
                                for element in each_page_html[1]:
                                    if element[0] == cap_box or cap_detection_flag == 1:
                                        if next == 0:
                                            if (
                                                element[0][1] > cap_box[1]
                                                and len(element[1]) > 30
                                            ):
                                                next = 1
                                                cap_detection_flag = 1
                                                cap_text.append(element[1])
                                                first_line_box = element[0]
                                                moving_box = element[0]
                                                cap_box = element[0]
                                            else:
                                                cap_detection_flag = 1

                                        else:
                                            cap_gap = max(
                                                min(
                                                    element[0][1]
                                                    - first_line_box[1]
                                                    - first_line_box[3],
                                                    cap_gap,
                                                ),
                                                3,
                                            )
                                            current_gap = (
                                                element[0][1]
                                                - moving_box[1]
                                                - moving_box[3]
                                            )
                                            # print current_gap
                                            # print moving_box
                                            # print element[0]
                                            if current_gap >= max(
                                                0.5 * info["row_height"], cap_gap
                                            ):  # 0.75*info['row_height']
                                                cap_detection_flag = 0
                                            elif (
                                                element[0][2] - first_line_box[2]
                                                > 5 * info["row_height"]
                                                or element[0][3] - first_line_box[3] > 1
                                            ) and current_gap - cap_gap > 3:
                                                cap_detection_flag = 0

                                            if (
                                                abs(first_line_box[0] - element[0][0])
                                                > 10 * info["row_height"]
                                                and cap_detection_flag == 0
                                            ):
                                                cap_detection_flag = 1
                                            elif (
                                                abs(first_line_box[0] - element[0][0])
                                                > 10 * info["row_height"]
                                                and cap_detection_flag == 1
                                            ):
                                                cap_detection_flag = 1

                                            elif cap_detection_flag == 1:
                                                moving_box = element[0]
                                                cap_box = merge_two_boxes(
                                                    cap_box, element[0]
                                                )
                                                cap_text.append(element[1])

                                distance_before = bbox_distance(new_fig, cap_box_cp)
                                distance_now = bbox_distance(new_fig, cap_box)
                                # if distance_now > 2*distance_before + 2*cap_box_cp[3]: No distance control is better
                                #     cap_box = cap_box_cp
                                #     cap_text = cap_text_cp

                            figures[page].append([new_fig, [cap_box, cap_text]])

                            captions[page].append([cap_box, cap_text])
                else:

                    for each_page_html in html_boxes:
                        if each_page_html[0] == int(page[4:-4]):
                            cap_detection_flag = 0
                            cap_text = []
                            cap_gap = info["row_height"]
                            for element in each_page_html[1]:
                                if element[0] == cap_box or cap_detection_flag == 1:
                                    if element[0] == cap_box:
                                        cap_detection_flag = 1
                                        cap_text.append(element[1])
                                        first_line_box = cap_box
                                        moving_box = cap_box
                                    else:
                                        cap_gap = max(
                                            min(
                                                element[0][1]
                                                - first_line_box[1]
                                                - first_line_box[3],
                                                cap_gap,
                                            ),
                                            3,
                                        )
                                        current_gap = (
                                            element[0][1]
                                            - moving_box[1]
                                            - moving_box[3]
                                        )
                                        # print current_gap
                                        # print moving_box
                                        # print element[0]
                                        if current_gap >= max(
                                            0.5 * info["row_height"], cap_gap
                                        ):  # 0.75*info['row_height']
                                            cap_detection_flag = 0
                                        elif (
                                            element[0][2] - first_line_box[2]
                                            > 5 * info["row_height"]
                                            or element[0][3] - first_line_box[3] > 1
                                        ) and current_gap - cap_gap > 3:
                                            cap_detection_flag = 0

                                        if (
                                            abs(first_line_box[0] - element[0][0])
                                            > 10 * info["row_height"]
                                            and cap_detection_flag == 0
                                        ):
                                            cap_detection_flag = 1
                                        elif (
                                            abs(first_line_box[0] - element[0][0])
                                            > 10 * info["row_height"]
                                            and cap_detection_flag == 1
                                        ):
                                            cap_detection_flag = 1

                                        elif cap_detection_flag == 1:
                                            moving_box = element[0]
                                            cap_box = merge_two_boxes(
                                                cap_box, element[0]
                                            )
                                            cap_text.append(element[1])
                                            if first_line_box[2] - element[0][
                                                2
                                            ] > 5 * info["row_height"] and element[
                                                1
                                            ].endswith(
                                                "."
                                            ):
                                                cap_detection_flag = 0
                            captions[page].append([cap_box, cap_text])
                            figures[page].append([each_figcap[0], [cap_box, cap_text]])

    #
    # for page in figures:
    #     if len(figures[page])>0:
    #         img = cv2.imread(html_file_path + '/' + page)
    #         img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    #         png_size = img.shape
    #         if png_size[0] > png_size[1]:
    #             png_ratio = float(png_size[0]) / info['page_height']
    #         else:
    #             png_ratio = float(png_size[0]) / info['page_width']
    #         bbox_no = 0
    #         while bbox_no < len(figures[page]):
    #             each_bbox = figures[page][bbox_no]
    #             each_figure = img[int(each_bbox[1]*png_ratio):int((each_bbox[3]+each_bbox[1])*png_ratio),
    #                           int(each_bbox[0] * png_ratio):int((each_bbox[2]+each_bbox[0]) * png_ratio)]
    #             each_figure = cv2.resize(each_figure, (200, 200))
    #             laplacian = cv2.Laplacian(each_figure, cv2.CV_64F)
    #             sobelx = cv2.Sobel(each_figure, cv2.CV_64F, 1, 0, ksize=5)
    #             sobely = cv2.Sobel(each_figure, cv2.CV_64F, 0, 1, ksize=5)
    #             img_complexity = entropy(sobelx) + entropy(sobely)
    #             print img_complexity
    #             if img_complexity > 0.5: ##### need to set carefully
    #                 bbox_no = bbox_no + 1
    #             else:
    #                 del figures[page][bbox_no]

    return figures, captions


def check_region(info, figures, captions):
    final_figures = figures
    final_captions = captions
    for page in figures:
        for each_figure in figures[page]:
            if len(each_figure[1]) > 0:
                caption_overlap_ratio = overlap_ratio_based(
                    each_figure[1][0], each_figure[0]
                )

                if (each_figure[1][0][0] + each_figure[1][0][2]) > info["right_bbox"][
                    0
                ]:
                    each_figure[1][0][2] = info["right_bbox"][0] - each_figure[1][0][0]
                # for two column documents
                if (
                    each_figure[0][2] > 1.5 * info["row_width"]
                    and each_figure[1][0][1] > each_figure[0][1] + each_figure[0][3]
                    and each_figure[1][0][0] + each_figure[1][0][2]
                    < each_figure[0][0] + each_figure[0][2] / 2
                    and each_figure[1][0][3] > 3 * info["row_height"]
                ):
                    each_figure[1][0][2] = (
                        2 * each_figure[1][0][2] + 2 * info["row_height"]
                    )

                if caption_overlap_ratio > 0.8:
                    # spliting caption box and the figure box
                    # top caption
                    if (
                        each_figure[1][0][1] >= each_figure[0][1]
                        and (each_figure[1][0][1] - each_figure[0][1])
                        < 2 * info["row_height"]
                        and each_figure[1][0][0]
                        < each_figure[0][0] + each_figure[0][2] / 2
                        and each_figure[1][0][0] + each_figure[1][0][2]
                        > each_figure[0][0] + each_figure[0][2] / 2
                        and each_figure[0][1]
                        + each_figure[0][3]
                        - each_figure[1][0][1]
                        - each_figure[1][0][3]
                        > 5 * info["row_height"]
                    ):
                        each_figure[0] = [
                            each_figure[0][0],
                            each_figure[1][0][1] + each_figure[1][0][3],
                            each_figure[0][2],
                            each_figure[0][1]
                            + each_figure[0][3]
                            - each_figure[1][0][1]
                            - each_figure[1][0][3],
                        ]
                    # down caption
                    elif (
                        each_figure[0][1] + each_figure[0][3]
                        >= each_figure[1][0][1] + each_figure[1][0][3]
                        and (
                            each_figure[0][1]
                            + each_figure[0][3]
                            - each_figure[1][0][1]
                            - each_figure[1][0][3]
                        )
                        < 2 * info["row_height"]
                        and each_figure[1][0][0]
                        < each_figure[0][0] + each_figure[0][2] / 2
                        and each_figure[1][0][0] + each_figure[1][0][2]
                        > each_figure[0][0] + each_figure[0][2] / 2
                        and each_figure[0][1] + each_figure[0][3] - each_figure[1][0][1]
                        > 5 * info["row_height"]
                    ):
                        each_figure[0] = [
                            each_figure[0][0],
                            each_figure[0][1],
                            each_figure[0][2],
                            each_figure[0][1]
                            + each_figure[0][3]
                            - each_figure[1][0][1],
                        ]
                    # right caption
                    elif (
                        each_figure[1][0][0] + each_figure[1][0][2]
                        <= each_figure[0][0] + each_figure[0][2]
                        and (
                            each_figure[0][0]
                            + each_figure[0][2]
                            - each_figure[1][0][0]
                            - each_figure[1][0][2]
                        )
                        < 2 * info["row_height"]
                        and each_figure[1][0][0]
                        > each_figure[0][0] + each_figure[0][2] / 2
                        and each_figure[1][0][0] - each_figure[0][0]
                        > 5 * info["row_height"]
                    ):
                        each_figure[0] = [
                            each_figure[0][0],
                            each_figure[0][1],
                            each_figure[1][0][0] - each_figure[0][0],
                            each_figure[0][3],
                        ]
                    # left caption
                    elif (
                        each_figure[1][0][0] >= each_figure[0][0]
                        and (each_figure[1][0][0] - each_figure[0][0])
                        < 2 * info["row_height"]
                        and each_figure[1][0][0] + each_figure[1][0][2]
                        < each_figure[0][0] + each_figure[0][2] / 2
                        and each_figure[0][0] + each_figure[0][2] - each_figure[1][0][0]
                        > 5 * info["row_height"]
                    ):
                        each_figure[0] = [
                            each_figure[1][0][0],
                            each_figure[0][1],
                            each_figure[0][0]
                            + each_figure[0][2]
                            - each_figure[1][0][0],
                            each_figure[0][3],
                        ]

    return figures, captions


def merge_boxes(figures, cap_regions, table_box, info):
    # region overlap
    # distance between all objects, thresh in 4 lines
    # objects under table box
    label = [-1] * len(figures)
    fig_merged = []

    for j in range(len(figures)):
        figure = figures[j]
        for i in range(len(cap_regions)):
            overlap = overlap_ratio_based(figure, cap_regions[i][1])
            if overlap > 0.5:
                label[j] = i
    for i in range(len(cap_regions)):
        index = [no for no in range(len(label)) if label[no] == i]
        check_box = figures[index]
        dis_matrix = np.zeros(shape=(len(check_box), len(check_box)))
        for j in range(len(check_box)):
            for k in range(len(check_box)):
                if j == k:
                    dis_matrix[j][k] = 10 * info["row_height"]
                else:
                    dis_matrix[j][k] = manhattan_dist(check_box[j], check_box[k])
        dis_matrix = min(dis_matrix)

    #
    #
    # for i in range(len(cap_regions)):
    #     if len(labeled_figures[str(i)]) > 0:
    #         if len(labeled_figures[str(i)]) < 2:
    #             fig_merged.append(labeled_figures[str(i)][0])
    #         else:
    #             x0 = []
    #             x1 = []
    #             y0 = []
    #             y1 = []
    #             for each_figure in labeled_figures[str(i)]:
    #                 x0.append(each_figure[0])
    #                 y0.append(each_figure[1])
    #                 x1.append(each_figure[0] + each_figure[2])
    #                 y1.append(each_figure[1] + each_figure[3])
    #
    #             new_fig = [min(x0), min(y0), max(x1)-min(x0),
    #                                       max(y1)-min(y0)]
    #             fig_merged.append(new_fig)
    #
    # return fig_merged


def overlap_ratio_based(box1, box2):
    # overlap ratio based on box1
    box1_x0 = box1[0]
    box1_y0 = box1[1]
    box1_x1 = box1[0] + box1[2]
    box1_y1 = box1[1] + box1[3]

    box2_x0 = box2[0]
    box2_y0 = box2[1]
    box2_x1 = box2[0] + box2[2]
    box2_y1 = box2[1] + box2[3]

    SI = max(0, min(box1_x1, box2_x1) - max(box1_x0, box2_x0)) * max(
        0, min(box1_y1, box2_y1) - max(box1_y0, box2_y0)
    )
    box1_area = box1[2] * box1[3]
    box2_area = box2[2] * box2[3]
    SU = box1_area + box2_area - SI
    if box1_area == 0:
        overlap_ratio = 0
    else:
        overlap_ratio = float(SI) / box1_area
    return overlap_ratio


def bbox_distance(bbox1, bbox2):
    x1 = bbox1[0]
    y1 = bbox1[1]
    x1b = bbox1[0] + bbox1[2]
    y1b = bbox1[1] + bbox1[3]
    x2 = bbox2[0]
    y2 = bbox2[1]
    x2b = bbox2[0] + bbox2[2]
    y2b = bbox2[1] + bbox2[3]
    left = x2b < x1
    right = x1b < x2
    bottom = y2b < y1
    top = y1b < y2
    if top and left:
        return manhattan_dist((x1, y1b), (x2b, y2))
    elif left and bottom:
        return manhattan_dist((x1, y1), (x2b, y2b))
    elif bottom and right:
        return manhattan_dist((x1b, y1), (x2, y2b))
    elif right and top:
        return manhattan_dist((x1b, y1b), (x2, y2))
    elif left:
        return x1 - x2b
    elif right:
        return x2 - x1b
    elif bottom:
        return y1 - y2b
    elif top:
        return y2 - y1b
    else:  # rectangles intersect
        return 0


def manhattan_dist(a, b):
    return sum(abs(a - b) for a, b in zip(a, b))


def merge_two_boxes(bbox1, bbox2):
    x0 = min(bbox1[0], bbox2[0])
    y0 = min(bbox1[1], bbox2[1])
    x1 = max(bbox1[0] + bbox1[2], bbox2[0] + bbox2[2])
    y1 = max(bbox1[1] + bbox1[3], bbox2[1] + bbox2[3])
    return [x0, y0, x1 - x0, y1 - y0]
