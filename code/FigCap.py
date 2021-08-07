"""
main code page
structure (xpdf_process):
1. Read pdfs from input folder
2. Figure and caption pair detection
    2.1. graphical content detection
    2.2 page segmentation
    2.3 figure detetion
    2.4 caption association

3. Mess up pdf processing


Writen by Pengyuan Li

Start from 19/10/2017
1.0 version 28/02/2018

"""

import os
import json
from pprint import pprint
import renderer
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from xpdf_process import figures_captions_list
import subprocess
import os
import time

if __name__ == "__main__":

    input_path = '/eecis/shatkay/homes/pengyuan/Documents/RESEARCH/PDFigCapX/code/sample_data_for_Juan'
    output_path = '/eecis/shatkay/homes/pengyuan/Documents/RESEARCH/PDFigCapX/code/sample_data_for_Juan'
    xpdf_path = output_path +'/xpdf/'  
    log_file = output_path + '/log.text'
    f_log = open(log_file, 'w') 
    if not os.path.isdir(xpdf_path):
        os.mkdir(xpdf_path)
# Read each files in the input path
    for pdf in os.listdir(input_path):
        if pdf.endswith('.pdf') and (not pdf.startswith('._')):
            data = {}
            print input_path+pdf
            images = renderer.render_pdf(input_path + '/' + pdf)
            data[pdf] = {}
            data[pdf]['figures'] = []
            data[pdf]['pages_annotated'] = []
            pdf_flag = 0
            try:
                if not os.path.isdir(xpdf_path+pdf[:-4]):
                    std_out = subprocess.check_output(["/usa/pengyuan/Documents/RESEARCH/PDFigCapX/xpdf-tools-linux-4.00/bin64/pdftohtml", input_path+'/'+pdf, xpdf_path+pdf[:-4]+'/'])
            except:
                print "\nWrong "+pdf+"\n"
                f_log.write(pdf+'\n')
                pdf_flag = 1

            if pdf_flag == 0:
                flag = 0
                wrong_count = 0
                while flag==0 and wrong_count<5:
                    try:
                        figures, info = figures_captions_list(input_path, pdf, xpdf_path)
                        flag = 1

                    except:
                        wrong_count = wrong_count +1
                        time.sleep(5)
                        print pdf
                        info['fig_no_est']=0
                        figures = []
                        print "------\nChrome Error\n----------\n"
        
                data[pdf]['fig_no'] = info['fig_no_est']

                output_file_path = output_path +'/' + pdf[:-4]
                if not os.path.isdir(output_file_path):
                    os.mkdir(output_file_path)      

                for figure in figures:
                    page_no = int(figure[:-4][4:])
                    page_fig= images[page_no -1]
                    rendered_size = page_fig.size

                    bboxes = figures[figure]
                    order_no = 0
                    for bbox in bboxes:
                        order_no = order_no + 1
                        png_ratio = float(rendered_size[1])/info['page_height']
                        print(png_ratio)

                        if len(bbox[1])>0:
                            data[pdf]['figures'].append({'page': page_no,
                                          'region_bb': bbox[0],
                                         'figure_type': 'Figure',
                                        'page_width': info['page_width'],
                                        'page_height': info['page_height'],
                                        'caption_bb': bbox[1][0],
                                        'caption_text': bbox[1][1]
                                         })
                            with open(output_file_path+'/'+str(page_no)+'_'+str(order_no)+'.txt', 'w') as capoutput:
                                capoutput.write(str(bbox[1][1]))
                                capoutput.close
                        else:
                            data[pdf]['figures'].append({'page': page_no,
                                                     'region_bb': bbox[0],
                                                     'figure_type': 'Figure',
                                                     'page_width': info['page_width'],
                                                     'page_height': info['page_height'],
                                                     'caption_bb': [],
                                                     'caption_text': []
                                                     })
                        fig_extracted = page_fig.crop([int(bbox[0][0]*png_ratio), int(bbox[0][1]*png_ratio), 
                                        int((bbox[0][0]+bbox[0][2])*png_ratio), int((bbox[0][1]+bbox[0][3])*png_ratio)])
                        fig_extracted.save(output_file_path+'/'+str(page_no)+'_'+str(order_no)+'.jpg')

                pprint(data)
                json_file = output_file_path+'/'+ pdf[:-4]+'.json'
                with open(json_file, 'w') as outfile:
                    json.dump(data, outfile)

