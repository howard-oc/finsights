# lseg_vix_agent

The price volatility agent, one of the finsights agents. Given a ticker (and optionally a time window), it analyses intraday price volatility
and returns a structured `VolatilityReport` (see `schemas.py`): regime, realized volatility, period return, max
drawdown, key events, trend, a short summary and risk flags that other agents can act on.

All the maths (realized and Parkinson volatility, gaps, drawdown, z-score anomalies) is deterministic Python in
`tools/volatility.py`. The model only decides which tools to call and how to interpret the numbers.

> **Data is synthetic.** `data/prices.csv` is a generated week of 30-minute NVDA bars (16–20 Nov 2026), not real
> market data. To use other data, replace the CSV with the same columns:
> `ticker,timestamp,open,high,low,close,volume`. Add rows for more tickers; nothing else needs to change.

## Run

From the finsights repo root, install once with `uv sync`, and make sure `.env` there is filled in. Then from `agents/lseg_vix_agent/`:

```bash
uv run python agent.py NVDA                          # print the report as JSON
uv run python -m scripts.generate_synthetic_prices  # regenerate the synthetic data
uv run langgraph dev                                 # open in LangGraph Studio
```

## Use from another agent

```python
from agent import analyse_volatility, build_agent, NAME, DESCRIPTION

report = analyse_volatility("NVDA", start="2026-11-18")   # VolatilityReport (pydantic)
report.regime, report.risk_flags
```

`NAME`, `DESCRIPTION` and `build_agent()` let an orchestrator (for example a Deep Agents supervisor) register this
agent as a sub-agent.

## Layout

```
agents/lseg_vix_agent/
├── agent.py             build_agent(), analyse_volatility(), CLI entry point
├── instructions.md      system prompt: workflow, regime thresholds, rules
├── schemas.py           VolatilityReport, the structured output
├── tools/volatility.py  get_volatility_metrics, detect_price_anomalies, get_price_bars
├── utils/data.py        reads data/prices.csv
├── utils/models.py      loads the repo-root .env and MODEL_NAME
├── data/prices.csv      synthetic NVDA bars
├── scripts/generate_synthetic_prices.py
└── langgraph.json
```

Outputs are analysis only, not investment advice.
