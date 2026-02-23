"""
api/saved.py — GET /api/saved
Returns saved articles from Supabase.
Vercel Serverless Function (Python 3.12)
"""
import json
from http.server import BaseHTTPRequestHandler
from datetime import datetime, timezone, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _supabase import get_client, LOOKBACK_HOURS


class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        try:
            client = get_client()

            resp = (
                client.table("articles")
                .select("*")
                .eq("saved", True)
                .order("saved_at", desc=True)
                .execute()
            )
            articles = resp.data or []

            # Stats
            all_total  = client.table("articles").select("id", count="exact").execute()
            cutoff     = (datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)).isoformat()
            today_r    = client.table("articles").select("id", count="exact").gte("published_at", cutoff).execute()
            last_run_r = client.table("scrape_runs").select("run_at").order("run_at", desc=True).limit(1).execute()

            sources = {}
            for a in articles:
                src = a.get("source", "unknown")
                sources[src] = sources.get(src, 0) + 1

            stats = {
                "total_articles": all_total.count or 0,
                "today_count":    today_r.count or 0,
                "saved_count":    len(articles),
                "sources":        sources,
                "last_run":       last_run_r.data[0]["run_at"] if last_run_r.data else None,
            }

            self._send_json({"articles": articles, "stats": stats})

        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)
