#!/usr/bin/env python3
"""
mac_booth_refresh.py — 毎週火曜に商品を更新（BOOTH検索順位を維持）
商品の説明文に空白を追加/削除して「更新日時」を動かす
"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path

AGENT_DIR = Path(__file__).parent
SESSION_FILE = AGENT_DIR / ".sessions" / "booth_session.json"


def refresh_cookie():
    try:
        import browser_cookie3
        jar = browser_cookie3.chrome(domain_name='.booth.pm')
        cookies = {c.name: c.value for c in jar}
        if not cookies:
            jar = browser_cookie3.safari(domain_name='.booth.pm')
            cookies = {c.name: c.value for c in jar}
        if cookies:
            cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())
            SESSION_FILE.write_text(
                json.dumps({"cookie": cookie_str, "updated": datetime.now().isoformat()}),
                encoding="utf-8"
            )
            return cookie_str
    except Exception as e:
        print(f"クッキー再取得失敗: {e}")
    return None


def get_session():
    import requests
    cookie_str = None
    if SESSION_FILE.exists():
        try:
            data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
            cookie_str = data.get("cookie", "")
        except Exception:
            pass
    if not cookie_str:
        cookie_str = refresh_cookie()
    if not cookie_str:
        return None
    sess = requests.Session()
    sess.headers.update({"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"})
    for part in cookie_str.split(";"):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            sess.cookies.set(k.strip(), v.strip(), domain=".booth.pm")
    return sess


def main():
    try:
        import requests
    except ImportError:
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "requests", "-q"])
        import requests

    sess = get_session()
    if not sess:
        print("セッション取得失敗")
        return

    # 商品一覧を取得
    r = sess.get("https://manage.booth.pm/items", timeout=15)
    if "sign_in" in r.url:
        print("セッション無効")
        return

    # 商品IDを抽出
    item_ids = re.findall(r'/items/(\d+)/edit', r.text)
    if not item_ids:
        print("商品が見つかりません")
        return

    print(f"[{datetime.now().strftime('%H:%M')}] {len(item_ids)}件の商品を更新中...")

    for item_id in item_ids[:4]:  # 最大4件
        edit_url = f"https://manage.booth.pm/items/{item_id}/edit"
        r = sess.get(edit_url, timeout=15)

        # CSRFトークン
        m = re.search(r'<meta[^>]+name=["\']csrf-token["\'][^>]+content=["\']([^"\']+)["\']', r.text)
        if not m:
            continue
        csrf = m.group(1)

        # 説明文を取得して末尾に空白を追加/削除（実質変更なし）
        desc_m = re.search(r'name="item\[description\]"[^>]*>(.*?)</textarea>', r.text, re.DOTALL)
        description = desc_m.group(1).rstrip() if desc_m else ""

        sess.post(
            f"https://manage.booth.pm/items/{item_id}",
            data={
                "_method": "patch",
                "authenticity_token": csrf,
                "item[description]": description + " ",
            },
            timeout=20,
            allow_redirects=True,
        )
        print(f"  ✅ 商品ID {item_id} 更新")

    print("完了")


if __name__ == "__main__":
    main()
