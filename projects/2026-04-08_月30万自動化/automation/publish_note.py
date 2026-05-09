"""
publish_note.py — note に Vol.2/3 を公開（タイトル・本文・公開設定・価格・タグまで自動入力）

実行方法:
  python3 publish_note.py vol2     # Vol.2 のみ
  python3 publish_note.py vol3     # Vol.3 のみ
  python3 publish_note.py all      # 両方

最終「公開する」ボタンの押下のみ人手（誤公開防止＋規約遵守）。
"""

import sys
import time
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

        # ─── 公開設定パネルを開く ───
        time.sleep(1.5)
        opened_settings = False
        # ヘッダー右の「公開設定」ボタンの候補
        for sel in [
            "button:has-text('公開設定')",
            "button:has-text('公開に進む')",
            "button:has-text('公開する')",
            "[data-testid='publish-button']",
            "header button",
        ]:
            try:
                btn = page.query_selector(sel)
                if btn and btn.is_visible():
                    btn.click()
                    opened_settings = True
                    print(f"  ✓ 公開設定パネルを開きました ({sel})")
                    break
            except Exception:
                continue
        if not opened_settings:
            print("  ⚠️  公開設定パネルが開けませんでした")

        time.sleep(1.5)

        # ─── 有料記事 → 価格入力 ───
        price_set = False
        # 「有料」タブ／ラジオボタン候補
        for sel in [
            "button:has-text('有料')",
            "label:has-text('有料')",
            "[role='tab']:has-text('有料')",
        ]:
            try:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    el.click()
                    print(f"  ✓ 有料記事タブを選択 ({sel})")
                    break
            except Exception:
                continue
        time.sleep(1)

        # 価格入力欄
        for sel in [
            "input[placeholder*='価格']",
            "input[placeholder*='円']",
            "input[type='number']",
            "input[name*='price']",
        ]:
            try:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    el.fill(str(target["price_jpy"]))
                    price_set = True
                    print(f"  ✓ 価格 ¥{target['price_jpy']:,} を入力 ({sel})")
                    break
            except Exception:
                continue
        if not price_set:
            print(f"  ⚠️  価格欄が見つかりません（手動で {target['price_jpy']} を入力してください）")

        time.sleep(0.8)

        # ─── タグ追加 ───
        tags_added = 0
        tag_sel = None
        for sel in [
            "input[placeholder*='ハッシュタグ']",
            "input[placeholder*='タグ']",
            "input[name*='tag']",
            "input[type='text'][placeholder*='追加']",
        ]:
            el = page.query_selector(sel)
            if el and el.is_visible():
                tag_sel = sel
                break

        if tag_sel:
            for tag in target["tags"]:
                try:
                    el = page.query_selector(tag_sel)
                    if el:
                        el.click()
                        page.keyboard.type(tag)
                        time.sleep(0.4)
                        page.keyboard.press("Enter")
                        time.sleep(0.5)
                        tags_added += 1
                except Exception:
                    pass
            print(f"  ✓ タグ {tags_added}/{len(target['tags'])} 件追加")
        else:
            print(f"  ⚠️  タグ欄が見つかりません（手動で追加: {', '.join(target['tags'])}）")

        time.sleep(0.8)

        # ─── 確認ステップ（最終公開ボタンは人手）───
        print("\n" + "─" * 60)
        print("  ✅ 自動入力完了:")
        print(f"     タイトル: {'OK' if title_filled else '✗ 手動'}")
        print(f"     本文:     {'OK' if body_filled else '✗ 手動'}")
        print(f"     設定パネル: {'OK' if opened_settings else '✗ 手動'}")
        print(f"     価格:     {'OK' if price_set else '✗ 手動'}")
        print(f"     タグ:     {tags_added}/{len(target['tags'])}件")
        print("─" * 60)
        print("\n  最終確認 → 「公開する」ボタン（オーナーが押す）")
        print("  完了したらターミナルで Enter...")
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
