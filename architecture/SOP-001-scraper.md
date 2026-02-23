# SOP-001: Scraper Tool — AI Pulse Dashboard

## Purpose
Scrapes Ben's Bites, The AI Rundown, and Reddit for articles from the last 24 hours.
Outputs structured JSON per the schema in `gemini.md`.

## Tool File
`tools/scraper.py`

## Inputs
- Environment variable: `LOOKBACK_HOURS` (default: 24)
- Environment variable: `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT`

## Outputs
- `.tmp/raw_bensbites.json`
- `.tmp/raw_therundown.json`
- `.tmp/raw_reddit.json`
- `.tmp/scrape.log`

## Logic

### Source 1: Ben's Bites (bensbites.beehiiv.com)
- **Method**: RSS feed via `https://bensbites.beehiiv.com/feed` or HTTP scraping of the archive page
- **Fallback**: Direct HTTP GET on homepage, parse `<article>` tags with BeautifulSoup
- **Filter**: Only articles where `pubDate` is within last 24 hours
- **Fields to extract**: title, url, summary/description, pubDate, author

### Source 2: The AI Rundown (therundown.ai)
- **Method**: HTTP GET on `https://www.therundown.ai/` then parse article cards
- **Selectors**: Look for `<a>` tags leading to `/p/` slugs
- **Filter**: Only articles where published date is within last 24 hours
- **Fields to extract**: title, url, summary (from og:description or article text), date

### Source 3: Reddit
- **Method**: PRAW (Python Reddit API Wrapper) — free, no scraping needed
- **Subreddits**: `r/artificial`, `r/MachineLearning`, `r/ArtificialIntelligence`
- **Sort**: `new` (most recent first)
- **Filter**: Only posts from last 24 hours with score > 10
- **Fields to extract**: title, url, selftext (as summary), created_utc, subreddit, score

## Edge Cases
- If a source is unreachable: log the error to `.tmp/scrape.log`, continue with other sources
- If no articles found within 24h window: write empty array `[]` to raw file
- Rate limiting: sleep 1 second between requests for HTTP scrapers
- If BeautifulSoup cannot find expected elements: fall back to `<meta property="og:*">` tags

## Known Constraints
- Ben's Bites on beehiiv may require custom RSS feed URL (check `rss.beehiiv.com/feeds/*.xml`)
- Ben's Bites also has a Substack mirror (bensbites.com) — the Substack version has a public feed
- The AI Rundown articles are behind a JavaScript renderer for dates — parse from URL slug or og:article:published_time meta tag
- Reddit API free tier: 60 requests/minute
