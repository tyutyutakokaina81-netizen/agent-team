#!/usr/bin/env python3
"""
mac_debug_booth.py — BOOTH HTMLの実際の構造を確認して問題を診断
"""
import json, re, sys
from pathlib import Path

SESSION_FILE = Path(__file__).parent / ".sessions" / "booth_session.json"

try:
    import requests
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "requests", "-q"])
    import requests

if not SESSION_FILE.exists():
    print("セッションファイルなし")
    sys.exit(1)

data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
cookie_str = data.get("cookie", "")

sess = requests.Session()
sess.headers.update({"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"})
for part in cookie_str.split(";"):
    part = part.strip()
    if "=" in part:
        k, v = part.split("=", 1)
        sess.cookies.set(k.strip(), v.strip(), domain=".booth.pm")

print("=== /items/new の最初の3000文字 ===")
r = sess.get("https://manage.booth.pm/items/new", timeout=15)
print(f"Status: {r.status_code}, URL: {r.url}")
print(r.text[:3000])

print("\n=== csrf関連の検索結果 ===")
for pat in ["csrf", "authenticity", "token", "_token"]:
    found = re.findall(rf'.{{0,60}}{pat}.{{0,60}}', r.text, re.IGNORECASE)
    for f in found[:3]:
        print(f"  [{pat}] {f.strip()}")
