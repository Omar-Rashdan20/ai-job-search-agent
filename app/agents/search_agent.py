from crewai import Agent
from app.agents.llm_factory import create_llm


def create_search_agent(search_tool) -> Agent:
    return Agent(
        role="Fresh Job Search Agent",
        goal=(
            "Use the search tool to find fresh direct job URLs from the selected target websites. "
            "Prefer current-month apply or job-description pages, and reject search pages, "
            "aggregators, blogs, news, old postings, and salary-only pages."
        ),
        backstory=(
            "You are a careful web researcher who keeps only links where a job seeker "
            "can open one role and apply."
        ),
        llm=create_llm(),
        tools=[search_tool],
        max_iter=2,
        verbose=False,
    )
