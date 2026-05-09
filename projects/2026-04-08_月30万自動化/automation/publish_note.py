"""
publish_note.py — note に Vol.2/3 を公開（属性ベースの寛容なセレクタ）

実行方法:
  python3 publish_note.py vol2 | vol3 | all

注: note の DOM 構造変化に強くするため、固定セレクタでなく
属性（placeholder / aria-label / name / テキスト）で全探索する方式。
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _browser import open_browser  # noqa: E402

URL_STORE = Path(__file__).parent / ".published_urls.json"
DEBUG_DIR = Path(__file__).parent / "_debug"
DEBUG_DIR.mkdir(exist_ok=True)


def _save_url(key: str, url: str):
    data = {}
    if URL_STORE.exists():
        try:
            data = json.loads(URL_STORE.read_text(encoding="utf-8"))
        except Exception:
            pass
    data[key] = url
    URL_STORE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


VOL_KEY = "_key"

VOL2 = {
    VOL_KEY: "vol2",
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

■ 内容
・Googleスプレッドシート（コピーして使用）
・投稿テーマ案50個リスト付き

■ 価格：680円
""",
}

VOL3 = {
    VOL_KEY: "vol3",
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

■ 価格：1,980円
一度購入すれば何度でも使えます。
""",
}


# ─────────────────────────────────────────────
# 寛容なエレメント探索ユーティリティ
# ─────────────────────────────────────────────

def _find_input_by_attr(page, keywords: list[str], input_type: str = "input") -> object | None:
    """属性（placeholder/aria-label/name）に keyword を含む input/textarea を全探索"""
    selectors = [input_type, "textarea", "[contenteditable='true']"]
    for sel in selectors:
        try:
            elements = page.query_selector_all(sel)
        except Exception:
            continue
        for el in elements:
            try:
                if not el.is_visible():
                    continue
                attrs = []
                for attr in ["placeholder", "aria-label", "name", "data-placeholder"]:
                    v = el.get_attribute(attr)
                    if v:
                        attrs.append(v)
                combined = " ".join(attrs).lower()
                if any(k.lower() in combined for k in keywords):
                    return el
            except Exception:
                continue
    return None


def _click_button_by_text(page, texts: list[str]) -> str | None:
    """ボタン（button/role=button/a）のテキストに texts のいずれかを含むものをクリック"""
    selectors = ["button", "[role='button']", "a", "div[role='button']"]
    for sel in selectors:
        try:
            elements = page.query_selector_all(sel)
        except Exception:
            continue
        for el in elements:
            try:
                if not el.is_visible():
                    continue
                content = (el.inner_text() or "").strip()
                if any(t in content for t in texts):
                    el.click()
                    return f"{sel} [{content[:30]}]"
            except Exception:
                continue
    return None


def _wait_for_editor(page, timeout: int = 60) -> object | None:
    """タイトル欄が表示されるまで最大 timeout 秒待つ"""
    waited = 0
    hint_shown = False
    while waited < timeout:
        el = _find_input_by_attr(page, ["タイトル", "title"], "textarea")
        if not el:
            el = _find_input_by_attr(page, ["タイトル", "title"], "input")
        if el:
            return el
        time.sleep(2)
        waited += 2
        if waited == 6 and not hint_shown:
            print("\n  ⏳ エディタ画面が検出できません。")
            print("     未ログインなら note にログインしてください")
            print("     既ログインなら「投稿」「+」「書く」ボタンを押してエディタを開いてください")
            print(f"     最大 {timeout} 秒待機します...")
            hint_shown = True
    return None


# ─────────────────────────────────────────────
# 公開フロー
# ─────────────────────────────────────────────

def open_note_editor(target: dict):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[ERROR] pip install playwright && playwright install chromium")
        sys.exit(1)

    with sync_playwright() as p:
        ctx = open_browser(p)
        page = ctx.new_page()

        # ─── エディタへ遷移 ───
        page.goto("https://note.com/notes/new", timeout=30000)
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass
        print(f"\n[note] URL: {page.url}")
        print(f"        title: {page.title()}")

        # エディタ要素を待つ
        title_input = _wait_for_editor(page, timeout=60)
        try:
            page.screenshot(path=str(DEBUG_DIR / f"01_after_load_{target[VOL_KEY]}.png"))
        except Exception:
            pass

        # ─── タイトル ───
        title_filled = False
        if title_input:
            try:
                title_input.click()
                title_input.fill("")
                title_input.fill(target["title"])
                title_filled = True
                print(f"  ✓ タイトル入力")
            except Exception as e:
                print(f"  ⚠️  タイトル入力失敗: {e}")
        else:
            print(f"  ⚠️  タイトル欄が見つかりません（手動で入力してください）")

        # ─── 本文（contenteditable をすべて探し、最後の visible なものに入力）───
        body_filled = False
        try:
            editables = page.query_selector_all("[contenteditable='true']")
            visibles = [e for e in editables if e.is_visible()]
            # 最後（タイトルの次）が本文と仮定
            if len(visibles) >= 2:
                body_el = visibles[-1]
            elif visibles:
                body_el = visibles[0]
            else:
                body_el = None
            if body_el:
                body_el.click()
                page.keyboard.type(target["body"])
                body_filled = True
                print(f"  ✓ 本文入力")
        except Exception as e:
            print(f"  ⚠️  本文入力失敗: {e}")
        if not body_filled:
            print(f"  ⚠️  本文欄が見つかりません（手動で貼り付けてください）")

        time.sleep(1.5)
        try:
            page.screenshot(path=str(DEBUG_DIR / f"02_after_input_{target[VOL_KEY]}.png"))
        except Exception:
            pass

        # ─── 公開設定パネルへ ───
        clicked = _click_button_by_text(page, ["公開に進む", "公開設定", "公開する"])
        opened_settings = bool(clicked)
        if clicked:
            print(f"  ✓ 公開設定 → {clicked}")
        else:
            print(f"  ⚠️  公開設定ボタンが見つかりません")
        time.sleep(2.5)
        try:
            page.screenshot(path=str(DEBUG_DIR / f"03_settings_{target[VOL_KEY]}.png"))
        except Exception:
            pass

        # ─── 有料記事タブ（あれば、複数経路で）───
        # 1) ボタン/role=button のテキスト
        _click_button_by_text(page, ["有料"])
        time.sleep(1.0)
        # 2) ラジオ・ラベル系
        try:
            for sel in ["label", "span", "div"]:
                for el in page.query_selector_all(sel):
                    if not el.is_visible():
                        continue
                    txt = (el.inner_text() or "").strip()
                    if txt == "有料" or txt == "有料記事":
                        el.click()
                        break
        except Exception:
            pass
        time.sleep(2.5)

        # ─── 価格入力（多段階探索）───
        price_set = False

        # (a) 属性キーワード探索
        price_el = _find_input_by_attr(
            page,
            ["価格", "円", "price", "金額", "値段", "料金", "amount"],
            "input",
        )
        # (b) type=number で visible なもの
        if not price_el:
            try:
                num_inputs = [e for e in page.query_selector_all("input[type='number']") if e.is_visible()]
                if num_inputs:
                    price_el = num_inputs[0]
            except Exception:
                pass
        # (c) 価格/金額ラベル直後の input/textbox を特定
        if not price_el:
            try:
                price_el = page.evaluate_handle("""() => {
                    const all = Array.from(document.querySelectorAll('label, span, div, p'));
                    for (const e of all) {
                        const t = (e.innerText || '').trim();
                        if (t === '価格' || t === '金額' || t === '料金') {
                            // 親要素や近傍の input を探す
                            let parent = e.parentElement;
                            for (let i = 0; i < 4 && parent; i++) {
                                const inp = parent.querySelector('input');
                                if (inp) return inp;
                                parent = parent.parentElement;
                            }
                            // 兄弟も
                            let sib = e.nextElementSibling;
                            while (sib) {
                                const inp = sib.querySelector ? sib.querySelector('input') : null;
                                if (inp) return inp;
                                if (sib.tagName === 'INPUT') return sib;
                                sib = sib.nextElementSibling;
                            }
                        }
                    }
                    return null;
                }""").as_element()
            except Exception:
                pass

        if price_el:
            try:
                price_el.click()
                # 既存値クリア
                try:
                    price_el.fill("")
                except Exception:
                    pass
                price_el.fill(str(target["price_jpy"]))
                price_set = True
                print(f"  ✓ 価格 ¥{target['price_jpy']:,} 入力")
            except Exception as e:
                print(f"  ⚠️  価格入力失敗: {e}")

        if not price_set:
            print(f"  ⚠️  価格欄が見つかりません（手動で {target['price_jpy']} を入力）")

        time.sleep(0.8)

        # ─── タグ ───
        tags_added = 0
        tag_el = _find_input_by_attr(
            page,
            ["ハッシュタグ", "タグ", "#", "hashtag", "tag"],
            "input",
        )
        if tag_el:
            for tag in target["tags"]:
                try:
                    tag_el.click()
                    page.keyboard.type(tag)
                    time.sleep(0.4)
                    page.keyboard.press("Enter")
                    time.sleep(0.5)
                    tags_added += 1
                except Exception:
                    continue
            print(f"  ✓ タグ {tags_added}/{len(target['tags'])} 件追加")
        else:
            print(f"  ⚠️  タグ欄が見つかりません（手動で追加: {', '.join(target['tags'])}）")

        time.sleep(0.8)
        try:
            page.screenshot(path=str(DEBUG_DIR / f"04_pre_publish_{target[VOL_KEY]}.png"))
        except Exception:
            pass

        # ─── 確認 + 自動公開 ───
        print("\n" + "─" * 60)
        print(f"  自動入力結果 / {target['title'][:40]}")
        print(f"     タイトル:   {'OK' if title_filled else '✗'}")
        print(f"     本文:       {'OK' if body_filled else '✗'}")
        print(f"     公開パネル: {'OK' if opened_settings else '✗'}")
        print(f"     価格:       {'OK' if price_set else '✗'}")
        print(f"     タグ:       {tags_added}/{len(target['tags'])}件")
        print("─" * 60)

        # 入力が不十分な場合、手動補完を促してから公開
        if not (title_filled and body_filled and price_set):
            print("\n  ⚠️  自動入力が不十分です。ブラウザで足りない項目を手動入力してから、")
            print("     「公開する」をオーナーが押してください。完了後、このターミナルで Enter。")
            input()
        else:
            print("\n  ⏰ 5 秒後に「公開する」を自動クリックします（Ctrl+C で中止可）")
            for i in range(5, 0, -1):
                print(f"     {i}...", end="\r", flush=True)
                time.sleep(1)
            print("     公開実行    ")

            published = _click_button_by_text(page, ["公開する", "投稿する", "公開"])
            if not published:
                print("  ⚠️  公開ボタンが見つかりません。手動で押してから Enter...")
                input()
            else:
                print(f"  ✓ クリック → {published}")

        # ─── URL 取得 ───
        time.sleep(5)
        try:
            page.wait_for_url("**/n/**", timeout=15000)
        except Exception:
            pass
        current_url = page.url
        if "/n/" in current_url:
            print(f"  ✅ 公開完了: {current_url}")
            _save_url(target.get(VOL_KEY, "unknown"), current_url)
        else:
            print(f"  公開後の URL を取得できず（現在: {current_url}）")
            url = input("  公開済みなら note 記事 URL を貼り付けてください（空 Enter でスキップ）: ").strip()
            if url:
                _save_url(target.get(VOL_KEY, "unknown"), url)

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
