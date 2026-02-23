# 🔍 Findings — Research, Discoveries & Constraints

> **Purpose:** Log all research findings, API quirks, rate limits, external service constraints, and architectural discoveries here. Updated throughout the project lifecycle.
> **Last Updated:** 2026-02-22

---

## 📡 External Services & APIs

> _To be populated after Discovery Q2 is answered._

| Service | Status | Notes / Constraints |
|---------|--------|---------------------|
| Ben's Bites | ⚠️ Partial | beehiiv.com feeds return HTML but require subscriber auth; Substack mirror RSS `bensbites.com/feed` found but 0 entries in 24h window on first test; HTML scraper fallback available |
| The AI Rundown | ✅ Working | Scrapes homepage `/p/` slugs + fetches article meta. 10 articles found in first test run. |
| Reddit (public JSON API) | ✅ Working | Public JSON API `reddit.com/r/{sub}/new.json` works without auth. 5+ posts found per run. |
| Reddit (PRAW) | ⚠️ Needs credentials | Free app at reddit.com/prefs/apps — works once client_id/secret set in .env |

---

## 🔗 Data Source Analysis

> _To be populated after Discovery Q3 is answered._

| Source | Type | Access Method | Auth Required? |
|--------|------|--------------|----------------|
| bensbites.beehiiv.com | Newsletter | HTTP scrape + RSS fallback | No (public articles) |
| therundown.ai | Newsletter | HTTP scrape of /p/ slugs | No |
| reddit.com/r/artificial | Community | Public JSON API | No |
| reddit.com/r/MachineLearning | Community | Public JSON API | No |
| reddit.com/r/ArtificialIntelligence | Community | Public JSON API | No |

---

## 🐛 Known Issues & Constraints

> _Updated as errors are encountered per the Self-Annealing loop._

| # | Issue | Root Cause | Resolution | Date |
|---|-------|-----------|------------|------|
| — | —     | —          | —          | —    |

---

## 📚 Research References

> _GitHub repos, docs, and resources found during Blueprint phase._

| Resource | URL | Relevance |
|----------|-----|----------|
| PRAW Python Reddit API Wrapper | https://praw.readthedocs.io | Reddit scraping |
| feedparser library | https://feedparser.readthedocs.io | RSS/Atom feed parsing |
| BeautifulSoup4 | https://pypi.org/project/beautifulsoup4/ | HTML scraping |
| Ben's Bites Beehiiv | https://bensbites.beehiiv.com | Primary source (auth-gated) |
| The Rundown AI | https://www.therundown.ai | Primary source (public) |

---

## 💡 Key Learnings

> _Architectural discoveries that inform design decisions._

- **Ben's Bites on beehiiv**: Feed endpoints return 404 or subscriber-only content. The RSS approach needs the specific publication ID (XXXX) in `rss.beehiiv.com/feeds/XXXX.xml` which is not publicly listed. **Fix**: HTML scrape /archive or /p/ pages directly.
- **The Rundown**: Homepage exposes `/p/<slug>` links. Each article page has `<meta property="og:description">` and `<meta property="article:published_time">` — reliable enough for scraping.
- **Reddit public API**: `https://www.reddit.com/r/{sub}/new.json?limit=25` requires only a User-Agent header. Returns 25 posts per subreddit. Rate limit: ~60 req/min. No auth for basic reading.
- **Date filtering**: All 3 sources have been tested. 24h filter works correctly.
- **Server**: Python stdlib `http.server` — no extra deps needed. Serves dashboard files + REST API on port 8080.
