import shutil
import os
from PIL import Image
import tempfile
from utils import natural_sort


def render_pdf(filename, customize_dpi):
    """
        This function renders the document unsing imagemagick and returns a list of images, one for each page.
        The images are PIL Image type.
    """
    output_dpi = str(customize_dpi)
    sep = os.path.sep
    outputDir = tempfile.mkdtemp()

    rasterScale = 3  # increase this if you want higher resolution images
    rasterDensity = str(rasterScale * 100)

    # If you have your path setup correctly in 'nix this should work,
    # right now its set up to have explicit path in windows
    if os.name == 'nt':
        imagemagickPath = '/usr/pengyuan/others/ImageMagick-7.0.3-5-portable-Q16-x86/convert.exe'
        os.system(
            imagemagickPath + ' -density ' + rasterDensity + ' -resample ' + output_dpi + ' -set colorspace RGB ' +
            filename + ' ' + os.path.join(outputDir, 'image.png'))
    else:
        os.system(
            # 'convert -density ' + rasterDensity + ' -resample ' + output_dpi + ' -set colorspace RGB ' + filename + ' ' + outputDir + 'image.png')
            # 'convert -density ' + output_dpi + ' -resample ' + output_dpi + ' -set colorspace RGB ' + filename + ' ' + outputDir + 'image.png')
            'gs -q -sDEVICE=png16m -o ' + os.path.join(outputDir, 'file-%02d.png') + ' -r' + output_dpi + ' ' + filename)

    files = [f for f in os.listdir(outputDir) if os.path.isfile(
        os.path.join(outputDir, f)) and not f.startswith('.')]
    files = natural_sort(files)
    images = []
    for f in files:
        if f.endswith('.png'):
            pageIm = Image.open(os.path.join(outputDir, f)).convert('RGB')
            pageIm.load()  # load into memory (also closes the file associated)
            images.append(pageIm)
    shutil.rmtree(outputDir)
    return images
