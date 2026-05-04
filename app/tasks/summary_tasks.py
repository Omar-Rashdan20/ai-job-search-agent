import os
from crewai import Task
from app.config import OUTPUT_DIR, DEFAULT_COUNTRY, DEFAULT_JOB_TITLE, DEFAULT_WEBSITES
from app.models.job_model import AllJobsWithSummary
from app.models.workflow_types import DateConstraints
from app.utils.json_output_converter import ToonOutputConverter


def create_summary_task(agent, inputs: dict, dates: DateConstraints) -> Task:
    country = inputs.get("country", DEFAULT_COUNTRY)
    job_title = inputs.get("job_title", DEFAULT_JOB_TITLE)
    websites = inputs.get("websites_list", DEFAULT_WEBSITES)
    user_skills = inputs.get("user_skills", "Not specified")

    return Task(
        description="\n".join([
            f"Review the extracted job listings for this job seeker: {job_title} positions in {country}.",
            f"Target job websites: {websites}.",
            f"Only keep jobs located in or clearly tied to {country}.",
            f"TODAY is {dates['today']}. Only rank jobs posted after {dates['cutoff']}.",
            'If there are no extracted jobs, return {"jobs": []}.',
            "Do not create new jobs or URLs during summarization.",
            "Remove jobs with old posting dates, expired deadlines, missing URLs, or listing-page URLs.",
            "Keep only jobs that appear open and accepting applications.",
            "Preserve posting dates, deadlines, and start dates from extracted jobs.",
            "Only leave date fields null when the source does not show a date.",
            "Write a 3-5 sentence summary covering role, company, responsibilities, posting date, and deadline.",
            "Rank jobs from 1 (best) to N (worst) using freshness, clarity, company quality, location flexibility, and fit.",
            "Add 2-4 recommendation notes explaining why the job is useful or weak for the seeker.",
            f"Compare required skills against this user skill profile: [{user_skills}].",
            "List missing skills in skill_gap.",
            "Do not mention or use salary information.",
        ]),
        expected_output=(
            "Return ONLY valid TOON, no markdown or prose. Use semicolons inside list fields. Example:\n"
            "jobs[1]{page_url,job_title,company_name,job_location,job_type,posting_date,"
            "application_deadline,expected_start_date,required_experience,required_skills,"
            "education_level,job_description,apply_url,job_summary,recommendation_rank,"
            "recommendation_notes,skill_gap}:\n"
            "  https://example.com/job/123,AI Engineer,Company,Jordan,Full-time,2026-05-01,"
            "2026-05-30,null,2 years,Python; LLM,Bachelor,Short description,"
            "https://example.com/apply/123,Summary of the role,1,Strong fit; Fresh post,SQL; Docker"
        ),
        output_pydantic=AllJobsWithSummary,
        converter_cls=ToonOutputConverter,
        output_file=os.path.join(OUTPUT_DIR, "step_4_ranked_jobs.json"),
        agent=agent,
    )
