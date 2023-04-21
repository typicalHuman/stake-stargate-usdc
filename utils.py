import time


def monthsToEpoch(months: int):
    return int(time.time()) + (months * 30 * 24 * 60 * 60)


def int_to_decimal(qty, decimal):
    return int(qty * int("".join(["1"] + ["0"] * decimal)))


def decimal_to_int(price, decimal):
    return price / int("".join((["1"] + ["0"] * decimal)))


def float_str(amount, decimals=18):
    temp_str = "%0.18f"
    temp_str = temp_str.replace("18", str(decimals))
    text_float = temp_str % amount
    return text_float
