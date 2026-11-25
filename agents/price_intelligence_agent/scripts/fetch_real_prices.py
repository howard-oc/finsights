"""Download real public market data into data/real/, in the same format as the synthetic data.

  data/real/prices.csv       30-minute bars for NVDA and its benchmark QQQ (exchange-local New York time)
  data/real/vix.csv          daily VIX closes
  data/real/instruments.csv  reference data

Source: Yahoo Finance via the yfinance package (public data; Yahoo's terms are for personal use, fine for a
hackathon demo, not for production). Yahoo only keeps 30-minute bars for about the last 60 days. Today's session is
left out because it isn't complete.

Run from agents/ (yfinance is a dev dependency):
    uv run python -m price_intelligence_agent.scripts.fetch_real_prices
Then point the agent at it with PRICE_INTEL_DATASET=real (in .env or the environment).
"""

import csv
from datetime import date, timedelta
from pathlib import Path

import yfinance as yf

OUT = Path(__file__).resolve().parent.parent / "data" / "real"
TICKERS = ["NVDA", "QQQ"]
DAYS_BACK = 55  # inside Yahoo's ~60-day limit for 30-minute bars
INSTRUMENTS = [
    {"ticker": "NVDA", "company_name": "NVIDIA Corporation", "currency": "USD", "exchange": "NASDAQ",
     "timezone": "America/New_York", "benchmark": "QQQ"},
    {"ticker": "QQQ", "company_name": "Invesco QQQ Trust (Nasdaq-100)", "currency": "USD", "exchange": "NASDAQ",
     "timezone": "America/New_York", "benchmark": ""},
]


def write_csv(path: Path, rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    end = date.today()  # exclusive: today's session is still open
    start = end - timedelta(days=DAYS_BACK)
    OUT.mkdir(parents=True, exist_ok=True)

    bars = []
    for ticker in TICKERS:
        history = yf.Ticker(ticker).history(start=start, end=end, interval="30m", auto_adjust=False)
        for ts, row in history.iterrows():
            bars.append({
                "ticker": ticker,
                "timestamp": ts.tz_convert("America/New_York").strftime("%Y-%m-%dT%H:%M"),
                "open": round(float(row["Open"]), 4),
                "high": round(float(row["High"]), 4),
                "low": round(float(row["Low"]), 4),
                "close": round(float(row["Close"]), 4),
                "volume": int(row["Volume"]),
            })
        print(f"{ticker}: {sum(b['ticker'] == ticker for b in bars)} bars")

    vix = yf.Ticker("^VIX").history(start=start, end=end, interval="1d", auto_adjust=False)
    vix_rows = [{"date": ts.strftime("%Y-%m-%d"), "close": round(float(row["Close"]), 2)} for ts, row in vix.iterrows()]

    write_csv(OUT / "prices.csv", bars)
    write_csv(OUT / "vix.csv", vix_rows)
    write_csv(OUT / "instruments.csv", INSTRUMENTS)
    print(f"Wrote {len(bars)} bars and {len(vix_rows)} VIX days ({start} to {end - timedelta(days=1)}) to {OUT}")


if __name__ == "__main__":
    main()
