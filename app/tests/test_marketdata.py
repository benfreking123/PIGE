from datetime import date

import pandas as pd

from app.services.marketdata.store import df_to_ohlcv_rows
from app.services.marketdata.symbols import add_months, generate_he_symbols, generate_he_symbols_future


def test_generate_he_symbols_range():
    symbols = generate_he_symbols(date(2023, 1, 1), date(2027, 8, 12))
    assert "HEG23" in symbols
    assert "HEZ26" in symbols
    assert "HEQ27" in symbols
    assert len(symbols) == 40


def test_add_months():
    base = date(2026, 2, 12)
    result = add_months(base, 18)
    assert result.year == 2027
    assert result.month == 8


def test_generate_he_symbols_future():
    symbols = generate_he_symbols_future(date(2026, 2, 12), date(2027, 6, 1))
    assert "HEG26" in symbols
    assert "HEZ25" not in symbols


def test_df_to_ohlcv_rows():
    df = pd.DataFrame(
        [
            {
                "ts_event": "2026-02-10T00:00:00Z",
                "symbol": "HEG26",
                "open": 1.0,
                "high": 2.0,
                "low": 0.5,
                "close": 1.5,
                "volume": 100,
                "open_interest": 200,
            }
        ]
    )
    rows = df_to_ohlcv_rows(df)
    assert rows[0]["symbol"] == "HEG26"
    assert rows[0]["trade_date"].isoformat() == "2026-02-10"
    assert rows[0]["open_interest"] == 200.0
