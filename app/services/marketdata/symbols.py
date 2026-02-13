from __future__ import annotations

from datetime import date
from typing import List


HE_MONTH_CODES = ["G", "J", "K", "M", "N", "Q", "V", "Z"]
HE_MONTH_MAP = {
    "G": 2,
    "J": 4,
    "K": 5,
    "M": 6,
    "N": 7,
    "Q": 8,
    "V": 10,
    "Z": 12,
}


def generate_he_symbols(start_date: date, end_date: date) -> List[str]:
    start_year = start_date.year
    end_year = end_date.year
    symbols: List[str] = []
    for year in range(start_year, end_year + 1):
        suffix = str(year)[-2:]
        for month_code in HE_MONTH_CODES:
            symbols.append(f"HE{month_code}{suffix}")
    return symbols


def generate_he_symbols_future(start_date: date, end_date: date) -> List[str]:
    symbols = generate_he_symbols(start_date, end_date)
    cutoff = date(start_date.year, start_date.month, 1)
    return [symbol for symbol in symbols if _symbol_month_start(symbol) >= cutoff]


def add_months(input_date: date, months: int) -> date:
    year = input_date.year + (input_date.month - 1 + months) // 12
    month = (input_date.month - 1 + months) % 12 + 1
    day = min(input_date.day, _days_in_month(year, month))
    return date(year, month, day)


def _days_in_month(year: int, month: int) -> int:
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    return (next_month - date(year, month, 1)).days


def _symbol_month_start(symbol: str) -> date:
    month_code = symbol[2]
    year_suffix = symbol[3:5]
    month = HE_MONTH_MAP[month_code]
    year = 2000 + int(year_suffix)
    return date(year, month, 1)


def filter_future_symbols(symbols: List[str], cutoff: date) -> List[str]:
    cutoff_month = date(cutoff.year, cutoff.month, 1)
    filtered: List[str] = []
    for symbol in symbols:
        try:
            if _symbol_month_start(symbol) >= cutoff_month:
                filtered.append(symbol)
        except Exception:
            continue
    return filtered
