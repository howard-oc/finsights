"""JSON-backed raw news feed loader."""

import json
import os
from pathlib import Path

from lseg_news_agent.schemas import RawNewsArticle

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
REAL_NEWS_JSON = DATA_DIR / "real" / "news.json"  # real public NVDA reports (default)
SYNTHETIC_NEWS_JSON = DATA_DIR / "news.json"  # synthetic Asterion feed used by the evals and tests

NEWS_JSON = Path(os.environ.get("LSEG_NEWS_JSON") or REAL_NEWS_JSON)


def load_news_feed() -> list[RawNewsArticle]:
    with NEWS_JSON.open(encoding="utf-8") as handle:
        return [RawNewsArticle.model_validate(row) for row in json.load(handle)]
