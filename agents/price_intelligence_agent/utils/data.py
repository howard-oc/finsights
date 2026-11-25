"""Read the CSV files the agent works from: prices, instruments and VIX.

Two datasets, chosen with PRICE_INTEL_DATASET (read on every call, so it can be set in .env or changed at runtime):
  synthetic (default)  data/            generated NVDA/QQQ week, used by the evals
  real                 data/real/       real public prices from Yahoo Finance (scripts/fetch_real_prices.py)

Every call reads the files again, so edits to the CSVs show up straight away.
"""

import csv
import os
from pathlib import Path

DATA_ROOT = Path(__file__).resolve().parent.parent / "data"

DATASETS = {
    "synthetic": {"dir": DATA_ROOT, "source": "synthetic"},
    "real": {"dir": DATA_ROOT / "real", "source": "Yahoo Finance (public)"},
}
DATA_STATUS = "historical"  # live, delayed or historical


def dataset() -> str:
    """The dataset in use: PRICE_INTEL_DATASET, defaulting to synthetic."""
    name = (os.environ.get("PRICE_INTEL_DATASET") or "synthetic").strip().lower()
    if name not in DATASETS:
        raise ValueError(f"PRICE_INTEL_DATASET={name!r}; use one of {', '.join(DATASETS)}")
    return name


def data_source() -> str:
    return DATASETS[dataset()]["source"]


def data_dir() -> Path:
    return DATASETS[dataset()]["dir"]


def table(name: str) -> list[dict]:
    """Every row in a CSV, for example `table("instruments")`.

    PRICE_INTEL_PRICES_CSV overrides just the prices file (the evals use it for data/eval_prices.csv).
    """
    override = os.environ.get("PRICE_INTEL_PRICES_CSV")
    path = Path(override) if name == "prices" and override else data_dir() / f"{name}.csv"
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
