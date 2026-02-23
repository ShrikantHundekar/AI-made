"""
api/_supabase.py — Shared Supabase client for Vercel serverless functions.
Imported by all /api/*.py handlers. Not a route itself (underscore prefix).
"""
import os
from supabase import create_client

def get_client():
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_ANON_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in Vercel env vars")
    return create_client(url, key)

LOOKBACK_HOURS = int(os.environ.get("LOOKBACK_HOURS", "24"))
