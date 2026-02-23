"""
api/unsave.py — POST /api/unsave
Alias that delegates to save.py handler (same logic, different path).
Vercel Serverless Function (Python 3.12)
"""
# Re-use the save handler — it reads self.path to distinguish /save vs /unsave
from save import handler
