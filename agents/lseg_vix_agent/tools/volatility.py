"""Volatility tools. All the maths is deterministic Python; the model only interprets the results."""

import math
from statistics import mean, pstdev

from langchain.tools import tool

from utils.data import available_tickers, load_bars

TRADING_DAYS = 252


def _daily(bars: list[dict]) -> list[dict]:
    days: dict[str, list[dict]] = {}
    for b in bars:
        days.setdefault(b["timestamp"][:10], []).append(b)
    return [
        {
            "date": d,
            "open": bs[0]["open"],
            "high": max(b["high"] for b in bs),
            "low": min(b["low"] for b in bs),
            "close": bs[-1]["close"],
            "volume": sum(b["volume"] for b in bs),
            "bars": len(bs),
        }
        for d, bs in sorted(days.items())
    ]


def _intraday_log_returns(bars: list[dict]) -> list[tuple[str, float]]:
    """Bar-to-bar log returns within each day (overnight gaps excluded; they are measured separately)."""
    out = []
    for prev, cur in zip(bars, bars[1:]):
        if prev["timestamp"][:10] == cur["timestamp"][:10]:
            out.append((cur["timestamp"], math.log(cur["close"] / prev["close"])))
    return out


def compute_metrics(ticker: str, start: str | None = None, end: str | None = None) -> dict:
    """Core volatility metrics for a ticker over a window. Pure function, also used by evals."""
    bars = load_bars(ticker, start, end)
    if len(bars) < 3:
        return {"error": f"Not enough data for {ticker}. Available tickers: {available_tickers()}"}
    return compute_metrics_from_bars(bars)


def compute_metrics_from_bars(bars: list[dict]) -> dict:
    """compute_metrics on bars already in memory (oldest first, all one ticker)."""
    days = _daily(bars)
    bars_per_day = max(d["bars"] for d in days)
    rets = [r for _, r in _intraday_log_returns(bars)]
    realized_ann = pstdev(rets) * math.sqrt(bars_per_day * TRADING_DAYS)
    parkinson_ann = math.sqrt(
        mean(math.log(d["high"] / d["low"]) ** 2 for d in days) / (4 * math.log(2))
    ) * math.sqrt(TRADING_DAYS)

    peak, max_dd = bars[0]["close"], 0.0
    for b in bars:
        peak = max(peak, b["high"])
        max_dd = min(max_dd, b["low"] / peak - 1)

    daily_rows, prev_close = [], None
    for d in days:
        daily_rows.append(
            {
                "date": d["date"],
                "open": d["open"],
                "close": d["close"],
                "return_pct": round((d["close"] / prev_close - 1) * 100, 2) if prev_close else None,
                "overnight_gap_pct": round((d["open"] / prev_close - 1) * 100, 2) if prev_close else None,
                "intraday_range_pct": round((d["high"] / d["low"] - 1) * 100, 2),
                "volume": d["volume"],
            }
        )
        prev_close = d["close"]

    half = len(days) // 2
    first, second = days[:half] or days, days[half:]
    range_first = mean(math.log(d["high"] / d["low"]) for d in first)
    range_second = mean(math.log(d["high"] / d["low"]) for d in second)

    return {
        "ticker": bars[0]["ticker"].upper(),
        "window": {"start": bars[0]["timestamp"], "end": bars[-1]["timestamp"], "bars": len(bars), "days": len(days)},
        "period_return_pct": round((bars[-1]["close"] / bars[0]["open"] - 1) * 100, 2),
        "realized_vol_annualized_pct": round(realized_ann * 100, 1),
        "parkinson_vol_annualized_pct": round(parkinson_ann * 100, 1),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "largest_overnight_gap_pct": max(
            (r["overnight_gap_pct"] for r in daily_rows if r["overnight_gap_pct"] is not None), key=abs, default=None
        ),
        "range_expansion_ratio": round(range_second / range_first, 2),
        "daily": daily_rows,
    }


def find_anomalies(ticker: str, z_threshold: float = 2.5, start: str | None = None, end: str | None = None) -> dict:
    """Intraday bars whose return is more than z_threshold standard deviations from the mean, and volume spikes."""
    bars = load_bars(ticker, start, end)
    rets = _intraday_log_returns(bars)
    if len(rets) < 5:
        return {"error": f"Not enough data for {ticker}."}
    mu, sd = mean(r for _, r in rets), pstdev(r for _, r in rets)
    by_ts = {b["timestamp"]: b for b in bars}
    vol_mu, vol_sd = mean(b["volume"] for b in bars), pstdev(b["volume"] for b in bars)

    moves = [
        {
            "timestamp": ts,
            "return_pct": round((math.exp(r) - 1) * 100, 2),
            "z_score": round((r - mu) / sd, 2),
            "volume": by_ts[ts]["volume"],
        }
        for ts, r in rets
        if abs(r - mu) / sd >= z_threshold
    ]
    volume_spikes = [
        {"timestamp": b["timestamp"], "volume": b["volume"], "z_score": round((b["volume"] - vol_mu) / vol_sd, 2)}
        for b in bars
        if (b["volume"] - vol_mu) / vol_sd >= z_threshold
    ]
    return {"ticker": ticker.upper(), "z_threshold": z_threshold, "price_moves": moves, "volume_spikes": volume_spikes}


@tool(parse_docstring=True)
def get_volatility_metrics(ticker: str, start: str | None = None, end: str | None = None) -> dict:
    """Compute volatility metrics for a ticker: realized and Parkinson volatility (annualized), max drawdown,
    overnight gaps, daily returns and ranges, and whether ranges expanded through the window.

    Args:
        ticker: Stock ticker, for example "NVDA".
        start: Optional ISO date or timestamp to start from (inclusive).
        end: Optional ISO date or timestamp to stop at (exclusive).
    """
    return compute_metrics(ticker, start, end)


@tool(parse_docstring=True)
def detect_price_anomalies(ticker: str, z_threshold: float = 2.5) -> dict:
    """Find unusual intraday moves and volume spikes, measured in standard deviations from the window's mean.

    Args:
        ticker: Stock ticker, for example "NVDA".
        z_threshold: How many standard deviations count as unusual. 2.5 is a sensible default.
    """
    return find_anomalies(ticker, z_threshold)


@tool(parse_docstring=True)
def get_price_bars(ticker: str, date: str) -> list[dict]:
    """Get the raw 30-minute price bars for one trading day, to look closely at what happened intraday.

    Args:
        ticker: Stock ticker, for example "NVDA".
        date: Trading day as YYYY-MM-DD.
    """
    next_day = date + "T99"  # every timestamp on `date` sorts before this
    return load_bars(ticker, date, next_day)
