import math


def sign_convert_byte(val: int) -> int:
    if val & 0b10000000:
        return -(val & 0b01111111)
    return val


def page_of(val: int) -> int:
    return math.floor(val / 0xFF)
