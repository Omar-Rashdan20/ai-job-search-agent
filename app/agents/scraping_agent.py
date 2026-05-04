from crewai import Agent
from app.agents.llm_factory import create_llm


def create_scraping_agent(scraping_tool) -> Agent:
    return Agent(
        role="Fresh Job Detail Extractor",
        goal=(
            "Extract structured details only from direct job posting pages returned by search: "
            "title, company, location, job type, posting date, deadline, skills, description, and apply URL. "
            "Skip listing pages, blocked pages, old postings, and anything not explicitly stated."
        ),
        backstory=(
            "You are a precise job-page reader who copies stated facts and leaves missing fields blank."
        ),
        llm=create_llm(),
        tools=[scraping_tool],
        max_iter=2,
        verbose=False,
    )
