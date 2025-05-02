"""
functions for tools.json. must only contain functions that are named after\
a key in tools.json. parameters must be the same name as in tools.json data
"""

# pylint: disable = C0116, C0115, C0114, C0411

import random
import sys
import inspect


def dice_roll(n_min: str | None, n_max: str | None) -> int | str:
    if not n_min or not n_max:
        return "Incorrect call, values not provided. Retry"

    if not isinstance(n_min, int) or not isinstance(n_max, int):
        if (
            not n_min.isascii()
            or not n_max.isascii()
            or not n_min.isdigit()
            or not n_max.isdigit()
        ):
            return "Incorrect call, values were not numbers. Retry"

    a, b = int(n_min), int(n_max)

    if a > b:
        return "Incorrect call, min cannot be greater than max. Retry"

    return random.randint(a, b)


functions = dict(inspect.getmembers(sys.modules[__name__], inspect.isfunction))
