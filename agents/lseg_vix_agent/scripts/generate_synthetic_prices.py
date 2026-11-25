"""Generate a synthetic week of 30-minute NVDA price bars into data/prices.csv.

The numbers are SYNTHETIC (seeded random walk), not real market data. The week is shaped to be interesting:
calm Monday and Tuesday, earnings after Wednesday's close, a gap up and an intraday whipsaw on Thursday, and a
partial retrace on Friday.

Run from the lseg_vix_agent folder:  uv run python -m scripts.generate_synthetic_prices
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

OUT = Path(__file__).resolve().parent.parent / "data" / "prices.csv"


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

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} synthetic bars to {OUT}")


if __name__ == "__main__":
    main()
