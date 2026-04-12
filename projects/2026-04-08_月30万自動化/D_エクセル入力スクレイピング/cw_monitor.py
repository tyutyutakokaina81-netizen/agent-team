"""
cw_monitor.py — クラウドワークス受信メッセージ監視スクリプト

【使い方】
  python3 cw_monitor.py          # 5分間隔で監視
  python3 cw_monitor.py --once   # 1回だけチェック

【前提】
  - pip install playwright && playwright install chromium
  - auto_apply.py でログイン済み（.sessions/cw_session.json が存在すること）
"""

import json
import sys
import signal
import argparse
import time
from pathlib import Path
from datetime import datetime

# --- パス定義 ---
BASE_DIR = Path(__file__).parent
SESSION_FILE = BASE_DIR / ".sessions" / "cw_session.json"
OUTPUT_DIR = BASE_DIR / "outputs"
LOG_FILE = OUTPUT_DIR / "messages_log.json"

# --- 定数 ---
MESSAGES_URL = "https://crowdworks.jp/messages"
CHECK_INTERVAL = 300  # 5分（秒）

# 採用通知キーワード
HIRE_KEYWORDS = ["採用", "承認", "契約", "選定", "決定", "お願いしたい", "依頼したい", "作業を開始"]


def load_session() -> dict:
    """セッションファイルを読み込む。存在しなければエラー終了。"""
    if not SESSION_FILE.exists():
        print("❌ セッションファイルが見つかりません")
        print(f"   パス: {SESSION_FILE}")
        print("   先に auto_apply.py を実行してログインしてください")
        sys.exit(1)

    return json.loads(SESSION_FILE.read_text(encoding="utf-8"))


def load_message_log() -> list:
    """既存のメッセージログを読み込む。"""
    if LOG_FILE.exists():
        try:
            return json.loads(LOG_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError):
            return []
    return []


def save_message_log(logs: list) -> None:
    """メッセージログをJSONファイルに保存する。"""
    OUTPUT_DIR.mkdir(exist_ok=True)
    LOG_FILE.write_text(
        json.dumps(logs, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get_known_ids(logs: list) -> set:
    """既に記録済みのメッセージIDセットを返す。"""
    return {entry.get("id", "") for entry in logs if entry.get("id")}


def check_hire_keywords(text: str) -> bool:
    """テキストに採用関連キーワードが含まれるか判定する。"""
    return any(kw in text for kw in HIRE_KEYWORDS)


def fetch_messages(page) -> list:
    """メッセージ一覧ページから受信メッセージを取得する。"""
    page.goto(MESSAGES_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)

    messages = []

    # メッセージ行を取得（CWのメッセージ一覧は各行がリンク要素）
    # 複数のセレクタを試行する
    selectors = [
        ".message-list__item",
        ".message_thread",
        "[class*='message'] a",
        ".thread-list__item",
        "table.messages tr",
        ".messages-list li",
        ".message-thread-list__item",
    ]

    items = []
    for selector in selectors:
        items = page.query_selector_all(selector)
        if items:
            break

    # セレクタで見つからない場合、リンク解析にフォールバック
    if not items:
        links = page.query_selector_all("a[href*='/messages/']")
        for link in links:
            try:
                href = link.get_attribute("href") or ""
                if "/messages/" not in href:
                    continue

                # メッセージIDをURLから抽出
                msg_id = href.rstrip("/").split("/")[-1]
                if not msg_id or not msg_id.isdigit():
                    continue

                text = link.inner_text().strip()
                if not text or len(text) < 2:
                    continue

                # テキストから送信者名・タイトル・プレビューを解析
                lines = [l.strip() for l in text.split("\n") if l.strip()]
                sender = lines[0] if len(lines) >= 1 else "不明"
                title = lines[1] if len(lines) >= 2 else ""
                preview = lines[2] if len(lines) >= 3 else ""

                url = href if href.startswith("http") else f"https://crowdworks.jp{href}"

                messages.append({
                    "id": msg_id,
                    "sender": sender,
                    "title": title,
                    "preview": preview,
                    "url": url,
                })
            except Exception:
                continue
    else:
        # セレクタでアイテムが見つかった場合
        for item in items:
            try:
                # リンクを取得
                link_el = item.query_selector("a[href*='/messages/']") or item
                href = link_el.get_attribute("href") or ""

                msg_id = ""
                if "/messages/" in href:
                    msg_id = href.rstrip("/").split("/")[-1]

                text = item.inner_text().strip()
                lines = [l.strip() for l in text.split("\n") if l.strip()]

                sender = lines[0] if len(lines) >= 1 else "不明"
                title = lines[1] if len(lines) >= 2 else ""
                preview = lines[2] if len(lines) >= 3 else ""

                url = href if href.startswith("http") else f"https://crowdworks.jp{href}"

                messages.append({
                    "id": msg_id or f"unknown_{hash(text)}",
                    "sender": sender,
                    "title": title,
                    "preview": preview,
                    "url": url,
                })
            except Exception:
                continue

    return messages


def display_new_messages(new_messages: list) -> None:
    """新着メッセージをターミナルに表示する。"""
    if not new_messages:
        return

    print()
    print("=" * 60)
    print(f"  🔔 新着メッセージ: {len(new_messages)}件")
    print("=" * 60)

    for msg in new_messages:
        combined_text = f"{msg['title']} {msg['preview']}"
        is_hire = check_hire_keywords(combined_text)

        if is_hire:
            print()
            print("  🎉🎉🎉 採用・契約通知の可能性あり！ 🎉🎉🎉")

        print(f"  送信者: {msg['sender']}")
        print(f"  タイトル: {msg['title']}")
        if msg["preview"]:
            print(f"  プレビュー: {msg['preview'][:80]}")
        print(f"  URL: {msg['url']}")

        if is_hire:
            print("  ⚡ すぐに確認してください！")

        print("-" * 60)

    print()


def run_check(page, known_ids: set, logs: list) -> tuple:
    """1回のチェックを実行し、新着メッセージを処理する。

    Returns:
        (更新後のknown_ids, 更新後のlogs, 新着件数)
    """
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now_str}] メッセージをチェック中...")

    try:
        messages = fetch_messages(page)
    except Exception as e:
        print(f"  ⚠️ ページ取得エラー: {e}")
        return known_ids, logs, 0

    if not messages:
        print(f"  → メッセージが取得できませんでした（ページ構造変更の可能性）")
        return known_ids, logs, 0

    # 新着を判定
    new_messages = [m for m in messages if m["id"] not in known_ids]

    if new_messages:
        display_new_messages(new_messages)

        # ログに記録
        for msg in new_messages:
            log_entry = {
                **msg,
                "detected_at": datetime.now().isoformat(),
                "is_hire_notice": check_hire_keywords(f"{msg['title']} {msg['preview']}"),
            }
            logs.append(log_entry)
            known_ids.add(msg["id"])

        save_message_log(logs)
        print(f"  💾 {len(new_messages)}件をログに記録しました → {LOG_FILE.name}")
    else:
        print(f"  → 新着なし（既知: {len(known_ids)}件）")

    return known_ids, logs, len(new_messages)


def main():
    parser = argparse.ArgumentParser(description="CWメッセージ監視スクリプト")
    parser.add_argument(
        "--once",
        action="store_true",
        help="1回だけチェックして終了",
    )
    args = parser.parse_args()

    # セッション読み込み
    storage = load_session()

    # 既存ログ読み込み
    logs = load_message_log()
    known_ids = get_known_ids(logs)

    # Playwright初期化
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ Playwright未インストール")
        print("   pip install playwright && playwright install chromium")
        sys.exit(1)

    # Ctrl+C で安全に停止するためのフラグ
    running = True

    def signal_handler(signum, frame):
        nonlocal running
        running = False
        print("\n\n⏹️  監視を停止します...")

    signal.signal(signal.SIGINT, signal_handler)

    print()
    print("=" * 60)
    print("  📬 CWメッセージ監視ツール")
    print("=" * 60)
    if args.once:
        print("  モード: 1回チェック")
    else:
        print(f"  モード: {CHECK_INTERVAL // 60}分間隔で監視")
        print("  停止: Ctrl+C")
    print(f"  ログ: {LOG_FILE}")
    print(f"  既知メッセージ: {len(known_ids)}件")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            storage_state=storage,
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()
        page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        if args.once:
            # 1回だけチェック
            known_ids, logs, count = run_check(page, known_ids, logs)
            if count == 0:
                print("  ✅ 新着メッセージはありません")
        else:
            # ループ監視
            while running:
                known_ids, logs, _ = run_check(page, known_ids, logs)

                if not running:
                    break

                # 5分待機（1秒刻みでフラグ確認）
                next_check = datetime.now().strftime("%H:%M:%S")
                print(f"  ⏳ 次回チェック: {CHECK_INTERVAL // 60}分後")
                for _ in range(CHECK_INTERVAL):
                    if not running:
                        break
                    time.sleep(1)

        browser.close()

    # 終了メッセージ
    total = len(logs)
    hire_count = sum(1 for l in logs if l.get("is_hire_notice"))
    print()
    print("=" * 60)
    print(f"  📊 累計記録: {total}件（うち採用通知候補: {hire_count}件）")
    print(f"  💾 ログ: {LOG_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()
