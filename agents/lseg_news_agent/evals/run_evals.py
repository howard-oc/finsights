"""Rule-based and optional LangSmith evaluation for the News Intelligence Agent.

Run locally:
    uv run python -m evals.run_evals

Optional LangSmith synchronization:
    Set LANGSMITH_API_KEY and run with LangSmith enabled.
"""

import os as _os
from pathlib import Path as _Path

# Pin the synthetic feed: these checks are written against the Asterion articles in data/news.json.
_os.environ["LSEG_NEWS_JSON"] = str(_Path(__file__).resolve().parent.parent / "data" / "news.json")

import os
from dataclasses import dataclass

from agent import analyse_news
from evals.scenarios import build_examples
from tools.news import advice_policy_violations


@dataclass
class ScoreRow:
    scenario: str
    retrieval_precision: float
    date_grouping: float
    deduplication: float
    source_traceability: float
    advice_policy: float


def evaluate_one(example: dict) -> dict:
    inputs = example["inputs"]
    expected = example["outputs"]
    report = analyse_news(**inputs)

    timeline_ids = {
        article_id
        for events in report.timeline.values()
        for event in events
        for article_id in event.article_ids
    }

    exclude = set(expected.get("exclude_article_ids", []))
    retrieval = 1.0 if not (timeline_ids & exclude) else 0.0

    date_ok = all(date.startswith("2026-11-") or date == "unknown" for date in report.timeline)

    duplicate_ids = set(expected.get("duplicate_article_ids", []))
    related_ids = set(expected.get("related_article_ids", []))
    conflict_ids = set(expected.get("conflict_article_ids", []))

    def grouped(ids: set[str]) -> bool:
        if not ids:
            return True
        for events in report.timeline.values():
            for event in events:
                if ids <= set(event.article_ids):
                    return True
        return False

    dedup = grouped(duplicate_ids) and grouped(related_ids)

    trace_ok = all(development.source_article_ids for development in report.key_developments)
    all_text = " ".join(development.summary + " " + development.why_it_matters for development in report.key_developments)
    advice_ok = not advice_policy_violations(all_text)

    conflict_ok = True
    if conflict_ids:
        conflict_ok = any(conflict_ids <= set(conflict.article_ids) for conflict in report.conflicting_signals)

    return {
        "retrieval_precision": retrieval,
        "date_grouping": float(date_ok),
        "deduplication": float(bool(dedup and (conflict_ok))),
        "source_traceability": float(trace_ok),
        "advice_policy": float(advice_ok),
    }


def main():
    rows = []
    totals = {key: [] for key in ["retrieval_precision", "date_grouping", "deduplication", "source_traceability", "advice_policy"]}
    for example in build_examples():
        scores = evaluate_one(example)
        scenario = example["metadata"]["scenario"]
        for key, value in scores.items():
            totals[key].append(value)
        print(f"{scenario:<32} " + " ".join(f"{key[:8]}={value:.2f}" for key, value in scores.items()))
        rows.append(scores)

    print("\nMEAN")
    for key, values in totals.items():
        print(f"{key:<24} {sum(values) / len(values):.2f}")

    if os.environ.get("LANGSMITH_API_KEY"):
        try:
            from langsmith import Client
            attendee = os.environ.get("ATTENDEE_NAME", "anon")
            dataset_name = f"lseg-news-agent-scenarios-{attendee}"
            client = Client()
            if client.has_dataset(dataset_name=dataset_name):
                dataset = client.read_dataset(dataset_name=dataset_name)
            else:
                dataset = client.create_dataset(dataset_name, description="Synthetic NVDA news agent scenarios")
            client.create_examples(dataset_id=dataset.id, examples=build_examples())
            print(f"Synced LangSmith dataset: {dataset_name}")
        except Exception as exc:
            print(f"LangSmith sync skipped: {exc}")


if __name__ == "__main__":
    main()
