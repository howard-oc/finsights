# FINSIGHTS
### Turning Market Noise into Financial Intelligence

**FSI Hackathon — London | 25 November 2026**

**Members:** Howard Hill, Josh Casswell, Mehar Mehta
**Product:** AI-Powered Company Research & Market Intelligence Copilot  
**Primary User:** Equity Research Analysts / Financial Analysts  
**Core Intelligence Pillars:** Price Intelligence · News Intelligence · Sentiment Intelligence  
**Technology:** Python · LangChain · LangGraph · Deep Agents · LangSmith

---

## 1. Overview

Financial analysts regularly deal with large volumes of information when researching publicly listed companies. This information includes company announcements, financial news, market movements, competitor developments, regulatory updates and changes in investor sentiment.

Manually collecting, filtering and connecting these different sources can be time-consuming.

**FINSIGHTS** is an AI-powered company research assistant designed to help financial analysts transform fragmented market information into structured, evidence-backed research intelligence.

Rather than simply summarising company headlines, FINSIGHTS combines three key intelligence dimensions:

1. **Price Intelligence:** Understand historical share price movements, trading volume and market performance.
2. **News Intelligence:** Retrieve, organise, classify and summarise relevant company news.
3. **Sentiment Intelligence:** Analyse the tone of financial news, identify positive and negative signals, and understand the overall narrative surrounding a company.

The system brings these findings together to identify emerging developments, highlight conflicting signals and provide analysts with a consolidated company research briefing.

### Our Vision

To help financial analysts move from information overload to informed, evidence-based research.

**Our central question:**

*"Don't just tell me what happened to this company. Help me understand what it means, what changed, and what I should investigate next."*

---

## 2. Problem Statement

Financial analysts often need to research multiple companies while monitoring large volumes of financial information.

Common challenges include:

- Information overload caused by numerous headlines and announcements.
- Repetitive reporting of the same company event across different news sources.
- Difficulty identifying the most important developments.
- Limited visibility into how company news aligns with historical share price movements.
- Difficulty understanding the overall sentiment of news coverage.
- Time spent manually comparing positive and negative developments.
- Difficulty identifying emerging risks and conflicting market signals.

Traditional news summarisation tools may condense articles into shorter summaries but do not necessarily connect news developments, price behaviour and sentiment into one cohesive research workflow.

FINSIGHTS addresses this by coordinating specialised AI components that investigate these different dimensions and consolidate their findings.

---

## 3. Product Features

### 3.1 Price Intelligence

Provides a structured overview of a company's historical market performance.

Key capabilities:

- Retrieve historical share price information.
- Calculate weekly percentage changes.
- Identify price highs and lows over a weekly.
- Analyse trading volume and unusual volume changes.
- Calculate historical volatility and returns.
- Compare company performance against a relevant market benchmark or peer.
- Highlight significant historical price movements.

**Example output:**

| Metric | Illustrative value |
|---|---:|
| Latest available price | $180 |
| Weekly change | +5.20% |
| Relative trading volume | 1.6x |
| VIX | 18.9 |

All price information should include an appropriate as-of timestamp and a clear indication of whether it is live, delayed or historical.

Price calculations should be performed using deterministic Python functions rather than relying on an LLM to perform financial arithmetic.

### 3.2 News Intelligence

Provides an organised view of relevant company news over a selected research period.

Key capabilities:

- Retrieve company-specific news headlines.
- Filter news by company, ticker and publication date.
- Remove exact duplicates and identify related coverage.
- Classify news into relevant event categories.
- Identify the importance of individual developments.
- Generate concise article-level summaries.
- Identify the most significant company developments.
- Group headlines chronologically by publication date.
- Preserve original sources, timestamps and article links.

**Example event categories:**

- Earnings and financial results.
- Mergers and acquisitions.
- Management and leadership changes.
- Product and technology announcements.
- Strategic partnerships.
- Regulatory developments.
- Litigation and legal proceedings.
- Competitor developments.
- Industry and macroeconomic developments.

**Proposed daily news structure:**

Company: Asterion Technologies  
Ticker: ASTR

**24 November 2026**
- Headline 1: Quarterly earnings announcement.
- Headline 2: New AI infrastructure partnership.
- Headline 3: Regulatory development.

**25 November 2026**
- Headline 4: Competitor announces a new AI product.
- Headline 5: Management commentary on future investment.

Each article retains its original publication timestamp and source information. Related articles can be grouped under a common event without losing the underlying source references.


### 3.3 Company Research Brief

The final output consolidates findings from all intelligence pillars.

A research brief includes:

1. Company overview and research period.
2. Executive summary.
3. Historical price performance.
4. Most significant news developments.
5. Chronological news timeline.
6. Summary observations.


The report is designed to support analyst research and independent judgement and not provide financial advice.

---

## 4. AI Agent Architecture

FINSIGHTS follows a multi-agent architecture orchestrated using LangGraph.

A Research Supervisor coordinates specialised intelligence components and combines their findings into a consolidated research report.

### 4.1 Research Supervisor Agent

**Responsibility:** Coordinate the overall research workflow.

Tasks:
- Understand the analyst's research request.
- Identify the company and relevant ticker.
- Determine the research period.
- Initialise the shared workflow state.
- Coordinate the Price, News and Sentiment components.
- Collect their outputs.
- Trigger cross-signal analysis.
- Initiate final evidence and risk validation.
- Generate the consolidated research report.

### 4.2 Price Intelligence Component

**Responsibility:** Analyse historical company price information.

Tasks:
- Retrieve historical price data.
- Calculate historical returns.
- Analyse trading volume.
- Identify significant movements.
- Compare performance against benchmarks.
- Produce structured price insights.

Primary implementation: Python analytics and LLM-assisted interpretation.

### 4.3 News Intelligence Agent

**Responsibility:** Research and summarise company news.

Tasks:
- Retrieve relevant company news.
- Filter and deduplicate articles.
- Validate publication dates and company relevance.
- Classify articles by event category.
- Assess article importance.
- Generate concise summaries.
- Explain why developments may matter.
- Organise findings chronologically.
- Preserve source traceability.

Primary implementation: LangChain agent, Python retrieval tools and structured LLM output.


### 4.3 Research Guard — Evidence and Risk Validation

**Responsibility:** Ensure the final output is appropriately sourced, balanced and within the intended product boundaries.

Tasks:
- Validate source references.
- Check article and price timestamps.
- Identify unsupported claims.
- Flag contradictory information.
- Identify missing or incomplete evidence.
- Distinguish reported facts from analytical interpretations.
- Detect investment recommendations and prohibited advice.
- Ensure the final report contains appropriate disclaimers.

This component combines deterministic Python validation with LLM-assisted review where appropriate.

### 4.7 Report Generator

**Responsibility:** Consolidate the validated findings into a structured company intelligence brief.

It should:
- Combine outputs from all intelligence components.
- Retain supporting evidence and citations.
- Present findings clearly.
- Separate facts, interpretations and uncertainties.
- Generate a concise and readable research report.


### Technology Responsibilities

| Technology | Role in SIGNAL LENS |
|---|---|
| Python | Core application logic and data processing |
| LangChain | LLM integration, prompts, tools and structured outputs |
| LangGraph | Agent orchestration, shared state and workflow control |
| Deep Agents | Optional advanced planning and delegation |
| LangSmith | Execution tracing, debugging, monitoring and evaluation |
| Pandas | Price and news data processing |
| Pydantic | Structured and validated agent outputs |
| Jupyter Notebook | Demonstration, experimentation and testing |

---

## 6. Data Architecture

The system should maintain structured records for price information, news articles and sentiment analysis.

### News Article Schema

```json
{
  "article_id": "NEWS001",
  "company_name": "Asterion Technologies",
  "ticker": "ASTR",
  "published_at": "2026-11-24T09:15:00Z",
  "headline": "Company announces quarterly results",
  "source": "Synthetic News Feed",
  "url": null,
  "snippet": "The company reported quarterly revenue growth.",
  "event_category": "earnings",
  "importance": "high",
  "summary": "..."
}
```

### Price Data Schema

```json
{
  "company_name": "Asterion Technologies",
  "ticker": "ASTR",
  "timestamp": "2026-11-24T16:00:00Z",
  "open": 175.00,
  "high": 182.00,
  "low": 174.00,
  "close": 180.00,
  "volume": 1500000,
  "currency": "USD"
}
```

All example values above are illustrative.

Original source data should be retained separately from AI-generated analysis so that downstream agents can independently validate claims.

---

## 7. LangSmith: Observability and Evaluation

LangSmith is used to inspect and evaluate the execution of SIGNAL LENS.

All team components should use a shared LangSmith project where appropriate.


### Tracing

Each research request should generate a trace containing:

- Research Supervisor execution.
- Price Intelligence execution.
- News Agent execution.
- Tool calls and returned data.

- Final report generation.

This enables inspection of inputs, outputs, model calls, execution time and errors.

### Evaluation

The team should create a synthetic evaluation dataset covering multiple company research scenarios.

Proposed evaluation criteria:

| Evaluation | What it measures |
|---|---|
| News retrieval precision | Whether retrieved articles are relevant |
| News retrieval recall | Whether expected relevant articles were retrieved |
| Deduplication | Whether repeated coverage is handled correctly |
| Date grouping | Whether articles are assigned to the correct publication date |
| Summary factuality | Whether summaries reflect their source articles |
| Source traceability | Whether important claims have verifiable sources |
| Price calculation accuracy | Whether deterministic calculations are correct |
| Advice-policy compliance | Whether prohibited recommendations are avoided |

Evaluation should be performed throughout development rather than only at the end.

---

## 8. Risk Management and Responsible AI

FINSIGHTS is intended to support professional financial research, not provide investment advice.

### Explicit Product Boundaries

FINSIGHT may:
- Summarise financial news.
- Analyse historical price data.
- Explain market developments.
- Identify reported financial and business risks.
- Compare company and benchmark performance.
- Highlight conflicting information.
- Suggest areas for additional research.

SIGNAL LENS must not:
- Recommend buying, selling or holding securities.
- Provide personalised investment recommendations.
- Suggest personal portfolio allocations.
- Generate personalised trading instructions.
- Execute financial transactions.
- Present speculative predictions as established facts.
