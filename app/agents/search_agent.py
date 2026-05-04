from crewai import Agent

from app.agents.llm_factory import create_llm


def create_search_agent(search_tool) -> Agent:
    return Agent(
        role="Fresh Job Search Agent",
        goal="Run the search tool only for the provided queries and return valid job URLs.",
        backstory="You are a careful web researcher who returns concise, deduplicated results.",
        llm=create_llm(),
        tools=[search_tool],
        max_iter=2,
        verbose=False,
    )
