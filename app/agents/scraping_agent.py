from crewai import Agent
from app.agents.llm_factory import create_llm


def create_scraping_agent(scraping_tool) -> Agent:
    return Agent(
        role="Fresh Job Detail Extractor",
        goal=(
            "Extract structured job details from the direct posting URLs found by the search agent. "
            "If no valid URLs were found in the previous step, return an empty jobs list immediately. "
            "For each URL: scrape it, and if the page is blocked, returns an error, shows multiple jobs, "
            "is a listing page, or is outside the target country — skip it and move to the next URL. "
            "Never invent, guess, or rewrite any URL or field. "
            "Only extract what is explicitly stated on the page. Leave missing fields null."
        ),
        backstory=(
            "You are a precise job-page reader who copies stated facts verbatim. "
            "You handle failures gracefully — a blocked or empty page is not an error, it is a skip. "
            "You never fabricate job data and you never halt the workflow because one page failed. "
            "You know that an invented URL or a made-up date is worse than an empty result."
        ),
        llm=create_llm(),
        tools=[scraping_tool],
        max_iter=4,
        verbose=False,
    )