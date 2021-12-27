from re import split
from os import system
from os.path import join
from typing import List


def convert(text):
    return int(text) if text.isdigit() else text.lower()


def alphanum_key(key):
    return [convert(c) for c in split('([0-9]+)', key)]


def natural_sort(arr: List[str]) -> List[str]:
    """ Sorts list in ascending order considering numpad for numbers """
    return sorted(arr, key=alphanum_key)


def pdf2images(file_path: str, output_path: str, dpi=300):
    """ convert PDF to images and save them on output location """
    gs_cmd = f"gs -q -sDEVICE=png16m \
        -o {join(output_path, 'file-%02d.png')} -r{dpi} {file_path}"
    # TODO: how to capture an error from the ghostscript command?
    system(gs_cmd)
