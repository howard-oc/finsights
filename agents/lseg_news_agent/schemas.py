"""Pydantic schemas for the LSEG News Intelligence Agent."""

from typing import Literal

from pydantic import BaseModel, Field

EventCategory = Literal[
    "earnings", "M&A", "management_change", "product_technology",
    "strategic_partnership", "regulatory", "litigation", "competitor",
    "industry_macro", "other",
]
Importance = Literal["high", "medium", "low"]


class RawNewsArticle(BaseModel):
    article_id: str
    company_name: str
    ticker: str
    published_at: str | None
    headline: str
    source: str
    url: str | None = None
    snippet: str


class ResearchPeriod(BaseModel):
    start_date: str
    end_date: str


class ArticleAnalysis(BaseModel):
    article_id: str
    event_category: EventCategory
    importance: Importance
    importance_rationale: str
    summary: str = Field(description="Concise summary of at most 40 words, grounded only in the snippet.")
    why_it_matters: str


class EventGroup(BaseModel):
    event_group_id: str
    article_ids: list[str]
    headlines: list[str]
    sources: list[str]
    published_at: list[str | None]
    urls: list[str | None]
    event_category: EventCategory | None = None
    importance: Importance | None = None
    importance_rationale: str | None = None
    summary: str | None = None
    why_it_matters: str | None = None


class TimelineEvent(BaseModel):
    event_group_id: str
    published_at: list[str | None]
    sources: list[str]
    urls: list[str | None]
    article_ids: list[str]
    headlines: list[str]
    event_category: EventCategory | None = None
    importance: Importance | None = None
    summary: str | None = None
    why_it_matters: str | None = None


class KeyDevelopment(BaseModel):
    event_group_id: str
    event_category: EventCategory
    importance: Importance
    summary: str
    why_it_matters: str
    source_article_ids: list[str]


class Conflict(BaseModel):
    description: str
    article_ids: list[str]


class DataQualityNote(BaseModel):
    article_id: str | None = None
    reason: str


class NewsIntelligenceOutput(BaseModel):
    company_name: str
    ticker: str
    research_period: ResearchPeriod
    key_developments: list[KeyDevelopment]
    timeline: dict[str, list[TimelineEvent]]
    category_counts: dict[str, int]
    conflicting_signals: list[Conflict]
    data_quality_notes: list[DataQualityNote]
    uncertainties: list[str]


class ClassificationItem(BaseModel):
    article_id: str
    event_category: EventCategory
    importance: Importance
    importance_rationale: str


class NewsClassificationBatch(BaseModel):
    items: list[ClassificationItem]


class SummaryItem(BaseModel):
    article_id: str
    summary: str = Field(description="At most 40 words, using only facts stated in the supplied snippet.")
    why_it_matters: str


class NewsSummaryBatch(BaseModel):
    items: list[SummaryItem]
