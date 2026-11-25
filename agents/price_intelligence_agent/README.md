# lseg_price_intelligence_agent

> **Names:** the agent is called `lseg_price_intelligence_agent` (in LangSmith traces, the graph in `agents/langgraph.json`
> and the `lseg-price-intelligence-agent` deployment). Its Python package and folder stay `price_intelligence_agent`, so
> imports are `from price_intelligence_agent.agent import ...`.

The **Price Intelligence** component of finsights (root README, sections 3.1 and 4.2). Given a ticker or company
name, and optionally a time window, it returns a structured `PriceIntelligenceReport` (see `schemas.py`) that the
Research Supervisor and other agents consume.

| Report section | Fields |
|---|---|
| Identity and provenance | ticker, company_name, currency, exchange, as_of (UTC), data_status (live/delayed/historical), data_source, window |
| Performance | latest_price, period_return_pct, period_high/low with timestamps |
| Volume | total_volume, relative_volume (latest session vs earlier average), unusual_volume_days |
| Benchmark and market | benchmark_ticker, benchmark_return_pct, relative_performance_pct, vix_latest, vix_change |
| Volatility | realized and Parkinson vol, max drawdown, largest overnight gap, regime (+ reasons), trend, risk_flags |
| Narrative (the model) | key_events, summary |

**How it works.** The agent has one tool, `get_price_report`, which takes a company name or ticker and returns
every fact above, worked out in plain Python (`tools/prices.py`, `utils/metrics.py`), as the root README requires.
A request is one tool call and one answer. The model writes only the key events and summary (`PriceNarrative`); the
`add_price_facts` hook in `agent.py` puts the code's numbers, regime, trend and flags into the final report, so the
model can't get them wrong. The thresholds for regime, trend and flags are constants at the top of
`utils/metrics.py`.

> **Data is synthetic.** `data/` holds a generated week (16-20 Nov 2026) of 30-minute bars for NVDA and its benchmark
> QQQ, daily VIX closes and instrument reference data. It is not real market data, and reports say
> `data_source: synthetic`, `data_status: historical`. To use other data, replace the CSVs with the same columns.

## Run

From the finsights repo root, install once with `uv sync` and make sure `.env` there is filled in. Everything runs
from the `agents/` folder, which is the import root for all finsights agents (the supervisor notebook uses it too):

```bash
cd agents
uv run python -m price_intelligence_agent.agent NVDA                          # print the report as JSON
uv run python -m price_intelligence_agent.scripts.generate_synthetic_prices  # regenerate the synthetic data
uv run langgraph dev                                                         # open in LangGraph Studio
```

`agents/langgraph.json` and `agents/requirements.txt` are shared by all agents in `agents/`. To deploy, see
`docs/demo_guide/deployment.md`.

## Use from the supervisor

The supervisor (`agents/supervisor_agent/supervisor.ipynb`) puts `agents/` on `sys.path`, so it can import this agent
directly and use it as a tool. It runs in the same process, so the whole run is one LangSmith trace with the price
agent nested inside.

```python
from price_intelligence_agent.agent import price_intelligence   # a LangChain tool

agent = create_agent(model=model, context_schema=InvestigationContext,
                     tools=[get_company, get_date, price_intelligence])
```

Or call it directly:

```python
from price_intelligence_agent.agent import analyse_price

report = analyse_price("Nvidia")      # PriceIntelligenceReport (pydantic); raises ValueError if there's no data
report.regime, report.relative_performance_pct, report.risk_flags
```

Inside this agent every import is written in full (`from price_intelligence_agent.utils import data`), so its
`utils`, `tools` and so on never clash with `agents/utils` or another agent's modules.

## Evals (LangSmith)

```bash
cd agents
uv run python -m price_intelligence_agent.evals.run_evals <experiment-name>
```

Dataset `lseg-price-intelligence-scenarios-<ATTENDEE_NAME>`: seven synthetic weeks with planted patterns (calm, normal,
earnings gap, intraday reversal, crash, cooling off, extreme) plus NVDA, with expected regime, trend and flags
computed from the data. Checks: regime, trend, flag recall, false alarms, volatility grounded, no investment advice,
summary agrees with regime, provenance stated.

| Experiment | What changed | Regime | Trend | False alarms | Median latency | Cost (8 runs) |
|---|---|---|---|---|---|---|
| baseline | model decides regime/trend/flags | 62% | 62% | 25% of runs | 9.8s | $0.0074 |
| v2 | rules moved into code | 100% | 100% | 0 | 9.3s | $0.0058 |
| v3 | full price intelligence report | 100% | 100% | 0 | 10.2s | $0.0080 |
| v4 | one tool, one call | 100% | 100% | 0 | 5.3s | $0.0040 |
| v5 | full-path imports, callable from the supervisor | 100% | 100% | 0 | — | — |

## Layout

```
agents/price_intelligence_agent/
├── agent.py              build_agent(), analyse_price(), add_price_facts hook
├── instructions.md       system prompt
├── schemas.py            PriceNarrative (model output), PriceIntelligenceReport (full report)
├── tools/prices.py       get_price_report: the one tool
├── utils/metrics.py      volatility maths and the regime / trend / flag rules
├── utils/data.py         reads data/*.csv
├── utils/models.py       loads the repo-root .env and MODEL_NAME
├── data/                 prices.csv, vix.csv, instruments.csv, eval_prices.csv (all synthetic)
├── evals/                scenarios.py (dataset), run_evals.py (experiments)
├── scripts/generate_synthetic_prices.py
└── (langgraph.json and requirements.txt live one level up, in agents/)
```

Outputs are analysis only, not investment advice.
