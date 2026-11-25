CLASSIFICATION_PROMPT = """You classify company news event groups.
Use only the supplied headline and snippet facts. Choose exactly one event_category and importance.
A single article or an event group may contain several sources. Summaries must not invent facts.
This is research assistance, not investment advice. Do not recommend buy/sell/hold or predict prices.
Return one item for every supplied article_id.
"""

SUMMARY_PROMPT = """Write a factual article summary of no more than 40 words using only facts in the supplied snippet.
Then write a concise why_it_matters interpretation explicitly marked as an interpretation.
Do not add facts, causal claims, price predictions, or investment advice such as buy/sell/hold.
Every why-it-matters statement must remain grounded in the supplied facts.
"""

ADVICE_GUARDRAIL = (
    "Provide research interpretations only. Never recommend buying, selling or holding, and never predict returns or prices."
)
