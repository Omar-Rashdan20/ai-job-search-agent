from crewai import Agent

from app.agents.llm_factory import create_llm


def create_scraping_agent(scraping_tool) -> Agent:
    return Agent(
        role="Fresh Job Detail Extractor",
        goal="Extract structured details only from official or ATS job URLs.",
        backstory="You copy stated job facts and skip blocked or unsuitable pages.",
        llm=create_llm(),
        tools=[scraping_tool],
        max_iter=2,
        verbose=False,
    )
