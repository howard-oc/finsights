"""Price Intelligence agent for finsights.

Run it from the agents/ folder:
    uv run python -m price_intelligence_agent.agent NVDA

From the supervisor (with agents/ on sys.path, as in supervisor.ipynb):
    from price_intelligence_agent.agent import price_intelligence      # a tool: add it to the supervisor's tools
    from price_intelligence_agent.agent import analyse_price           # or call it directly
    report = analyse_price("Nvidia")    # PriceIntelligenceReport

The model makes one tool call (get_price_report) and writes the key events and summary. The numbers, regime, trend
and flags in the final report come straight from the code, not from the model.
"""

import sys

from langchain.agents import create_agent
from langchain.agents.middleware import after_agent
from langchain.chat_models import init_chat_model
from langchain.tools import tool

from price_intelligence_agent.schemas import PriceIntelligenceReport, PriceNarrative
from price_intelligence_agent.tools.prices import get_price_report, price_report
from price_intelligence_agent.utils.models import PROJECT_ROOT, model

NAME = "lseg_price_intelligence_agent"
DESCRIPTION = (
    "Price Intelligence: latest price, return, high/low, volume, benchmark, VIX, volatility regime, trend, risk "
    "flags, key moves and a short summary for a stock over a window."
)


@after_agent
def add_price_facts(state, runtime):
    """Combine the model's narrative with the facts from the same get_price_report call."""
    narrative = state.get("structured_response")
    if not isinstance(narrative, PriceNarrative):
        return None
    call_args = [
        call["args"]
        for message in state["messages"]
        for call in getattr(message, "tool_calls", None) or []
        if call["name"] == "get_price_report"
    ]
    facts = price_report(**call_args[-1]) if call_args else price_report(narrative.ticker)
    if isinstance(facts, str):  # no data for that stock
        return None
    fields = {k: v for k, v in facts.items() if k in PriceIntelligenceReport.model_fields}
    report = PriceIntelligenceReport(**fields, key_events=narrative.key_events, summary=narrative.summary)
    return {"structured_response": report}


#
# LangChain Agent Definition
#
def build_agent(**kwargs):
    return create_agent(
        model=init_chat_model(model),
        tools=[get_price_report],
        system_prompt=(PROJECT_ROOT / "instructions.md").read_text(),
        response_format=PriceNarrative,
        middleware=[add_price_facts],
        name=NAME,
        **kwargs,
    )


agent = build_agent()


def analyse_price(company_or_ticker: str, start: str | None = None, end: str | None = None) -> PriceIntelligenceReport:
    window = "".join([f" from {start}" if start else "", f" until {end}" if end else ""])
    result = agent.invoke({"messages": [{"role": "user", "content": f"Analyse the price of {company_or_ticker}{window}."}]})
    report = result.get("structured_response")
    if not isinstance(report, PriceIntelligenceReport):
        raise ValueError(result["messages"][-1].text)
    return report


@tool(parse_docstring=True)
def price_intelligence(company_or_ticker: str, start: str | None = None, end: str | None = None) -> dict | str:
    """Price Intelligence for a company: latest price, return, high and low, volume, benchmark comparison, VIX,
    volatility regime, trend, risk flags, key moves and a short summary. All numbers are computed from historical
    data, with an as-of timestamp.

    Args:
        company_or_ticker: A company name such as "NVIDIA" or a ticker such as "NVDA".
        start: Optional start date, for example "2026-11-16".
        end: Optional date to stop before, for example "2026-11-21".
    """
    try:
        return analyse_price(company_or_ticker, start, end).model_dump()
    except ValueError as error:
        return str(error)


if __name__ == "__main__":
    print(analyse_price(sys.argv[1] if len(sys.argv) > 1 else "NVDA").model_dump_json(indent=2))
