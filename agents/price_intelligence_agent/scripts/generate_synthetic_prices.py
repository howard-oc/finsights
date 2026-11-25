"""Generate the synthetic market data the price intelligence agent reads.

  data/prices.csv       30-minute bars: NVDA (the subject) and QQQ (its benchmark, Nasdaq-100 tracker)
  data/vix.csv          daily VIX closes for the same week (market-wide implied volatility)
  data/instruments.csv  reference data: company name, currency, exchange, timezone, benchmark

All numbers are SYNTHETIC (seeded random walks), not real market data. The NVDA week is shaped to be interesting:
calm Monday and Tuesday, earnings after Wednesday's close, a gap up and an intraday whipsaw on Thursday, and a
partial retrace on Friday. QQQ moves with NVDA at a fraction of the size; VIX drifts up into earnings.

Run from agents/:  uv run python -m price_intelligence_agent.scripts.generate_synthetic_prices
"""

import csv
import math
import random
from datetime import datetime, timedelta
from pathlib import Path

SEED = 25
TICKER = "NVDA"
START_PRICE = 186.40
DAYS = ["2026-11-16", "2026-11-17", "2026-11-18", "2026-11-19", "2026-11-20"]
BARS_PER_DAY = 13  # 09:30 to 16:00 in 30-minute bars

# Per day: (overnight gap, 30-minute volatility, intraday drift per bar, base volume per bar)
DAY_SHAPE = {
    "2026-11-16": (0.000, 0.0035, 0.0002, 2_400_000),
    "2026-11-17": (-0.004, 0.0040, -0.0003, 2_600_000),
    "2026-11-18": (0.002, 0.0050, 0.0004, 3_400_000),  # pre-earnings positioning
    "2026-11-19": (0.061, 0.0110, -0.0012, 7_800_000),  # earnings gap up, then whipsaw
    "2026-11-20": (-0.012, 0.0075, -0.0006, 5_100_000),  # partial retrace
}

DATA = Path(__file__).resolve().parent.parent / "data"
OUT = DATA / "prices.csv"

BENCHMARK = "QQQ"
BENCHMARK_START = 512.80
BENCHMARK_GAPS = {"2026-11-17": -0.002, "2026-11-18": 0.001, "2026-11-19": 0.012, "2026-11-20": -0.004}
VIX = {"2026-11-16": 17.2, "2026-11-17": 17.8, "2026-11-18": 18.4, "2026-11-19": 19.6, "2026-11-20": 18.9}
INSTRUMENTS = [
    {"ticker": "NVDA", "company_name": "NVIDIA Corporation", "currency": "USD", "exchange": "NASDAQ",
     "timezone": "America/New_York", "benchmark": "QQQ"},
    {"ticker": "QQQ", "company_name": "Invesco QQQ Trust (Nasdaq-100)", "currency": "USD", "exchange": "NASDAQ",
     "timezone": "America/New_York", "benchmark": ""},
]


def benchmark_rows(nvda_rows: list[dict]) -> list[dict]:
    """QQQ bars that move with NVDA at about a third of the size, plus their own noise."""
    rng, rows, price = random.Random(SEED + 1), [], BENCHMARK_START
    prev_day = None
    for nv in nvda_rows:
        day = nv["timestamp"][:10]
        if day != prev_day:
            price *= 1 + BENCHMARK_GAPS.get(day, 0.0)
            prev_day = day
        nv_ret = math.log(nv["close"] / nv["open"])
        shock = 0.35 * nv_ret + rng.gauss(0, 0.0012)
        open_, close = price, price * math.exp(shock)
        high = max(open_, close) * (1 + abs(rng.gauss(0, 0.0006)))
        low = min(open_, close) * (1 - abs(rng.gauss(0, 0.0006)))
        rows.append({"ticker": BENCHMARK, "timestamp": nv["timestamp"], "open": round(open_, 2), "high": round(high, 2),
                     "low": round(low, 2), "close": round(close, 2), "volume": int(nv["volume"] * 0.9 * rng.uniform(0.8, 1.2))})
        price = close
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    rng = random.Random(SEED)
    rows, price = [], START_PRICE
    for day in DAYS:
        gap, vol, drift, base_volume = DAY_SHAPE[day]
        price *= 1 + gap
        t = datetime.fromisoformat(f"{day}T09:30")
        for i in range(BARS_PER_DAY):
            open_ = price
            shock = rng.gauss(drift, vol)
            if day == "2026-11-19" and i in (2, 3):  # sharp intraday reversal after the gap
                shock = -0.028 if i == 2 else 0.019
            close = open_ * math.exp(shock)
            high = max(open_, close) * (1 + abs(rng.gauss(0, vol / 2)))
            low = min(open_, close) * (1 - abs(rng.gauss(0, vol / 2)))
            # U-shaped volume through the day, scaled up on big moves
            u_shape = 1.6 if i in (0, BARS_PER_DAY - 1) else 0.8 + 0.05 * abs(i - 6)
            volume = int(base_volume * u_shape * (1 + 20 * abs(shock)) * rng.uniform(0.85, 1.15))
            rows.append(
                {
                    "ticker": TICKER,
                    "timestamp": t.strftime("%Y-%m-%dT%H:%M"),
                    "open": round(open_, 2),
                    "high": round(high, 2),
                    "low": round(low, 2),
                    "close": round(close, 2),
                    "volume": volume,
                }
            )
            price = close
            t += timedelta(minutes=30)

    DATA.mkdir(parents=True, exist_ok=True)
    all_rows = rows + benchmark_rows(rows)
    write_csv(OUT, all_rows)
    write_csv(DATA / "vix.csv", [{"date": d, "close": v} for d, v in VIX.items()])
    write_csv(DATA / "instruments.csv", INSTRUMENTS)
    print(f"Wrote {len(all_rows)} synthetic bars to {OUT}, plus vix.csv and instruments.csv")


if __name__ == "__main__":
    main()
