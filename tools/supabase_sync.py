"""
supabase_sync.py — AI Pulse Dashboard
Layer 3 Tool: Syncs the local JSON store to Supabase cloud DB
SOP Reference: architecture/SOP-003-supabase.md
Schema Reference: gemini.md Section 2.1

Usage:
  python tools/supabase_sync.py              # Sync store → Supabase
  python tools/supabase_sync.py --test       # Just test connection
  python tools/supabase_sync.py --log-run    # Log a scrape run record
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

# ─────────────────────────────────────────────────────────────────────────────
# Setup
# ─────────────────────────────────────────────────────────────────────────────
load_dotenv()

BASE_DIR  = Path(__file__).parent.parent
DATA_FILE = BASE_DIR / "data" / "articles_store.json"
TMP_DIR   = BASE_DIR / ".tmp"
TMP_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(TMP_DIR / "supabase_sync.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("supabase_sync")

SUPABASE_URL      = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")


def get_client():
    """Return a Supabase client, or raise clearly if not configured."""
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_ANON_KEY must be set in .env"
        )
    try:
        from supabase import create_client, Client
        return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    except ImportError:
        raise RuntimeError(
            "supabase-py not installed. Run: pip install supabase"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Test Connection
# ─────────────────────────────────────────────────────────────────────────────
def test_connection() -> bool:
    """Ping Supabase and return True if it responds correctly."""
    log.info("[Supabase] Testing connection...")
    try:
        client = get_client()
        resp = client.table("articles").select("id").limit(1).execute()
        log.info(f"[Supabase] ✅ Connection OK — {SUPABASE_URL}")
        return True
    except Exception as e:
        log.error(f"[Supabase] ❌ Connection FAILED: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Load Local Store
# ─────────────────────────────────────────────────────────────────────────────
def load_local_store() -> dict:
    if not DATA_FILE.exists():
        log.warning(f"[Supabase] Local store not found: {DATA_FILE}")
        return {"articles": [], "last_run": None, "version": 1}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# ─────────────────────────────────────────────────────────────────────────────
# Article serialiser → Supabase row shape
# ─────────────────────────────────────────────────────────────────────────────
def to_db_row(article: dict) -> dict:
    """
    Convert a local article dict to the Supabase articles table schema.
    Handles None values and type coercions safely.
    """
    pub = article.get("published_at")
    saved_at = article.get("saved_at")
    scraped  = article.get("scraped_at")

    return {
        "id":           article["id"],
        "source":       article.get("source", "unknown"),
        "title":        article.get("title", "Untitled"),
        "summary":      article.get("summary") or None,
        "url":          article.get("url", ""),
        "published_at": pub      or None,
        "scraped_at":   scraped  or datetime.now(timezone.utc).isoformat(),
        "author":       article.get("author") or None,
        "tags":         article.get("tags")   or [],
        "image_url":    article.get("image_url") or None,
        "saved":        bool(article.get("saved", False)),
        "saved_at":     saved_at or None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Upsert All Articles
# ─────────────────────────────────────────────────────────────────────────────
def sync_articles(client) -> dict:
    """
    Upsert every article from local store into Supabase.
    Uses id as conflict key → idempotent (safe to run multiple times).
    """
    store = load_local_store()
    articles = store.get("articles", [])

    if not articles:
        log.info("[Supabase] No local articles to sync.")
        return {"upserted": 0, "errors": 0}

    log.info(f"[Supabase] Syncing {len(articles)} articles → Supabase...")

    rows    = [to_db_row(a) for a in articles]
    batch   = 50          # Supabase HTTP body limit safety
    total   = 0
    errors  = 0

    for i in range(0, len(rows), batch):
        chunk = rows[i:i + batch]
        try:
            resp = (
                client.table("articles")
                .upsert(chunk, on_conflict="id")
                .execute()
            )
            total += len(chunk)
            log.info(f"[Supabase] ✅ Batch {i//batch + 1}: {len(chunk)} rows upserted")
        except Exception as e:
            errors += len(chunk)
            log.error(f"[Supabase] ❌ Batch {i//batch + 1} failed: {e}")

    log.info(f"[Supabase] Sync complete — {total} upserted, {errors} errors")
    return {"upserted": total, "errors": errors}


# ─────────────────────────────────────────────────────────────────────────────
# Sync Save/Unsave State Back to Supabase
# ─────────────────────────────────────────────────────────────────────────────
def sync_saved_state(client, article_id: str, saved: bool) -> bool:
    """Update a single article's saved/saved_at state in Supabase."""
    try:
        payload = {
            "saved": saved,
            "saved_at": datetime.now(timezone.utc).isoformat() if saved else None
        }
        client.table("articles").update(payload).eq("id", article_id).execute()
        log.info(f"[Supabase] save={saved} synced for article {article_id[:12]}...")
        return True
    except Exception as e:
        log.error(f"[Supabase] Failed to sync saved state: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Hard Delete Article from Supabase
# ─────────────────────────────────────────────────────────────────────────────
def delete_article(client, article_id: str) -> bool:
    """
    Hard-delete an article from the Supabase articles table by id.
    Called when user un-saves — article is permanently removed from cloud.
    """
    try:
        client.table("articles").delete().eq("id", article_id).execute()
        log.info(f"[Supabase] 🗑️  Deleted article {article_id[:12]}... from cloud")
        return True
    except Exception as e:
        log.error(f"[Supabase] Failed to delete article {article_id[:12]}...: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Log a Scrape Run
# ─────────────────────────────────────────────────────────────────────────────
def log_scrape_run(client, scrape_summary: dict) -> bool:
    """Insert a scrape_runs record from the scraper's summary dict."""
    try:
        sources = scrape_summary.get("sources", {})
        row = {
            "run_at":           scrape_summary.get("run_at") or datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds":  scrape_summary.get("elapsed_seconds", 0),
            "bensbites_count":  sources.get("bensbites", 0),
            "therundown_count": sources.get("therundown", 0),
            "reddit_count":     sources.get("reddit", 0),
            "total_new":        scrape_summary.get("total_articles", 0),
            "status":           "ok",
        }
        client.table("scrape_runs").insert(row).execute()
        log.info(f"[Supabase] ✅ Scrape run logged")
        return True
    except Exception as e:
        log.error(f"[Supabase] Failed to log scrape run: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Pull Cloud → Merge Local (for multi-device sync)
# ─────────────────────────────────────────────────────────────────────────────
def pull_from_supabase(client) -> int:
    """
    Pull all articles from Supabase and merge into local store.
    Useful when re-seeding after a local store wipe.
    Returns number of articles pulled.
    """
    try:
        resp   = client.table("articles").select("*").order("published_at", desc=True).execute()
        rows   = resp.data or []
        log.info(f"[Supabase] Pulled {len(rows)} articles from cloud")

        # Load and merge into local store
        store = load_local_store()
        existing_ids = {a["id"] for a in store.get("articles", [])}

        new_count = 0
        for row in rows:
            if row["id"] not in existing_ids:
                store.setdefault("articles", []).append(row)
                new_count += 1
            else:
                # Update existing (cloud is authoritative for saved state)
                for a in store["articles"]:
                    if a["id"] == row["id"]:
                        a["saved"]    = row.get("saved", False)
                        a["saved_at"] = row.get("saved_at")
                        break

        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(store, f, indent=2, ensure_ascii=False)
        log.info(f"[Supabase] ✅ Merge complete — {new_count} new articles added locally")
        return new_count
    except Exception as e:
        log.error(f"[Supabase] Pull failed: {e}")
        return 0


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
def run():
    args = sys.argv[1:]

    if "--test" in args:
        ok = test_connection()
        sys.exit(0 if ok else 1)

    log.info("=" * 60)
    log.info("Supabase Sync — Starting")
    log.info("=" * 60)

    try:
        client = get_client()
    except RuntimeError as e:
        log.error(str(e))
        sys.exit(1)

    # Test first
    if not test_connection():
        log.error("Aborting sync — connection failed")
        sys.exit(1)

    # Full sync
    result = sync_articles(client)

    log.info(f"✅ Sync done — upserted: {result['upserted']}, errors: {result['errors']}")


if __name__ == "__main__":
    run()
