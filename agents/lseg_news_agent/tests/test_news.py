import json
from pathlib import Path

from schemas import RawNewsArticle
from tools.news import (
    advice_policy_violations,
    deduplicate_articles,
    filter_articles,
    organise_timeline,
    parse_utc,
)

DATA = Path(__file__).resolve().parent.parent / "data" / "news.json"


def load_articles():
    return [RawNewsArticle.model_validate(row) for row in json.loads(DATA.read_text())]


def test_synthetic_feed_has_planted_cases():
    articles = load_articles()
    assert len(articles) == 30
    headlines = [a.headline for a in articles]
    assert "Asterion reports record cloud revenue" in headlines
    assert sum(a.headline == "Asterion reports record cloud revenue" for a in articles) >= 3
    assert any(a.ticker != "ASTR" for a in articles)
    assert any(a.published_at is None or a.published_at == "not-a-timestamp" for a in articles)


def test_filter_keeps_only_requested_ticker_company_and_dates():
    kept, notes = filter_articles(
        load_articles(), "Asterion Technologies", "ASTR", "2026-11-18", "2026-11-25"
    )
    assert kept
    assert all(a.ticker == "ASTR" for a in kept)
    assert all(a.company_name == "Asterion Technologies" for a in kept)
    assert all(parse_utc(a.published_at) is not None for a in kept)
    assert any(n.reason == "invalid_or_missing_timestamp" for n in notes)
    assert any(n.reason == "wrong_company_or_ticker" for n in notes)
    assert any(n.reason.startswith("outside_research_period") for n in notes)


def test_exact_and_near_duplicate_groups_keep_every_source():
    groups = deduplicate_articles(load_articles()[0:9])
    earnings = next(g for g in groups if "Asterion reports record cloud revenue" in g.headlines)
    assert set(earnings.article_ids) >= {"ASTR-001", "ASTR-004", "ASTR-005"}
    assert len(earnings.sources) == len(earnings.article_ids)


def test_timeline_groups_dates_and_dedicated_unknown_group():
    kept, _ = filter_articles(load_articles(), "Asterion Technologies", "ASTR", "2026-11-18", "2026-11-25")
    groups = deduplicate_articles(kept)
    timeline = organise_timeline(groups, newest_first=True)
    assert "2026-11-25" in timeline
    assert list(timeline)[0] == "2026-11-25"
    assert all(date == "unknown" or parse_utc(date + "T00:00:00Z") is not None for date in timeline)


def test_advice_post_check_flags_prohibited_language():
    assert advice_policy_violations("You should buy this stock and hold it") == ["buy", "hold"]
    assert advice_policy_violations("This is an interpreted research signal") == []
