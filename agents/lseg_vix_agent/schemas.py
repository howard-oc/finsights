"""The structured report this agent returns. Other finsights agents (or an orchestrator) consume this, not prose."""

from typing import Literal

from pydantic import BaseModel, Field


class VolatilityEvent(BaseModel):
    timestamp: str = Field(description="When it happened, ISO format.")
    description: str = Field(description="What happened, in one sentence.")
    magnitude_pct: float = Field(description="Size of the move in percent (signed).")


class VolatilityReport(BaseModel):
    ticker: str
    window_start: str
    window_end: str
    regime: Literal["low", "normal", "elevated", "extreme"] = Field(
        description="Volatility regime over the window, judged from annualized realized volatility and the events."
    )
    realized_vol_annualized_pct: float
    period_return_pct: float
    max_drawdown_pct: float
    key_events: list[VolatilityEvent] = Field(description="The 1-5 most important moves, largest first.")
    trend: Literal["volatility_rising", "volatility_falling", "stable"]
    summary: str = Field(description="Two or three sentences for an analyst. No investment advice.")
    risk_flags: list[str] = Field(description="Short flags for downstream agents, e.g. 'overnight_gap', 'intraday_reversal'.")
