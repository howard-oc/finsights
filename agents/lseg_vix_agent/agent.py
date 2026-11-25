"""lseg_vix_agent: the price volatility agent, one of the finsights agents.

Use it on its own:    uv run python agent.py [TICKER]
Use it from another agent / orchestrator:
    from agent import analyse_volatility
    report = analyse_volatility("NVDA")      # -> schemas.VolatilityReport
"""

import sys

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model

from schemas import VolatilityReport
from tools.volatility import detect_price_anomalies, get_price_bars, get_volatility_metrics
from utils.models import PROJECT_ROOT, model

NAME = "lseg_vix_agent"
DESCRIPTION = (
    "Analyses intraday price volatility for a stock over a window and returns a structured VolatilityReport: "
    "regime, realized volatility, key moves, trend and risk flags."
)


def build_agent(**kwargs):
    """Build the agent with `create_agent`. Pass `checkpointer` / `store` for memory if the caller needs it."""
    return create_agent(
        model=init_chat_model(model),
        tools=[get_volatility_metrics, detect_price_anomalies, get_price_bars],
        system_prompt=(PROJECT_ROOT / "instructions.md").read_text(),
        response_format=VolatilityReport,
        name=NAME,
        **kwargs,
    )


agent = build_agent()  # registered in langgraph.json for `langgraph dev`


def analyse_volatility(ticker: str, start: str | None = None, end: str | None = None) -> VolatilityReport:
    window = f" from {start}" if start else ""
    window += f" until {end}" if end else ""
    result = agent.invoke({"messages": [{"role": "user", "content": f"Analyse price volatility for {ticker}{window}."}]})
    return result["structured_response"]


if __name__ == "__main__":
    report = analyse_volatility(sys.argv[1] if len(sys.argv) > 1 else "NVDA")
    print(report.model_dump_json(indent=2))
