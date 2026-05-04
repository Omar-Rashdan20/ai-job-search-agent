from crewai import Agent
from app.agents.llm_factory import create_llm


def create_query_agent() -> Agent:
    return Agent(
        role="Fresh Job Query Generator",
        goal=(
            "Create focused search queries for fresh job posts on the user's selected websites and country. "
            "Every query should aim for one direct posting page, include current-month language, "
            "and avoid listing pages, aggregators, old dates, and salary-focused results."
        ),
        backstory=(
            "You write practical recruiter-style searches that surface direct apply pages "
            "instead of broad search results."
        ),
        llm=create_llm(),
        max_iter=2,
        verbose=False,
    )
