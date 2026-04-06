"""Configuration constants for the Twitter/X Nitter scraper."""

# Nitter instances ordered by reliability (updated periodically).
# Users can also supply their own via --instance.
NITTER_INSTANCES = [
    "https://nitter.privacydev.net",
    "https://nitter.poast.org",
    "https://nitter.1d4.us",
    "https://nitter.woodland.cafe",
    "https://nitter.mint.lgbt",
    "https://nitter.esmailelbob.xyz",
]

DEFAULT_OUTPUT_DIR = "data"
REQUEST_TIMEOUT = 15  # seconds
MAX_PAGES = 5

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}
