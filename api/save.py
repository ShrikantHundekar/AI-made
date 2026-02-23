"""
api/save.py — POST /api/save   |  POST /api/unsave
Handles save and hard-delete (unsave) in Supabase.
Vercel Serverless Function (Python 3.12)
"""
import json
from http.server import BaseHTTPRequestHandler
from datetime import datetime, timezone
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from _supabase import get_client


class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        try:
            length  = int(self.headers.get("Content-Length", 0))
            body    = self.rfile.read(length) if length else b""
            payload = json.loads(body) if body else {}
        except Exception:
            payload = {}

        article_id = payload.get("id", "").strip()
        if not article_id:
            self._send_json({"status": "error", "message": "Missing id"}, 400)
            return

        # Detect route: /api/save vs /api/unsave
        from urllib.parse import urlparse
        path = urlparse(self.path).path

        try:
            client = get_client()

            if path.endswith("/unsave"):
                # Hard delete from Supabase
                client.table("articles").delete().eq("id", article_id).execute()
                self._send_json({"status": "ok", "action": "deleted"})

            else:
                # Mark as saved
                client.table("articles").update({
                    "saved":    True,
                    "saved_at": datetime.now(timezone.utc).isoformat()
                }).eq("id", article_id).execute()
                self._send_json({"status": "ok", "action": "saved"})

        except Exception as e:
            self._send_json({"status": "error", "message": str(e)}, 500)

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)
