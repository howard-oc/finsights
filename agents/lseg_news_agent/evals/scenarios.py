"""Labelled deterministic eval cases for the synthetic Asterion news feed."""

SCENARIOS = [
    {
        "name": "retrieval_precision",
        "inputs": {"company_name": "Asterion Technologies", "ticker": "ASTR", "start_date": "2026-11-18", "end_date": "2026-11-25"},
        "expected": {"exclude_article_ids": ["ASTR-017", "ASTR-018", "ASTR-019", "ASTR-020", "ASTR-021", "ASTR-022"]},
    },
    {
        "name": "exact_duplicate",
        "inputs": {"company_name": "Asterion Technologies", "ticker": "ASTR", "start_date": "2026-11-18", "end_date": "2026-11-25"},
        "expected": {"duplicate_article_ids": ["ASTR-001", "ASTR-004", "ASTR-005", "ASTR-023"]},
    },
    {
        "name": "near_duplicate_partnership",
        "inputs": {"company_name": "Asterion Technologies", "ticker": "ASTR", "start_date": "2026-11-18", "end_date": "2026-11-25"},
        "expected": {"related_article_ids": ["ASTR-006", "ASTR-007"]},
    },
    {
        "name": "conflicting_patent_signals",
        "inputs": {"company_name": "Asterion Technologies", "ticker": "ASTR", "start_date": "2026-11-18", "end_date": "2026-11-25"},
        "expected": {"conflict_article_ids": ["ASTR-008", "ASTR-009"]},
    },
]


def build_examples():
    return [{"inputs": s["inputs"], "outputs": s["expected"], "metadata": {"scenario": s["name"]}} for s in SCENARIOS]
