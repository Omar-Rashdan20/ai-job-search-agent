import os

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv() -> None:
        return None

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
SEARCH_SCORE_THRESHOLD = float(os.getenv("SEARCH_SCORE_THRESHOLD", "0.1"))

FAST_MODE = os.getenv("FAST_MODE", "true").lower() in {"1", "true", "yes"}

# Only block scraping for these domains (search-only results)
SEARCH_ONLY_DOMAINS = [
    "linkedin.com",
    "bayt.com",
    "indeed.com",
    "glassdoor.com",
]

# Optional: extend blocked domains from .env
EXTRA_BLOCKED_DOMAINS = os.getenv("EXTRA_BLOCKED_DOMAINS", "")
EXTRA_BLOCKED_DOMAINS = [
    d.strip() for d in EXTRA_BLOCKED_DOMAINS.split(",") if d.strip()
]

SEARCH_ONLY_DOMAINS += EXTRA_BLOCKED_DOMAINS

# Scraping
SCRAPEGRAPH_API_KEY = os.getenv("SCRAPEGRAPH_API_KEY", "")

# AgentOps (optional monitoring)
AGENTOPS_API_KEY = os.getenv("AGENTOPS_API_KEY", "")

# Output
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

CACHE_DIR = os.getenv("CACHE_DIR", "./cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# Defaults
DEFAULT_TOP_RESULTS = int(os.getenv("DEFAULT_TOP_RESULTS", "5"))
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "English")
DEFAULT_COUNTRY = os.getenv("DEFAULT_COUNTRY", "Jordan")
DEFAULT_JOB_TITLE = os.getenv("DEFAULT_JOB_TITLE", "AI Engineer")
DEFAULT_WORK_MODE = os.getenv("DEFAULT_WORK_MODE", "Any")

# Limits & timeouts
MAX_SCRAPE_URLS = int(os.getenv("MAX_SCRAPE_URLS", "3"))
SCRAPE_TIMEOUT_SECONDS = int(os.getenv("SCRAPE_TIMEOUT_SECONDS", "10"))
LINK_CHECK_TIMEOUT_SECONDS = float(os.getenv("LINK_CHECK_TIMEOUT_SECONDS", "5"))