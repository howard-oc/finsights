"""The chat model this agent uses. Set MODEL_NAME (provider:model) in the .env at the finsights repo root."""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent  # price_intelligence_agent/

REPO_ROOT = PROJECT_ROOT.parents[1]  # agents/<this agent>/ -> finsights repo root

load_dotenv(REPO_ROOT / ".env")

model = os.environ.get("MODEL_NAME", "openai:gpt-6-luna")
