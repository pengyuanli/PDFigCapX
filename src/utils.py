from re import split


def convert(text):
    return int(text) if text.isdigit() else text.lower()


def alphanum_key(key):
    return [convert(c) for c in split('([0-9]+)', key)]


def natural_sort(arr):
    """ Sorts list in ascending order. Starting numeric strings are 
    "   transform to match digits.
    """
    return sorted(arr, key=alphanum_key)
