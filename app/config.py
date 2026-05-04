import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
if GEMINI_API_KEY and not GOOGLE_API_KEY:
    os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY

# LLM
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").strip().lower()
LLM_API_BASE = os.getenv("LLM_API_BASE", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini/gemini-2.5-flash")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0"))
OLLAMA_API_BASE = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
LLM_FALLBACK_TO_OLLAMA = os.getenv("LLM_FALLBACK_TO_OLLAMA", "true").lower() in {
    "1", "true", "yes",
}

# Search
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
SEARCH_SCORE_THRESHOLD = float(os.getenv("SEARCH_SCORE_THRESHOLD", "0.3"))

# Scraping
SCRAPEGRAPH_API_KEY = os.getenv("SCRAPEGRAPH_API_KEY", "")

# AgentOps (optional monitoring)
AGENTOPS_API_KEY = os.getenv("AGENTOPS_API_KEY", "")

# Output
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def _list_from_env(name: str, default: list[str]) -> list[str]:
    value = os.getenv(name)
    if not value:
        return default
    items = [item.strip() for item in value.split(",") if item.strip()]
    return items or default


# Defaults
DEFAULT_TOP_RESULTS = int(os.getenv("DEFAULT_TOP_RESULTS", "5"))
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "English")
DEFAULT_COUNTRY = os.getenv("DEFAULT_COUNTRY", "Jordan")
DEFAULT_JOB_TITLE = os.getenv("DEFAULT_JOB_TITLE", "AI Engineer")
DEFAULT_WEBSITES = _list_from_env(
    "DEFAULT_WEBSITES",
    ["linkedin.com", "bayt.com", "akhtaboot.com", "tanqeeb.com"],
)
MAX_SCRAPE_URLS = int(os.getenv("MAX_SCRAPE_URLS", "3"))
SCRAPE_TIMEOUT_SECONDS = int(os.getenv("SCRAPE_TIMEOUT_SECONDS", "10"))
LINK_CHECK_TIMEOUT_SECONDS = float(os.getenv("LINK_CHECK_TIMEOUT_SECONDS", "4"))
