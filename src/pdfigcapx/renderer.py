from shutil import rmtree
from os import listdir, system
from os.path import join, isfile
import tempfile
from PIL import Image
from utils import natural_sort, pdf2images


def render_pdf(filename):
    """ Transforms PDF to images and return them as an array. Intermediate
        images are deleted from OS.
    """
    # save images to temp directory
    temp_output_dir = tempfile.mkdtemp()
    pdf2images(filename, temp_output_dir)

    # load images to memory
    img_paths = [join(temp_output_dir, filename)
                 for filename in listdir(temp_output_dir)
                 if isfile(join(temp_output_dir, filename)) and
                 not filename.startswith('.') and
                 filename.endswith('.png')]
    img_paths = natural_sort(img_paths)

    images = []
    for img_path in img_paths:
        page_image = Image.open(img_path).convert('RGB')
        # load into memory and close associated file
        page_image.load()
        images.append(page_image)

    # clean directory
    rmtree(temp_output_dir)

    return images
