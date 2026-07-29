"""
========================================================
  Naukri.com Job Market Scraper
  Project: Job Market Intelligence Dashboard
  Step 1 of 5
========================================================
  Scrapes Data/AI job postings from Naukri.com for
  Indian cities and saves results to a CSV file.

  OUTPUT: naukri_jobs_raw.csv
  FIELDS: job_id, job_title, company, location, experience,
          salary, skills, job_type, posted_date, job_url,
          scraped_at
"""

import time
import random
import csv
import re
import logging
import hashlib
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
)
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup


# ─────────────────────────────────────────────────────────
#  CONFIGURATION  — edit these before running
# ─────────────────────────────────────────────────────────

# Job roles to search (combined with each city below)
SEARCH_QUERIES = [
    "data scientist",
    "data analyst",
    "machine learning engineer",
    "AI engineer",
    "data engineer",
    "business intelligence analyst",
    "NLP engineer",
    "deep learning engineer",
]

# Indian cities to search across
TARGET_CITIES = [
    "bangalore",
    "hyderabad",
    "pune",
    "mumbai",
    "delhi",
    "chennai",
    "noida",
    "gurgaon",
]

# How many result pages to scrape per (query + city) pair
# Naukri shows ~20 jobs per page, so 5 pages ≈ 100 jobs per pair
PAGES_PER_QUERY = 1

# Seconds to wait between page requests (randomised between MIN and MAX)
MIN_DELAY = 5.0
MAX_DELAY = 10.0

# Output CSV filename
OUTPUT_FILE = "naukri_jobs_raw.csv"

# Set to True to see the Chrome browser window while scraping
SHOW_BROWSER = True


# ─────────────────────────────────────────────────────────
#  LOGGING SETUP
# ─────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────
#  DATA MODEL
# ─────────────────────────────────────────────────────────

@dataclass
class JobPosting:
    """
    One row in the output CSV.
    Every field is optional — we store whatever Naukri exposes
    so the cleaning pipeline (Step 2) handles missing values.
    """
    job_id: str = ""            # SHA-1 hash of the job URL (stable dedup key)
    job_title: str = ""
    company: str = ""
    location: str = ""          # Raw string e.g. "Bangalore, Hyderabad"
    experience: str = ""        # Raw string e.g. "2-5 Yrs"
    salary: str = ""            # Raw string e.g. "8-15 Lacs PA"
    skills: str = ""            # Pipe-separated list of key skills
    job_type: str = ""          # Full-time / Contract / etc.
    posted_date: str = ""       # Raw e.g. "30+ days ago" or "Just now"
    job_url: str = ""
    scraped_at: str = field(default_factory=lambda: datetime.now().isoformat())


# ─────────────────────────────────────────────────────────
#  BROWSER SETUP
# ─────────────────────────────────────────────────────────

def create_driver(headless: bool = True) -> webdriver.Chrome:
    """
    Returns a configured Selenium Chrome driver.

    We set several options to:
      1. Reduce the chance of being blocked (disable automation flags).
      2. Run headlessly so it doesn't need a display (set headless=False
         to watch the browser in action — useful for debugging).
      3. Improve performance by disabling images and notifications.
    """
    options = Options()

    if headless:
        options.add_argument("--headless=new")  # new headless mode (Chrome 112+)

    # ── Avoid detection ──────────────────────────────────
    # Remove the "Chrome is being controlled by automated software" banner
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # Spoof a real user-agent so the site doesn't see "HeadlessChrome"
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    # ── Performance ──────────────────────────────────────
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-notifications")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    # Disable loading images — we only need text, so this is ~2× faster
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.default_content_setting_values.notifications": 2,
    }
    options.add_experimental_option("prefs", prefs)

    # webdriver-manager auto-downloads the correct chromedriver binary
    service = Service("chromedriver.exe")
    driver = webdriver.Chrome(service=service, options=options)

    # Patch navigator.webdriver to False (anti-bot measure)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
    )

    return driver


# ─────────────────────────────────────────────────────────
#  URL BUILDER
# ─────────────────────────────────────────────────────────

def build_search_url(query: str, city: str, page: int = 1) -> str:
    """
    Build the Naukri search URL for a given query, city, and page.

    Naukri URL structure:
      https://www.naukri.com/{query-slug}-jobs-in-{city-slug}-{page}
      e.g. https://www.naukri.com/data-scientist-jobs-in-bangalore-2

    The first page has no page number suffix.
    """
    query_slug = query.lower().replace(" ", "-")
    city_slug = city.lower().replace(" ", "-")

    base = f"https://www.naukri.com/{query_slug}-jobs-in-{city_slug}"
    return base if page == 1 else f"{base}-{page}"


# ─────────────────────────────────────────────────────────
#  PAGE SCRAPER — listing page (20 cards per page)
# ─────────────────────────────────────────────────────────

def scrape_listing_page(driver: webdriver.Chrome, url: str) -> list[JobPosting]:
    """
    Load one Naukri search results page and extract all job cards.

    Naukri renders its job cards with JavaScript, so we use Selenium
    to load the page fully, then hand the HTML to BeautifulSoup for
    fast and convenient parsing.

    Returns a list of (possibly partially filled) JobPosting objects.
    """
    log.info(f"  Fetching: {url}")
    jobs: list[JobPosting] = []

    try:
        driver.get(url)

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".cust-job-tuple, article.jobTuple"))
        )

        time.sleep(random.uniform(1.5, 3.0))

    except TimeoutException:
        log.warning(f"  Timed out waiting for job cards on {url}. Skipping page.")
        return jobs
    except Exception as e:
        log.warning(f"  Network error on {url}: {e}. Waiting 15s and skipping.")
        time.sleep(15)
        return jobs

    # ── Parse with BeautifulSoup ─────────────────────────
    soup = BeautifulSoup(driver.page_source, "html.parser")

    # Naukri uses two selectors depending on the page variant:
    cards = soup.select(".cust-job-tuple") or soup.select("article.jobTuple")

    if not cards:
        log.warning(f"  No job cards found on {url}.")
        return jobs

    log.info(f"  Found {len(cards)} cards")

    for card in cards:
        job = parse_job_card(card)
        if job.job_url:                 # skip cards with no URL
            jobs.append(job)

    return jobs


# ─────────────────────────────────────────────────────────
#  CARD PARSER — extract fields from one <article> element
# ─────────────────────────────────────────────────────────

def safe_text(element, selector: str, attr: Optional[str] = None) -> str:
    """
    Helper: find a CSS selector inside element, return its text (or an
    attribute value if `attr` is given).  Returns "" on any failure.
    """
    try:
        found = element.select_one(selector)
        if found is None:
            return ""
        if attr:
            return found.get(attr, "").strip()
        return found.get_text(separator=" ", strip=True)
    except Exception:
        return ""


def parse_job_card(card: BeautifulSoup) -> JobPosting:
    """
    Extract all fields from a single job card element.

    Naukri's HTML class names change occasionally. We try multiple
    selectors for resilience, marked with comments.
    """
    job = JobPosting()

    # ── Job Title & URL ──────────────────────────────────
    # The title link has class "title" or is an <a> inside ".row1"
    title_tag = card.select_one("a.title") or card.select_one(".row1 a")
    if title_tag:
        job.job_title = title_tag.get_text(strip=True)
        raw_url = title_tag.get("href", "")
        # Naukri sometimes uses relative URLs — normalise to absolute
        job.job_url = raw_url if raw_url.startswith("http") else f"https://www.naukri.com{raw_url}"
        # Stable unique ID from URL (ignores query-string noise)
        clean_url = re.sub(r"\?.*$", "", job.job_url)
        job.job_id = hashlib.sha1(clean_url.encode()).hexdigest()[:12]

    # ── Company ──────────────────────────────────────────
    job.company = (
        safe_text(card, "a.comp-name")
        or safe_text(card, ".subTitle.ellipsis.fleft")
        or safe_text(card, ".companyInfo a")
    )

    # ── Location ─────────────────────────────────────────
    # Multiple locations are comma-separated inside the element
    job.location = (
        safe_text(card, ".locWdth")
        or safe_text(card, "span.location")
        or safe_text(card, ".jobTupleHeader span.ellipsis")
    )

    # ── Experience ───────────────────────────────────────
    job.experience = (
        safe_text(card, ".expwdth")
        or safe_text(card, "span.experience")
        or safe_text(card, "li.experience")
    )

    # ── Salary ───────────────────────────────────────────
    # Salary is often hidden/not disclosed; capture what's visible
    job.salary = (
        safe_text(card, ".salary")
        or safe_text(card, "span.salary")
        or safe_text(card, "li.salary")
    )

    # ── Skills ───────────────────────────────────────────
    # Key skills appear as individual <li> or <span> tags inside .tags
    skills_container = (
        card.select_one("ul.tags-gt") or
        card.select_one(".tags-gt") or
        card.select_one(".key-skill") or
        card.select_one(".tags")
    )
    if skills_container:
        skill_tags = skills_container.find_all(["li", "a", "span"])
        skill_list = [s.get_text(strip=True) for s in skill_tags if s.get_text(strip=True)]
        job.skills = " | ".join(skill_list)
    else:
        all_skill_spans = card.select("span.tag-li, a.tag-li, li.tag-li")
        if all_skill_spans:
            job.skills = " | ".join([s.get_text(strip=True) for s in all_skill_spans if s.get_text(strip=True)])

    # ── Posted Date ──────────────────────────────────────
    job.posted_date = (
        safe_text(card, "span.job-post-day")
        or safe_text(card, ".status-container .fresh-relevance-txt")
        or safe_text(card, "span.fleft.postedDate")
    )

    return job


# ─────────────────────────────────────────────────────────
#  CSV WRITER
# ─────────────────────────────────────────────────────────

def init_csv(filepath: str) -> None:
    """Write the CSV header row (overwrites any existing file)."""
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(JobPosting.__dataclass_fields__.keys()))
        writer.writeheader()
    log.info(f"Initialised output file: {filepath}")


def append_to_csv(filepath: str, jobs: list[JobPosting]) -> None:
    """Append a list of jobs to the CSV (no header)."""
    if not jobs:
        return
    with open(filepath, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(JobPosting.__dataclass_fields__.keys()))
        writer.writerows([asdict(j) for j in jobs])


# ─────────────────────────────────────────────────────────
#  DEDUPLICATION
# ─────────────────────────────────────────────────────────

class SeenJobsTracker:
    """
    Tracks job IDs we have already written to avoid duplicates.
    The same job can appear across multiple (query, city) searches.
    """
    def __init__(self):
        self._seen: set[str] = set()

    def is_new(self, job: JobPosting) -> bool:
        if job.job_id in self._seen:
            return False
        self._seen.add(job.job_id)
        return True

    @property
    def count(self) -> int:
        return len(self._seen)


# ─────────────────────────────────────────────────────────
#  MAIN ORCHESTRATOR
# ─────────────────────────────────────────────────────────

def run_scraper():
    """
    Main entry point.

    Outer loop:  each search query (e.g. "data scientist")
    Middle loop: each city (e.g. "bangalore")
    Inner loop:  each page (1 … PAGES_PER_QUERY)

    We write results to CSV incrementally so no data is lost
    if the script is interrupted.
    """
    log.info("=" * 58)
    log.info("  Naukri Job Scraper  —  starting run")
    log.info(f"  Queries  : {len(SEARCH_QUERIES)}")
    log.info(f"  Cities   : {len(TARGET_CITIES)}")
    log.info(f"  Pages/pair: {PAGES_PER_QUERY}")
    log.info(f"  Max jobs  : ~{len(SEARCH_QUERIES)*len(TARGET_CITIES)*PAGES_PER_QUERY*20:,}")
    log.info("=" * 58)

    init_csv(OUTPUT_FILE)
    tracker = SeenJobsTracker()

    driver = create_driver(headless=not SHOW_BROWSER)

    try:
        for query in SEARCH_QUERIES:
            for city in TARGET_CITIES:
                log.info(f"\n── {query.upper()}  ·  {city.upper()} ──────────────────")

                for page in range(1, PAGES_PER_QUERY + 1):
                    url = build_search_url(query, city, page)
                    try:
                        jobs = scrape_listing_page(driver, url)
                    except Exception as e:
                        log.warning(f"  Skipping page due to error: {e}")
                        time.sleep(20)
                        continue

                    # Deduplicate before writing
                    new_jobs = [j for j in jobs if tracker.is_new(j)]
                    append_to_csv(OUTPUT_FILE, new_jobs)

                    log.info(
                        f"  Page {page}: {len(jobs)} scraped, "
                        f"{len(new_jobs)} new  |  Total unique: {tracker.count}"
                    )

                    # If a page returned 0 results, there are no more pages
                    if len(jobs) == 0:
                        log.info("  No results — stopping early for this query/city.")
                        break

                    # Polite delay between requests
                    delay = random.uniform(MIN_DELAY, MAX_DELAY)
                    log.info(f"  Sleeping {delay:.1f}s …")
                    time.sleep(delay)

    except KeyboardInterrupt:
        log.warning("\nInterrupted by user. Partial results saved to CSV.")

    finally:
        driver.quit()
        log.info("\n" + "=" * 58)
        log.info(f"  Done.  Unique jobs saved: {tracker.count}")
        log.info(f"  Output file : {OUTPUT_FILE}")
        log.info("=" * 58)


# ─────────────────────────────────────────────────────────
#  RUN
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    run_scraper()
