"""JSON-backed raw news feed loader."""

import json
import os
from pathlib import Path

from lseg_news_agent.schemas import RawNewsArticle

NEWS_JSON = Path(os.environ.get("LSEG_NEWS_JSON") or Path(__file__).resolve().parent.parent / "data" / "news.json")


def load_news_feed() -> list[RawNewsArticle]:
    with NEWS_JSON.open(encoding="utf-8") as handle:
        return [RawNewsArticle.model_validate(row) for row in json.load(handle)]
