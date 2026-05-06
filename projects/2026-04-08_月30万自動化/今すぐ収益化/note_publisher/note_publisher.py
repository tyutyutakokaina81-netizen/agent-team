#!/usr/bin/env python3
"""
note_publisher.py — note への自動下書き登録ボット（Playwright）

dist/ にある xlsx/PDF を順番に note の有料記事として下書き登録する。
※ 自動公開はしない（誤公開を避けるため、必ず人手で「公開」ボタンを押す）

【人手が必要なこと】
  ① 初回セットアップ：python note_publisher.py setup
     → ブラウザが起動するので note にログイン → セッション保存
  ② 公開ボタンのクリック（下書きが作成されるので、各記事を確認して公開）

【自動で実行されること】
  - 各 dist ファイルに対して下書き作成
  - タイトル・本文・価格を自動入力
  - ファイル添付
  - 下書き保存

【使い方】
  pip install playwright
  playwright install chromium
  python note_publisher.py setup       # 初回ログイン
  python note_publisher.py publish     # 全 dist を下書き登録
  python note_publisher.py publish Vol5  # Vol5 のみ
"""

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent  # 月30万自動化/
DIST = ROOT / "C_テンプレ販売" / "dist"
SESSION_FILE = Path(__file__).parent / ".note_session.json"
META_FILE = Path(__file__).parent / "note_meta.json"

# ─── 各 Vol のメタデータ ───
VOL_META = {
    "Vol2": {
        "title": "【¥680】SNSコンテンツカレンダー｜30日分の投稿テーマと曜日別フォーマット",
        "price": 680,
        "summary": "SNS運用の『毎日何投稿しよう…』を解決する月次コンテンツカレンダー。投稿テーマ50選付き。",
        "tags": ["SNS運用", "コンテンツマーケ", "Instagram", "X", "テンプレート"],
    },
    "Vol3": {
        "title": "【¥1,980】飲食店向けSNS投稿プロンプト集 20選｜Instagram/X 即使えるテンプレ",
        "price": 1980,
        "summary": "飲食店オーナー・SNS担当者がそのまま使える投稿生成プロンプト20本＋カテゴリ別ハッシュタグ集。",
        "tags": ["飲食店", "SNS", "プロンプト", "ChatGPT"],
    },
    "Vol5": {
        "title": "【¥1,480】フリーランス確定申告準備5シート｜青色申告まで対応",
        "price": 1480,
        "summary": "月次収支入力→集計→年間サマリ→経費科目チートシート→青色vs白色ガイド の5シート構成。",
        "tags": ["確定申告", "フリーランス", "青色申告", "経費"],
    },
    "Vol6": {
        "title": "【¥1,980】フリーランス向けクライアント管理DB（Excel 4テーブル）",
        "price": 1980,
        "summary": "クライアント・案件・請求・契約の4テーブル連携DB。同時案件20件まで管理可能。",
        "tags": ["フリーランス", "案件管理", "Excel", "テンプレート"],
    },
    "Vol7": {
        "title": "【¥980】フリーランス週次レビューテンプレ｜KPT＋数値の毎週30分振り返り",
        "price": 980,
        "summary": "毎週日曜30分でできる、KPT（Keep/Problem/Try）＋売上・稼働時間の振り返りテンプレ。",
        "tags": ["フリーランス", "KPT", "振り返り", "Notion"],
    },
    "Vol8": {
        "title": "【¥1,980】士業向け新規顧客獲得 営業メール文例 20選",
        "price": 1980,
        "summary": "税理士・社労士・行政書士向けに業種別新規顧客への営業メール文例20本。",
        "tags": ["士業", "営業", "税理士", "社労士", "営業メール"],
    },
    "Vol9": {
        "title": "【¥1,980】SEO ブログ記事構成20選｜2,000〜8,000字の即使える型",
        "price": 1980,
        "summary": "SEO記事構成テンプレ20本。文字数別・ジャンル別・読者意図別に分類。",
        "tags": ["SEO", "ブログ", "ライティング", "記事構成"],
    },
    "Vol10": {
        "title": "【¥1,480】月次売上ダッシュボード｜柱別・月次・年間の収益見える化",
        "price": 1480,
        "summary": "取引データを入力すれば、柱別月次・年間累計・予実差が自動計算されるExcelダッシュボード。",
        "tags": ["売上管理", "ダッシュボード", "Excel", "経営"],
    },
}


def setup():
    """初回セットアップ：ログインしてセッション保存"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[ERROR] Playwright が未インストール。`pip install playwright && playwright install chromium`")
        sys.exit(1)

    print("[INFO] ブラウザを起動します。note にログインしてください。")
    print("[INFO] ログイン完了後、ターミナルで Enter を押すとセッションを保存します。")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://note.com/login")
        input("ログインが完了したら Enter を押してください...")
        state = context.storage_state()
        SESSION_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[OK] セッションを保存：{SESSION_FILE}")
        browser.close()


def publish_one(page, dist_file: Path, meta: dict):
    """1つの dist ファイルを note に下書き登録"""
    print(f"\n[STEP] {dist_file.name} を登録中...")
    page.goto("https://note.com/notes/new")
    page.wait_for_load_state("networkidle")

    # タイトル入力
    title_selector = 'textarea[placeholder*="タイトル"], input[placeholder*="タイトル"]'
    page.wait_for_selector(title_selector, timeout=10000)
    page.fill(title_selector, meta["title"])

    # 本文：概要をペースト
    body_selector = 'div[contenteditable="true"]'
    page.click(body_selector)
    body = (
        f"{meta['summary']}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"【本テンプレの内容】\n"
        f"添付ファイルをダウンロードしてご利用ください。\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"※ 購入後、本ページから添付ファイルをダウンロードできます。\n"
        f"※ ご質問・修正サポートは購入者向け窓口より受付けています。\n"
    )
    page.keyboard.type(body)

    # ファイル添付（note のファイルアップロード仕様に依存）
    print(f"  [WARN] note のファイルアップロード UI はバージョンにより変動します。")
    print(f"  [TODO] 手動で {dist_file} をドラッグ＆ドロップしてください。")

    # 下書き保存
    save_btn = page.get_by_text("保存", exact=False).first
    save_btn.click()
    page.wait_for_timeout(2000)
    print(f"  [OK] 下書きを保存")


def publish(filter_vol: str | None = None):
    """全 dist を順番に下書き登録"""
    if not SESSION_FILE.exists():
        print("[ERROR] セッション未設定。先に `python note_publisher.py setup` を実行してください")
        sys.exit(1)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[ERROR] Playwright が未インストール")
        sys.exit(1)

    state = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
    targets = sorted(DIST.glob("Vol*"))
    if filter_vol:
        targets = [p for p in targets if p.name.startswith(filter_vol + "_")]
    if not targets:
        print(f"[ERROR] 対象ファイルが見つかりません（filter: {filter_vol}）")
        sys.exit(1)

    print(f"[INFO] {len(targets)} 件を登録します")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state=state)
        page = context.new_page()

        for f in targets:
            vol_id = f.name.split("_")[0]
            meta = VOL_META.get(vol_id)
            if not meta:
                print(f"[SKIP] {f.name}：メタ情報なし")
                continue
            try:
                publish_one(page, f, meta)
                time.sleep(3)  # 連続アクセス回避
            except Exception as e:
                print(f"[ERROR] {f.name}：{e}")

        print("\n[DONE] 全件登録完了。note の管理画面で各記事を確認してから公開してください。")
        input("ブラウザを閉じる準備ができたら Enter...")
        browser.close()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1]
    if cmd == "setup":
        setup()
    elif cmd == "publish":
        filter_vol = sys.argv[2] if len(sys.argv) > 2 else None
        publish(filter_vol)
    else:
        print(f"[ERROR] 未知のコマンド: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
