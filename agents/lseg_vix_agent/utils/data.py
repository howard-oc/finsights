"""Read price bars from data/prices.csv. One row per bar: ticker, timestamp, open, high, low, close, volume.

To use other data (more tickers, real public prices), replace or append to the CSV with the same columns.
"""

import csv
import os
from pathlib import Path

# LSEG_VIX_PRICES_CSV points the agent at another file, e.g. the eval scenarios in data/eval_prices.csv.
PRICES_CSV = Path(
    os.environ.get("LSEG_VIX_PRICES_CSV") or Path(__file__).resolve().parent.parent / "data" / "prices.csv"
)


def load_bars(ticker: str, start: str | None = None, end: str | None = None) -> list[dict]:
    """A ticker's bars, oldest first, from `start` up to (not including) `end` (ISO dates or timestamps)."""
    with PRICES_CSV.open() as f:
        bars = [
            {**row, **{k: float(row[k]) for k in ("open", "high", "low", "close")}, "volume": int(row["volume"])}
            for row in csv.DictReader(f)
            if row["ticker"].upper() == ticker.upper()
            and (start is None or row["timestamp"] >= start)
            and (end is None or row["timestamp"] < end)
        ]
    return sorted(bars, key=lambda b: b["timestamp"])


def available_tickers() -> list[str]:
    with PRICES_CSV.open() as f:
        return sorted({row["ticker"] for row in csv.DictReader(f)})
