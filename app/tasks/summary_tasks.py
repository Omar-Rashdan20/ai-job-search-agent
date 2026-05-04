import os

from crewai import Task

from app.config import DEFAULT_COUNTRY, DEFAULT_JOB_TITLE, DEFAULT_WORK_MODE, OUTPUT_DIR
from app.models.job_model import AllJobsWithSummary
from app.models.workflow_types import DateConstraints
from app.utils.json_output_converter import ToonOutputConverter


def create_summary_task(agent, inputs: dict, dates: DateConstraints) -> Task:
    country = inputs.get("country", DEFAULT_COUNTRY)
    job_title = inputs.get("job_title", DEFAULT_JOB_TITLE)
    work_mode = inputs.get("work_mode", DEFAULT_WORK_MODE)
    user_skills = inputs.get("user_skills", "Not specified")

    return Task(
        description="\n".join([
            f"Rank and summarize job listings for: {job_title} in {country}.",
            f"Selected work mode: {work_mode}.",
            f"TODAY is {dates['today']}. Only rank jobs posted after {dates['cutoff']}.",
            "",
            "If the extracted jobs list is empty, return {\"jobs\": []}; do not invent jobs.",
            "",
            "Filtering rules:",
            "  - Do not invent URLs.",
            "  - Only use URLs returned by search tools.",
            f"  - Drop jobs not located in or clearly tied to {country}.",
            "  - Respect selected work mode.",
            "  - Drop jobs with old posting dates, expired deadlines, or listing-page URLs.",
            "  - Keep LinkedIn, Bayt, Indeed, and Glassdoor as search-only results.",
            "  - Scraped results must be official company or ATS job pages.",
            "",
            "For each remaining job:",
            "  - Preserve original URLs, dates, source_type, source_note, and is_verified_url.",
            "  - Write a 3-5 sentence summary covering role, company, responsibilities, posting date, and deadline.",
            "  - Rank from 1 (best) to N using freshness, clarity, company quality, location fit, and skill match.",
            "  - Add 2-4 recommendation notes.",
            f"  - Compare required skills against user profile: [{user_skills}].",
            "  - List missing skills in skill_gap.",
            "  - Do not mention or include salary information.",
        ]),
        expected_output=(
            "Return ONLY valid TOON. No markdown, no prose. Use semicolons inside list fields.\n\n"
            "jobs[N]{page_url,job_title,company_name,job_location,job_type,posting_date,"
            "application_deadline,expected_start_date,required_experience,required_skills,"
            "education_level,job_description,apply_url,source_type,source_note,is_verified_url,"
            "job_summary,recommendation_rank,recommendation_notes,skill_gap}:\n"
            "  https://site.com/job/123,AI Engineer,Acme,Jordan,Full-time,2026-05-01,"
            "2026-05-30,null,2 years,Python; LLM,Bachelor,Short description,"
            "https://site.com/apply/123,scraped,,true,Summary of the role.,1,Strong fit; Fresh post,SQL; Docker\n\n"
            "If no jobs passed filtering:\n"
            "jobs[0]{page_url,job_title,company_name,job_location,job_type,posting_date,"
            "application_deadline,expected_start_date,required_experience,required_skills,"
            "education_level,job_description,apply_url,source_type,source_note,is_verified_url,"
            "job_summary,recommendation_rank,recommendation_notes,skill_gap}:"
        ),
        output_pydantic=AllJobsWithSummary,
        converter_cls=ToonOutputConverter,
        output_file=os.path.join(OUTPUT_DIR, "step_4_ranked_jobs.json"),
        agent=agent,
    )
