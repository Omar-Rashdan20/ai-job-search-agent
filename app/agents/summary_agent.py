from crewai import Agent

from app.agents.llm_factory import create_llm


def create_summary_agent() -> Agent:
    return Agent(
        role="Job Summary & Fit Ranker",
        goal="Rank only the provided jobs and write concise fit notes.",
        backstory="You summarize real job data without inventing missing facts.",
        llm=create_llm(),
        max_iter=1,
        verbose=False,
    )
