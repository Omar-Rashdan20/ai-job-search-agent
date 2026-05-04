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
            f"Extract structured job details from at most {scrape_limit} URLs.",
            f"Use ONLY the URLs that appear in the search results from the previous step.",
            f"If the previous step returned zero URLs, output {{\"jobs\": []}} immediately — do not invent URLs.",
            "",
            f"Target job websites: {websites}.",
            f"Country filter: {country} — skip any page not located in {country}.",
            f"Date filter: TODAY is {dates['today']}. Skip jobs posted before {dates['cutoff']}.",
            "",
            "SCRAPING RULES:",
            "  • Each URL must open one direct job posting page — skip listing or search pages.",
            "  • Skip pages with multiple jobs, category results, or company job lists.",
            "  • Skip blocked/error pages — move on to the next URL.",
            "  • Do NOT invent, guess, or rewrite any URL.",
            "  • Do NOT fabricate any field — only extract what is explicitly shown on the page.",
            "  • Do NOT extract salary information.",
            "",
            "EXTRACT these fields when present:",
            "  job title, company name, location, job type, posting date, application deadline,",
            "  expected start date, required experience, required skills, education level,",
            "  job description, apply URL.",
            "  Set fields to null only when the page genuinely does not show them.",
        ]),
        expected_output=(
            "Return ONLY valid TOON. No markdown, no prose. Use semicolons inside list fields.\n\n"
            "If jobs were extracted:\n"
            "jobs[N]{page_url,job_title,company_name,job_location,job_type,posting_date,"
            "application_deadline,expected_start_date,required_experience,required_skills,"
            "education_level,job_description,apply_url}:\n"
            "  https://site.com/job/123,AI Engineer,Acme,Jordan,Full-time,2026-05-01,"
            "2026-05-30,null,2 years,Python; LLM,Bachelor,Short description,https://site.com/apply/123\n\n"
            "If no valid URLs were available:\n"
            'jobs[0]{page_url,job_title,company_name,job_location,job_type,posting_date,'
            'application_deadline,expected_start_date,required_experience,required_skills,'
            'education_level,job_description,apply_url}:'
        ),
        output_pydantic=AllJobs,
        converter_cls=ToonOutputConverter,
        output_file=os.path.join(OUTPUT_DIR, "step_3_extracted_jobs.json"),
        agent=agent,
    )