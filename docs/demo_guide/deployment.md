# Deploying agents to LangSmith

How finsights agents are deployed, how the hackathon template (`fsi-hackathon-london-2026`) expects its agents to be
deployed, and how to check a deployment works.

## How deployment works

finsights has one `agents/langgraph.json` for all its agents (the template has one per agent). The LangGraph CLI reads it, builds a container
image that wraps the agent in the LangGraph API server (threads, state, streaming and human-in-the-loop are handled
for you), and deploys it to LangSmith, which gives each agent a hosted API URL.

```json
{
  "dependencies": ["."],                          // what to install: agents/ + agents/requirements.txt
  "graphs": {                                     // graph name -> file:variable to serve
    "price_intelligence_agent": "./price_intelligence_agent/agent.py:agent"
  },
  "env": "../.env",                               // env vars sent to the deployment (API keys, MODEL_NAME)
  "python_version": "3.12"
}
```

| Command | What it does | Needs Docker? |
|---|---|---|
| `uv run langgraph validate` | Checks `langgraph.json` | No |
| `uv run langgraph dev` | Local API server + LangGraph Studio UI | No |
| `uv run langgraph dockerfile <path>` | Writes the Dockerfile the build will use, to inspect it | No |
| `uv run langgraph deploy --name <name>` | Builds the image and deploys it to LangSmith | No: builds remotely in LangSmith if Docker isn't installed |
| `uv run langgraph deploy list` | Lists deployments and their URLs | No |
| `uv run langgraph deploy delete <id> --force` | Deletes a deployment | No |

Notes:
- The build does **not** use `uv sync` or `uv.lock`. It installs the agent folder's own dependency file
  (`requirements.txt` here) against the LangGraph base image's constraints, so pin anything that matters there.
- Only the `agents/` folder is uploaded. The `.env` file is not copied into the image; its **values** are sent as
  deployment settings, including your LangSmith API key (the agent needs it to reach the model gateway).
- `deploy list` and `deploy delete` read `.env` from the current folder only, so load the root one into the shell
  first (see below).

## finsights: price_intelligence_agent

Deployed name: `price-intelligence-agent`
URL: https://price-intelligence-agent-e7c81654e512554a9066d0a40d3aac6a.us.langgraph.app

### Deploy or update

From the repo root, with `.env` filled in:

```bash
cd agents
uv run langgraph validate
set -a && source ../.env && set +a           # make the API key visible to the CLI
uv run langgraph deploy --name price-intelligence-agent
```

New agents (for example the supervisor) are added as more entries under `graphs`; they then deploy together.

Running the same command again updates the existing deployment. A remote build takes about 3 minutes
(queued -> building -> deploying). If you stop the command locally, LangSmith keeps building anyway.

### Test the hosted agent

```python
import os
from dotenv import load_dotenv
from langgraph_sdk import get_sync_client

load_dotenv(".env")  # repo root
client = get_sync_client(
    url="https://price-intelligence-agent-e7c81654e512554a9066d0a40d3aac6a.us.langgraph.app",
    api_key=os.environ["LANGSMITH_API_KEY"],
)
out = client.runs.wait(
    None,  # no thread: a one-off run
    "price_intelligence_agent",  # the graph name from langgraph.json
    input={"messages": [{"role": "user", "content": "How did Nvidia trade last week?"}]},
)
report = out["structured_response"]  # PriceIntelligenceReport as a dict
print(report["regime"], report["latest_price"], report["relative_performance_pct"])
```

Expected for the synthetic NVDA week: `elevated`, `192.93`, `4.18`.

Runs on the hosted agent are traced in LangSmith under the project `price-intelligence-agent-production`.

### Remove it

```bash
cd agents
set -a && source ../.env && set +a
uv run langgraph deploy list                      # find the deployment ID
uv run langgraph deploy delete <deployment-id> --force
```

Deleting a deployment does not delete its tracing project; delete that separately in LangSmith if needed.

## The hackathon template (fsi-hackathon-london-2026)

The template's agents were only run locally in this project; none were deployed. The template suggests two routes:

| Topic | Suggested command | What it does |
|---|---|---|
| `01_kyc_agent` | `uv run langgraph deploy` | Same as finsights: reads `langgraph.json`, builds, deploys to LangSmith |
| `02_transaction_monitoring_agent`, `03_document_summary_agent` | `uv run mda deploy` | Managed Deep Agents: compiles the `agent` in `agent.py` into a Deep Agent and deploys it to LangSmith as a managed agent. `uv run mda dev` runs it locally first; `mda logs` tails logs |

`mda` reads `.env` from the topic folder, not the repo root, so copy it first:

```bash
cd fsi-hackathon-london-2026/02_transaction_monitoring_agent
cp ../.env .env
uv run mda deploy          # or: uv run langgraph deploy --name transaction-monitoring-agent
```

The transaction monitoring agent pauses for human review (`interrupt()`); a LangSmith deployment provides the
checkpointer that needs, so it works hosted without code changes.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `403 Forbidden` from LangSmith, `401 Unauthorized` from the model | API key in `.env` is wrong. Check for leftover `<...>` placeholder brackets around the value |
| `No LangSmith API key found` from `deploy list` / `delete` | The CLI didn't see the root `.env`: run `set -a && source ../.env && set +a` from `agents/` first |
| Build fails on missing packages | The agent folder has no `requirements.txt` / `pyproject.toml`, or a package is missing from it |
| `ModuleNotFoundError: price_intelligence_agent` | Run from `agents/` (or put `agents/` on `sys.path`), and use full imports like `from price_intelligence_agent.utils import data` |
| A stopped deploy still created a deployment | Expected: the remote build carries on. Check `deploy list` and delete it if unwanted |
