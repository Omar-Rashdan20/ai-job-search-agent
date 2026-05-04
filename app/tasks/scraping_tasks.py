import os
from crewai import Task
from app.config import DEFAULT_COUNTRY, DEFAULT_WEBSITES, MAX_SCRAPE_URLS, OUTPUT_DIR
from app.models.job_model import AllJobs
from app.models.workflow_types import DateConstraints
from app.utils.json_output_converter import ToonOutputConverter


def create_scraping_task(agent, inputs: dict, dates: DateConstraints) -> Task:
    country = inputs.get("country", DEFAULT_COUNTRY)
    scrape_limit = inputs.get("scrape_limit", MAX_SCRAPE_URLS)
    websites = inputs.get("websites_list", DEFAULT_WEBSITES)

    return Task(
        description="\n".join([
            f"Extract job details from at most {scrape_limit} search-result URLs.",
            f"Target job websites: {websites}.",
            f"Only extract postings for the provided country: {country}.",
            f"TODAY is {dates['today']}. Only extract jobs posted after {dates['cutoff']}.",
            "Use ONLY URLs that already exist in the previous search results.",
            'If there are no valid search-result URLs, return {"jobs": []}.',
            "Never invent, guess, or rewrite job URLs.",
            "Each URL MUST open one direct job posting page, not a listing or search page.",
            "Skip pages that show multiple jobs, category results, company job lists, or old dates.",
            f"Skip pages whose location is not {country}.",
            "Only keep pages where one job title and one company name are clearly visible.",
            "Extract: job title, company, location, type, posting date, deadline, start date, "
            "required experience, required skills, education level, job description, apply URL.",
            "If a posting date, deadline, or start date is visible, extract the exact date.",
            "Only set date fields to null when the page truly does not show them.",
            "If any other field is not available on the page, set it to null.",
            "Do not fabricate information. Only extract what is explicitly stated on the page.",
            "Do not extract salary information.",
        ]),
        expected_output=(
            "Return ONLY valid TOON, no markdown or prose. Use semicolons inside list fields. Example:\n"
            "jobs[1]{page_url,job_title,company_name,job_location,job_type,posting_date,"
            "application_deadline,expected_start_date,required_experience,required_skills,"
            "education_level,job_description,apply_url}:\n"
            "  https://example.com/job/123,AI Engineer,Company,Jordan,Full-time,2026-05-01,"
            "2026-05-30,null,2 years,Python; LLM,Bachelor,Short description,https://example.com/apply/123"
        ),
        output_pydantic=AllJobs,
        converter_cls=ToonOutputConverter,
        output_file=os.path.join(OUTPUT_DIR, "step_3_extracted_jobs.json"),
        agent=agent,
    )
