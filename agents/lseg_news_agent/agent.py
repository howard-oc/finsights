"""News Intelligence Agent: standalone LangGraph workflow and LangChain supervisor tool."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TypedDict
from pathlib import Path

from langchain.agents import create_agent
from langchain.agents.middleware import after_agent
from langchain.chat_models import init_chat_model
from langchain.tools import ToolRuntime, tool
from langgraph.graph import END, StateGraph

from lseg_news_agent.prompts import ADVICE_GUARDRAIL, CLASSIFICATION_PROMPT, SUMMARY_PROMPT
from lseg_news_agent.schemas import (
    DataQualityNote, EventGroup, KeyDevelopment, NewsClassificationBatch,
    NewsIntelligenceOutput, NewsSummaryBatch, RawNewsArticle, ResearchPeriod,
)
from lseg_news_agent.tools.news import (
    advice_policy_violations, deduplicate_articles, filter_articles,
    find_conflicts, organise_timeline, retrieve_news, validate_traceability,
)
from lseg_news_agent.utils.data import load_news_feed
from lseg_news_agent.utils.models import model

NAME = "lseg_news_agent"
DESCRIPTION = (
    "News Intelligence: retrieves, deduplicates, classifies, summarises and chronologically organises company news "
    "with source traceability."
)


@dataclass
class NewsContext:
    """Caller investigation context, compatible with the research supervisor."""

    company_name: str = ""
    date_str: str = ""


class NewsAgentState(TypedDict, total=False):
    company_name: str
    ticker: str
    start_date: str
    end_date: str
    newest_first: bool
    raw_articles: list[dict]
    filtered_articles: list[dict]
    event_groups: list[dict]
    data_quality_notes: list[dict]
    conflicting_signals: list[dict]
    uncertainties: list[str]
    output: dict
    timeline: dict


def trace(node_name: str):
    """Best-effort LangSmith tracing decorator for each graph node."""
    try:
        from langsmith.run_helpers import traceable
        return traceable(name=node_name, tags=["news-agent", f"node:{node_name}"], run_type="chain")
    except Exception:
        def identity(fn):
            return fn
        return identity


@trace("retrieve_news")
def retrieve_news_node(state: NewsAgentState) -> dict:
    rows = retrieve_news.invoke({"company_name": state["company_name"], "ticker": state["ticker"]})
    return {"raw_articles": rows}


@trace("filter_articles")
def filter_articles_node(state: NewsAgentState) -> dict:
    articles = [RawNewsArticle.model_validate(row) for row in state["raw_articles"]]
    kept, notes = filter_articles(
        articles, state["company_name"], state["ticker"], state["start_date"], state["end_date"]
    )
    return {
        "filtered_articles": [a.model_dump() for a in kept],
        "data_quality_notes": [n.model_dump() for n in notes],
    }


@trace("deduplicate")
def deduplicate_node(state: NewsAgentState) -> dict:
    articles = [RawNewsArticle.model_validate(row) for row in state["filtered_articles"]]
    groups = deduplicate_articles(articles)
    return {"event_groups": [g.model_dump() for g in groups]}


def _heuristic_category(headlines: str) -> str:
    text = headlines.lower()
    if any(w in text for w in ("earnings", "revenue", "quarter", "margin", "guidance", "filing")):
        return "earnings"
    if any(w in text for w in ("acquire", "acquisition", "merger", "deal")):
        return "M&A"
    if any(w in text for w in ("chief", "ceo", "officer", "director", "board", "appoint")):
        return "management_change"
    if any(w in text for w in ("ai accelerator", "chip", "platform", "technology", "research")):
        return "product_technology"
    if any(w in text for w in ("partnership", "supply agreement", "partners", "expands")):
        return "strategic_partnership"
    if any(w in text for w in ("regulator", "review", "regulatory")):
        return "regulatory"
    if any(w in text for w in ("patent", "court", "litigation", "dispute", "settle", "legal")):
        return "litigation"
    if any(w in text for w in ("competitor", "rival", "nova systems")):
        return "competitor"
    if any(w in text for w in ("industry", "market report", "survey", "demand")):
        return "industry_macro"
    return "other"


@trace("classify_and_assess")
def classify_node(state: NewsAgentState) -> dict:
    groups = [EventGroup.model_validate(row) for row in state["event_groups"]]
    articles = {row["article_id"]: RawNewsArticle.model_validate(row) for row in state["raw_articles"]}
    payload = []
    for group in groups:
        refs = [articles[aid].model_dump() for aid in group.article_ids if aid in articles]
        payload.append({"event_group_id": group.event_group_id, "articles": refs})

    llm_items = {}
    try:
        llm = init_chat_model(model).with_structured_output(NewsClassificationBatch)
        result = llm.invoke([
            ("system", CLASSIFICATION_PROMPT + " " + ADVICE_GUARDRAIL),
            ("human", f"Classify these event groups:\n{payload}"),
        ])
        llm_items = {item.article_id: item for item in result.items}
    except Exception:
        pass

    for group in groups:
        for article_id in group.article_ids:
            item = llm_items.get(article_id)
            if item:
                group.event_category = item.event_category
                group.importance = item.importance
                group.importance_rationale = item.importance_rationale
            else:
                category = _heuristic_category(" ".join(group.headlines))
                group.event_category = category
                group.importance = "high" if category in {"earnings", "M&A", "regulatory", "litigation"} else "medium"
                group.importance_rationale = "Assigned by deterministic fallback from event category."
    return {"event_groups": [g.model_dump() for g in groups]}


@trace("summarise")
def summarise_node(state: NewsAgentState) -> dict:
    groups = [EventGroup.model_validate(row) for row in state["event_groups"]]
    articles = {row["article_id"]: RawNewsArticle.model_validate(row) for row in state["raw_articles"]}
    payload = [{"article_id": aid, "headline": article.headline, "snippet": article.snippet}
               for aid, article in articles.items() if aid in {aid for g in groups for aid in g.article_ids}]

    llm_items = {}
    try:
        llm = init_chat_model(model).with_structured_output(NewsSummaryBatch)
        result = llm.invoke([
            ("system", SUMMARY_PROMPT),
            ("human", f"Summarise and interpret these source records:\n{payload}"),
        ])
        llm_items = {item.article_id: item for item in result.items}
    except Exception:
        pass

    for group in groups:
        summaries, why_notes = [], []
        for article_id in group.article_ids:
            article = articles.get(article_id)
            item = llm_items.get(article_id)
            if item:
                summary = item.summary
                why = item.why_it_matters
            elif article:
                words = article.snippet.split()
                summary = " ".join(words[:40])
                why = "This may be relevant because it concerns an announced company development."
            else:
                summary = ""
                why = "Source record unavailable."
            summaries.append(summary)
            why_notes.append(why)
        group.summary = " ".join(summaries)[:500]
        group.why_it_matters = " ".join(dict.fromkeys(why_notes))
    return {"event_groups": [g.model_dump() for g in groups]}


@trace("organise_timeline")
def timeline_node(state: NewsAgentState) -> dict:
    groups = [EventGroup.model_validate(row) for row in state["event_groups"]]
    timeline = organise_timeline(groups, newest_first=state.get("newest_first", True))
    conflicts = find_conflicts(groups)
    return {"timeline": timeline, "event_groups": [g.model_dump() for g in groups],
            "conflicting_signals": [c.model_dump() for c in conflicts]}


@trace("validate_output")
def validate_node(state: NewsAgentState) -> dict:
    groups = [EventGroup.model_validate(row) for row in state["event_groups"]]
    notes = [DataQualityNote.model_validate(row) for row in state.get("data_quality_notes", [])]
    timeline = state["timeline"]
    uncertainties, unsupported = validate_traceability(groups, notes)

    rank = {"high": 3, "medium": 2, "low": 1}
    top = sorted(groups, key=lambda g: (rank.get(g.importance or "low", 0), g.published_at[0] or ""), reverse=True)[:5]
    key_developments = []
    all_output_text = []
    for group in top:
        if group.event_category and group.summary:
            key_developments.append(KeyDevelopment(
                event_group_id=group.event_group_id,
                event_category=group.event_category,
                importance=group.importance or "low",
                summary=group.summary,
                why_it_matters=group.why_it_matters or "",
                source_article_ids=group.article_ids,
            ))
            all_output_text.extend([group.summary, group.why_it_matters or ""])

    violations = []
    for text in all_output_text:
        violations.extend(advice_policy_violations(text))
    if violations:
        uncertainties.append("Advice-policy post-check found prohibited language: " + ", ".join(sorted(set(violations))))
    uncertainties.extend(unsupported)

    category_counts = {}
    for group in groups:
        category = group.event_category or "other"
        category_counts[category] = category_counts.get(category, 0) + 1

    output = NewsIntelligenceOutput(
        company_name=state["company_name"],
        ticker=state["ticker"].upper(),
        research_period=ResearchPeriod(start_date=state["start_date"], end_date=state["end_date"]),
        key_developments=key_developments,
        timeline=timeline,
        category_counts=category_counts,
        conflicting_signals=find_conflicts(groups),
        data_quality_notes=notes,
        uncertainties=sorted(set(uncertainties)),
    )
    return {"output": output.model_dump(), "uncertainties": uncertainties}


def build_graph():
    """Construct the deployable LangGraph state transition graph."""
    graph = StateGraph(NewsAgentState)
    graph.add_node("retrieve_news", retrieve_news_node)
    graph.add_node("filter_articles", filter_articles_node)
    graph.add_node("deduplicate", deduplicate_node)
    graph.add_node("classify_and_assess", classify_node)
    graph.add_node("summarise", summarise_node)
    graph.add_node("organise_timeline", timeline_node)
    graph.add_node("validate_output", validate_node)
    graph.set_entry_point("retrieve_news")
    graph.add_edge("retrieve_news", "filter_articles")
    graph.add_edge("filter_articles", "deduplicate")
    graph.add_edge("deduplicate", "classify_and_assess")
    graph.add_edge("classify_and_assess", "summarise")
    graph.add_edge("summarise", "organise_timeline")
    graph.add_edge("organise_timeline", "validate_output")
    graph.add_edge("validate_output", END)
    return graph.compile()


def build_agent(**kwargs):
    """Build a LangChain supervisor-compatible agent around the deterministic news graph."""
    return create_agent(
        model=init_chat_model(model),
        tools=[get_news_report],
        system_prompt=(Path(__file__).resolve().parent / "instructions.md").read_text(),
        response_format=NewsIntelligenceOutput,
        context_schema=NewsContext,
        middleware=[add_news_facts],
        name=NAME,
        **kwargs,
    )


_news_workflow = build_graph()


def resolve_request(
    company_or_ticker: str | None = None,
    ticker: str | None = None,
    start: str | None = None,
    end: str | None = None,
    context=None,
) -> tuple[str, str, str, str]:
    """Resolve supervisor context and optional tool arguments to a concrete news query."""
    context_company = getattr(context, "company_name", None) if context is not None else None
    context_date = getattr(context, "date_str", None) if context is not None else None
    if isinstance(context, dict):
        context_company = context.get("company_name")
        context_date = context.get("date_str")

    articles = load_news_feed()
    target = (ticker or company_or_ticker or context_company or "").strip()

    match = None
    for article in articles:
        target_lower = target.lower()
        if (
            target_lower
            and (
                article.ticker.lower() == target_lower
                or article.company_name.lower() == target_lower
                or target_lower in article.headline.lower()
            )
        ):
            match = article
            break
        if ticker and article.ticker.lower() == ticker.lower():
            match = article
            break

    if match is None:
        available = sorted({f"{a.company_name}/{a.ticker}" for a in articles})
        raise ValueError(f"No news data found for '{target}'. Available companies/tickers: {', '.join(available)}")

    end_date = end or context_date
    if not end_date:
        dated = [a.published_at for a in articles if a.published_at]
        end_date = max(dated)[:10] if dated else datetime.now().strftime("%Y-%m-%d")

    start_date = start
    if not start_date:
        start_date = (datetime.strptime(end_date[:10], "%Y-%m-%d") - timedelta(days=7)).strftime("%Y-%m-%d")

    return match.company_name, match.ticker, start_date, end_date[:10]


def analyse_news(
    company_name: str,
    ticker: str,
    start_date: str,
    end_date: str,
    newest_first: bool = True,
) -> NewsIntelligenceOutput:
    """Run the news workflow directly without terminal or notebook input."""
    result = _news_workflow.invoke(
        {
            "company_name": company_name,
            "ticker": ticker,
            "start_date": start_date,
            "end_date": end_date,
            "newest_first": newest_first,
        },
        config={"tags": ["news-agent"], "metadata": {"project": "finsights"}},
    )
    return NewsIntelligenceOutput.model_validate(result["output"])


@tool(parse_docstring=True)
def get_news_report(
    runtime: ToolRuntime[NewsContext],
    company_or_ticker: str | None = None,
    ticker: str | None = None,
    start: str | None = None,
    end: str | None = None,
) -> dict | str:
    """Retrieve and analyse company news for a research period.

    Args:
        company_or_ticker: Company name or ticker to analyse. Optional; uses the supervisor context by default.
        ticker: Optional explicit ticker symbol.
        start: Optional start date in YYYY-MM-DD format.
        end: Optional end date in YYYY-MM-DD format.
    """
    try:
        company, resolved_ticker, start_date, end_date = resolve_request(
            company_or_ticker, ticker, start, end, runtime.context
        )
        return analyse_news(company, resolved_ticker, start_date, end_date).model_dump()
    except (ValueError, KeyError) as error:
        return str(error)


@after_agent
def add_news_facts(state, runtime):
    """Replace model-formatted output with the facts and report from the news workflow tool call."""
    call_args = [
        call["args"]
        for message in state["messages"]
        for call in getattr(message, "tool_calls", None) or []
        if call["name"] == "get_news_report"
    ]
    args = call_args[-1] if call_args else {}
    try:
        company, ticker, start, end = resolve_request(
            args.get("company_or_ticker"),
            args.get("ticker"),
            args.get("start"),
            args.get("end"),
            runtime.context,
        )
        report = analyse_news(company, ticker, start, end)
        return {"structured_response": report}
    except (ValueError, KeyError):
        return None


agent = build_agent()
