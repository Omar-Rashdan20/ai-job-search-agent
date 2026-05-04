from crewai import Agent

from app.agents.llm_factory import create_llm


def create_query_agent() -> Agent:
    return Agent(
        role="Fresh Job Query Generator",
        goal="Generate a few complete, targeted search queries for fresh job postings.",
        backstory="You write concise recruiter-style search queries without extra commentary.",
        llm=create_llm(),
        max_iter=1,
        verbose=False,
    )
