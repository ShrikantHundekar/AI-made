# ⚡ AI Pulse — ZYROX Intelligence Dashboard

> Real-time AI news aggregator. Latest articles from **Ben's Bites**, **The AI Rundown**, and **Reddit AI** — curated daily, cloud-backed via Supabase.

![Dashboard Preview](https://img.shields.io/badge/Status-Live-brightgreen) ![Python](https://img.shields.io/badge/Python-3.10%2B-blue) ![Supabase](https://img.shields.io/badge/Supabase-Connected-3ECF8E)

---

## 🚀 Features

- **Real-time feed** — Articles from the last 24 hours, auto-filtered
- **3 sources** — Ben's Bites, The AI Rundown, Reddit AI subreddits
- **Save articles** — Bookmark articles; syncs instantly to Supabase cloud
- **Unsave = delete** — Removing a saved article wipes it from local + cloud
- **Search** — Live client-side search across title, summary, author
- **Source filters** — Filter by individual source with one click
- **Article modal** — Click any card for full detail: image, tags, author, read link
- **ZYROX brand** — Dark brutalist design, `#BFF549` lime accent, Geist Mono typography
- **Supabase cloud** — All articles automatically synced after every scrape

---

## 🏗️ Architecture

```
scraper.py  ──→  .tmp/raw_*.json
                       │
               store.py (merge + dedup)
                       │
       data/articles_store.json  ←── primary source of truth
                       │  (background thread)
            supabase_sync.py  ──→  Supabase cloud
                       │
           server.py (REST API on :3737)
                       │
        dashboard/ (index.html + app.js + styles.css)
```

---

## ⚙️ Setup

### 1. Clone & install dependencies

```bash
git clone https://github.com/ShrikantHundekar/AI-made.git
cd AI-made
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Then edit `.env` and fill in:

| Variable | Description |
|---|---|
| `REDDIT_CLIENT_ID` | Reddit app client ID (from reddit.com/prefs/apps) |
| `REDDIT_CLIENT_SECRET` | Reddit app secret |
| `REDDIT_USER_AGENT` | Any descriptive string |
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_ANON_KEY` | Your Supabase anon/public key |
| `LOOKBACK_HOURS` | How far back to show articles (default: `24`) |
| `DASHBOARD_PORT` | Local server port (default: `3737`) |

### 3. Reddit API setup

1. Go to [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps)
2. Click **"Create App..."** → select **`script`** type
3. Name: `AI_Pulse_Scraper`, Redirect URI: `http://localhost:8080`
4. Copy the **client ID** (under app name) + **secret** into `.env`

### 4. Run

```bash
# Windows — one-click startup (scrapes + starts server)
run.bat

# Or manually:
python tools/scraper.py   # fetch latest articles
python tools/store.py     # merge into local store
python server.py          # start dashboard server
```

Dashboard opens at **http://localhost:3737** 🎉

---

## 🗂️ Project Structure

```
├── server.py                  # HTTP server + REST API
├── run.bat                    # One-click Windows launcher
├── requirements.txt           # Python dependencies
├── .env.example               # Environment template
│
├── tools/
│   ├── scraper.py             # Multi-source web scraper
│   ├── store.py               # Local JSON store + dedup
│   └── supabase_sync.py       # Cloud sync (upsert / delete)
│
├── dashboard/
│   ├── index.html             # Dashboard HTML
│   ├── styles.css             # ZYROX brand styles
│   └── app.js                 # Frontend logic
│
├── architecture/
│   ├── SOP-001-scraper.md     # Scraper architecture doc
│   ├── SOP-002-store.md       # Store SOP
│   └── SOP-003-supabase.md    # Supabase integration SOP
│
└── data/                      # ⚠️ gitignored — machine-generated
    └── articles_store.json
```

---

## 🛢️ Supabase Schema

Two tables: `articles` and `scrape_runs`. Full schema in `architecture/SOP-003-supabase.md`.

```sql
-- Quick test
SELECT source, COUNT(*) FROM articles GROUP BY source;
```

---

## 🔄 Data Flow

| Action | Local JSON | Supabase |
|---|---|---|
| Scrape runs | Updated immediately | Upserted in background |
| Save article | `saved=true` written | `saved_at` synced |
| **Unsave article** | **Article deleted** | **Row hard-deleted** |

---

## 🧰 Manual Supabase Commands

```bash
# Test Supabase connection
python tools/supabase_sync.py --test

# Full sync local → Supabase
python tools/supabase_sync.py

# Pull cloud → local (re-seed)
python -c "from tools.supabase_sync import *; c=get_client(); pull_from_supabase(c)"
```

---

## 📋 Roadmap

- [x] Ben's Bites scraper (HTML fallback)
- [x] The AI Rundown scraper
- [x] Reddit AI scraper (public API + PRAW)
- [x] 24h date filtering
- [x] Save / hard-delete unsave
- [x] Supabase cloud sync
- [x] ZYROX brand dashboard
- [ ] Windows Task Scheduler daily automation
- [ ] Supabase Realtime live updates

---

## 📄 License

MIT — built with [Antigravity](https://antigravity.dev) × ZYROX.
