"""Structured output of the price intelligence agent. Other finsights agents (and the Research Supervisor) consume
PriceIntelligenceReport, not prose.

The model only produces PriceNarrative (what it is good at: picking out what matters and explaining it). Every other
field of PriceIntelligenceReport comes from tools/prices.py, added by the add_price_facts hook in agent.py.
"""

from typing import Literal

from pydantic import BaseModel, Field


class KeyEvent(BaseModel):
    timestamp: str = Field(description="When it happened, exactly as the tools give it.")
    description: str = Field(description="What happened, in one sentence.")
    magnitude_pct: float = Field(description="Size of the move in percent (signed), exactly as the tools give it.")


class PriceNarrative(BaseModel):
    """What the model writes."""

    ticker: str = Field(description="The ticker you analysed.")
    key_events: list[KeyEvent] = Field(description="The 1-5 most important moves, largest first.")
    summary: str = Field(
        description="Two or three sentences for an analyst: what happened, why the regime is what it is, and how the "
        "stock did against its benchmark. No investment advice."
    )


class VolumeDay(BaseModel):
    date: str
    times_average: float


class PriceIntelligenceReport(BaseModel):
    """The full report: code-computed facts and decisions plus the model's narrative."""

    # Identity and provenance (README: as-of timestamp, live/delayed/historical)
    ticker: str
    company_name: str | None
    currency: str | None
    exchange: str | None
    as_of: str = Field(description="UTC time of the latest data point, ISO 8601 with Z.")
    data_status: Literal["live", "delayed", "historical"]
    data_source: str
    window_start: str = Field(description="UTC, ISO 8601 with Z.")
    window_end: str = Field(description="UTC, ISO 8601 with Z.")

    # Price performance
    latest_price: float
    period_return_pct: float
    period_high: float
    period_high_at: str
    period_low: float
    period_low_at: str

    # Volume
    total_volume: int
    relative_volume: float | None = Field(description="Latest session's volume / average of the earlier sessions.")
    unusual_volume_days: list[VolumeDay]

    # Benchmark and market context
    benchmark_ticker: str | None
    benchmark_return_pct: float | None
    relative_performance_pct: float | None = Field(description="Period return minus the benchmark's, in points.")
    vix_latest: float | None
    vix_change: float | None

    # Volatility
    realized_vol_annualized_pct: float = Field(description="Intraday realized volatility, annualized.")
    parkinson_vol_annualized_pct: float
    max_drawdown_pct: float
    largest_overnight_gap_pct: float | None
    regime: Literal["low", "normal", "elevated", "extreme"]
    regime_reasons: list[str]
    trend: Literal["volatility_rising", "volatility_falling", "stable"]
    risk_flags: list[str]

    # The model's part
    key_events: list[KeyEvent]
    summary: str


