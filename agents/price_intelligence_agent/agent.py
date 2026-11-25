"""Price Intelligence agent for finsights.

Run it from the agents/ folder:
    uv run python -m price_intelligence_agent.agent NVDA

From the supervisor (with agents/ on sys.path, as in supervisor.ipynb):
    from price_intelligence_agent.agent import price_intelligence      # a tool: add it to the supervisor's tools
    from price_intelligence_agent.agent import agent                   # or invoke the agent with your context
    agent.invoke({"messages": [...]}, context=InvestigationContext(company_name="NVDA", date_str="2026-11-19"))

Context: the agent reads `company_name` and `date_str` from whatever context the caller passes (the supervisor's
InvestigationContext works as is). The company is used when the request doesn't name one, and the analysis covers
the trailing week up to and including `date_str`, never data after it.

The model makes one tool call (get_price_report) and writes the key events and summary. The numbers, regime, trend
and flags in the final report come straight from the code, not from the model.
"""

import sys

from langchain.agents import create_agent
from langchain.agents.middleware import after_agent
from langchain.chat_models import init_chat_model
from langchain.tools import ToolRuntime, tool

from price_intelligence_agent.schemas import PriceContext, PriceIntelligenceReport, PriceNarrative
from price_intelligence_agent.tools.prices import get_price_report, price_report, resolve_request
from price_intelligence_agent.utils.models import PROJECT_ROOT, model

NAME = "lseg_price_intelligence_agent"
DESCRIPTION = (
    "Price Intelligence: latest price, return, high/low, volume, benchmark, VIX, volatility regime, trend, risk "
    "flags, key moves and a short summary for a stock over a window."
)


@after_agent
def add_price_facts(state, runtime):
    """Combine the model's narrative with the facts from the same get_price_report call (same context, same window)."""
    narrative = state.get("structured_response")
    if not isinstance(narrative, PriceNarrative):
        return None
    call_args = [
        call["args"]
        for message in state["messages"]
        for call in getattr(message, "tool_calls", None) or []
        if call["name"] == "get_price_report"
    ]
    args = call_args[-1] if call_args else {"company_or_ticker": narrative.ticker}
    company, start, end = resolve_request(
        args.get("company_or_ticker"), args.get("start"), args.get("end"), runtime.context
    )
    facts = price_report(company or narrative.ticker, start, end)
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
        context_schema=PriceContext,
        middleware=[add_price_facts],
        name=NAME,
        **kwargs,
    )


agent = build_agent()


def analyse_price(
    company_or_ticker: str | None = None,
    start: str | None = None,
    end: str | None = None,
    context=None,
) -> PriceIntelligenceReport:
    """Run the agent and return the full report. `context` is any object with company_name / date_str."""
    target = company_or_ticker or "the company under investigation"
    window = "".join([f" from {start}" if start else "", f" until {end}" if end else ""])
    result = agent.invoke(
        {"messages": [{"role": "user", "content": f"Analyse the price of {target}{window}."}]},
        context=context or PriceContext(),
    )
    report = result.get("structured_response")
    if not isinstance(report, PriceIntelligenceReport):
        raise ValueError(result["messages"][-1].text)
    return report


@tool(parse_docstring=True)
def price_intelligence(
    runtime: ToolRuntime,
    company_or_ticker: str | None = None,
    start: str | None = None,
    end: str | None = None,
) -> dict | str:
    """Price Intelligence for a company: latest price, return, high and low, volume, benchmark comparison, VIX,
    volatility regime, trend, risk flags, key moves and a short summary. All numbers are computed from historical
    data, with an as-of timestamp. Uses the company and date under investigation if you don't give them.

    Args:
        company_or_ticker: A company name such as "NVIDIA" or a ticker such as "NVDA". Optional.
        start: Optional start date, for example "2026-11-16".
        end: Optional last day to include, for example "2026-11-20".
    """
    try:
        return analyse_price(company_or_ticker, start, end, context=runtime.context).model_dump()
    except ValueError as error:
        return str(error)


if __name__ == "__main__":
    print(analyse_price(sys.argv[1] if len(sys.argv) > 1 else "NVDA").model_dump_json(indent=2))
