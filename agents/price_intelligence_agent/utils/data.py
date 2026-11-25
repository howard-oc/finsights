"""Read the CSV files in `data/`: prices, instruments and VIX. All of it is synthetic.

Every call reads the file again, so edits to the CSVs show up straight away.
"""

import csv
import os
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# The evals point this at data/eval_prices.csv.
PRICES_FILE = Path(os.environ.get("PRICE_INTEL_PRICES_CSV") or DATA_DIR / "prices.csv")


def table(name: str) -> list[dict]:
    """Every row in a CSV, for example `table("instruments")`."""
    path = PRICES_FILE if name == "prices" else DATA_DIR / f"{name}.csv"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as file:
        return list(csv.DictReader(file))


def bars(ticker: str, start: str | None = None, end: str | None = None) -> list[dict]:
    """A ticker's price bars, oldest first, from `start` up to (not including) `end`."""
    rows = [
        {**row, "open": float(row["open"]), "high": float(row["high"]), "low": float(row["low"]),
         "close": float(row["close"]), "volume": int(row["volume"])}
        for row in table("prices")
        if row["ticker"] == ticker
        and (start is None or row["timestamp"] >= start)
        and (end is None or row["timestamp"] < end)
    ]
    return sorted(rows, key=lambda row: row["timestamp"])


def find_instrument(name_or_ticker: str) -> dict | None:
    """The instrument with this ticker, or whose company name contains the text, for example "nvidia"."""
    text = name_or_ticker.strip().lower()
    instruments = table("instruments")
    for row in instruments:
        if row["ticker"].lower() == text:
            return row
    for row in instruments:
        if text in row["company_name"].lower():
            return row
    return None


DATA_SOURCE = "synthetic"
DATA_STATUS = "historical"  # live, delayed or historical
