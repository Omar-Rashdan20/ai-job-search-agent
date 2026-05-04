from crewai import Agent
from app.agents.llm_factory import create_llm


def create_summary_agent() -> Agent:
    return Agent(
        role="Job Summary & Fit Ranker",
        goal=(
            "Summarize only fresh direct job postings, rank them by freshness, clarity, fit, "
            "company quality, location flexibility, and skill match. "
            "Identify practical skill gaps from the user's skill profile. "
            "Do not create new jobs, change URLs, or use salary information."
        ),
        backstory=(
            "You are a concise career advisor who compares current openings using practical fit "
            "and skill-match signals."
        ),
        llm=create_llm(),
        max_iter=2,
        verbose=False,
    )
