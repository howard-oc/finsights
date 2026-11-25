"""News Intelligence Agent: standalone LangGraph workflow for company news."""

import sys
from typing import TypedDict

from langchain.chat_models import init_chat_model
from langgraph.graph import END, StateGraph

from prompts import ADVICE_GUARDRAIL, CLASSIFICATION_PROMPT, SUMMARY_PROMPT
from schemas import (
    DataQualityNote, EventGroup, KeyDevelopment, NewsClassificationBatch,
    NewsIntelligenceOutput, NewsSummaryBatch, RawNewsArticle, ResearchPeriod,
)
from tools.news import (
    advice_policy_violations, deduplicate_articles, filter_articles,
    find_conflicts, organise_timeline, retrieve_news, validate_traceability,
)
from utils.models import model

NAME = "lseg_news_agent"
DESCRIPTION = "Retrieves, deduplicates, classifies, summarises and chronologically organises company news with source traceability."


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
    """VIX-style public graph factory for LangGraph and supervisors."""
    return build_graph()


agent = build_agent()  # registered in langgraph.json


def analyse_news(company_name: str, ticker: str, start_date: str, end_date: str, newest_first: bool = True) -> NewsIntelligenceOutput:
    result = agent.invoke({
        "company_name": company_name,
        "ticker": ticker,
        "start_date": start_date,
        "end_date": end_date,
        "newest_first": newest_first,
    }, config={"tags": ["news-agent"], "metadata": {"project": "finsights"}})
    return NewsIntelligenceOutput.model_validate(result["output"])


if __name__ == "__main__":
    company = sys.argv[1] if len(sys.argv) > 1 else "Asterion Technologies"
    ticker = sys.argv[2] if len(sys.argv) > 2 else "ASTR"
    start = sys.argv[3] if len(sys.argv) > 3 else "2026-11-18"
    end = sys.argv[4] if len(sys.argv) > 4 else "2026-11-25"
    print(analyse_news(company, ticker, start, end).model_dump_json(indent=2))
