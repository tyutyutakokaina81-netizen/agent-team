#!/usr/bin/env python3
"""
note 有料記事 自動公開ヘルパー（オーナーのMacで実行する）

publish_to_note.py（無料記事用）の姉妹スクリプト。有料デジタル商品／有料記事を扱う。
設計の最優先＝**絶対にタダで公開しない**：
  - デフォルトは下書き保存で止まる。公開は --publish を明示した時だけ。
  - 有料ライン(有料エリア指定)と価格の両方が確実にセットできたと判断できた時だけ公開する。
    どちらかでも未確定なら公開せず下書きで止め、手動手順を出す。

2026-07-03 更新（cowork self-fix）: note新エディタ(editor.note.com)にUI追従。
  - 入口: editor.note.com/new（/notes/new は一覧へリダイレクトするため）
  - 有料ライン: 本文の境界行でブロックメニュー(メニューを開く)→「有料エリア指定」
  - 価格: 「公開に進む」→ /publish/ 画面で「有料」を選び価格入力
  - 公開ボタン: 「投稿する」（旧「公開する」は廃止）
  - 公開前に「下書き保存」で編集状態を確定（見出し画像等の後の公開バリデーション誤判定回避）

入力ファイル（2形式に対応）：
  A) 明示ブロック形式（推奨・当リポジトリのCMO有料記事）：
     `## タイトル` / `## 無料部分` / `## 有料部分` / `## ハッシュタグ` の各コードブロック。
  B) note_ready.md 形式：先頭 `# 見出し` ＋ `<!-- PAYWALL price=NNN -->` または `★【ここから…】★`。

使い方:
  python3 publish_paid_note.py --login
  python3 publish_paid_note.py --article <path> --price 300           # 下書き（安全・既定）
  python3 publish_paid_note.py --article <path> --price 300 --publish  # 公開まで（安全ゲート付き）
"""

import argparse
import re
import sys
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("Playwrightが未インストールです。`./setup.sh` を実行してください。")

PROFILE_DIR = Path.home() / ".note_publisher_profile"
NOTE_LOGIN_URL = "https://note.com/login"
NOTE_NEW_URL_CANDIDATES = [
    "https://editor.note.com/new",
    "https://note.com/notes/new",
    "https://note.com/new",
]
TITLE_SELECTOR = (
    'textarea[placeholder="記事タイトル"], '
    'input[placeholder*="タイトル"], textarea[placeholder*="タイトル"], '
    '[contenteditable="true"][data-placeholder*="タイトル"], '
    'h1[contenteditable="true"], div[role="textbox"][aria-label*="タイトル"]'
)

_MARKER_PATTERNS = [
    re.compile(r"^[━─=]{6,}\s*$"),
    re.compile(r"^\s*★?【ここから.*?】★?\s*$"),
    re.compile(r"^\s*◆◆.*?◆◆\s*$"),
    re.compile(r"^\s*（note.*?有料.*?）\s*$"),
    re.compile(r"^\s*<!--\s*PAYWALL.*?-->\s*$"),
]


# ---------- セッション管理（publish_to_note.py と同方式） ----------

def _launch(playwright):
    try:
        ctx = playwright.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR), channel="chrome", headless=False,
            args=["--disable-blink-features=AutomationControlled"])
        print("🌐 本物のGoogle Chrome を使用しています")
        return ctx
    except Exception as e:
        print(f"⚠️  Chrome起動失敗 → Chromiumにフォールバック: {e}")
        return playwright.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR), headless=False,
            args=["--disable-blink-features=AutomationControlled"])


def login():
    print("ブラウザを起動します。表示されたウィンドウで note にログインしてください。")
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        ctx = _launch(p)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(NOTE_LOGIN_URL)
        input("ログインが完了したら Enter ...")
        ctx.close()
        print(f"✅ プロファイルを保存しました: {PROFILE_DIR}")


def load_context(playwright):
    if not PROFILE_DIR.exists() or not any(PROFILE_DIR.iterdir()):
        sys.exit("初回ログインがまだです。 `python3 publish_paid_note.py --login` を実行してください。")
    return _launch(playwright)


# ---------- サムネ（見出し画像・publish_to_note.py と同じ allowlist 方式） ----------

def _verified_thumb_stems() -> set:
    f = Path(__file__).resolve().parent / "thumbnails" / "_verified.txt"
    if not f.exists():
        return set()
    return {ln.strip() for ln in f.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.strip().startswith("#")}


def find_thumbnail_for(md_path: Path) -> Path | None:
    """_verified.txt 掲載stem のみ返す（未検証サムネは使わない＝誤サムネより無サムネが正）。"""
    if md_path.stem not in _verified_thumb_stems():
        return None
    thumbs = Path(__file__).resolve().parent / "thumbnails"
    for ext in ("jpg", "jpeg", "png", "webp", "JPG", "PNG"):
        p = thumbs / f"{md_path.stem}.{ext}"
        if p.exists():
            return p
    return None


def _set_header_image(page, thumb: Path) -> bool:
    """新エディタの見出し画像を設定する（publish_to_note.py の実測フローを踏襲）。"""
    # 2026-08-19 実測: 既存セレクタが30秒待っても解決せず、無料/有料とも全滅した
    # （note側UI変更）。候補を広げ、待ちも 30s→6s に短縮する（3本で90秒待たされていた）。
    # 当たらない場合は無サムネで進み、記事URLを出して手動設定に回す＝公開自体は止めない。
    opener = ('button[aria-label="画像を追加"], button[aria-label*="画像"], '
              'button:has-text("画像を追加"), button:has-text("見出し画像"), '
              '[aria-label*="見出し画像"], [data-name*="eyecatch"], [class*="eyecatch"] button')
    try:
        page.locator(opener).first.click(timeout=6000)
        page.wait_for_timeout(800)
        with page.expect_file_chooser() as fc:
            page.locator('button:has-text("画像をアップロード"), button:has-text("アップロード")'
                         ).first.click(timeout=6000)
        fc.value.set_files(str(thumb))
        page.wait_for_timeout(2500)
        crop_dialog = '[role="dialog"], [aria-modal="true"], .ReactModal__Content'
        for label in ("保存", "適用", "決定", "完了", "この画像を挿入"):
            try:
                btn = page.locator(f'{crop_dialog} >> button:has-text("{label}")').last
                if btn.is_visible(timeout=600):
                    btn.click()
                    page.wait_for_timeout(800)
                    break
            except Exception:
                continue
        return True
    except Exception as e:
        print(f"⚠️  サムネ自動設定に失敗: {type(e).__name__}（見出し画像は手動で設定してください）")
        print(f"   手動設定用に開くURL: {page.url}")
        print(f"   使う画像: {thumb}")
        return False


# ---------- パース ----------

def _clean_lines(block: str) -> str:
    kept = [ln for ln in block.splitlines() if not any(p.match(ln) for p in _MARKER_PATTERNS)]
    text = "\n".join(kept)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _extract_block(text: str, header: str):
    """`## <header>` 直下の ``` コードブロックを返す。無ければ None。

    見出しは行頭・行全体で一致させる。緩い一致だと `## 本文` ブロック内の説明文
    （例：「## 無料部分」「## 有料部分」という案内）を見出しと誤認し、本文が数文字だけ
    抽出されたまま公開されてしまう。"""
    m = re.search(rf"^##[ \t]*{re.escape(header)}[ \t]*$\n+```[^\n]*\n(.+?)\n```",
                  text, re.S | re.M)
    return m.group(1).strip() if m else None


def parse_paid_article(md_path: Path, title_override=None, price_override=None):
    """(title, free_body, paid_body, price, tags) を返す。
    明示ブロック形式（## 無料部分 / ## 有料部分）を優先。無ければ PAYWALL/★ 形式にフォールバック。"""
    text = md_path.read_text(encoding="utf-8")

    # 価格
    price = None
    m = re.search(r"<!--\s*PAYWALL[^>]*\bprice\s*=\s*(\d+)", text, re.I)
    if m:
        price = int(m.group(1))
    # 大文字/小文字を問わず「価格/Price」＋数字を拾う（英語有料商品の Price: ¥100 対応・2026-07-08）
    m2 = re.search(r"(?:価格|price)[^\d]{0,8}?(\d{3,5})", text, re.I)
    if price is None and m2:
        price = int(m2.group(1))
    if price_override is not None:
        price = price_override

    # タグ
    tags = []
    tag_block = _extract_block(text, "ハッシュタグ")
    if tag_block:
        tags = [t.lstrip("#").strip() for t in re.findall(r"#\S+", tag_block)]

    # 明示ブロック形式（推奨）
    free_block = _extract_block(text, "無料部分")
    paid_block = _extract_block(text, "有料部分")
    title_block = _extract_block(text, "タイトル")
    if free_block and paid_block:
        if title_override:
            title = title_override.strip()
        elif title_block:
            title = title_block.splitlines()[0].strip()
        else:
            tm = re.search(r"^#\s+(.+?)\s*$", text, re.M)
            title = tm.group(1).strip() if tm else md_path.stem
        free_body = _clean_lines(free_block)
        paid_body = _clean_lines(paid_block)
    else:
        # フォールバック：note_ready.md 形式
        sentinel = re.search(r"<!--\s*PAYWALL.*?-->", text)
        if sentinel:
            free_raw, paid_raw = text[:sentinel.start()], text[sentinel.end():]
        else:
            alt = re.search(r"^.*(?:★?【ここから.*?】★?|◆◆.*?◆◆).*$", text, re.M)
            if not alt:
                sys.exit("✗ 有料境界が見つかりません（## 無料部分/## 有料部分 も PAYWALL も ◆◆ も無い）。")
            free_raw, paid_raw = text[:alt.start()], text[alt.end():]
        if title_override:
            title = title_override.strip()
        else:
            tm = re.search(r"^#\s+(.+?)\s*$", free_raw, re.M)
            if not tm:
                sys.exit("✗ タイトル（先頭の `# 見出し`）が見つかりません。--title で指定してください。")
            title = tm.group(1).strip()
            free_raw = free_raw[:tm.start()] + free_raw[tm.end():]
        free_body = _clean_lines(free_raw)
        paid_body = _clean_lines(paid_raw)

    if not paid_body:
        sys.exit("✗ 有料エリアの本文が空です。境界の位置を確認してください。")
    # 2026-08-19 インシデント：見出し抽出バグで本文が7文字になったまま、価格と境界の
    # ゲートは「確定✅」を返し、¥300の値札が付いた空の記事が公開された。ゲートが本文の
    # 長さを一切見ていなかったのが原因。抽出ミスは短さとして必ず現れるので、ここで止める。
    MIN_FREE, MIN_PAID = 200, 200
    if len(free_body) < MIN_FREE or len(paid_body) < MIN_PAID:
        sys.exit(
            f"✗ 本文が短すぎます（無料{len(free_body)}字/有料{len(paid_body)}字・各{MIN_FREE}字以上必要）。\n"
            "  抽出ミスの可能性が高いので公開しません。`## 無料部分` / `## 有料部分` の\n"
            "  見出しとコードブロックが正しく閉じているか確認してください。")
    if price is None:
        sys.exit("✗ 価格が不明です。--price 300 を指定してください。")
    # note の有料記事は ¥100〜¥50,000。範囲外は事故（例：¥50 で弾かれる/桁ミス）なので明示的に止める。
    if not (100 <= price <= 50000):
        sys.exit(f"✗ 価格 ¥{price} は note の有料範囲（¥100〜¥50,000）外です。--price で修正してください。")
    print(f"🧾 記事解析OK：タイトル『{title[:30]}…』 価格=¥{price} 無料{len(free_body)}字/有料{len(paid_body)}字")
    return title, free_body, paid_body, price, tags


# ---------- note UI 操作（新エディタ） ----------

def _type_body(page, text: str):
    for i, para in enumerate(text.split("\n")):
        if para:
            page.keyboard.insert_text(para)
        page.keyboard.press("Enter")
        page.wait_for_timeout(20)


def _open_editor(page):
    """editor.note.com/new へ入り、タイトル欄を返す。"""
    for entry in NOTE_NEW_URL_CANDIDATES:
        try:
            page.goto(entry, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(1500)
        except Exception:
            continue
        if "accounts.google.com" in page.url or page.url.rstrip("/").endswith("/login"):
            sys.exit("✗ note にログインしていません。 `python3 publish_paid_note.py --login` を再実行してください。")
        cand = page.locator(TITLE_SELECTOR).first
        try:
            cand.wait_for(state="visible", timeout=20000)
            print(f"🚪 エディタ入口: {entry} → {page.url}")
            return cand
        except Exception:
            continue
    return None


def _try_set_paywall(page) -> bool:
    """現在のカーソル行で ブロックメニュー(メニューを開く)→「有料エリア指定」を挿入。"""
    try:
        m = page.locator('[aria-label="メニューを開く"]').first
        if m.is_visible(timeout=2000):
            m.click()
            page.wait_for_timeout(700)
            item = page.locator(
                '[role="menuitem"]:has-text("有料エリア指定"), button:has-text("有料エリア指定"), '
                'li:has-text("有料エリア指定"), span:has-text("有料エリア指定")'
            ).first
            if item.is_visible(timeout=2000):
                item.click()
                page.wait_for_timeout(800)
                return True
    except Exception:
        pass
    return False


def _try_set_price_on_publish(page, price: int) -> bool:
    """/publish/ で「有料」を選び、価格を**実キーボード**で入力し、paid選択＋価格==price をDOM検証したら True。
    2026-07-11 cowork self-fix（実測 nb90084f378c8）：note の価格欄は React 制御の
    <input type=text placeholder="300"> で、Playwright の fill() は onChange が発火せず
    アプリ状態が既定300のまま＝価格未確定になっていた（＝過去の「価格未確定で下書き止め」の主因）。
    実マウス click→Meta+A(+Ctrl+A)→Backspace→keyboard.type→Tab で onChange を発火させると確定する。
    ※ここでは有料エリア境界の確定はしない。開くと入力欄が畳まれ価格を再検証できなくなるため、
      境界確定は _confirm_paid_boundary() で別途行う（順序＝価格→検証→境界→投稿）。
    2026-07-11 追補（実測 nba958ccd6cb8）：fresh フロー（公開に進む直後）では /publish/ UI が
    未settleで価格入力に失敗しうる。settle待ち＋scroll_into_view＋検証リトライ(最大3回)で堅牢化。"""
    def _paid_checked():
        return page.evaluate(
            "()=>{const r=document.querySelector('input[name=is_paid][value=paid]');return r?r.checked:false;}")
    def _price_value():
        # 価格欄は placeholder="300" 固定とは限らない（note UI変更・数値/価格系のいずれか）。
        # 入力に使うのと同じ候補セレクタ群から最初に見つかった値を読み、数字だけに正規化して返す
        # （"¥1,000"→"1000"）。ここが placeholder 固定だと ¥100 の確定検証が空振りしていた。
        return page.evaluate(
            "()=>{const sels=['input[placeholder=\"300\"]','input[type=\"number\"]',"
            "'input[inputmode=\"numeric\"]','input[placeholder*=\"価格\"]','input[placeholder*=\"金額\"]'];"
            "for(const s of sels){const i=document.querySelector(s);"
            "if(i&&i.value!==''&&i.value!=null){return (i.value+'').replace(/[^0-9]/g,'');}}return null;}")

    print(f"💰 価格を設定します：目標=¥{price}")
    for attempt in range(3):
        # 1) 「有料」を選択（labelクリックでpaid radioをオン）
        if not _paid_checked():
            for sel in ('label:has-text("有料")', 'input[value="paid"]',
                        '[role="radio"][value="paid"]', 'text=有料'):
                try:
                    el = page.locator(sel).first
                    if el.is_visible(timeout=1500):
                        el.click()
                        page.wait_for_timeout(1200)
                        break
                except Exception:
                    continue
        # 2) 価格入力＝React制御inputに「ネイティブsetterで上書き＋input/changeイベント発火」。
        #    2026-08-19 実測：キーボード方式(Meta+A→Backspace→type)は既存値をクリアできず
        #    300→300300→300300300 と"累積"して価格確定に失敗していた（可視ログで判明）。
        #    ネイティブsetterは値を確実に「置換」し、React内部stateにも反映される（onChange発火）。
        sels = ['input[placeholder="300"]', 'input[type="number"]',
                'input[inputmode="numeric"]', 'input[placeholder*="価格"]', 'input[placeholder*="金額"]']
        try:
            page.evaluate(
                "([sels,val])=>{for(const s of sels){const i=document.querySelector(s);"
                "if(i){const set=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;"
                "i.focus();set.call(i,'');i.dispatchEvent(new Event('input',{bubbles:true}));"
                "set.call(i,String(val));i.dispatchEvent(new Event('input',{bubbles:true}));"
                "i.dispatchEvent(new Event('change',{bubbles:true}));i.blur();return i.value;}}return null;}",
                [sels, price])
            page.wait_for_timeout(500)
        except Exception:
            pass
        # フォールバック：それでも不一致なら、三連クリックで全選択→削除→キー入力（累積を避ける）
        try:
            if str(_price_value()) != str(price):
                for sel in sels:
                    inp = page.locator(sel).first
                    if inp.is_visible(timeout=1500):
                        inp.click(click_count=3)     # フィールド内テキストを全選択（Meta+A不発対策）
                        page.keyboard.press("Backspace")
                        page.wait_for_timeout(150)
                        page.keyboard.type(str(price), delay=120)
                        page.keyboard.press("Tab")
                        page.wait_for_timeout(600)
                        break
        except Exception:
            pass
        # 3) paid選択 と 価格==price をDOMで検証（両方揃って初めて価格確定とみなす）
        try:
            paid_ok = bool(_paid_checked())
            got = _price_value()
            print(f"   試行{attempt+1}: 有料選択={paid_ok} / 入力欄の価格={got}（目標¥{price}）")
            if paid_ok and str(got) == str(price):
                print(f"✅ 価格確定：¥{price}")
                return True
        except Exception:
            pass
        page.wait_for_timeout(1500)  # settle 待ちして再試行
    print(f"⚠️ 価格が¥{price}で確定できませんでした（下書き止め＝全文無料事故を防止）。"
          f" note編集画面で価格欄を目視し、必要なら手入力してください。")
    return False


def _confirm_paid_boundary(page) -> bool:
    """「有料エリア設定」を開き「このラインより先を有料にする」で本文の既存 PAYWALL-LINE を確定する。
    2026-07-11 実測: 確定後は価格/paid入力欄が畳まれ「投稿する」が出現する（＝境界確定が最終ボタン出現の前提）。
    そのため価格検証は必ず本関数の**前**に済ませること。「投稿する」が出現したら True。"""
    try:
        area = page.locator('button:has-text("有料エリア設定")').first
        if area.is_visible(timeout=2500):
            area.click()
            page.wait_for_timeout(2000)
    except Exception:
        pass
    boundary_btn = False
    try:
        b = page.locator('button:has-text("このラインより先を有料にする")').first
        if b.is_visible(timeout=2500):
            boundary_btn = True
            b.click()
            page.wait_for_timeout(2000)
    except Exception:
        pass
    try:
        return boundary_btn and page.evaluate(
            "()=>[...document.querySelectorAll('button')].some(b=>(b.innerText||'').includes('投稿する'))")
    except Exception:
        return boundary_btn


def _verify_paid_published(nid: str, price: int) -> bool:
    """公開後の最終検証：note v3 公開API で price==price かつ can_read==False（＝有料ラインが効いている）
    かつ status==published を確認。全文無料事故を後追いでも必ず検知するための belt-and-suspenders。
    2026-07-11 実測: 正しく有料公開された記事は is_limited=False。有料の真の判定は price と can_read。"""
    import json as _json, urllib.request as _url
    try:
        req = _url.Request(f"https://note.com/api/v3/notes/{nid}", headers={"User-Agent": "Mozilla/5.0"})
        d = _json.load(_url.urlopen(req, timeout=15))
        data = d.get("data", d)
        ok = (str(data.get("price")) == str(price)
              and data.get("can_read") is False
              and data.get("status") == "published")
        print(f"🔎 公開後v3検証: price={data.get('price')} can_read={data.get('can_read')} "
              f"status={data.get('status')} → {'✅ 有料が効いている' if ok else '⚠️ 想定不一致（要確認）'}")
        return ok
    except Exception as e:
        print(f"🔎 公開後v3検証に失敗: {e}（手動確認を推奨）")
        return False


def publish(md_path: Path, do_publish: bool, title_override, price_override, tags_override,
            no_thumb: bool = False):
    title, free_body, paid_body, price, file_tags = parse_paid_article(
        md_path, title_override, price_override)
    tags = tags_override if tags_override else file_tags

    print(f"📝 商品: {md_path.name}")
    print(f"🏷️  タイトル: {title}")
    print(f"💴 価格: ¥{price}")
    print(f"🆓 無料パート: {len(free_body)} 文字 / 🔒 有料パート: {len(paid_body)} 文字")
    print(f"🔖 タグ: {', '.join(tags) if tags else 'なし'}")
    print(f"🚦 モード: {'公開まで(--publish)' if do_publish else '下書き保存（安全・既定）'}")

    thumb = None if no_thumb else find_thumbnail_for(md_path)
    print(f"🖼️  サムネ(見出し画像): {thumb.name if thumb else 'なし（_verified.txt 未登録）'}")

    with sync_playwright() as p:
        ctx = load_context(p)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        title_input = _open_editor(page)
        if title_input is None:
            print("⚠️  タイトル入力欄が見つかりません。note側のUI変更/ログイン切れの可能性。")
            print(f"    現在のURL: {page.url}")
            if sys.stdin.isatty():
                input("Enterで閉じる ...")
            ctx.close()
            sys.exit(2)
        title_input.click()
        title_input.fill(title)
        print("✅ タイトル入力完了")

        editor = page.locator('div[contenteditable="true"]').first
        editor.click()
        _type_body(page, free_body)          # 無料パート＋末尾で改行済み
        print("✅ 無料パート入力完了")

        # 有料ライン（無料パートの直後＝正しい境界）
        paywall_ok = _try_set_paywall(page)
        if paywall_ok:
            print("✅ 「有料エリア指定」ラインをセットしました（無料パート直後）")
        else:
            editor.click()
            page.keyboard.insert_text("━━━【ここから下を有料に設定してください】━━━")
            page.keyboard.press("Enter")
            print("⚠️  有料ラインの自動セットに失敗。本文に目印を入れました（後で手動設定）。")

        # 有料パート
        # カーソルを編集領域の末尾へ確実に移動（JSで選択範囲を末尾に collapse）。
        # 旧実装（editor.click()+End）は本文中間にカーソルが飛び、有料本文が無料パートの
        # 途中に混入して全文がスクランブルする不具合があった（2026-07-07 cowork self-fix：
        # ncdcbf437aa5d で実測→JS caret-to-end に置換。FREE/PAYWALL-LINE/PAID の順序を保証）。
        page.evaluate(
            "()=>{const ed=document.querySelector('div[contenteditable=\"true\"]');"
            "if(!ed)return;ed.focus();const r=document.createRange();"
            "r.selectNodeContents(ed);r.collapse(false);"
            "const s=window.getSelection();s.removeAllRanges();s.addRange(r);}"
        )
        page.wait_for_timeout(200)
        _type_body(page, paid_body)
        print("✅ 有料パート入力完了")

        # サムネ（見出し画像）＝本文確定後・下書き保存の前に設定する
        if thumb and _set_header_image(page, thumb):
            print(f"✅ サムネ(見出し画像)に {thumb.name} を設定")

        # 下書き保存で状態確定
        try:
            ds = page.locator('button:has-text("下書き保存")').first
            if ds.is_visible(timeout=2000):
                ds.click()
                page.wait_for_timeout(2500)
                print("✅ 下書き保存で編集状態を確定")
        except Exception as e:
            print(f"⚠️  下書き保存クリック省略: {e}")

        # 公開設定画面へ
        try:
            page.locator('button:has-text("公開に進む")').first.click()
            try:
                page.wait_for_url("**/publish/**", timeout=15000)
            except Exception:
                page.wait_for_timeout(3000)
        except Exception as e:
            print(f"⚠️  『公開に進む』クリック失敗: {e}")
        page.wait_for_timeout(1500)

        # タグ
        if tags:
            try:
                tag_input = page.locator(
                    'input[placeholder*="ハッシュタグ"], input[placeholder*="タグ"]').first
                tag_input.wait_for(state="visible", timeout=8000)
                for t in tags[:10]:
                    tag_input.click()
                    page.keyboard.type(t)
                    page.keyboard.press("Enter")
                    page.wait_for_timeout(180)
                print(f"✅ タグ {len(tags[:10])} 個を入力")
            except Exception as e:
                print(f"⚠️  タグ入力に失敗: {e}")

        # 価格設定（実キーボード）→ paid+価格==price を検証 → その後に有料エリア境界を確定
        # （順序厳守：境界を先に開くと入力欄が畳まれ価格を検証できなくなる。2026-07-11 self-fix）
        price_ok = _try_set_price_on_publish(page, price)
        print(f"{'✅' if price_ok else '⚠️ '} 価格設定: "
              f"{'¥'+str(price)+' をDOM検証OK（paid選択＋価格一致）' if price_ok else '自動入力/検証に失敗'}")
        boundary_ok = _confirm_paid_boundary(page) if price_ok else False
        print(f"{'✅' if boundary_ok else '⚠️ '} 有料境界確定: "
              f"{'『投稿する』出現までOK' if boundary_ok else '境界確定に失敗'}")

        # --- 収益化セーフティ：有料ライン・価格・境界の3つ全部が確定した時だけ公開 ---
        safe_to_publish = paywall_ok and price_ok and boundary_ok
        if not do_publish or not safe_to_publish:
            if do_publish and not safe_to_publish:
                print("\n🛑 安全のため公開を中止します（有料ライン/価格の自動セットが未確定）。")
            else:
                print("\n📋 下書きモード（既定）：公開しません。")
            print("   下書きは保存されています。note画面で次を確認し、必要なら手動で「投稿する」を：")
            print("   1) 本文中の「ここから有料」ライン（無料パート直後）")
            print(f"   2) /publish/ 画面で「有料」を選び、価格 ¥{price}")
            print(f"   現在URL: {page.url}")
            if sys.stdin.isatty():
                input("   確認したら Enter で閉じる ...")
            ctx.close()
            return None

        # 公開（投稿する）。公開は1回のみ。
        print("\n🚀 投稿する（＝公開）を押します（3秒後）...")
        page.wait_for_timeout(3000)
        published_id = None
        try:
            pub = page.locator('button:has-text("投稿する")').first
            pub.wait_for(state="visible", timeout=10000)
            pub.click()
            page.wait_for_timeout(2500)
            for lbl in ("有料エリア設定で投稿", "投稿する", "公開する", "OK"):
                try:
                    c = page.locator(f'[role="dialog"] >> button:has-text("{lbl}")').last
                    if c.is_visible(timeout=800):
                        c.click()
                        page.wait_for_timeout(1500)
                        break
                except Exception:
                    continue
            page.wait_for_timeout(3000)
            m = re.search(r"/notes/(n[a-z0-9]+)/", page.url) or re.search(r"/n/(n[a-z0-9]+)", page.url)
            published_id = m.group(1) if m else None
            print(f"✅ 公開リクエスト送信。最終URL: {page.url}")
            if published_id:
                # 無人実行(cowork_run.sh)がログから機械的に拾う定型行。書式を変えないこと。
                print(f"PAID_PUBLISHED\t{published_id}\t{price}\t{md_path.name}")
                print(f"🔗 想定公開URL: https://note.com/safe_canna441/n/{published_id}")
        except Exception as e:
            print(f"⚠️  公開ボタン(投稿する)自動クリック失敗: {e}（画面で手動公開してください）")
            if sys.stdin.isatty():
                input("   公開を確認したら Enter ...")
        ctx.close()
        # 公開後の最終検証（v3 API：price一致・can_read=False・published）。全文無料事故の後追い検知。
        if published_id:
            _verify_paid_published(published_id, price)
        return published_id


# ---------- CLI ----------

def main():
    ap = argparse.ArgumentParser(description="note 有料記事 自動公開ヘルパー（収益化セーフティ付き）")
    ap.add_argument("--login", action="store_true")
    ap.add_argument("--article", type=str)
    ap.add_argument("--publish", action="store_true",
                    help="公開まで実行（有料ライン+価格の自動セットが確証できた時のみ実際に公開）。既定は下書き保存。")
    ap.add_argument("--price", type=int, default=None)
    ap.add_argument("--title", type=str, default=None)
    ap.add_argument("--tags", type=str, default=None)
    ap.add_argument("--no-thumb", action="store_true",
                    help="_verified.txt 掲載のサムネがあっても見出し画像を設定しない")
    args = ap.parse_args()

    if args.login:
        login()
        return
    if not args.article:
        sys.exit("--article <path> を指定してください。")
    md_path = Path(args.article).expanduser()
    if not md_path.exists():
        sys.exit(f"記事が見つかりません: {md_path}")

    tags = [t.strip().lstrip("#") for t in args.tags.split(",")] if args.tags else None
    published_id = publish(md_path, do_publish=args.publish, title_override=args.title,
                           price_override=args.price, tags_override=tags, no_thumb=args.no_thumb)
    # --publish を指示したのに公開されなかった場合は非ゼロで終わる。
    # 無人実行(cowork_run.sh)が「安全のため中止」を成功と誤判定してキューから消すのを防ぐ。
    if args.publish and not published_id:
        sys.exit(3)


if __name__ == "__main__":
    main()
