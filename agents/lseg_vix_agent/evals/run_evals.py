"""Run lseg_vix_agent against the scenario dataset in LangSmith and score it.

Creates (or reuses) the dataset `lseg-vix-agent-scenarios-<ATTENDEE_NAME>`, runs the agent on every example and
records an experiment with these scores:
  regime_correct      exact regime match (1/0)
  regime_within_one   regime at most one step off (1/0)
  trend_correct       trend matches (1/0)
  flag_recall         share of the planted flags the agent raised
  false_alarms        1 if the agent raised a flag that is neither expected nor acceptable, else 0 (lower is better)
  vol_grounded        realized vol in the report matches the tool's number within 0.5 points (hallucination check)

Run from agents/lseg_vix_agent:  uv run python -m evals.run_evals [experiment-prefix]
"""

import os
import sys

from evals.scenarios import EVAL_CSV, REGIMES, build

os.environ["LSEG_VIX_PRICES_CSV"] = str(EVAL_CSV)  # before the agent's tools are imported

from langsmith import Client  # noqa: E402

from agent import agent  # noqa: E402

ATTENDEE = os.environ.get("ATTENDEE_NAME", "anon")
DATASET = f"lseg-vix-agent-scenarios-{ATTENDEE}"


def sync_dataset(client: Client) -> str:
    """Create the dataset, or replace its examples so they match the current scenarios."""
    examples = build()
    if client.has_dataset(dataset_name=DATASET):
        ds = client.read_dataset(dataset_name=DATASET)
        old = [e.id for e in client.list_examples(dataset_id=ds.id)]
        if old:
            client.delete_examples(example_ids=old)
    else:
        ds = client.create_dataset(
            DATASET, description="Synthetic price weeks with planted volatility patterns and expected reports."
        )
    client.create_examples(dataset_id=ds.id, examples=examples)
    return DATASET


def target(inputs: dict) -> dict:
    result = agent.invoke(
        {"messages": [{"role": "user", "content": f"Analyse price volatility for {inputs['ticker']}."}]}
    )
    return result["structured_response"].model_dump()


def regime_correct(outputs: dict, reference_outputs: dict) -> bool:
    return outputs["regime"] == reference_outputs["regime"]


def regime_within_one(outputs: dict, reference_outputs: dict) -> bool:
    return abs(REGIMES.index(outputs["regime"]) - REGIMES.index(reference_outputs["regime"])) <= 1


def trend_correct(outputs: dict, reference_outputs: dict) -> bool:
    return outputs["trend"] == reference_outputs["trend"]


def flag_recall(outputs: dict, reference_outputs: dict) -> float:
    expected = set(reference_outputs["flags"])
    return 1.0 if not expected else len(expected & set(outputs["risk_flags"])) / len(expected)


def false_alarms(outputs: dict, reference_outputs: dict) -> dict:
    allowed = set(reference_outputs["flags"]) | set(reference_outputs["acceptable_flags"])
    extra = sorted(set(outputs["risk_flags"]) - allowed)
    return {"key": "false_alarms", "score": int(bool(extra)), "comment": ", ".join(extra) or "none"}


def vol_grounded(outputs: dict, reference_outputs: dict) -> bool:
    return abs(outputs["realized_vol_annualized_pct"] - reference_outputs["realized_vol_annualized_pct"]) <= 0.5


EVALUATORS = [regime_correct, regime_within_one, trend_correct, flag_recall, false_alarms, vol_grounded]


def main(prefix: str = "baseline") -> None:
    client = Client()
    dataset = sync_dataset(client)
    results = client.evaluate(
        target,
        data=dataset,
        evaluators=EVALUATORS,
        experiment_prefix=f"lseg-vix-{prefix}",
        metadata={"agent": "lseg_vix_agent", "model": os.environ.get("MODEL_NAME")},
        max_concurrency=4,
    )
    print(f"\nExperiment: {results.experiment_name}")
    rows = list(results)
    keys = [e.__name__ for e in EVALUATORS]
    print(f"{'ticker':<9}" + "".join(f"{k:>18}" for k in keys))
    totals = {k: [] for k in keys}
    for r in sorted(rows, key=lambda r: r["example"].inputs["ticker"]):
        scores = {e.key: e.score for e in r["evaluation_results"]["results"]}
        for k in keys:
            totals[k].append(float(scores.get(k, 0)))
        print(f"{r['example'].inputs['ticker']:<9}" + "".join(f"{float(scores.get(k, 0)):>18.2f}" for k in keys))
    print(f"{'MEAN':<9}" + "".join(f"{sum(v) / len(v):>18.2f}" for v in totals.values()))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "baseline")
