"""
store.py — AI Pulse Dashboard
Layer 3 Tool: Merges, deduplicates, and persists articles.
Also syncs save/unsave state to Supabase when configured.
SOP Reference: architecture/SOP-002-store.md
Schema Reference: gemini.md Section 2.2
"""

import json
import logging
import shutil
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent
TMP_DIR = BASE_DIR / ".tmp"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

STORE_FILE = DATA_DIR / "articles_store.json"
BACKUP_FILE = DATA_DIR / "articles_store.backup.json"

LOOKBACK_HOURS = int(os.getenv("LOOKBACK_HOURS", "24"))

log = logging.getLogger("store")


# ─────────────────────────────────────────────────────────────────────────────
# Store I/O
# ─────────────────────────────────────────────────────────────────────────────
def load_store() -> dict:
    """Load the persistent article store. Creates empty store if missing."""
    if not STORE_FILE.exists():
        log.info("[Store] No existing store — creating fresh.")
        return {"articles": [], "last_run": None, "run_count": 0}

    try:
        with open(STORE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        log.info(f"[Store] Loaded {len(data.get('articles', []))} existing articles")
        return data
    except (json.JSONDecodeError, KeyError) as e:
        log.error(f"[Store] Store file corrupted: {e} — backing up and resetting")
        shutil.copy(STORE_FILE, BACKUP_FILE)
        return {"articles": [], "last_run": None, "run_count": 0}


def save_store(store: dict) -> None:
    """Write the store to disk."""
    with open(STORE_FILE, "w", encoding="utf-8") as f:
        json.dump(store, f, indent=2, ensure_ascii=False)
    log.info(f"[Store] Saved {len(store['articles'])} articles to {STORE_FILE}")


# ─────────────────────────────────────────────────────────────────────────────
# Load Raw Files
# ─────────────────────────────────────────────────────────────────────────────
def load_raw(filename: str) -> list:
    """Load a raw scraped JSON file from .tmp/"""
    path = TMP_DIR / filename
    if not path.exists():
        log.warning(f"[Store] Raw file not found: {path}")
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ─────────────────────────────────────────────────────────────────────────────
# Merge & Dedup
# ─────────────────────────────────────────────────────────────────────────────
def merge_and_store() -> dict:
    """
    Load all raw files, merge them into the store, dedup by article ID.
    Returns a summary of what was added.
    """
    store = load_store()
    existing_ids = {a["id"] for a in store["articles"]}

    # Load raw sources
    raw_sources = {
        "bensbites": load_raw("raw_bensbites.json"),
        "therundown": load_raw("raw_therundown.json"),
        "reddit": load_raw("raw_reddit.json"),
    }

    new_count = 0
    for source_name, articles in raw_sources.items():
        for article in articles:
            art_id = article.get("id")
            if not art_id or art_id in existing_ids:
                continue

            # Ensure saved fields exist
            article.setdefault("saved", False)
            article.setdefault("saved_at", None)

            store["articles"].append(article)
            existing_ids.add(art_id)
            new_count += 1

    store["last_run"] = datetime.now(timezone.utc).isoformat()
    store["run_count"] = store.get("run_count", 0) + 1

    save_store(store)

    # ── Supabase upsert after merge (background thread) ────────────────────
    if supabase_enabled():
        def _bg_sync():
            try:
                import sys as _sys
                _tools = str(Path(__file__).parent)
                if _tools not in _sys.path:
                    _sys.path.insert(0, _tools)
                from supabase_sync import get_client, sync_articles
                sync_articles(get_client())
            except Exception as e:
                log.warning(f"[Store] Supabase background sync failed: {e}")
        threading.Thread(target=_bg_sync, daemon=True).start()

    summary = {
        "new_articles": new_count,
        "total_articles": len(store["articles"]),
        "last_run": store["last_run"],
        "run_count": store["run_count"]
    }
    log.info(f"[Store] +{new_count} new articles | Total: {len(store['articles'])}")
    return summary


# ─────────────────────────────────────────────────────────────────────────────
# Save Article Action
# ─────────────────────────────────────────────────────────────────────────────
def supabase_enabled() -> bool:
    """True if Supabase credentials are configured in .env."""
    return bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_ANON_KEY"))


def save_article(article_id: str) -> bool:
    """Mark an article as saved. Syncs to Supabase if configured."""
    store = load_store()
    for article in store["articles"]:
        if article["id"] == article_id:
            article["saved"] = True
            article["saved_at"] = datetime.now(timezone.utc).isoformat()
            save_store(store)
            log.info(f"[Store] Article saved: {article_id[:16]}...")
            # Sync to Supabase
            if supabase_enabled():
                def _sync():
                    try:
                        import sys as _sys
                        _tools = str(Path(__file__).parent)
                        if _tools not in _sys.path:
                            _sys.path.insert(0, _tools)
                        from supabase_sync import get_client, sync_saved_state
                        sync_saved_state(get_client(), article_id, True)
                    except Exception as e:
                        log.warning(f"[Store] Supabase saved-state sync failed: {e}")
                threading.Thread(target=_sync, daemon=True).start()
            return True
    log.warning(f"[Store] Article not found for save: {article_id}")
    return False


def unsave_article(article_id: str) -> bool:
    """
    Hard-delete an article from the local store and Supabase.
    Called when the user un-saves — the article is permanently removed.
    """
    store = load_store()
    before_count = len(store["articles"])

    # Remove from local store entirely
    store["articles"] = [a for a in store["articles"] if a["id"] != article_id]

    if len(store["articles"]) == before_count:
        # Article wasn't found
        log.warning(f"[Store] Article not found for delete: {article_id}")
        return False

    save_store(store)
    log.info(f"[Store] 🗑️  Article hard-deleted locally: {article_id[:16]}...")

    # Hard-delete from Supabase in background thread
    if supabase_enabled():
        def _delete():
            try:
                import sys as _sys
                _tools = str(Path(__file__).parent)
                if _tools not in _sys.path:
                    _sys.path.insert(0, _tools)
                from supabase_sync import get_client, delete_article as sb_delete
                sb_delete(get_client(), article_id)
            except Exception as e:
                log.warning(f"[Store] Supabase delete failed: {e}")
        threading.Thread(target=_delete, daemon=True).start()

    return True


# ─────────────────────────────────────────────────────────────────────────────
# Query Helpers
# ─────────────────────────────────────────────────────────────────────────────
def get_today_feed(store: dict) -> list:
    """Return articles from the last LOOKBACK_HOURS."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
    result = []
    for a in store["articles"]:
        try:
            pub = datetime.fromisoformat(a["published_at"])
            if pub.tzinfo is None:
                pub = pub.replace(tzinfo=timezone.utc)
            if pub >= cutoff:
                result.append(a)
        except Exception:
            continue
    return sorted(result, key=lambda x: x.get("published_at", ""), reverse=True)


def get_saved_articles(store: dict) -> list:
    """Return all saved articles, newest saved first."""
    saved = [a for a in store["articles"] if a.get("saved")]
    return sorted(saved, key=lambda x: x.get("saved_at", ""), reverse=True)


def get_stats(store: dict) -> dict:
    """Return dashboard statistics."""
    today_feed = get_today_feed(store)
    saved = get_saved_articles(store)
    sources = {}
    for a in today_feed:
        src = a.get("source", "unknown")
        sources[src] = sources.get(src, 0) + 1

    return {
        "total_articles": len(store["articles"]),
        "today_count": len(today_feed),
        "saved_count": len(saved),
        "sources": sources,
        "last_run": store.get("last_run"),
        "run_count": store.get("run_count", 0)
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    summary = merge_and_store()
    print(json.dumps(summary, indent=2))
