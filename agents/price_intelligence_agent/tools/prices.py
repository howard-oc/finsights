"""The agent's one tool: everything about a stock's price over a window, worked out in code."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from langchain.tools import tool

from price_intelligence_agent.utils import data
from price_intelligence_agent.utils.metrics import volatility_summary

BAR_MINUTES = 30


def to_utc(local_time: str, timezone: str) -> str:
    """Exchange-local "YYYY-MM-DDTHH:MM" to UTC, for example "2026-11-20T16:00" -> "2026-11-20T21:00:00Z"."""
    local = datetime.fromisoformat(local_time).replace(tzinfo=ZoneInfo(timezone))
    return local.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ")


def price_report(company_or_ticker: str, start: str | None = None, end: str | None = None) -> dict | str:
    """All the price facts for a stock. Returns a message instead if there is no data for it."""
    instrument = data.find_instrument(company_or_ticker) or {"ticker": company_or_ticker.upper()}
    ticker = instrument["ticker"]
    bars = data.bars(ticker, start, end)
    if len(bars) < 3:
        known = sorted({row["ticker"] for row in data.table("prices")})
        return f"There is no price data for {company_or_ticker}. Stocks with data: {', '.join(known)}."

    tz = instrument.get("timezone") or "America/New_York"
    summary = volatility_summary(bars)
    days = summary["daily"]
    high = max(bars, key=lambda b: b["high"])
    low = min(bars, key=lambda b: b["low"])
    window_end = (datetime.fromisoformat(bars[-1]["timestamp"]) + timedelta(minutes=BAR_MINUTES)).isoformat()[:16]

    # Volume: latest session against the average of the earlier ones, and days well above the window's average.
    volumes = [d["volume"] for d in days]
    earlier = volumes[:-1]
    relative_volume = round(volumes[-1] / mean_of(earlier), 2) if mean_of(earlier) else None
    unusual_volume_days = [
        {"date": d["date"], "times_average": round(d["volume"] / mean_of(volumes), 2)}
        for d in days
        if d["volume"] >= 1.5 * mean_of(volumes)
    ]

    # Benchmark and VIX over the same window.
    benchmark = instrument.get("benchmark") or None
    bench_bars = data.bars(benchmark, start, end) if benchmark else []
    bench_return = round((bench_bars[-1]["close"] / bench_bars[0]["open"] - 1) * 100, 2) if len(bench_bars) > 1 else None
    vix = [float(r["close"]) for r in data.table("vix") if days[0]["date"] <= r["date"] <= days[-1]["date"]]

    # Times the model might quote go out in UTC, like the rest of the report.
    for item in summary["unusual_moves"] + summary["volume_spikes"]:
        item["timestamp"] = to_utc(item["timestamp"], tz)
    for turn in summary["intraday_reversals"]:
        turn["from"], turn["to"] = to_utc(turn["from"], tz), to_utc(turn["to"], tz)

    return {
        "ticker": ticker,
        "company_name": instrument.get("company_name"),
        "currency": instrument.get("currency"),
        "exchange": instrument.get("exchange"),
        "as_of": to_utc(window_end, tz),
        "data_status": data.DATA_STATUS,
        "data_source": data.DATA_SOURCE,
        "window_start": to_utc(bars[0]["timestamp"], tz),
        "window_end": to_utc(window_end, tz),
        "latest_price": bars[-1]["close"],
        "period_high": high["high"],
        "period_high_at": to_utc(high["timestamp"], tz),
        "period_low": low["low"],
        "period_low_at": to_utc(low["timestamp"], tz),
        "total_volume": sum(volumes),
        "relative_volume": relative_volume,
        "unusual_volume_days": unusual_volume_days,
        "benchmark_ticker": benchmark if bench_return is not None else None,
        "benchmark_return_pct": bench_return,
        "relative_performance_pct": (
            round(summary["period_return_pct"] - bench_return, 2) if bench_return is not None else None
        ),
        "vix_latest": vix[-1] if vix else None,
        "vix_change": round(vix[-1] - vix[0], 2) if len(vix) > 1 else None,
        **summary,
    }


def mean_of(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


@tool(parse_docstring=True)
def get_price_report(company_or_ticker: str, start: str | None = None, end: str | None = None) -> dict | str:
    """Get everything about a stock's price over a window in one call: latest price, return, high and low, volume,
    benchmark and VIX, volatility, daily rows, unusual moves, reversals, and the regime, trend and risk flags.

    Args:
        company_or_ticker: A ticker such as "NVDA" or a company name such as "Nvidia".
        start: Optional date or timestamp to start from, for example "2026-11-18".
        end: Optional date or timestamp to stop before.
    """
    return price_report(company_or_ticker, start, end)
