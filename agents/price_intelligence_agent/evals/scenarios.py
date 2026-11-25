"""Synthetic eval scenarios: price weeks with planted patterns and the answers we expect the agent to give.

Writes data/eval_prices.csv (all scenarios plus the NVDA week) and returns the labelled examples. Expected regime is
computed from the deterministic metrics with the policy we WANT (see reference_regime), so labels are reproducible
rather than hand-guessed. Expected flags and trend come from what each scenario plants. Each scenario's seed is
chosen so its data clearly matches its labels: volatility well away from regime boundaries, and a range-expansion
ratio that agrees with the expected trend.

Run from agents/:  uv run python -m price_intelligence_agent.evals.scenarios
"""

import csv
import math
import random
from datetime import datetime, timedelta
from pathlib import Path

from price_intelligence_agent.utils.metrics import REGIMES, volatility_summary

DATA = Path(__file__).resolve().parent.parent / "data"
EVAL_CSV = DATA / "eval_prices.csv"
DAYS = ["2026-11-16", "2026-11-17", "2026-11-18", "2026-11-19", "2026-11-20"]
BARS = 13

# Each scenario: per-day (overnight gap, 30-min sigma, drift per bar), planted intraday shocks {(day, bar): return},
# what we expect, and flags that are acceptable but not required (so they don't count as false alarms).
SCENARIOS = {
    "SYNCALM": {
        "days": [(0.0, 0.0026, 0.0)] * 5,
        "trend": "stable",
        "flags": [],
        "acceptable": [],
        "about": "Quiet week, low volatility, nothing happens.",
    },
    "SYNNORM": {
        "days": [(0.004, 0.0060, 0.0), (-0.005, 0.0060, 0.0), (0.003, 0.0060, 0.0), (-0.004, 0.0060, 0.0), (0.002, 0.0060, 0.0)],
        "trend": "stable",
        "flags": [],
        "acceptable": ["volume_spike"],
        "about": "Ordinary large-cap week, normal volatility, no events.",
    },
    "SYNGAP": {
        "days": [(0.0, 0.0055, 0.0), (0.002, 0.0055, 0.0), (-0.002, 0.0055, 0.0), (0.072, 0.0055, 0.0), (0.0, 0.0055, 0.0)],
        "trend": "stable",
        "flags": ["overnight_gap"],
        "acceptable": ["volume_spike", "trend_break", "range_expansion"],
        "about": "Normal volatility with a 7.2% overnight gap up on Thursday that holds.",
    },
    "SYNREV": {
        "days": [(0.0, 0.0045, 0.0)] * 5,
        "shocks": {(2, 3): -0.042, (2, 4): 0.036},
        "trend": "stable",
        "flags": ["intraday_reversal"],
        "acceptable": ["volume_spike", "range_expansion"],
        "about": "Calm week except a 4.2% drop and 3.6% rebound on Wednesday morning.",
    },
    "SYNCRASH": {
        "days": [(0.0, 0.0040, 0.0), (0.0, 0.0045, 0.0), (-0.01, 0.0080, -0.0030), (-0.015, 0.0110, -0.0040), (-0.01, 0.0130, -0.0035)],
        "trend": "volatility_rising",
        "flags": ["drawdown_over_5pct", "range_expansion"],
        "acceptable": ["volume_spike", "trend_break", "overnight_gap", "intraday_reversal"],
        "about": "Steady sell-off from Wednesday with volatility building each day.",
    },
    "SYNCOOL": {
        "days": [(0.0, 0.0140, 0.0), (0.01, 0.0130, 0.0), (0.0, 0.0070, 0.0), (0.0, 0.0035, 0.0), (0.0, 0.0030, 0.0)],
        "trend": "volatility_falling",
        "flags": [],
        "acceptable": ["volume_spike", "intraday_reversal", "drawdown_over_5pct"],
        "about": "Turbulent Monday and Tuesday that calms down into a quiet end of week.",
    },
    "SYNHOT": {
        "days": [(0.01, 0.0200, 0.0), (-0.012, 0.0200, 0.0), (0.008, 0.0200, 0.0), (-0.01, 0.0200, 0.0), (0.009, 0.0200, 0.0)],
        "trend": "stable",
        "flags": [],
        "acceptable": ["volume_spike", "intraday_reversal", "drawdown_over_5pct", "range_expansion", "trend_break"],
        "about": "Persistently extreme volatility all week (meme-stock style), no single event.",
    },
}

# The NVDA week from data/prices.csv, labelled the same way.
NVDA = {
    "trend": "volatility_rising",
    "flags": ["overnight_gap", "intraday_reversal", "drawdown_over_5pct"],
    "acceptable": ["volume_spike", "range_expansion", "trend_break"],
    "about": "Synthetic NVDA earnings week: 6.1% gap up Thursday, then an intraday whipsaw.",
}



def _bars(ticker: str, spec: dict, seed: int) -> list[dict]:
    rng, price, rows = random.Random(seed), 100.0, []
    shocks = spec.get("shocks", {})
    for d, (day, (gap, sigma, drift)) in enumerate(zip(DAYS, spec["days"])):
        price *= 1 + gap
        t = datetime.fromisoformat(f"{day}T09:30")
        for i in range(BARS):
            shock = shocks.get((d, i), rng.gauss(drift, sigma))
            open_, close = price, price * math.exp(shock)
            high = max(open_, close) * (1 + abs(rng.gauss(0, sigma / 2)))
            low = min(open_, close) * (1 - abs(rng.gauss(0, sigma / 2)))
            volume = int(2_000_000 * (1.5 if i in (0, BARS - 1) else 1) * (1 + 20 * abs(shock)) * rng.uniform(0.9, 1.1))
            rows.append({"ticker": ticker, "timestamp": t.strftime("%Y-%m-%dT%H:%M"), "open": round(open_, 4),
                         "high": round(high, 4), "low": round(low, 4), "close": round(close, 4), "volume": volume})
            price = close
            t += timedelta(minutes=30)
    return rows


BOUNDARIES = (25, 50, 80)
MAX_SEED_TRIES = 500
TREND_OK = {
    "stable": lambda r: 0.8 <= r <= 1.25,
    "volatility_rising": lambda r: r >= 1.5,
    "volatility_falling": lambda r: r <= 0.67,
}


def reference_regime(metrics: dict, planted_reversal: bool) -> str:
    """The regime policy we want: instructions.md's rule, plus one step up for a drawdown worse than 10%.

    The drawdown step is deliberately NOT in the baseline instructions, so the baseline experiment shows the gap.
    """
    vol = metrics["realized_vol_annualized_pct"]
    level = 0 if vol < 25 else 1 if vol < 50 else 2 if vol < 80 else 3
    gap = abs(metrics["largest_overnight_gap_pct"] or 0)
    if gap > 5 or planted_reversal:
        level = min(level + 1, 3)
    if metrics["max_drawdown_pct"] < -10:
        level = min(level + 1, 3)
    return REGIMES[level]


def _clear_cut(rows: list[dict], expected_trend: str) -> bool:
    """True if the scenario's data unambiguously matches its labels."""
    m = volatility_summary(rows)
    vol_ok = all(abs(m["realized_vol_annualized_pct"] - b) >= 4 for b in BOUNDARIES)
    return vol_ok and TREND_OK[expected_trend](m["range_expansion_ratio"])


def build() -> list[dict]:
    """Write data/eval_prices.csv and return the labelled examples (inputs + expected outputs)."""
    by_ticker = {}
    for n, (ticker, spec) in enumerate(SCENARIOS.items()):
        for seed in range(1000 * n, 1000 * n + MAX_SEED_TRIES):
            if _clear_cut(candidate := _bars(ticker, spec, seed), spec["trend"]):
                break
        else:
            raise ValueError(f"No seed in {MAX_SEED_TRIES} tries gives {ticker} clear-cut data; adjust its spec.")
        by_ticker[ticker] = candidate
    with (DATA / "prices.csv").open() as f:
        real_rows = list(csv.DictReader(f))  # NVDA (and its benchmark), unchanged
    by_ticker["NVDA"] = [
        {**r, **{k: float(r[k]) for k in ("open", "high", "low", "close")}, "volume": int(r["volume"])}
        for r in real_rows
        if r["ticker"] == "NVDA"
    ]

    with EVAL_CSV.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(real_rows[0]))
        writer.writeheader()
        for rows in by_ticker.values():
            writer.writerows(rows)
        writer.writerows(r for r in real_rows if r["ticker"] != "NVDA")

    examples = []
    for ticker, spec in {**SCENARIOS, "NVDA": NVDA}.items():
        m = volatility_summary(by_ticker[ticker])
        examples.append(
            {
                "inputs": {"ticker": ticker},
                "outputs": {
                    "regime": reference_regime(m, "intraday_reversal" in spec["flags"]),
                    "trend": spec["trend"],
                    "flags": spec["flags"],
                    "acceptable_flags": spec["acceptable"],
                    "realized_vol_annualized_pct": m["realized_vol_annualized_pct"],
                    "max_drawdown_pct": m["max_drawdown_pct"],
                    "range_expansion_ratio": m["range_expansion_ratio"],
                },
                "metadata": {"scenario": spec["about"]},
            }
        )
    return examples


if __name__ == "__main__":
    for ex in build():
        o = ex["outputs"]
        print(f"{ex['inputs']['ticker']:<9} vol={o['realized_vol_annualized_pct']:>6}% dd={o['max_drawdown_pct']:>6}% "
              f"range_ratio={o['range_expansion_ratio']:<5} -> {o['regime']:<8} {o['trend']:<18} {o['flags']}")
