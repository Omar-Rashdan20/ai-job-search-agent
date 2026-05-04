from html import escape
import gradio as gr
from urllib.parse import urlparse

from app.config import (
    DEFAULT_COUNTRY,
    DEFAULT_JOB_TITLE,
    DEFAULT_LANGUAGE,
    DEFAULT_TOP_RESULTS,
    DEFAULT_WORK_MODE,
    SEARCH_SCORE_THRESHOLD,
)
from app.crew import run_job_search_crew
from app.utils.url_utils import is_likely_job_posting_url, is_valid_url

CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;800&family=DM+Sans:wght@300;400;500;700&display=swap');

:root {
    --black: #050505;
    --panel: #101010;
    --panel-soft: #171717;
    --gold: #d4af37;
    --gold-bright: #f7d56b;
    --gold-dim: #8f6f18;
    --text: #f3f0e8;
    --muted: #a7a092;
    --border: #302a18;
}

body, .gradio-container {
    background: radial-gradient(circle at top, #181307 0%, var(--black) 42%) !important;
    color: var(--text) !important;
    font-family: 'DM Sans', sans-serif !important;
}

.gradio-container { max-width: 1280px !important; }

.gradio-container .block,
.gradio-container .form,
.gradio-container .panel,
.gradio-container .tabs,
.gradio-container .tabitem {
    background: var(--panel) !important;
    border-color: var(--border) !important;
}

.gradio-container input,
.gradio-container textarea,
.gradio-container select {
    background: #0b0b0b !important;
    color: var(--text) !important;
    border-color: var(--border) !important;
}

.gradio-container label,
.gradio-container .wrap label { color: var(--gold-bright) !important; }

.gradio-container button.primary {
    background: linear-gradient(135deg, var(--gold-bright), var(--gold)) !important;
    color: #070707 !important;
    border: 0 !important;
    font-weight: 800 !important;
}

h1, h2, h3 { font-family: 'Syne', sans-serif !important; }

.hero { display: none; }

.title-page {
    background: linear-gradient(180deg, rgba(247,213,107,0.12), rgba(16,16,16,0.72));
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 2rem 1.6rem;
    margin: 1rem 0 1.4rem;
    text-align: center;
}

.title-eyebrow {
    color: var(--gold-bright);
    font-size: 0.78rem;
    font-weight: 800;
    letter-spacing: 0;
    text-transform: uppercase;
    margin-bottom: 0.45rem;
}

.hero-title {
    font-family: 'Syne', sans-serif;
    font-size: 2.8rem;
    font-weight: 800;
    color: #ffffff;
    text-shadow: 0 0 18px rgba(247,213,107,0.28);
    margin-bottom: 0.3rem;
}

.title-subtitle { color: var(--muted); font-size: 1rem; margin-bottom: 1rem; }

.title-meta { display: flex; justify-content: center; flex-wrap: wrap; gap: 0.5rem; }

.title-chip {
    border: 1px solid var(--gold-dim);
    border-radius: 999px;
    color: var(--gold-bright);
    background: #0b0b0b;
    font-size: 0.78rem;
    font-weight: 700;
    padding: 0.28rem 0.7rem;
}

.job-card {
    background: linear-gradient(180deg, var(--panel-soft), #0a0a0a);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
    transition: border-color 0.2s, box-shadow 0.2s;
}

.job-card:hover {
    border-color: var(--gold);
    box-shadow: 0 0 0 1px rgba(212,175,55,0.25);
}

.job-card-title {
    font-family: 'Syne', sans-serif;
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--gold-bright);
    margin-bottom: 0.2rem;
}

.job-meta { color: var(--muted); font-size: 0.85rem; margin-bottom: 0.6rem; }

.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    margin-right: 4px;
}

.badge-type { background: #211b0a; color: var(--gold-bright); }
.badge-rank { background: #2a1a00; color: var(--gold); }
.badge-gap  { background: #1f1000; color: #ffc46b; }

.skill-tag {
    display: inline-block;
    background: #191304;
    color: var(--gold-bright);
    border: 1px solid var(--gold-dim);
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 0.75rem;
    margin: 2px;
}

.section-header {
    font-family: 'Syne', sans-serif;
    font-size: 1.3rem;
    font-weight: 700;
    color: var(--text);
    border-left: 3px solid var(--gold);
    padding-left: 10px;
    margin: 1.5rem 0 1rem;
}

.apply-btn {
    display: inline-block;
    background: linear-gradient(135deg, var(--gold-bright), var(--gold));
    color: #000 !important;
    font-weight: 700;
    font-size: 0.8rem;
    padding: 7px 14px;
    border-radius: 6px;
    text-decoration: none;
    margin-top: 8px;
}

.summary-box {
    background: #0b0b0b;
    border-left: 3px solid var(--gold);
    padding: 0.8rem 1rem;
    border-radius: 0 8px 8px 0;
    font-size: 0.9rem;
    color: var(--text);
    margin-top: 0.5rem;
    line-height: 1.6;
}

.no-results {
    color: var(--muted);
    text-align: center;
    padding: 2rem;
    font-style: italic;
}
"""

def _empty(value, fallback="N/A"):
    return value or fallback


def _html(value, fallback="N/A") -> str:
    return escape(str(_empty(value, fallback)))


def _render_tags(values: list, css_class: str) -> str:
    return " ".join(f'<span class="{css_class}">{escape(str(v))}</span>' for v in values if v)


def _domain_label(url: str) -> str:
    host = urlparse(url or "").netloc.replace("www.", "")
    return escape(host or "N/A")


def render_job_cards(jobs: list, empty_message: str = "No job results yet. Run a search above.") -> str:
    if not jobs:
        return f'<div class="no-results">{escape(empty_message)}</div>'

    html = ""
    for job in sorted(jobs, key=lambda j: j.get("recommendation_rank", 99)):
        skills_html = _render_tags((job.get("required_skills") or [])[:8], "skill-tag")
        gap_html    = _render_tags((job.get("skill_gap") or [])[:5], "badge badge-gap")
        notes_html  = "".join(
            f"<li>{escape(str(n))}</li>" for n in (job.get("recommendation_notes") or [])
        )

        rank         = _html(job.get("recommendation_rank"), "?")
        job_type     = _html(job.get("job_type"))
        source_type  = str(job.get("source_type") or "scraped")
        source_label = "Search-only" if source_type == "search_only" else "Scraped"
        source_note  = _html(job.get("source_note"), "")
        verified     = bool(job.get("is_verified_url"))
        posting_date = _html(job.get("posting_date"))
        deadline     = _html(job.get("application_deadline"))
        summary      = _html(job.get("job_summary") or job.get("job_description"), "")
        apply_url    = job.get("apply_url") or job.get("page_url", "#")
        source       = _domain_label(apply_url)
        apply_html   = ""

        if is_likely_job_posting_url(apply_url):
            safe_apply_url = escape(str(apply_url), quote=True)
            apply_html = (
                f'<a class="apply-btn" href="{safe_apply_url}" target="_blank" '
                'rel="noopener noreferrer">Apply Now</a>'
            )

        html += f"""
        <div class="job-card">
            <div class="job-card-title">#{rank} - {_html(job.get('job_title'))}</div>
            <div class="job-meta">
                Company: {_html(job.get('company_name'))} &nbsp;|&nbsp;
                Location: {_html(job.get('job_location'))} &nbsp;|&nbsp;
                Website: {source} &nbsp;|&nbsp;
                Posted: {posting_date} &nbsp;|&nbsp;
                Deadline: {deadline}
            </div>
            <span class="badge badge-type">{job_type}</span>
            <span class="badge badge-rank">Rank #{rank}</span>
            <span class="badge badge-type">{source_label}</span>
            {('<span class="badge badge-rank">Verified URL</span>') if verified else ''}
            <br><br>
            <strong style="color:var(--muted);font-size:0.8rem;">SKILLS REQUIRED</strong><br>
            {skills_html or '<span style="color:var(--muted)">Not specified</span>'}
            {('<br><br><strong style="color:#ffc46b;font-size:0.8rem;">SKILL GAP</strong><br>' + gap_html) if gap_html else ''}
            {('<div class="summary-box"><strong>Summary:</strong> ' + summary + '</div>') if summary else ''}
            {('<div class="summary-box"><strong>Source:</strong> ' + source_note + '</div>') if source_note else ''}
            {('<strong style="display:block;color:var(--muted);font-size:0.8rem;margin-top:0.7rem;">RECOMMENDATION NOTES</strong><ul style="color:var(--muted);font-size:0.82rem;margin:0.3rem 0 0 1rem;">' + notes_html + '</ul>') if notes_html else ''}
            {apply_html}
        </div>
        """

    return html


def render_search_only_cards(jobs: list) -> str:
    if not jobs:
        return '<div class="no-results">No search-only results found.</div>'

    html = ""
    for job in sorted(jobs, key=lambda j: j.get("recommendation_rank", 99)):
        rank = _html(job.get("recommendation_rank"), "?")
        title = _html(job.get("job_title"))
        company = _html(job.get("company_name"))
        location = _html(job.get("job_location"))
        summary = _html(job.get("job_summary") or job.get("job_description"), "")
        source_note = _html(
            job.get("source_note"),
            "Search-only result. Open the link to view full details.",
        )
        apply_url = job.get("apply_url") or job.get("page_url", "")
        source = _domain_label(apply_url)
        apply_html = ""

        if is_valid_url(apply_url):
            safe_apply_url = escape(str(apply_url), quote=True)
            apply_html = (
                f'<a class="apply-btn" href="{safe_apply_url}" target="_blank" '
                'rel="noopener noreferrer">Open Job</a>'
            )

        html += f"""
        <div class="job-card">
            <div class="job-card-title">#{rank} - {title}</div>
            <div class="job-meta">
                Company: {company} &nbsp;|&nbsp;
                Location: {location} &nbsp;|&nbsp;
                Website: {source}
            </div>
            <span class="badge badge-type">Search-only</span>
            <span class="badge badge-rank">Rank #{rank}</span>
            {('<div class="summary-box"><strong>Snippet:</strong> ' + summary + '</div>') if summary else ''}
            <div class="summary-box"><strong>Source:</strong> {source_note}</div>
            {apply_html}
        </div>
        """

    return html


def _progress(message: str) -> str:
    return f'<div class="no-results">{escape(message)}</div>'


def run_search(job_title, country, user_skills, work_mode, no_results, language, score_th):
    for message in (
        "Preparing search...",
        "Generating search queries...",
        "Searching and validating URLs...",
        "Scraping official/ATS pages...",
        "Keeping blocked job boards as search-only...",
        "Ranking and summarizing jobs...",
    ):
        progress = _progress(message)
        yield progress, progress

    inputs = {
        "job_title": job_title,
        "country": country,
        "work_mode": work_mode,
        "no_results": int(no_results),
        "language": language,
        "user_skills": user_skills,
        "score_th": float(score_th),
    }
    try:
        result = run_job_search_crew(inputs)
        jobs = result.get("jobs", [])
        scraped_jobs = [job for job in jobs if job.get("source_type") == "scraped"]
        search_only_jobs = [job for job in jobs if job.get("source_type") == "search_only"]
        yield _progress("Done."), _progress("Done.")
        yield (
            render_job_cards(scraped_jobs, "No scraped official/ATS jobs found."),
            render_search_only_cards(search_only_jobs),
        )
    except Exception as exc:
        error_html = f'<div class="no-results">Error: {escape(str(exc))}</div>'
        yield error_html, error_html


def build_ui():
    with gr.Blocks(css=CUSTOM_CSS, title="AI Agent Job Search") as demo:
        gr.HTML("""
        <section class="title-page">
            <div class="title-eyebrow">Powered by CrewAI · Tavily · ScrapeGraph · Gemini</div>
            <div class="hero-title">AI Agent Job Search</div>
            <div class="title-subtitle">Find fresh direct job postings and rank the strongest matches.</div>
            <div class="title-meta">
                <span class="title-chip">AI agents</span>
                <span class="title-chip">Direct job pages</span>
                <span class="title-chip">Fresh dates only</span>
            </div>
        </section>
        """)

        with gr.Row():
            with gr.Column(scale=1):
                gr.HTML('<div class="section-header">Search Parameters</div>')
                job_title = gr.Textbox(
                    label="Job Title",
                    placeholder="e.g. Machine Learning Engineer",
                    value=DEFAULT_JOB_TITLE,
                )
                country = gr.Textbox(
                    label="Country",
                    placeholder="e.g. Jordan, Egypt, Saudi Arabia",
                    value=DEFAULT_COUNTRY,
                )
                user_skills = gr.Textbox(
                    label="Your Skills",
                    placeholder="LLM, Python, Machine Learning, TensorFlow",
                    value="LLM, Python, Machine Learning",
                    lines=2,
                )
                work_mode = gr.Dropdown(
                    label="Work Mode",
                    choices=["Any", "Remote", "Hybrid", "Onsite"],
                    value=DEFAULT_WORK_MODE,
                )
                with gr.Row():
                    no_results = gr.Slider(
                        label="Number of Results",
                        minimum=2, maximum=8, step=1,
                        value=DEFAULT_TOP_RESULTS,
                    )
                    score_th = gr.Slider(
                        label="Search Score Threshold",
                        minimum=0.1, maximum=0.8, step=0.01,
                        value=SEARCH_SCORE_THRESHOLD,
                    )
                language = gr.Dropdown(
                    label="Search Language",
                    choices=["English", "Arabic", "French", "German", "Spanish"],
                    value=DEFAULT_LANGUAGE,
                )
                run_btn = gr.Button("Search Jobs", variant="primary", size="lg")

            with gr.Column(scale=2):
                gr.HTML('<div class="section-header">Results</div>')
                with gr.Tabs():
                    with gr.Tab("Scraped Jobs"):
                        scraped_jobs_html = gr.HTML(
                            value='<div class="no-results">Run a search to see scraped official/ATS jobs.</div>'
                        )
                    with gr.Tab("Search-only Jobs"):
                        search_only_jobs_html = gr.HTML(
                            value='<div class="no-results">Run a search to see LinkedIn, Bayt, Indeed, Glassdoor, and similar results.</div>'
                        )

        run_btn.click(
            fn=run_search,
            inputs=[job_title, country, user_skills, work_mode, no_results, language, score_th],
            outputs=[scraped_jobs_html, search_only_jobs_html],
        )

    return demo
