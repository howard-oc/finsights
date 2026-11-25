# Real NVDA news (public reports)

`news.json` holds 14 public news reports about NVIDIA (NVDA), 11-24 November 2026: Jensen Huang's resignation
(12 Nov), the reported SEC probe and AI selloff (20 Nov), his reinstatement (23 Nov) and the next day's pullback
(24 Nov). It matches the real prices in `agents/price_intelligence_agent/data/real/`, so the supervisor can line up
price moves with news.

Use it by pointing the news agent at it (in the repo-root `.env` or the environment):

```bash
LSEG_NEWS_JSON=/absolute/path/to/finsights/agents/lseg_news_agent/data/real/news.json
```

`data/news.json` (synthetic Asterion/ASTR articles) is unchanged, and the news agent's evals and tests still use it.

Notes:
- Each article keeps its real `source` and `url`. Headlines and snippets are short paraphrases in our own words, not
  copied article text.
- Publication **dates** come from the sources; the **times** (`T12:00:00Z`) are nominal, because the sources don't
  give exact times. Don't read intraday ordering into them.
- Claims the sources mark as unconfirmed (the alleged spy link, the reported SEC probe, the White House role) are
  labelled "reported" or "alleged" in the snippets.
- All articles use `company_name` "NVIDIA Corporation" and `ticker` "NVDA", because the news agent's filter requires
  both to match.
