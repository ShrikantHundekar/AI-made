# SOP-002: Article Store — AI Pulse Dashboard

## Purpose
Merges raw scraped articles from all sources, deduplicates them, and persists them
to the article store JSON file. Also handles the "save article" action.

## Tool File
`tools/store.py`

## Inputs
- `.tmp/raw_bensbites.json`
- `.tmp/raw_therundown.json`
- `.tmp/raw_reddit.json`
- Existing `data/articles_store.json` (if it exists)

## Outputs
- `data/articles_store.json` — the persistent article store

## Logic

### Merge Step
1. Load all three raw JSON files
2. Normalize each article to the unified schema (see `gemini.md` Section 2.1)
3. Generate `id` = SHA256 hex of the article's `url`
4. Set `saved = false`, `saved_at = null` for all new articles

### Dedup Step
1. Load existing `data/articles_store.json` (if it exists)
2. Build a set of existing `id` values
3. Only add articles whose `id` is NOT already in the store
4. Merge new articles into the store array

### 24h Filter Step
- When building the "today's feed" view, filter articles where:
  `published_at >= (now - LOOKBACK_HOURS)`
- Saved articles (`saved = true`) ALWAYS appear in the "Saved" tab regardless of age

### Save Action
- When the user clicks "Save" on an article:
  - Set `saved = true`
  - Set `saved_at = current ISO8601 datetime`
  - Write back to `data/articles_store.json`
- This is triggered via the dashboard API endpoint `/api/save/<article_id>`

## Edge Cases
- If `data/articles_store.json` does not exist: create it with empty `articles` array
- If an article's URL is malformed: skip it and log to `.tmp/scrape.log`
- If the store file is corrupted: back it up to `data/articles_store.backup.json` and start fresh
