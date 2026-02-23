"""
scraper.py — AI Pulse Dashboard
Layer 3 Tool: Scrapes Ben's Bites, The AI Rundown, and Reddit
SOP Reference: architecture/SOP-001-scraper.md
Schema Reference: gemini.md Section 2.1
"""

import os
import json
import hashlib
import time
import logging
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import feedparser

# ─────────────────────────────────────────────────────────────────────────────
# Setup
# ─────────────────────────────────────────────────────────────────────────────
load_dotenv()

BASE_DIR = Path(__file__).parent.parent
TMP_DIR = BASE_DIR / ".tmp"
TMP_DIR.mkdir(exist_ok=True)

LOG_FILE = TMP_DIR / "scrape.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("scraper")

LOOKBACK_HOURS = int(os.getenv("LOOKBACK_HOURS", "24"))
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def make_id(url: str) -> str:
    """SHA256 hash of the URL — unique, stable article identifier."""
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def is_within_window(dt: datetime) -> bool:
    """True if the datetime is within the lookback window."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
    return dt >= cutoff


def save_raw(filename: str, articles: list) -> None:
    """Save raw articles to .tmp/"""
    path = TMP_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)
    log.info(f"Saved {len(articles)} articles → {path}")


def get_page(url: str) -> BeautifulSoup | None:
    """GET a URL and return BeautifulSoup, or None on failure."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        log.error(f"Failed to fetch {url}: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Source 1: Ben's Bites
# ─────────────────────────────────────────────────────────────────────────────
def scrape_bensbites() -> list:
    """
    Strategy: Try multiple feed endpoints for Ben's Bites.
    1. Try Substack RSS (they moved to substack)
    2. Try Beehiiv web scraping
    3. Try common beehiiv RSS patterns
    """
    articles = []

    # Strategy 1: Substack RSS
    rss_urls = [
        "https://bensbites.com/feed",
        "https://www.bensbites.co/feed",
        "https://bensbites.beehiiv.com/feed",
        "https://www.bensbites.com/rss",
    ]

    for rss_url in rss_urls:
        log.info(f"[BensBites] Trying RSS: {rss_url}")
        try:
            feed = feedparser.parse(rss_url)
            if feed.entries:
                log.info(f"[BensBites] ✅ RSS found at {rss_url} — {len(feed.entries)} entries")
                for entry in feed.entries:
                    try:
                        # Parse pub date
                        pub_struct = entry.get("published_parsed") or entry.get("updated_parsed")
                        if pub_struct:
                            pub_dt = datetime(*pub_struct[:6], tzinfo=timezone.utc)
                        else:
                            pub_dt = datetime.now(timezone.utc)

                        if not is_within_window(pub_dt):
                            continue

                        url = entry.get("link", "")
                        if not url:
                            continue

                        summary = entry.get("summary", "")
                        # Strip HTML from summary
                        if summary:
                            soup = BeautifulSoup(summary, "html.parser")
                            summary = soup.get_text(separator=" ", strip=True)[:500]

                        articles.append({
                            "id": make_id(url),
                            "source": "bensbites",
                            "title": entry.get("title", "Untitled"),
                            "summary": summary,
                            "url": url,
                            "published_at": pub_dt.isoformat(),
                            "scraped_at": datetime.now(timezone.utc).isoformat(),
                            "author": entry.get("author", "Ben Tossell"),
                            "tags": ["AI", "Newsletter"],
                            "image_url": None
                        })
                    except Exception as e:
                        log.warning(f"[BensBites] Failed to parse entry: {e}")
                        continue

                if articles:
                    save_raw("raw_bensbites.json", articles)
                    return articles
        except Exception as e:
            log.warning(f"[BensBites] RSS failed at {rss_url}: {e}")
        time.sleep(1)

    # Strategy 2: BeautifulSoup scrape of beehiiv archive page
    log.info("[BensBites] Falling back to HTML scraping...")
    archive_url = "https://bensbites.beehiiv.com/archive"
    soup = get_page(archive_url)
    if soup:
        # Try to find article links
        links = soup.find_all("a", href=True)
        seen = set()
        for link in links:
            href = link.get("href", "")
            # Filter for article-like links
            if "/p/" in href and href not in seen:
                seen.add(href)
                full_url = href if href.startswith("http") else f"https://bensbites.beehiiv.com{href}"
                title = link.get_text(strip=True)
                if len(title) < 10:
                    continue
                # Can't reliably get date from list page — include and flag
                articles.append({
                    "id": make_id(full_url),
                    "source": "bensbites",
                    "title": title,
                    "summary": "Visit article for full content.",
                    "url": full_url,
                    "published_at": datetime.now(timezone.utc).isoformat(),
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                    "author": "Ben Tossell",
                    "tags": ["AI", "Newsletter"],
                    "image_url": None
                })
                if len(articles) >= 5:  # Limit to top 5 from HTML scrape
                    break

    if articles:
        log.info(f"[BensBites] ✅ Scraped {len(articles)} articles from HTML")
    else:
        log.warning("[BensBites] ⚠️ No articles found — source may require auth or has changed")

    save_raw("raw_bensbites.json", articles)
    return articles


# ─────────────────────────────────────────────────────────────────────────────
# Source 2: The AI Rundown
# ─────────────────────────────────────────────────────────────────────────────
def scrape_therundown() -> list:
    """
    Scrapes The AI Rundown homepage for latest article cards.
    Each article links to /p/<slug>.
    """
    articles = []
    base_url = "https://www.therundown.ai"

    log.info("[TheRundown] Scraping homepage...")
    soup = get_page(base_url)
    if not soup:
        save_raw("raw_therundown.json", [])
        return []

    seen = set()

    # Find all links pointing to /p/ slugs
    for a_tag in soup.find_all("a", href=True):
        href = a_tag.get("href", "")
        if href.startswith("/p/") or "/p/" in href:
            full_url = href if href.startswith("http") else f"{base_url}{href}"
            if full_url in seen:
                continue
            seen.add(full_url)

            # Title: text inside the link or nearby heading
            title = a_tag.get_text(strip=True)
            if len(title) < 8:
                # Try parent heading
                parent = a_tag.find_parent(["h1", "h2", "h3", "h4"])
                if parent:
                    title = parent.get_text(strip=True)

            if len(title) < 8:
                continue

            # Try to get published date from the slug (e.g. URL won't have date, need meta)
            # We'll fetch the article page to get og:published_time
            time.sleep(0.5)
            article_soup = get_page(full_url)
            pub_dt = datetime.now(timezone.utc)
            summary = ""
            image_url = None

            if article_soup:
                # Try og:article:published_time
                meta_pub = (
                    article_soup.find("meta", property="article:published_time") or
                    article_soup.find("meta", attrs={"name": "publish_date"}) or
                    article_soup.find("meta", property="og:article:published_time")
                )
                if meta_pub and meta_pub.get("content"):
                    try:
                        from dateutil import parser as dateutil_parser
                        pub_dt = dateutil_parser.parse(meta_pub["content"])
                        if pub_dt.tzinfo is None:
                            pub_dt = pub_dt.replace(tzinfo=timezone.utc)
                    except Exception:
                        pass

                # Try og:description for summary
                meta_desc = (
                    article_soup.find("meta", property="og:description") or
                    article_soup.find("meta", attrs={"name": "description"})
                )
                if meta_desc and meta_desc.get("content"):
                    summary = meta_desc["content"][:500]

                # Try og:image
                meta_img = article_soup.find("meta", property="og:image")
                if meta_img and meta_img.get("content"):
                    image_url = meta_img["content"]

            if not is_within_window(pub_dt):
                log.info(f"[TheRundown] Skipping old article: {title[:50]}")
                continue

            articles.append({
                "id": make_id(full_url),
                "source": "therundown",
                "title": title,
                "summary": summary or "Daily AI briefing from The Rundown AI.",
                "url": full_url,
                "published_at": pub_dt.isoformat(),
                "scraped_at": datetime.now(timezone.utc).isoformat(),
                "author": "Zach Mink",
                "tags": ["AI", "Newsletter", "Daily Briefing"],
                "image_url": image_url
            })

            if len(articles) >= 10:
                break

    log.info(f"[TheRundown] ✅ Found {len(articles)} articles in last {LOOKBACK_HOURS}h")
    save_raw("raw_therundown.json", articles)
    return articles


# ─────────────────────────────────────────────────────────────────────────────
# Source 3: Reddit
# ─────────────────────────────────────────────────────────────────────────────
def scrape_reddit() -> list:
    """
    Uses PRAW to scrape top new posts from AI subreddits.
    Requires REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT in .env
    Falls back to Reddit JSON API if PRAW credentials not set.
    """
    articles = []
    subreddits = ["artificial", "MachineLearning", "ArtificialIntelligence"]

    reddit_id = os.getenv("REDDIT_CLIENT_ID", "")
    reddit_secret = os.getenv("REDDIT_CLIENT_SECRET", "")
    user_agent = os.getenv("REDDIT_USER_AGENT", "AI_Pulse_Dashboard/1.0")

    # Strategy 1: PRAW (if credentials are set)
    if reddit_id and reddit_secret and reddit_id != "your_reddit_client_id_here":
        try:
            import praw
            reddit = praw.Reddit(
                client_id=reddit_id,
                client_secret=reddit_secret,
                user_agent=user_agent
            )
            log.info("[Reddit] Using PRAW API")

            for sub_name in subreddits:
                try:
                    sub = reddit.subreddit(sub_name)
                    for post in sub.new(limit=25):
                        created_dt = datetime.fromtimestamp(post.created_utc, tz=timezone.utc)
                        if not is_within_window(created_dt):
                            continue
                        if post.score < 5:
                            continue

                        url = f"https://www.reddit.com{post.permalink}"
                        summary = (post.selftext[:400] if post.selftext else
                                   f"[Link Post] {post.url}")

                        articles.append({
                            "id": make_id(url),
                            "source": "reddit",
                            "title": post.title,
                            "summary": summary,
                            "url": url,
                            "published_at": created_dt.isoformat(),
                            "scraped_at": datetime.now(timezone.utc).isoformat(),
                            "author": str(post.author) if post.author else "Unknown",
                            "tags": ["Reddit", f"r/{sub_name}", "AI"],
                            "image_url": (post.thumbnail if post.thumbnail and
                                          post.thumbnail.startswith("http") else None)
                        })
                    time.sleep(0.5)
                except Exception as e:
                    log.warning(f"[Reddit] Error scraping r/{sub_name}: {e}")

            log.info(f"[Reddit] ✅ Found {len(articles)} posts via PRAW")
            save_raw("raw_reddit.json", articles)
            return articles

        except ImportError:
            log.warning("[Reddit] PRAW not installed — falling back to JSON API")
        except Exception as e:
            log.warning(f"[Reddit] PRAW failed: {e} — falling back to JSON API")

    # Strategy 2: Reddit public JSON API (no auth needed)
    log.info("[Reddit] Using public JSON API (limited to top 25 new posts)")
    for sub_name in subreddits:
        url = f"https://www.reddit.com/r/{sub_name}/new.json?limit=25"
        try:
            resp = requests.get(url, headers={
                "User-Agent": user_agent
            }, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            posts = data.get("data", {}).get("children", [])

            for item in posts:
                post = item.get("data", {})
                created_utc = post.get("created_utc", 0)
                created_dt = datetime.fromtimestamp(created_utc, tz=timezone.utc)

                if not is_within_window(created_dt):
                    continue
                if post.get("score", 0) < 5:
                    continue

                permalink = post.get("permalink", "")
                full_url = f"https://www.reddit.com{permalink}"
                selftext = post.get("selftext", "")
                link_url = post.get("url", "")
                summary = selftext[:400] if selftext else f"[Link Post] {link_url}"

                thumbnail = post.get("thumbnail", "")
                image_url = thumbnail if thumbnail.startswith("http") else None

                articles.append({
                    "id": make_id(full_url),
                    "source": "reddit",
                    "title": post.get("title", "Untitled"),
                    "summary": summary,
                    "url": full_url,
                    "published_at": created_dt.isoformat(),
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                    "author": post.get("author", "Unknown"),
                    "tags": ["Reddit", f"r/{sub_name}", "AI"],
                    "image_url": image_url
                })

            time.sleep(1)  # Be polite to Reddit
        except Exception as e:
            log.error(f"[Reddit] JSON API failed for r/{sub_name}: {e}")

    log.info(f"[Reddit] ✅ Found {len(articles)} posts via JSON API")
    save_raw("raw_reddit.json", articles)
    return articles


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
def run_all_scrapers() -> dict:
    """Run all scrapers and return summary."""
    log.info("=" * 60)
    log.info(f"AI Pulse Scraper — Starting (lookback: {LOOKBACK_HOURS}h)")
    log.info("=" * 60)

    start = datetime.now(timezone.utc)

    bb_articles = scrape_bensbites()
    tr_articles = scrape_therundown()
    rd_articles = scrape_reddit()

    total = len(bb_articles) + len(tr_articles) + len(rd_articles)
    elapsed = (datetime.now(timezone.utc) - start).total_seconds()

    summary = {
        "run_at": start.isoformat(),
        "elapsed_seconds": round(elapsed, 2),
        "sources": {
            "bensbites": len(bb_articles),
            "therundown": len(tr_articles),
            "reddit": len(rd_articles)
        },
        "total_articles": total
    }

    log.info(f"✅ Complete — {total} articles in {elapsed:.1f}s")
    log.info(f"   Ben's Bites: {len(bb_articles)}")
    log.info(f"   The Rundown: {len(tr_articles)}")
    log.info(f"   Reddit: {len(rd_articles)}")

    return summary


if __name__ == "__main__":
    run_all_scrapers()
