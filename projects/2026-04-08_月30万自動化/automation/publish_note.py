"""
publish_note.py — note に Vol.2/3 を公開（半自動）

実行方法:
  python3 publish_note.py vol2     # Vol.2 のみ
  python3 publish_note.py vol3     # Vol.3 のみ
  python3 publish_note.py all      # 両方

永続プロファイル方式（_browser.py）でログイン状態を維持する。
最終公開ボタンの押下は人手（規約遵守＋誤公開防止）。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _browser import open_browser  # noqa: E402

# ─────────────────────────────────────────────
# 公開コンテンツ定義
# ─────────────────────────────────────────────

VOL2 = {
    "title": "【コピーして使う】SNS投稿カレンダー｜月の投稿を30分で計画するスプレッドシート",
    "price_jpy": 680,
    "tags": ["SNS運用", "フリーランス", "テンプレート", "スプレッドシート", "副業"],
    "body": """「毎日何を投稿すればいいかわからない」
「投稿が思いつかなくて結局サボってしまう」

このカレンダーを使えば、月初の30分で
1ヶ月分の投稿計画が完成します。

■ できること
✅ 月別カレンダー形式で投稿を管理
✅ Instagram・X・Facebookを一括管理
✅ 投稿テーマ・ハッシュタグ・ステータスを一覧化
✅ 月別の投稿数・エンゲージメントを記録

■ 内容
・Googleスプレッドシート（コピーして使用）
・投稿テーマ案50個リスト付き（5カテゴリ×10個）
・媒体別ハッシュタグ雛形

■ 価格：680円
""",
}

VOL3 = {
    "title": "【コピペで使える】飲食店オーナー向けChatGPT・Claudeプロンプト集20選｜SNS投稿文を30秒で生成",
    "price_jpy": 1980,
    "tags": ["飲食店", "AI", "プロンプト", "Instagram", "SNS集客"],
    "body": """「SNSに投稿したいけど文章が思いつかない」
「毎日投稿するネタがない」
「AIを使いたいけどうまく指示できない」

このプロンプト集があれば、
AIに貼り付けるだけで投稿文が完成します。

■ 収録プロンプト20選
1. 新メニュー紹介投稿
2. 季節限定メニューの告知
3. スタッフ紹介投稿
（…20件すべて含まれます）

■ 使い方
ChatGPT・Claude・Geminiなど
主要なAIすべてで使えます。
[ ] 部分をお店の情報に書き換えて貼り付けるだけ。

■ 価格：1,980円
一度購入すれば何度でも使えます。
""",
}


def open_note_editor(target: dict):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[ERROR] pip install playwright && playwright install chromium")
        sys.exit(1)

    with sync_playwright() as p:
        ctx = open_browser(p)
        page = ctx.new_page()
        page.goto("https://note.com/notes/new")
        try:
            page.wait_for_load_state("domcontentloaded", timeout=15000)
        except Exception:
            pass

        print(f"\n[note] エディタを開きました")
        print(f"  タイトル: {target['title']}")
        print(f"  価格: ¥{target['price_jpy']:,}")
        print(f"  タグ: {', '.join(target['tags'])}")

        # タイトル欄
        title_filled = False
        for sel in [
            "textarea[placeholder*='タイトル']",
            "input[placeholder*='タイトル']",
            "[contenteditable='true'][data-placeholder*='タイトル']",
        ]:
            try:
                el = page.query_selector(sel)
                if el:
                    el.fill(target["title"])
                    title_filled = True
                    break
            except Exception:
                continue
        if not title_filled:
            print("  ⚠️  タイトル欄が見つかりません（手動で入力してください）")

        # 本文欄
        body_filled = False
        for sel in [
            "div.note-common-styles__textnote-body[contenteditable='true']",
            "[role='textbox']",
            "div[contenteditable='true']",
        ]:
            try:
                els = page.query_selector_all(sel)
                if els:
                    target_el = els[-1] if len(els) > 1 else els[0]
                    target_el.click()
                    page.keyboard.type(target["body"])
                    body_filled = True
                    break
            except Exception:
                continue
        if not body_filled:
            print("  ⚠️  本文欄が見つかりません（手動で貼り付けてください）")

        print("\n  ✅ 入力完了。あとは note 画面で：")
        print("     1. 公開設定 → 有料記事 → 価格を入力")
        print(f"     2. タグを追加: {', '.join(target['tags'])}")
        print("     3. 「公開する」ボタンを押す")
        print("\n  ブラウザは開いたまま。完了したらターミナルで Enter...")
        input()

        ctx.close()


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    targets = []
    if cmd in ("vol2", "all"):
        targets.append(VOL2)
    if cmd in ("vol3", "all"):
        targets.append(VOL3)
    if not targets:
        print("使い方: python3 publish_note.py {vol2|vol3|all}")
        sys.exit(1)
    for t in targets:
        open_note_editor(t)


if __name__ == "__main__":
    main()
