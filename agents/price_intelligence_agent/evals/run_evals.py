"""Run the agent on the scenario dataset in LangSmith and score it.

    cd agents && uv run python -m price_intelligence_agent.evals.run_evals <experiment-name>

Every score is 1 for good, 0 for bad:
  regime_correct, regime_within_one, trend_correct   the report's decisions match the expected ones
  flag_recall                                        share of the planted risk flags that were raised
  no_false_alarms                                    every flag raised is planted, acceptable or true of the data
  vol_grounded                                       realized vol matches the expected value (no made-up numbers)
  no_investment_advice                               no buy/sell/hold recommendation or price target in the text
  summary_mentions_regime                            the written summary agrees with the regime
  provenance_stated                                  UTC as-of time and live/delayed/historical are given
"""

import os
import re
import sys

from price_intelligence_agent.evals.scenarios import EVAL_CSV, build

os.environ["PRICE_INTEL_PRICES_CSV"] = str(EVAL_CSV)  # must be set before the agent is imported

from langsmith import Client  # noqa: E402

from price_intelligence_agent.agent import agent  # noqa: E402
from price_intelligence_agent.utils.metrics import REGIMES  # noqa: E402

DATASET = f"price-intelligence-scenarios-{os.environ.get('ATTENDEE_NAME', 'anon')}"


def sync_dataset(client: Client) -> None:
    """Create the dataset, add new scenarios and update changed ones. Never deletes, so old experiments still line up."""
    if not client.has_dataset(dataset_name=DATASET):
        client.create_dataset(DATASET, description="Synthetic price weeks with planted patterns and expected reports.")
    existing = {e.inputs["ticker"]: e for e in client.list_examples(dataset_name=DATASET)}
    for example in build():
        old = existing.get(example["inputs"]["ticker"])
        if old is None:
            client.create_examples(dataset_name=DATASET, examples=[example])
        elif old.outputs != example["outputs"]:
            client.update_example(old.id, outputs=example["outputs"], metadata=example["metadata"])


def target(inputs: dict) -> dict:
    message = {"role": "user", "content": f"Analyse the price of {inputs['ticker']}."}
    return agent.invoke({"messages": [message]})["structured_response"].model_dump()


def regime_correct(outputs: dict, reference_outputs: dict) -> bool:
    return outputs["regime"] == reference_outputs["regime"]


def regime_within_one(outputs: dict, reference_outputs: dict) -> bool:
    return abs(REGIMES.index(outputs["regime"]) - REGIMES.index(reference_outputs["regime"])) <= 1


def trend_correct(outputs: dict, reference_outputs: dict) -> bool:
    return outputs["trend"] == reference_outputs["trend"]


def flag_recall(outputs: dict, reference_outputs: dict) -> float:
    expected = set(reference_outputs["flags"])
    return len(expected & set(outputs["risk_flags"])) / len(expected) if expected else 1.0


def no_false_alarms(outputs: dict, reference_outputs: dict) -> dict:
    allowed = set(reference_outputs["flags"]) | set(reference_outputs["acceptable_flags"])
    if reference_outputs["max_drawdown_pct"] < -5:
        allowed.add("drawdown_over_5pct")  # true of the data even if not planted
    if reference_outputs["range_expansion_ratio"] >= 1.5:
        allowed.add("range_expansion")
    extra = sorted(set(outputs["risk_flags"]) - allowed)
    return {"key": "no_false_alarms", "score": int(not extra), "comment": ", ".join(extra) or "none"}


def vol_grounded(outputs: dict, reference_outputs: dict) -> bool:
    return abs(outputs["realized_vol_annualized_pct"] - reference_outputs["realized_vol_annualized_pct"]) <= 0.5


# Recommendation language. Descriptions like "sell-off" or "selling pressure" are fine.
ADVICE = re.compile(
    r"\b(should|could|might want to|consider|recommend\w*|suggest\w*|advis\w*)\s+"
    r"(buy|sell|hold|buying|selling|holding|accumulat\w+|trim\w*|exit\w*)\b"
    r"|\b(buy|sell|hold|outperform|underperform|overweight|underweight)\s+rating\b"
    r"|\bprice\s+target\b|\btarget\s+price\b|\b(go|going)\s+(long|short)\b|\bstrong\s+buy\b",
    re.IGNORECASE,
)


def no_investment_advice(outputs: dict) -> dict:
    text = " ".join([outputs["summary"]] + [e["description"] for e in outputs["key_events"]])
    hit = ADVICE.search(text)
    return {"key": "no_investment_advice", "score": int(hit is None), "comment": hit.group(0) if hit else "none"}


def summary_mentions_regime(outputs: dict) -> bool:
    return outputs["regime"] in outputs["summary"].lower()


def provenance_stated(outputs: dict) -> bool:
    return (outputs.get("as_of") or "").endswith("Z") and outputs.get("data_status") in ("live", "delayed", "historical")


EVALUATORS = [
    regime_correct, regime_within_one, trend_correct, flag_recall, no_false_alarms,
    vol_grounded, no_investment_advice, summary_mentions_regime, provenance_stated,
]


if __name__ == "__main__":
    client = Client()
    sync_dataset(client)
    results = client.evaluate(
        target,
        data=DATASET,
        evaluators=EVALUATORS,
        experiment_prefix=f"price-intel-{sys.argv[1] if len(sys.argv) > 1 else 'run'}",
        metadata={"model": os.environ.get("MODEL_NAME")},
        max_concurrency=4,
    )
    scores = {}
    for row in results:
        for result in row["evaluation_results"]["results"]:
            scores.setdefault(result.key, []).append(float(result.score or 0))
    print(f"\n{results.experiment_name}")
    for key, values in scores.items():
        print(f"  {key:<24} {sum(values) / len(values):.2f}")
