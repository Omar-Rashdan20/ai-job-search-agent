import os
from crewai import Task
from app.config import OUTPUT_DIR, DEFAULT_COUNTRY, DEFAULT_WEBSITES, SEARCH_SCORE_THRESHOLD
from app.models.job_model import AllSearchResults
from app.models.workflow_types import DateConstraints
from app.utils.json_output_converter import ToonOutputConverter


def create_search_task(agent, inputs: dict, dates: DateConstraints) -> Task:
    score_threshold = inputs.get("score_th", SEARCH_SCORE_THRESHOLD)
    country = inputs.get("country", DEFAULT_COUNTRY)
    websites = inputs.get("websites_list", DEFAULT_WEBSITES)

    return Task(
        description="\n".join([
            "Run the search engine tool for every generated query.",
            f"Target job websites: {websites}.",
            f"Only keep results for the provided country: {country}.",
            f"TODAY is {dates['today']}. Keep only jobs posted after {dates['cutoff']}.",
            "Discard every URL whose domain is not one of the target job websites.",
            "Collect the strongest direct job results for each query.",
            f"Discard results whose title, snippet, URL, or location does not mention {country}.",
            f"Prefer results mentioning '{dates['month_year']}' OR 'posted this month'.",
            "Use fresh hiring signals: apply now, job description, urgent hiring, remote, hybrid.",
            "Each result MUST be a SINGLE job posting page with a unique job ID, not a listing page.",
            "Reject aggregator pages, company search pages, category pages, blogs, and news articles.",
            "Reject salary-only pages and do not keep salary-focused results.",
            f"Ignore results with a confidence score below {score_threshold}.",
            "Deduplicate URLs. Do not include the same job posting twice.",
        ]),
        expected_output=(
            "Return ONLY valid TOON, no markdown or prose. Example:\n"
            "results[1]{title,url,content,score,search_query}:\n"
            "  Job title,https://example.com/job/123,Short snippet,0.9,original query"
        ),
        output_pydantic=AllSearchResults,
        converter_cls=ToonOutputConverter,
        output_file=os.path.join(OUTPUT_DIR, "step_2_search_results.json"),
        agent=agent,
    )
