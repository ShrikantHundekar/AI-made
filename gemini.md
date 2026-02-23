# 📜 gemini.md — Project Constitution

> **Status:** 🔴 DRAFT — Schema not yet defined. Awaiting Discovery answers.
> **Rule:** This file is LAW. Logic changes here before code changes anywhere.
> **Last Updated:** 2026-02-22

---

## 🏛️ Section 1: Project Identity

| Field            | Value                                                                                 |
|------------------|---------------------------------------------------------------------------------------|
| **Project Name** | **AI Pulse Dashboard**                                                               |
| **North Star**   | Beautiful interactive dashboard showing latest AI articles from newsletters & Reddit |
| **Protocol**     | B.L.A.S.T.                                                                           |
| **Architecture** | A.N.T. 3-Layer                                                                        |
| **Environment**  | Windows / PowerShell                                                                  |
| **Language**     | Python 3.x + HTML/CSS/JS                                                             |

---

## 🗂️ Section 2: Data Schema (THE LAW)

> ✅ **Schema CONFIRMED. Coding may proceed.**

### 2.1 — Raw Scraped Article (Input Schema)

```json
{
  "id": "string (SHA256 of url)",
  "source": "string (e.g. 'bensbites' | 'therundown' | 'reddit')",
  "title": "string",
  "summary": "string",
  "url": "string",
  "published_at": "ISO8601 datetime string",
  "scraped_at": "ISO8601 datetime string",
  "author": "string | null",
  "tags": ["string"],
  "image_url": "string | null"
}
```

### 2.2 — Saved Article Store (Output Schema)

```json
{
  "articles": [
    {
      "id": "string",
      "source": "string",
      "title": "string",
      "summary": "string",
      "url": "string",
      "published_at": "ISO8601",
      "scraped_at": "ISO8601",
      "saved": "boolean",
      "saved_at": "ISO8601 | null",
      "author": "string | null",
      "tags": ["string"],
      "image_url": "string | null"
    }
  ],
  "last_run": "ISO8601 datetime",
  "run_count": "integer"
}
```

### 2.3 — Intermediate `.tmp/` Files

```json
// .tmp/raw_bensbites.json      — raw scraped from Ben's Bites
// .tmp/raw_therundown.json     — raw scraped from The AI Rundown
// .tmp/raw_reddit.json         — raw scraped from Reddit
// .tmp/merged_articles.json    — all sources merged before dedup
// .tmp/scrape.log              — run log with timestamps
```

---

## ⚙️ Section 3: Behavioral Rules

> ✅ Confirmed from Discovery Q5.

| Rule # | Rule Description                                                              | Source          |
|--------|-------------------------------------------------------------------------------|-----------------|
| R-01   | Only ingest articles published within the last 24 hours                       | Discovery Q5    |
| R-02   | If no new articles found, do nothing — no empty state emails or alerts        | Discovery Q5    |
| R-03   | Deduplication by article URL SHA256 — never store the same article twice      | Architectural   |
| R-04   | Saved articles are PERMANENT — they persist even after 24h window expires    | Discovery Q5    |
| R-05   | Scraper runs every 24 hours (Windows Task Scheduler in Phase 5)               | Discovery Q5    |
| R-06   | All API keys / credentials must be in `.env` — never hardcoded               | Architectural   |
| R-07   | Dashboard shows two tabs: "Today's Feed" and "Saved Articles"                 | Discovery Q5    |
| R-08   | Source of Truth is local JSON file (`.tmp/articles_store.json`) until Supabase | Discovery Q3  |

---

## 🔗 Section 4: Integration Map

> ✅ Confirmed from Discovery Q2. Phase 1: Scraping only.

| Service          | Purpose                   | Auth Method           | Rate Limit        | Status        |
|------------------|---------------------------|-----------------------|-------------------|---------------|
| Ben's Bites      | AI newsletter scraping    | HTTP scrape (no auth) | Be polite, 1 req/s | ✅ Ready      |
| The AI Rundown   | AI newsletter scraping    | HTTP scrape (no auth) | Be polite, 1 req/s | ✅ Ready      |
| Reddit (r/artificial, r/MachineLearning) | AI community posts | PRAW API (free app) | 60 req/min | ⚠️ Needs Reddit app credentials |
| Supabase         | Cloud database (Phase 5)  | API Key               | Per plan          | ⬜ Phase 5   |

---

## 🏗️ Section 5: Architectural Invariants

These constraints CANNOT be violated without a schema change vote:

1. **All secrets** live in `.env` — never hardcoded.
2. **All intermediate files** go to `.tmp/` — never to root.
3. **Tools in `tools/`** are atomic (single responsibility).
4. **SOPs in `architecture/`** must be updated BEFORE the code they describe.
5. **A project is only "Complete"** when the payload reaches its cloud destination.
6. **Self-Annealing Loop** must be executed on every tool failure — no silent errors.

---

## 📂 Section 6: File Structure

```
├── gemini.md           # Project Constitution (this file)
├── task_plan.md        # Phase tracker & checklists
├── findings.md         # Research & discoveries
├── progress.md         # Execution log
├── .env                # Secrets (never committed)
├── architecture/       # Layer 1: SOPs (Markdown specs)
├── tools/              # Layer 3: Python scripts (deterministic)
└── .tmp/               # Ephemeral workspace (scratch files)
```

---

## 🔧 Section 7: Maintenance Log

> _Append entries here after Phase 5 (Trigger) and after any production change._

| Date | Change | Author | Impact |
|------|--------|--------|--------|
| 2026-02-22 | Project Constitution initialized | System Pilot | None — Draft state |
