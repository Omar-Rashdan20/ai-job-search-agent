import os
from crewai import Task
from app.config import OUTPUT_DIR, DEFAULT_COUNTRY, DEFAULT_WEBSITES, SEARCH_SCORE_THRESHOLD
from app.models.job_model import AllSearchResults
from app.models.workflow_types import DateConstraints
from app.utils.json_output_converter import ToonOutputConverter


def create_search_task(agent, inputs: dict, dates: DateConstraints) -> Task:
    country = inputs.get("country", DEFAULT_COUNTRY)
    websites = inputs.get("websites_list", DEFAULT_WEBSITES)
    # Use a low hard floor so borderline results are not silently dropped;
    # the crew.py pipeline re-filters with the user-configured threshold.
    score_floor = max(0.05, float(inputs.get("score_th", SEARCH_SCORE_THRESHOLD)) - 0.15)

    return Task(
        description="\n".join([
            "Run the search engine tool for EVERY query produced in the previous step.",
            f"Target job websites: {websites}.",
            f"Country filter: {country} — keep only results that mention {country}.",
            f"Date filter: TODAY is {dates['today']}. Keep only jobs posted after {dates['cutoff']}.",
            "",
            "ACCEPTANCE RULES:",
            f"  • URL domain must be one of the target websites.",
            f"  • Title or snippet must mention {country}.",
            f"  • Page must be a SINGLE job posting (unique job ID in the URL), not a listing page.",
            f"  • Confidence score must be ≥ {score_floor:.2f}.",
            "  • Reject: aggregator pages, search pages, category pages, blogs, salary-only pages.",
            "  • Deduplicate by URL — never repeat the same posting.",
            "",
            "IMPORTANT: If a query returns zero results from the search tool, still try every other query.",
            "Do not stop early. Run all queries and collect every valid result you find.",
            f"Prefer results that mention '{dates['month_year']}' or 'posted this month'.",
        ]),
        expected_output=(
            "Return ONLY valid TOON. No markdown, no prose.\n\n"
            "If results were found:\n"
            "results[N]{title,url,content,score,search_query}:\n"
            "  Job Title,https://site.com/jobs/12345,Short snippet,0.85,original query\n\n"
            "If truly nothing was found after running all queries:\n"
            "results[0]{title,url,content,score,search_query}:"
        ),
        output_pydantic=AllSearchResults,
        converter_cls=ToonOutputConverter,
        output_file=os.path.join(OUTPUT_DIR, "step_2_search_results.json"),
        agent=agent,
    )