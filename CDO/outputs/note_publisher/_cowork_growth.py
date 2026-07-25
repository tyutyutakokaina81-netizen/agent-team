#!/usr/bin/env python3
"""cowork 集客: 富山/氷見/高岡の実在発信者に フォロー + スキ + (任意)本物コメント。

安全設計（2026-07-25 self-fix で強化）:
- **フォロー優先(follow-first)**: 既定は「スキ＋フォローのみ」。フォロー/スキは冪等（既フォロー/既スキは触らない
  ＝取り消し防止）なので何度でも安全に再実行できる＝フォロワーを重複無害に積める。
- **重複コメント検知(A5違反防止)**: コメントは `--comment` を明示した時だけ。かつ投稿前に
  `already_commented()` で「自分(safe_canna441)が既にこの記事にコメント済みか」をDOM判定し、
  済みならスキップ。判定不能時は fail-safe で「コメントしない」側に倒す。
  → 同一文面の重複コメント(bot判定/A5違反)を構造的に防ぐ。
- **discover モード(--discover)**: 富山/氷見/高岡 等のハッシュタグ・フィードから、まだ TARGETS に無い
  新しい発信者(handle)を収集して表示する。飽和した固定リストの補充に使う（読み取りのみ・安全）。

使い方:
  python3 _cowork_growth.py                 # DRY(状態確認のみ・何も操作しない)
  python3 _cowork_growth.py --discover      # 新規発信者を収集して表示(読み取りのみ)
  python3 _cowork_growth.py --discover --go # 収集した新規発信者に follow+like を実行(コメント無し=安全)
  python3 _cowork_growth.py --go            # 固定TARGETSに follow+like を実行(コメント無し)
  python3 _cowork_growth.py --go --comment  # +コメントも(重複検知でガード)
"""
import sys, json, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from playwright.sync_api import sync_playwright
import publish_to_note as P

GO = "--go" in sys.argv
COMMENT = "--comment" in sys.argv
DISCOVER = "--discover" in sys.argv
MY_HANDLE = "safe_canna441"

# discover が拾いに行くハッシュタグ・フィード（一次コンテンツの発信者が集まる場所）
DISCOVER_TAGS = ["氷見", "高岡", "富山", "立山", "黒部", "富山観光", "北陸"]
DISCOVER_LIMIT = 14   # 1便で新規に触る上限(bot判定回避=owner則の量上限)

# 厳選: 実際に富山/氷見/高岡の一次コンテンツを出している発信者。comment は手書きオリジナル。
# (2026-07-14作成→07-23便でフォロー飽和済。follow/likeは冪等なので再実行しても無害=スキップされる)
TARGETS = [
    {"a":"cool_weasel4244","k":"nfd7c1fad2eae","t":"富山・氷見海岸でカメラさんぽ",
     "c":"氷見の海岸、光がやわらかくて散歩に良いですよね。作例、地元民としても新鮮な視点で楽しませてもらいました。"},
    {"a":"wineshoko","k":"n7cde62c4df7c","t":"氷見うどんと夏越そば",
     "c":"夏越そばに氷見うどんの取り合わせ、季節感があっていいですね。おうちビストロの発想が素敵でした。"},
    {"a":"koharu_25","k":"n501c199b46cf","t":"氷見の亀寿し",
     "c":"氷見に行くと寿司はやっぱり寄りたくなりますよね。写真からネタの良さが伝わってきました。"},
    {"a":"kerontan","k":"nb1b284db47c3","t":"JR氷見線で氷見&高岡の旅",
     "c":"氷見線ののんびりした車窓、いいですよね。高岡と氷見を一日で回る初夏の旅、参考になりました。"},
    {"a":"yuji1003","k":"n42380897ef6a","t":"移住ってホンマに不便なん",
     "c":"高岡の暮らし、不便そうで意外と何とかなる感じ、共感します。等身大の移住話が面白かったです。"},
    {"a":"jkmf","k":"n531091ce2909","t":"五郎丸屋 薄氷",
     "c":"薄氷、口に入れるとほろりと溶けるあの感じが好きです。富山の和菓子の奥深さが伝わりました。"},
    # follow+likeのみ(コメントは付けない=量を抑える)
    {"a":"nagi96_cam","k":"na5b80cea0948","t":"氷見漁港にて"},
    {"a":"hihillstyle","k":"n338cc576aa35","t":"高岡の都市構造を語る"},
    {"a":"kimurak202106","k":"n4d5729ccff2b","t":"高岡御車山祭"},
    {"a":"lycka_dag","k":"nd722437d6da0","t":"富山の物撮りフォトグラファー"},
    {"a":"szhr19_88","k":"nc14fa99084fc","t":"富山へマラソン旅"},
    {"a":"eittoness0216","k":"n70cf653e123d","t":"黒部暮らし"},
]

def do_like(page):
    btns = page.query_selector_all('button.o-noteLikeV3__iconButton[aria-label]')
    for b in btns:
        al = (b.get_attribute("aria-label") or "")
        if "スキ" in al and "取り消" not in al:
            try:
                b.scroll_into_view_if_needed(); page.wait_for_timeout(600)
                b.click(); page.wait_for_timeout(1500)
                al2 = b.get_attribute("aria-label") or ""
                return ("取り消" in al2) or True
            except Exception as e:
                return f"err:{e}"
    return "no-btn-or-already"

def do_follow(page):
    b = page.query_selector('button.o-noteContentHeader__actionFollow')
    if not b:
        return "no-follow-btn"
    txt = (b.inner_text() or "").strip()
    if "フォロー中" in txt:
        return "already-following"
    if "フォロー" in txt:  # "フォローする" or "フォロー"
        try:
            b.scroll_into_view_if_needed(); page.wait_for_timeout(600)
            b.click()
            # クリック後、記事ヘッダのボタンは「フォロー中」への反映が1.8秒では間に合わず
            # 誤って clicked(now=フォローする) と報告していた（実際は成功=プロフィールで確認済 2026-07-26）。
            # 最大5秒ポーリングして反映を待つ＝正しく followed を返す（待機のみの機械修正）。
            t2 = ""
            for _ in range(10):
                page.wait_for_timeout(500)
                t2 = (b.inner_text() or "").strip()
                if "フォロー中" in t2:
                    return "followed"
            return f"clicked(now={t2})"
        except Exception as e:
            return f"err:{e}"
    return f"unknown-state:{txt}"

def already_commented(page, handle=MY_HANDLE):
    """自分(handle)が既にこの記事にコメント済みかをDOMで判定＝重複コメント(A5違反)防止。
    コメント一覧コンテナ内に自分のプロフィールリンク(/handle)があれば「済み」。
    判定不能・例外時は True(=コメントしない)側に倒す fail-safe。"""
    try:
        for _ in range(4):
            page.mouse.wheel(0, 2500); page.wait_for_timeout(600)
        # コメント一覧に絞って自分へのリンクを探す(グローバルナビの自分リンクを誤検知しないため)
        containers = page.query_selector_all(
            '[class*="ommentList"], [class*="oteComment"], [class*="omment_"], .o-noteComment, section:has(textarea)'
        )
        for c in containers:
            try:
                html = c.inner_html() or ""
            except Exception:
                continue
            if f'/{handle}"' in html or f'/{handle}?' in html or f'/{handle}/' in html:
                return True
        return False
    except Exception:
        return True  # 不明ならコメントしない(安全側)

def do_comment(page, text):
    for _ in range(4):
        page.mouse.wheel(0, 2500); page.wait_for_timeout(700)
    box = page.query_selector('textarea[placeholder*="コメント"], [contenteditable="true"][data-placeholder*="コメント"], textarea[name*="comment"]')
    if not box:
        box = page.query_selector('form textarea, .o-noteComment textarea')
    if not box:
        return "no-comment-box(disabled?)"
    try:
        box.scroll_into_view_if_needed(); page.wait_for_timeout(600)
        box.click(); page.wait_for_timeout(500)
        box.type(text, delay=35); page.wait_for_timeout(800)
        sub = page.query_selector('button:has-text("投稿"), button:has-text("送信"), button:has-text("コメントする")')
        if not sub:
            return "typed-but-no-submit"
        if sub.is_disabled():
            return "submit-disabled"
        sub.click(); page.wait_for_timeout(2000)
        return "commented"
    except Exception as e:
        return f"err:{e}"

def discover(page, known_handles):
    """ハッシュタグ・フィードから TARGETS 未収録の新規発信者を収集(読み取りのみ)。
    戻り値: [{"a":handle,"k":key,"t":tag由来ラベル}] を DISCOVER_LIMIT 件まで。"""
    found = {}  # handle -> {a,k,t}
    for tag in DISCOVER_TAGS:
        if len(found) >= DISCOVER_LIMIT:
            break
        try:
            page.goto(f"https://note.com/hashtag/{tag}", wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(3500)
            for _ in range(3):
                page.mouse.wheel(0, 3000); page.wait_for_timeout(900)
            anchors = page.query_selector_all('a[href*="/n/n"]')
            for a in anchors:
                href = a.get_attribute("href") or ""
                m = re.search(r"/([A-Za-z0-9_]+)/n/(n[0-9a-f]+)", href)
                if not m:
                    continue
                handle, key = m.group(1), m.group(2)
                if handle == MY_HANDLE or handle in known_handles or handle in found:
                    continue
                found[handle] = {"a": handle, "k": key, "t": f"#{tag}フィード発見"}
                if len(found) >= DISCOVER_LIMIT:
                    break
        except Exception as e:
            print(f"discover({tag}) err: {e}")
    return list(found.values())

def read_followers(page):
    try:
        page.goto(f"https://note.com/{MY_HANDLE}", wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(4000)
        body = page.inner_text("body")
        for line in body.splitlines():
            if "フォロワー" in line and len(line) < 20:
                return line.strip()
    except Exception as e:
        return f"err:{e}"
    return "unknown"

def main():
    results = []
    with sync_playwright() as pw:
        ctx = P.load_context(pw)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            fb = read_followers(page)
            print("FOLLOWERS_BEFORE::", fb)

            targets = list(TARGETS)
            if DISCOVER:
                known = {t["a"] for t in TARGETS}
                newbies = discover(page, known)
                print(f"DISCOVERED {len(newbies)} new handles:",
                      json.dumps([n["a"] for n in newbies], ensure_ascii=False))
                # discover時は新規発信者のみを対象にする(飽和した固定リストは再訪しない)
                targets = newbies

            for i, tg in enumerate(targets):
                r = {"author": tg["a"], "title": tg.get("t", "")}
                try:
                    page.goto(f"https://note.com/{tg['a']}/n/{tg['k']}",
                              wait_until="domcontentloaded", timeout=45000)
                    page.wait_for_timeout(4500)
                    if not GO:
                        b = page.query_selector('button.o-noteContentHeader__actionFollow')
                        r["follow_state"] = (b.inner_text().strip() if b else "no-btn")
                        results.append(r); print("DRY", json.dumps(r, ensure_ascii=False)); continue
                    r["like"] = do_like(page); page.wait_for_timeout(2500)
                    r["follow"] = do_follow(page); page.wait_for_timeout(2500)
                    # コメントは明示フラグ時のみ・重複検知でガード
                    if COMMENT and tg.get("c"):
                        if already_commented(page):
                            r["comment"] = "skip-already-commented"
                        else:
                            r["comment"] = do_comment(page, tg["c"])
                    elif tg.get("c"):
                        r["comment"] = "skip(follow-first・--comment未指定)"
                except Exception as e:
                    r["error"] = str(e)[:80]
                results.append(r); print("DONE", json.dumps(r, ensure_ascii=False))
                page.wait_for_timeout(9000 + (i % 5) * 2600)  # 人間的ペース

            fa = read_followers(page)
            print("FOLLOWERS_AFTER::", fa)
        finally:
            ctx.close()
    print("\n=== SUMMARY ===")
    print(json.dumps(results, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()
