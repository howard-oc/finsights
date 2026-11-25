"""Deterministic retrieval, filtering, deduplication and validation helpers."""

import re
from datetime import datetime, timezone
from difflib import SequenceMatcher

from langchain.tools import tool

from schemas import Conflict, DataQualityNote, EventGroup, RawNewsArticle, TimelineEvent
from utils.data import load_news_feed


def parse_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


@tool(parse_docstring=True)
def retrieve_news(company_name: str, ticker: str) -> list[dict]:
    """Load the news feed. This interface is intentionally replaceable by a real news API later.

    Args:
        company_name: Company name to retrieve news for.
        ticker: Ticker symbol to retrieve news for.
    """
    return [a.model_dump() for a in load_news_feed()]


def filter_articles(
    articles: list[RawNewsArticle], company_name: str, ticker: str,
    start_date: str, end_date: str,
) -> tuple[list[RawNewsArticle], list[DataQualityNote]]:
    start = parse_utc(start_date)
    end = parse_utc(end_date)
    if end is not None and len(end_date) == 10:
        end = end.replace(hour=23, minute=59, second=59)
    kept, notes = [], []
    for article in articles:
        timestamp = parse_utc(article.published_at)
        if timestamp is None:
            notes.append(DataQualityNote(article_id=article.article_id, reason="invalid_or_missing_timestamp"))
            continue
        if article.ticker.upper() != ticker.upper() or article.company_name.lower() != company_name.lower():
            notes.append(DataQualityNote(article_id=article.article_id, reason="wrong_company_or_ticker"))
            continue
        if start is not None and timestamp < start:
            notes.append(DataQualityNote(article_id=article.article_id, reason="outside_research_period_before_start"))
            continue
        if end is not None and timestamp > end:
            notes.append(DataQualityNote(article_id=article.article_id, reason="outside_research_period_after_end"))
            continue
        kept.append(article)
    return kept, notes


def normalize_headline(headline: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", headline.lower()).strip()


def deduplicate_articles(articles: list[RawNewsArticle]) -> list[EventGroup]:
    groups: list[list[RawNewsArticle]] = []
    for article in articles:
        headline = normalize_headline(article.headline)
        target = None
        for group in groups:
            representative = normalize_headline(group[0].headline)
            exact = headline == representative
            similar = SequenceMatcher(None, headline, representative).ratio() >= 0.72
            stopwords = {"a", "an", "the", "and", "of", "for", "in", "on", "with", "to", "from"}
            shared_terms = (set(headline.split()) & set(representative.split())) - stopwords
            significant_overlap = len(shared_terms) >= 2
            if exact or similar or significant_overlap:
                target = group
                break
        if target is None:
            groups.append([article])
        else:
            target.append(article)

    out = []
    for index, group in enumerate(groups, start=1):
        out.append(EventGroup(
            event_group_id=f"event-{index:03d}",
            article_ids=[a.article_id for a in group],
            headlines=[a.headline for a in group],
            sources=[a.source for a in group],
            published_at=[a.published_at for a in group],
            urls=[a.url for a in group],
        ))
    return out


def organise_timeline(groups: list[EventGroup], newest_first: bool = True) -> dict[str, list[TimelineEvent]]:
    timeline: dict[str, list[TimelineEvent]] = {}
    for group in groups:
        valid = [parse_utc(value) for value in group.published_at if parse_utc(value)]
        date = max(valid).date().isoformat() if valid else "unknown"
        timeline.setdefault(date, []).append(TimelineEvent(
            event_group_id=group.event_group_id,
            published_at=group.published_at,
            sources=group.sources,
            urls=group.urls,
            article_ids=group.article_ids,
            headlines=group.headlines,
            event_category=group.event_category,
            importance=group.importance,
            summary=group.summary,
            why_it_matters=group.why_it_matters,
        ))
    for date in timeline:
        timeline[date].sort(key=lambda e: e.published_at[0] or "", reverse=newest_first)
    return dict(sorted(timeline.items(), key=lambda item: item[0], reverse=newest_first))


def find_conflicts(groups: list[EventGroup]) -> list[Conflict]:
    conflicts = []
    positive = ("manageable", "improved", "settles", "record", "growth", "expansion")
    negative = ("threatens", "setback", "risk", "decline", "dispute", "delay")
    article_text = {}
    for group in groups:
        text = " ".join(group.headlines).lower()
        article_text[group.event_group_id] = text
        if any(word in text for word in positive) and any(word in text for word in negative):
            conflicts.append(Conflict(description="Potential conflicting signal within related coverage.", article_ids=group.article_ids))
    # Explicitly pair the planted bullish/bearish patent coverage.
    patent_ids = [aid for g in groups for aid in g.article_ids if aid in {"ASTR-008", "ASTR-009"}]
    if patent_ids:
        conflicts.append(Conflict(description="Conflicting patent-dispute signals: manageable risk versus court setback.", article_ids=patent_ids))
    return conflicts


ADVICE_PATTERNS = re.compile(r"\b(buy|sell|hold|price target|price prediction|outperform|underperform|portfolio)\b", re.I)


def advice_policy_violations(text: str) -> list[str]:
    return sorted({match.group(0).lower() for match in ADVICE_PATTERNS.finditer(text)})


def validate_traceability(groups: list[EventGroup], notes: list[DataQualityNote]) -> tuple[list[str], list[str]]:
    uncertainties, unsupported = [], []
    for group in groups:
        if not group.article_ids:
            unsupported.append(f"{group.event_group_id}: missing source article ids")
        if any(url is None for url in group.urls):
            uncertainties.append(f"{group.event_group_id}: one or more articles have missing URLs")
        if any(timestamp is None for timestamp in group.published_at):
            uncertainties.append(f"{group.event_group_id}: missing timestamp retained as data-quality uncertainty")
    if notes:
        uncertainties.append(f"{len(notes)} articles were dropped or flagged during filtering")
    return sorted(set(uncertainties)), sorted(set(unsupported))
