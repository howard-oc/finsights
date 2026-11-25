import os

from dotenv import load_dotenv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

load_dotenv(PROJECT_ROOT.parent / ".env")

model = os.environ.get("MODEL_NAME", "openai:gpt-6-luna")