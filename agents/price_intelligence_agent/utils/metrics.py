"""Price and volatility maths, and the rules for regime, trend and risk flags. Plain Python, no LLM.

Change a threshold here and re-run the evals to see the effect.
"""

import math
from statistics import mean, median, pstdev

TRADING_DAYS = 252
REGIMES = ["low", "normal", "elevated", "extreme"]

# Regime: annualized realized vol below 25% is low, below 50% normal, below 80% elevated, otherwise extreme.
VOL_BOUNDS = (25, 50, 80)
# Each of these moves the regime up one step.
GAP_BUMP_PCT = 5.0
REVERSAL_BUMP_PCT = 3.0
DRAWDOWN_BUMP_PCT = 10.0
# Risk flags.
GAP_FLAG_PCT = 3.0
DRAWDOWN_FLAG_PCT = 5.0
REVERSAL_LEG_PCT = 1.5
VOLUME_SPIKE_MULTIPLE = 2.5  # times the median bar volume
UNUSUAL_MOVE_Z = 2.5
# Trend: average daily range in the second half of the window vs the first half.
RISING_RATIO = 1.5
FALLING_RATIO = 0.67


def daily(bars: list[dict], prev_close: float | None = None) -> list[dict]:
    """One row per trading day: open, high, low, close, volume, return, overnight gap and range.

    `prev_close` is the close of the session before the window, so the first day's return and gap are measured from
    it, the way a day's move is normally reported.
    """
    by_day = {}
    for bar in bars:
        by_day.setdefault(bar["timestamp"][:10], []).append(bar)

    days = []
    for date, day_bars in sorted(by_day.items()):
        high = max(b["high"] for b in day_bars)
        low = min(b["low"] for b in day_bars)
        open_, close = day_bars[0]["open"], day_bars[-1]["close"]
        days.append({
            "date": date,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": sum(b["volume"] for b in day_bars),
            "bars": len(day_bars),
            "return_pct": round((close / prev_close - 1) * 100, 2) if prev_close else None,
            "overnight_gap_pct": round((open_ / prev_close - 1) * 100, 2) if prev_close else None,
            "intraday_range_pct": round((high / low - 1) * 100, 2),
        })
        prev_close = close
    return days


def intraday_returns(bars: list[dict]) -> list[tuple[str, float]]:
    """Bar-to-bar log returns within each day. Overnight gaps are left out (they are measured separately)."""
    return [
        (cur["timestamp"], math.log(cur["close"] / prev["close"]))
        for prev, cur in zip(bars, bars[1:])
        if prev["timestamp"][:10] == cur["timestamp"][:10]
    ]


def max_drawdown_pct(bars: list[dict], prev_close: float | None = None) -> float:
    """Worst fall from a running peak to a later low, in percent (negative). Starts from the previous close if known,
    so a gap down at the start of the window counts."""
    peak, worst = prev_close or bars[0]["open"], 0.0
    for bar in bars:
        worst = min(worst, bar["low"] / peak - 1)
        peak = max(peak, bar["high"])
    return round(worst * 100, 2)


def unusual_moves(bars: list[dict]) -> list[dict]:
    """Intraday bars whose return is UNUSUAL_MOVE_Z or more standard deviations from the window's average."""
    returns = intraday_returns(bars)
    if len(returns) < 5:
        return []
    avg, sd = mean(r for _, r in returns), pstdev(r for _, r in returns)
    if sd == 0:
        return []
    return [
        {"timestamp": ts, "return_pct": round((math.exp(r) - 1) * 100, 2), "z_score": round((r - avg) / sd, 2)}
        for ts, r in returns
        if abs(r - avg) / sd >= UNUSUAL_MOVE_Z
    ]


def volume_spikes(bars: list[dict]) -> list[dict]:
    """Bars with VOLUME_SPIKE_MULTIPLE times the median bar volume or more."""
    typical = median(b["volume"] for b in bars)
    return [
        {"timestamp": b["timestamp"], "volume": b["volume"], "times_median": round(b["volume"] / typical, 1)}
        for b in bars
        if typical and b["volume"] >= VOLUME_SPIKE_MULTIPLE * typical
    ]


def reversals(moves: list[dict]) -> list[dict]:
    """Back-to-back unusual moves on the same day in opposite directions, each at least REVERSAL_LEG_PCT."""
    return [
        {"from": a["timestamp"], "to": b["timestamp"], "legs_pct": [a["return_pct"], b["return_pct"]]}
        for a, b in zip(moves, moves[1:])
        if a["timestamp"][:10] == b["timestamp"][:10]
        and a["return_pct"] * b["return_pct"] < 0
        and min(abs(a["return_pct"]), abs(b["return_pct"])) >= REVERSAL_LEG_PCT
    ]


def volatility_summary(bars: list[dict], prev_close: float | None = None) -> dict:
    """Volatility metrics plus the regime, trend and risk flags for a window of bars (one ticker, oldest first)."""
    days = daily(bars, prev_close)
    returns = [r for _, r in intraday_returns(bars)]
    bars_per_day = max(d["bars"] for d in days)
    realized = pstdev(returns) * math.sqrt(bars_per_day * TRADING_DAYS) if len(returns) > 1 else 0.0
    log_ranges = [math.log(d["high"] / d["low"]) for d in days]
    parkinson = math.sqrt(mean(r**2 for r in log_ranges) / (4 * math.log(2)) * TRADING_DAYS)

    half = len(log_ranges) // 2
    first, second = log_ranges[:half] or log_ranges, log_ranges[half:]
    range_ratio = round(mean(second) / mean(first), 2) if mean(first) > 0 else 1.0

    gaps = [d["overnight_gap_pct"] for d in days if d["overnight_gap_pct"] is not None]
    largest_gap = max(gaps, key=abs, default=None)
    vol_pct = round(realized * 100, 1)
    drawdown = max_drawdown_pct(bars, prev_close)
    moves = unusual_moves(bars)
    spikes = volume_spikes(bars)
    turns = reversals(moves)

    # Regime
    level = sum(vol_pct >= bound for bound in VOL_BOUNDS)
    reasons = [f"realized vol {vol_pct}% -> {REGIMES[level]}"]
    big_turn = any(max(abs(leg) for leg in t["legs_pct"]) > REVERSAL_BUMP_PCT for t in turns)
    if abs(largest_gap or 0) > GAP_BUMP_PCT or big_turn:
        level = min(level + 1, 3)
        reasons.append("+1 for an overnight gap or intraday reversal above threshold")
    if drawdown < -DRAWDOWN_BUMP_PCT:
        level = min(level + 1, 3)
        reasons.append(f"+1 for a {drawdown}% drawdown")

    # Trend
    if range_ratio >= RISING_RATIO:
        trend = "volatility_rising"
    elif range_ratio <= FALLING_RATIO:
        trend = "volatility_falling"
    else:
        trend = "stable"

    # Risk flags
    flags = []
    if abs(largest_gap or 0) > GAP_FLAG_PCT:
        flags.append("overnight_gap")
    if turns:
        flags.append("intraday_reversal")
    if spikes:
        flags.append("volume_spike")
    if range_ratio >= RISING_RATIO:
        flags.append("range_expansion")
    if drawdown < -DRAWDOWN_FLAG_PCT:
        flags.append("drawdown_over_5pct")

    return {
        "period_return_pct": round((bars[-1]["close"] / (prev_close or bars[0]["open"]) - 1) * 100, 2),
        "period_return_basis": "previous close" if prev_close else "window open",
        "previous_close": prev_close,
        "intraday_return_pct": round((bars[-1]["close"] / bars[0]["open"] - 1) * 100, 2),
        "realized_vol_annualized_pct": vol_pct,
        "parkinson_vol_annualized_pct": round(parkinson * 100, 1),
        "max_drawdown_pct": drawdown,
        "largest_overnight_gap_pct": largest_gap,
        "range_expansion_ratio": range_ratio,
        "regime": REGIMES[level],
        "regime_reasons": reasons,
        "trend": trend,
        "risk_flags": flags,
        "daily": days,
        "unusual_moves": moves,
        "volume_spikes": spikes,
        "intraday_reversals": turns,
    }
