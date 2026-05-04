import os

from crewai import Task

from app.config import DEFAULT_COUNTRY, DEFAULT_WORK_MODE, MAX_SCRAPE_URLS, OUTPUT_DIR
from app.models.job_model import AllJobs
from app.models.workflow_types import DateConstraints
from app.utils.json_output_converter import ToonOutputConverter


def create_scraping_task(agent, inputs: dict, dates: DateConstraints) -> Task:
    country = inputs.get("country", DEFAULT_COUNTRY)
    work_mode = inputs.get("work_mode", DEFAULT_WORK_MODE)
    scrape_limit = inputs.get("scrape_limit", MAX_SCRAPE_URLS)

    return Task(
        description="\n".join([
            f"Extract structured job details from at most {scrape_limit} URLs.",
            "Use ONLY URLs that appear in the previous search results.",
            "If the previous step returned zero valid URLs, return {\"jobs\": []}.",
            "",
            f"Country filter: skip any page not located in or clearly tied to {country}.",
            f"Work mode filter: respect selected work mode {work_mode}.",
            f"Date filter: TODAY is {dates['today']}. Skip jobs posted before {dates['cutoff']}.",
            "",
            "Scraping rules:",
            "  - Do not scrape LinkedIn, Bayt, Indeed, or Glassdoor.",
            "  - Keep blocked job boards as search-only; do not pass them to scraping.",
            "  - Scrape only official company or ATS job pages.",
            "  - Each URL must open one direct job posting page, not a listing/search page.",
            "  - Do not invent, guess, or rewrite URLs.",
            "  - Do not fabricate fields; only extract what is explicitly shown.",
            "  - Do not extract salary information.",
            "",
            "Extract these fields when present: job title, company name, location, job type,",
            "posting date, application deadline, expected start date, required experience,",
            "required skills, education level, job description, apply URL, source_type,",
            "source_note, and is_verified_url.",
        ]),
        expected_output=(
            "Return ONLY valid TOON. No markdown, no prose. Use semicolons inside list fields.\n\n"
            "jobs[N]{page_url,job_title,company_name,job_location,job_type,posting_date,"
            "application_deadline,expected_start_date,required_experience,required_skills,"
            "education_level,job_description,apply_url,source_type,source_note,is_verified_url}:\n"
            "  https://site.com/job/123,AI Engineer,Acme,Jordan,Full-time,2026-05-01,"
            "2026-05-30,null,2 years,Python; LLM,Bachelor,Short description,"
            "https://site.com/apply/123,scraped,,true\n\n"
            "If no valid URLs were available:\n"
            "jobs[0]{page_url,job_title,company_name,job_location,job_type,posting_date,"
            "application_deadline,expected_start_date,required_experience,required_skills,"
            "education_level,job_description,apply_url,source_type,source_note,is_verified_url}:"
        ),
        output_pydantic=AllJobs,
        converter_cls=ToonOutputConverter,
        output_file=os.path.join(OUTPUT_DIR, "step_3_extracted_jobs.json"),
        agent=agent,
    )
