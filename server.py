"""
server.py — AI Pulse Dashboard
Web server that serves the dashboard and provides the REST API.
Default port: 3737 (configurable via DASHBOARD_PORT in .env)
"""

import json
import sys
import logging
import os
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

# Add tools to the path
sys.path.insert(0, str(Path(__file__).parent / "tools"))
from store import (
    load_store, save_article, unsave_article,
    get_today_feed, get_saved_articles, get_stats, merge_and_store
)
from scraper import run_all_scrapers

from dotenv import load_dotenv
load_dotenv()

BASE_DIR = Path(__file__).parent
DASHBOARD_DIR = BASE_DIR / "dashboard"
PORT = int(os.getenv("DASHBOARD_PORT", "3737"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger("server")


class DashboardHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        log.info(f"{self.address_string()} — {format % args}")

    def send_json(self, data: dict, status: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path: Path, content_type: str = "text/html"):
        if not path.exists():
            self.send_response(404)
            self.end_headers()
            return
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # ── Dashboard UI ──────────────────────────────────────────────────
        if path == "/" or path == "/index.html":
            self.send_file(DASHBOARD_DIR / "index.html", "text/html; charset=utf-8")
            return

        if path.endswith(".css"):
            self.send_file(DASHBOARD_DIR / path.lstrip("/"), "text/css")
            return

        if path.endswith(".js"):
            self.send_file(DASHBOARD_DIR / path.lstrip("/"), "application/javascript")
            return

        # ── API Endpoints ─────────────────────────────────────────────────
        if path == "/api/feed":
            store = load_store()
            self.send_json({
                "articles": get_today_feed(store),
                "stats": get_stats(store)
            })
            return

        if path == "/api/saved":
            store = load_store()
            self.send_json({
                "articles": get_saved_articles(store),
                "stats": get_stats(store)
            })
            return

        if path == "/api/stats":
            store = load_store()
            self.send_json(get_stats(store))
            return

        if path == "/api/all":
            store = load_store()
            self.send_json({
                "articles": store.get("articles", []),
                "stats": get_stats(store)
            })
            return

        if path == "/api/refresh":
            # Trigger a fresh scrape + store merge
            log.info("[API] Manual refresh triggered")
            try:
                scrape_summary = run_all_scrapers()
                store_summary = merge_and_store()
                self.send_json({
                    "status": "ok",
                    "scrape": scrape_summary,
                    "store": store_summary
                })
            except Exception as e:
                log.error(f"[API] Refresh failed: {e}")
                self.send_json({"status": "error", "message": str(e)}, 500)
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # Read body
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""
        try:
            payload = json.loads(body) if body else {}
        except Exception:
            payload = {}

        if path == "/api/save":
            article_id = payload.get("id", "")
            if not article_id:
                self.send_json({"status": "error", "message": "Missing id"}, 400)
                return
            success = save_article(article_id)
            self.send_json({"status": "ok" if success else "not_found"})
            return

        if path == "/api/unsave":
            article_id = payload.get("id", "")
            if not article_id:
                self.send_json({"status": "error", "message": "Missing id"}, 400)
                return
            success = unsave_article(article_id)
            self.send_json({"status": "ok" if success else "not_found"})
            return

        self.send_response(404)
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


def main():
    log.info("=" * 60)
    log.info("AI Pulse Dashboard Server")
    log.info(f"  Starting on http://localhost:{PORT}")
    log.info("=" * 60)

    # Run initial scrape if no data exists
    store_file = BASE_DIR / "data" / "articles_store.json"
    if not store_file.exists():
        log.info("[Server] No data found — running initial scrape...")
        try:
            run_all_scrapers()
            merge_and_store()
        except Exception as e:
            log.error(f"[Server] Initial scrape failed: {e}")

    server = HTTPServer(("localhost", PORT), DashboardHandler)
    try:
        log.info(f"✅ Dashboard live at http://localhost:{PORT}")
        # Open browser
        import webbrowser
        webbrowser.open(f"http://localhost:{PORT}")
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Server stopped.")
        server.shutdown()


if __name__ == "__main__":
    main()
