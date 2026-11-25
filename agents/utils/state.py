from dataclasses import dataclass
from langchain.tools import tool, ToolRuntime

@dataclass
class InvestigationContext:
    company_name: str = "None"
    date_str: str = "None"

@tool
def get_company(runtime: ToolRuntime[InvestigationContext]) -> str:
    """Get the current company name"""
    return runtime.context.company_name


@tool
def get_date(runtime: ToolRuntime[InvestigationContext]) -> str:
    """Get the current date"""
    return runtime.context.date_str


