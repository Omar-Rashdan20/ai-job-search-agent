# AI Job Search Agent

AI Job Search Agent is a CrewAI-powered application that helps job seekers find recent, relevant job postings. It generates targeted search queries, searches the web with Tavily, extracts structured job details from official company , and presents ranked results in a Gradio interface.

The project is designed to prioritize fresh postings, valid job URLs, and transparent source handling. Job boards that are difficult or inappropriate to scrape, such as LinkedIn, Bayt, Indeed, and Glassdoor, are kept as search-only results.

---
# Demo :
[Demo Link](https://www.linkedin.com/posts/omar-rashdan-64a475282_ai-machinelearning-crewai-ugcPost-7457141796293423104-gg8E?utm_source=share&utm_medium=member_desktop&rcm=ACoAAETErFoBium0uFL-HSaG10fR0-6OHAO8NXU)
---

## Key Features

- Generates targeted job-search queries from the user's role, location, skills, and preferred work mode.
- Searches job sources with Tavily and filters results by country, role relevance, work mode, and posting date.
- Extracts structured job data from official company career pages.
- Keeps blocked job boards as search-only results instead of scraping them.
- Ranks jobs by freshness, relevance, source quality, location fit, and skill match.
- Displays results in a Gradio web interface with source badges for scraped and search-only jobs.
- Supports Gemini as the primary LLM provider with Ollama fallback.
- Includes optional AgentOps monitoring for workflow visibility.

## Technology Stack

| Layer | Technology |
| --- | --- |
| Agent orchestration | CrewAI |
| LLM provider | Gemini, with optional Ollama fallback |
| Search | Tavily |
| Scraping | ScrapeGraph AI |
| UI | Gradio |
| Validation | Pydantic |
| Monitoring | AgentOps |


## Project Structure

```text
ai-job-search-agent/
|-- app/
|   |-- agents/          # CrewAI agent factories
|   |-- models/          # Pydantic models and workflow types
|   |-- tasks/           # CrewAI task definitions
|   |-- tools/           # Tavily search and ScrapeGraph tools
|   |-- utils/           # Filtering, URL, cache, date, and parsing helpers
|   |-- config.py        # Environment-based application settings
|   `-- crew.py          # Main workflow orchestration
|-- ui/
|   `-- gradio_app.py    # Gradio interface
|-- output/              # Generated workflow outputs
|-- .env.example         # Gemini configuration template
|-- .env.ollama.example  # Ollama configuration template
|-- requirements.txt
`-- main.py
```


## Installation

```bash
git clone <repo-url>
cd ai-job-search-agent
python -m venv .venv
```

Activate the virtual environment:

```bash
# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create your local environment file:

```bash
# Windows
copy .env.example .env

# macOS/Linux
cp .env.example .env
```

## Configuration

Edit `.env` and provide the required API keys:

```env
GEMINI_API_KEY=your_gemini_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
SCRAPEGRAPH_API_KEY=your_scrapegraph_api_key_here
```


To use Ollama, copy the relevant values from `.env.ollama.example` into `.env` and ensure the selected Ollama model is available locally.

## Running the Application

```bash
python main.py
```

By default, the app starts at:

```text
http://127.0.0.1:7860
```

## Workflow

```text
User input
  -> Query generation
  -> Web search
  -> URL validation and source classification
  -> Official/ATS scraping when available
  -> Job ranking and summarization
  -> Gradio job cards
```

When scraping is blocked or unavailable, the application falls back to structured search-result data so users can still review relevant postings.

## Output Files

Generated files are written to the configured `OUTPUT_DIR`:

| File | Purpose |
| --- | --- |
| `step_1_search_queries.json` | Generated search queries |
| `step_2_search_results.json` | Filtered Tavily results |
| `step_3_extracted_jobs.json` | Scraped job details |
| `step_4_ranked_jobs.json` | Final ranked jobs |
| `last_error.txt` | Most recent workflow error, when applicable |

## Notes

- The application never invents job URLs. Final links must come from search results or scraped pages.
- Search-only job boards are intentionally not scraped.
- Cache entries expire after 12 hours by default and are refreshed on the next search or scrape.
- Cache files and generated outputs should not be committed.



## 📫 Connect With Me

* LinkedIn: [LinkedIn](https://www.linkedin.com/in/omar-rashdan-64a475282/)
* Email: [Email](mailto:rashdanomar15@gmail.com)

---
  

## License

MIT
