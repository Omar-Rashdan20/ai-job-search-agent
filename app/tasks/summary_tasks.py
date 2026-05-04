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
            f"Rank and summarise the extracted job listings for: {job_title} in {country}.",
            f"Target job websites: {websites}.",
            f"TODAY is {dates['today']}. Only rank jobs posted after {dates['cutoff']}.",
            "",
            "If the extracted jobs list is empty, output {\"jobs\": []} immediately — do not invent jobs.",
            "",
            "FILTERING (apply before ranking):",
            f"  • Drop jobs not located in or clearly tied to {country}.",
            "  • Drop jobs with old posting dates, expired deadlines, or missing/listing-page URLs.",
            "  • Keep only jobs that appear open and actively accepting applications.",
            "",
            "FOR EACH remaining job:",
            "  • Preserve all original field values — do NOT change URLs, dates, or titles.",
            "  • Write a 3–5 sentence summary: role, company, responsibilities, posting date, deadline.",
            "  • Rank from 1 (best) to N using: freshness, clarity, company quality, location fit, skill match.",
            "  • Add 2–4 recommendation notes explaining strengths or weaknesses for this seeker.",
            f"  • Compare required skills against user profile: [{user_skills}].",
            "  • List any missing skills in skill_gap.",
            "  • Do NOT mention or include salary information.",
        ]),
        expected_output=(
            "Return ONLY valid TOON. No markdown, no prose. Use semicolons inside list fields.\n\n"
            "If ranked jobs exist:\n"
            "jobs[N]{page_url,job_title,company_name,job_location,job_type,posting_date,"
            "application_deadline,expected_start_date,required_experience,required_skills,"
            "education_level,job_description,apply_url,job_summary,recommendation_rank,"
            "recommendation_notes,skill_gap}:\n"
            "  https://site.com/job/123,AI Engineer,Acme,Jordan,Full-time,2026-05-01,"
            "2026-05-30,null,2 years,Python; LLM,Bachelor,Short description,"
            "https://site.com/apply/123,Summary of the role.,1,Strong fit; Fresh post,SQL; Docker\n\n"
            "If no jobs passed filtering:\n"
            "jobs[0]{page_url,job_title,company_name,job_location,job_type,posting_date,"
            "application_deadline,expected_start_date,required_experience,required_skills,"
            "education_level,job_description,apply_url,job_summary,recommendation_rank,"
            "recommendation_notes,skill_gap}:"
        ),
        output_pydantic=AllJobsWithSummary,
        converter_cls=ToonOutputConverter,
        output_file=os.path.join(OUTPUT_DIR, "step_4_ranked_jobs.json"),
        agent=agent,
    )