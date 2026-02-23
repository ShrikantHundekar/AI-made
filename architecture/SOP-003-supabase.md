# SOP-003 — Supabase Integration
## AI Pulse Dashboard · ZYROX Intelligence System

> **Status:** ✅ Active  
> **Last Updated:** 2026-02-22  
> **Schema Reference:** `gemini.md` Section 2.1 / 2.2

---

## Purpose
Store all scraped articles and scrape run logs in Supabase for:
- Persistent cloud storage (survives local machine resets)
- Future multi-device / multi-user access
- Future real-time updates via `supabase-js` in the dashboard
- Analytics on scrape frequency and source health

---

## Tables

### `articles`
| Column | Type | Notes |
|--------|------|-------|
| `id` | TEXT (PK) | SHA256 of URL — stable, dedup-safe |
| `source` | TEXT | `bensbites` \| `therundown` \| `reddit` |
| `title` | TEXT | |
| `summary` | TEXT \| NULL | Truncated to 500 chars |
| `url` | TEXT (UNIQUE) | Canonical article URL |
| `published_at` | TIMESTAMPTZ | Original pub date |
| `scraped_at` | TIMESTAMPTZ | When our scraper found it |
| `author` | TEXT \| NULL | |
| `tags` | TEXT[] | Array of tag strings |
| `image_url` | TEXT \| NULL | OG image from article page |
| `saved` | BOOLEAN | Default FALSE |
| `saved_at` | TIMESTAMPTZ \| NULL | Set when user saves |

### `scrape_runs`
Logs every scraper execution for monitoring.

---

## Data Flow

```
scraper.py  →  .tmp/raw_*.json
                     ↓
             store.py (merge + dedup)
                     ↓
         data/articles_store.json  (local JSON, always primary)
                     ↓  (background thread)
         supabase_sync.py → Supabase cloud (upsert, idempotent)
```

---

## RLS Policies
- `anon` can SELECT all articles (public dashboard)
- `anon` can INSERT new articles (scraper w/ anon key)
- `anon` can UPDATE articles (save/unsave buttons)
- No DELETE policy — articles accumulate forever (by design)

---

## Key Invariants (gemini.md rules)
1. **Local JSON is the primary source of truth.** Supabase is a replica.
2. **Upsert is idempotent** — running sync multiple times is always safe.
3. **Save state is synced immediately** via background thread on every save/unsave.
4. **Connection failures are non-blocking** — logged but never crash the dashboard.

---

## Credentials
- **Project URL:** `https://axuhqdtkvtorvzocpnbn.supabase.co`
- **Region:** `ap-south-1` (Mumbai)
- Credentials stored in `.env` — never committed to git

---

## Running Manually

```bash
# Test connection
python tools/supabase_sync.py --test

# Full sync (upsert all local articles → Supabase)
python tools/supabase_sync.py

# Pull cloud → local (re-seed after local wipe)
python -c "from tools.supabase_sync import *; c=get_client(); pull_from_supabase(c)"
```

---

## Error Handling
| Error | Cause | Recovery |
|-------|-------|----------|
| `Connection failed` | Bad credentials / network | Check `.env` keys |
| `Batch upsert failed` | Schema mismatch or RLS | Check table schema |
| `ImportError: supabase` | Not installed | `pip install supabase` |
