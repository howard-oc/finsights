"""Model configuration for the news agent; secrets and project settings come from environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PROJECT_ROOT.parents[1]
load_dotenv(REPO_ROOT / ".env")

model = os.environ.get("MODEL_NAME", "openai:gpt-4o-mini")
os.environ.setdefault("LANGSMITH_TRACING", "true")
os.environ.setdefault("LANGSMITH_PROJECT", "finsights")
