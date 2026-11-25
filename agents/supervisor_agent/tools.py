from langchain.tools import tool
from utils.state import InvestigationContext
# from agents.price_intelligence_agent.agent import agent as price_agent

# @tool
# def call_price_agent(
#     query: str,
#     runtime: ToolRuntime[InvestigationContext]
# ) -> str:
#     """Delegate financial analysis tasks to the financial analyst."""

#     result = price_agent.invoke(
#         {
#             "messages": [
#                 {"role": "user", "content": query}
#             ]
#         },
#         context=runtime.context
#     )

#     return result["messages"][-1].content