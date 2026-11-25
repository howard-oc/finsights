"""Validate local LangGraph deployment configuration without deploying remotely."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    config_path = ROOT / "langgraph.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))

    errors = []
    for name, graph_path in config.get("graphs", {}).items():
        module_file, separator, export_name = graph_path.replace("./", "", 1).partition(":")
        if not separator or not export_name:
            errors.append(f"Invalid graph entry for {name}: {graph_path}")
            continue
        if not (ROOT / module_file).is_file():
            errors.append(f"Missing graph module for {name}: {module_file}")

    sys.path.insert(0, str(ROOT))
    try:
        from agent import agent, analyse_news
        result = agent.invoke({
            "company_name": "NVDA",
            "ticker": "ASTR",
            "start_date": "2026-11-18",
            "end_date": "2026-11-25",
            "newest_first": True,
        })
        if not result.get("output"):
            errors.append("Graph invocation did not produce NewsIntelligenceOutput")
        report = analyse_news("NVDA", "ASTR", "2026-11-18", "2026-11-25")
        if report.ticker != "ASTR":
            errors.append("Standalone analyse_news returned the wrong ticker")
    except Exception as exc:
        errors.append(f"Graph import/invocation failed: {exc}")

    if errors:
        print("DEPLOYMENT CHECK FAILED")
        for error in errors:
            print(f"- {error}")
        return 1

    print("DEPLOYMENT CHECK PASSED")
    print(f"- config: {config_path.relative_to(ROOT)}")
    print(f"- graphs: {', '.join(config['graphs'])}")
    print("- standalone graph invocation: passed")
    print("- NewsIntelligenceOutput validation: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
