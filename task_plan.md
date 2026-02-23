# 📋 Task Plan — B.L.A.S.T. Project Blueprint
## ZYROX AI Intelligence Dashboard

> **Status:** � IN PROGRESS — Phase 5 remaining (Automation Trigger)
> **Protocol:** B.L.A.S.T. (Blueprint → Link → Architect → Stylize → Trigger)
> **Last Updated:** 2026-02-22 23:36 IST

---

## 🎯 Phase Tracker

| Phase | Name      | Status        | Completed                                                |
|-------|-----------|---------------|----------------------------------------------------------|
| 0     | Init      | ✅ Complete   | `gemini.md`, `task_plan.md`, `findings.md`, `progress.md` created |
| 1     | Blueprint | ✅ Complete   | Discovery answered, schema defined, blueprint approved   |
| 2     | Link      | ✅ Complete   | All sources verified; Supabase + Reddit API connected    |
| 3     | Architect | ✅ Complete   | All Layer 3 tools built, SOPs written, data flowing      |
| 4     | Stylize   | ✅ Complete   | ZYROX brand applied, dashboard live on port 3737         |
| 5     | Trigger   | 🟡 In Progress | Supabase live; Windows Task Scheduler not yet configured |

---

## ✅ Phase 0: Init — COMPLETE

- [x] `gemini.md` — Project Constitution created
- [x] `task_plan.md` — Phase tracker initialized
- [x] `findings.md` — Research log initialized
- [x] `progress.md` — Append-only execution log initialized

---

## ✅ Phase 1: Blueprint — COMPLETE

- [x] Discovery Q1 — North Star: Beautiful interactive AI news dashboard, last 24h
- [x] Discovery Q2 — Integrations: Web scraping (no keys) → Supabase + Reddit API (Phase 5)
- [x] Discovery Q3 — Source of Truth: bensbites.beehiiv.com, therundown.ai, reddit.com
- [x] Discovery Q4 — Payload: Local dashboard + 24h auto-refresh + save articles + Supabase cloud
- [x] Discovery Q5 — Rules: Only show new content, dedup by URL hash, saved articles persist
- [x] JSON Data Schema defined in `gemini.md` (Article schema v1.0)
- [x] Blueprint approved → Coding started

---

## ✅ Phase 2: Link — COMPLETE

- [x] `.env` file created with all credentials
- [x] **Ben's Bites** — HTML scrape fallback working (beehiiv RSS is subscriber-gated)
- [x] **The Rundown** — `therundown.ai` homepage scrape working ✅ 10 articles
- [x] **Reddit** — Public JSON API working ✅ 5–7 posts per run (PRAW ready when credentials added)
- [x] **Supabase** — Connection tested ✅ `ACTIVE_HEALTHY` (ap-south-1)
- [x] Handshake test: `python tools/supabase_sync.py --test` → PASS

---

## ✅ Phase 3: Architect — COMPLETE

### SOPs Written
- [x] `architecture/SOP-001-scraper.md` — Scraper architecture + edge cases
- [x] `architecture/SOP-002-store.md` — Merge, dedup, save/unsave logic
- [x] `architecture/SOP-003-supabase.md` — Supabase sync + RLS + data flow

### Layer 3 Tools Built
- [x] `tools/scraper.py` — Multi-source scraper (Ben's Bites, The Rundown, Reddit)
- [x] `tools/store.py` — Merge, dedup, local JSON persistence + Supabase threading
- [x] `tools/supabase_sync.py` — Full upsert, save-state sync, pull-from-cloud

### Infrastructure
- [x] `server.py` — Python stdlib HTTP server + REST API (port 3737)
- [x] `.tmp/` directory — scraper intermediates
- [x] `data/articles_store.json` — Local persistent store (**17 articles**)
- [x] Supabase `articles` table — **17 rows live**, RLS enabled, FTS index
- [x] Supabase `scrape_runs` table — audit log ready
- [x] Supabase views: `today_feed`, `saved_articles`

---

## ✅ Phase 4: Stylize — COMPLETE

- [x] **ZYROX brand** applied — `#BFF549` lime × `#0D0D0D` black
- [x] **Typography** — Aspekta (headings) · Inter (body) · Geist Mono (monospace)
- [x] **Icon-only sidebar** — 72px, `ZX` lime logo, nav badges
- [x] **Source strip** — Ben's Bites / The Rundown / Reddit AI count cards
- [x] **Article grid** — Neumorphic dark cards with editorial images
- [x] **Filter chips** — All / Ben's Bites / The Rundown / Reddit AI
- [x] **Search** — Live client-side search across title + summary + author
- [x] **Modal** — Click-to-expand with source badge, image, tags, Read + Save actions
- [x] **Save / Unsave** — Persists to local JSON + syncs to Supabase instantly
- [x] **Toasts** — Success / error / info feedback toasts
- [x] **Skeleton loading** — Shimmer cards while fetching
- [x] **Empty state** — with Refresh button CTA
- [x] Dashboard verified live at **http://localhost:3737** ✅

---

## � Phase 5: Trigger — IN PROGRESS

- [x] Supabase cloud database live and populated
- [x] Auto-sync on scrape (background thread)
- [x] Auto-sync on save/unsave (background thread)
- [ ] **Windows Task Scheduler** — set daily scrape + sync at 6:00 AM
- [ ] **Maintenance Log** finalized in `gemini.md`
- [ ] Project marked COMPLETE

### Pending Task Scheduler Setup

```bat
REM Run this once in an elevated PowerShell to schedule daily scrape:
schtasks /create /tn "ZYROX-AI-Pulse" /tr "python C:\Users\Shrikant\Desktop\antigravity Project\scrapperrr\tools\scraper.py && python C:\Users\Shrikant\Desktop\antigravity Project\scrapperrr\tools\store.py" /sc daily /st 06:00 /ru SYSTEM
```

---

## 🗒️ Goals & Notes

### North Star
> A beautiful, interactive ZYROX-branded dashboard showing the latest AI articles from the last 24 hours — automatically refreshed daily, articles saveable, cloud-backed via Supabase.

### Key Decisions
| Decision | Choice | Reason |
|----------|--------|--------|
| Local store format | JSON | Zero deps, works offline, Supabase is replica |
| Article ID | SHA256 of URL | Stable, dedup-safe across runs |
| Server | Python stdlib `http.server` | No framework deps |
| Port | 3737 | 8080 was taken by another project |
| Supabase sync | Background threads | Non-blocking — dashboard never slows down |
| RLS policy | `anon` read/write | Single-user local-first dashboard |

### Remaining Optional Enhancements
- [ ] Reddit PRAW upgrade (add credentials to `.env`)
- [ ] Ben's Bites subscriber RSS (requires newsletter subscription)
- [ ] Real-time Supabase Realtime subscriptions in dashboard
- [ ] Task Scheduler daily automation
- [ ] `gemini.md` Maintenance Log finalization
