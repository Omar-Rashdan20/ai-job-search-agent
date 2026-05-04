# AI Agent Job Search

A CrewAI-powered job search app that generates targeted queries, finds valid job URLs automatically, keeps blocked job boards as search-only results, extracts official/ATS job details when possible, and displays ranked job cards in a Gradio interface.

## Features

- Generates focused job-search queries from a job title and country.
- Searches automatically with Tavily (queries run in parallel).
- Extracts structured job details with ScrapeGraph only for official company or ATS pages.
- Falls back to Tavily search data when scraping is blocked or unavailable.
- Keeps LinkedIn, Bayt, Indeed, and Glassdoor as search-only results.
- Supports work mode filtering: Any, Remote, Hybrid, Onsite.
- Thread-safe — multiple Gradio sessions don't interfere with each other.

## Source Rules

| Source | Behavior |
|---|---|
| `linkedin.com` | Search-only |
| `bayt.com` | Search-only |
| `indeed.com` | Search-only |
| `glassdoor.com` | Search-only |
| Official company career pages | Scraped when they look like direct job pages |
| ATS pages such as `greenhouse.io`, `lever.co`, `workable.com`, `ashbyhq.com`, `smartrecruiters.com` | Scraped |

## Tech Stack

| Layer | Technology |
|---|---|
| Agent framework | CrewAI |
| LLM | Gemini 2.5 Flash (Ollama fallback) |
| Search | Tavily |
| Scraping | ScrapeGraph AI |
| UI | Gradio |
| Validation | Pydantic |
| Monitoring (opt.) | AgentOps |

## Project Structure

```text
ai-job-search-agent/
├── app/
│   ├── agents/
│   │   ├── llm_factory.py      # Thread-safe LLM provider factory
│   │   ├── query_agent.py
│   │   ├── search_agent.py
│   │   ├── scraping_agent.py
│   │   └── summary_agent.py
│   ├── tasks/
│   │   ├── query_tasks.py
│   │   ├── search_tasks.py
│   │   ├── scraping_tasks.py
│   │   └── summary_tasks.py
│   ├── tools/
│   │   ├── search_tool.py      # Parallel Tavily search
│   │   └── scraping_tool.py    # Shared executor, no per-call thread pool
│   ├── models/
│   │   └── job_model.py
│   ├── utils/
│   │   ├── json_output_converter.py  # TOON + JSON parser (semicolon bug fixed)
│   │   ├── job_fallback.py
│   │   ├── location_utils.py
│   │   └── url_utils.py
│   ├── config.py
│   └── crew.py                 # Main workflow orchestrator
├── ui/
│   └── gradio_app.py
├── output/
│   └── .gitkeep
├── .env.example
├── .env.ollama.example
├── requirements.txt
└── main.py
```

## Setup

```bash
git clone <repo-url>
cd ai-job-search-agent
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env      # Windows
# cp .env.example .env      # macOS/Linux
```

Edit `.env` and add your API keys:

```env
GEMINI_API_KEY=your_gemini_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
SCRAPEGRAPH_API_KEY=your_scrapegraph_api_key_here
```

## Run

```bash
python main.py
```

Open: http://127.0.0.1:7860

## UI Inputs

| Field | Example |
|---|---|
| Job Title | `AI Engineer` |
| Country | `Jordan` |
| Your Skills | `LLM, Python, Machine Learning` |
| Work Mode | `Any`, `Remote`, `Hybrid`, `Onsite` |
| Number of Results | `5` |
| Search Score Threshold | `0.3` |
| Search Language | `English` |

## Workflow

```
User inputs → Query Agent → Search Agent → Scraping Agent → Summary Agent → Job Cards
                               ↓ (parallel Tavily fallback if needed)
```

## License

MIT
