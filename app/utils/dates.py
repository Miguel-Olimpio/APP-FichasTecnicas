"""Datas e timestamps."""

from datetime import datetime


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def timestamp_file() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")
