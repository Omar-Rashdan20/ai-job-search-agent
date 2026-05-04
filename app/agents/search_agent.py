from crewai import Agent
from app.agents.llm_factory import create_llm


def create_search_agent(search_tool) -> Agent:
    return Agent(
        role="Fresh Job Search Agent",
        goal=(
            "Run the search tool for every single query provided — never skip a query. "
            "Collect all direct job posting URLs from the target websites that mention the target country. "
            "If one query returns zero results, continue immediately to the next query. "
            "Only keep single-posting pages with a unique job ID in the URL. "
            "Reject listing pages, aggregators, search pages, blogs, salary-only pages, and old postings. "
            "Deduplicate by URL before returning results."
        ),
        backstory=(
            "You are a careful web researcher who treats every query as equally important. "
            "You never stop after the first failed query — you work through the entire list. "
            "You only pass back URLs where a job seeker can open one specific role and click apply. "
            "You know that listing pages and aggregators waste the job seeker's time and you reject them."
        ),
        llm=create_llm(),
        tools=[search_tool],
        max_iter=5,
        verbose=False,
    )