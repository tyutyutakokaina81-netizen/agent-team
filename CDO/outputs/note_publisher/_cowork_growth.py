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
# ★2026-10-07: タグが**富山の地名だけ**で、2026-07 に作ったまま止まっていた。
#   そのころは富山の記事しか書いていなかったが、いまは
#   **お取り寄せ（全国のB級グルメ）が毎日1本**あり、だし・乾物まで扱っている。
#   地名タグだけでは、その読者層にまったく届かない＝**書いている中身と探す場所がずれていた**。
#   富山の地名は残したうえで、いま書いているものに対応する面を足す。
#   `#毎日note` は note でいちばん大きい面のひとつで、毎日書く人が集まる＝相性がいい。
DISCOVER_TAGS = [
    "氷見", "高岡", "富山", "立山", "黒部", "北陸",          # 住んでいる土地（従来）
    "お取り寄せ", "B級グルメ", "ご当地グルメ", "郷土料理",      # お取り寄せシリーズの読者
    "毎日note", "エッセイ", "日本の暮らし",                   # 毎日書く人・暮らしを書く人
]
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

# ★2026-10-07: **セレクタが全滅していた。**
#   note は Nuxt から Next.js に移っており、保存した移行後の実ページで数えると
#   `.m-creatorProfile__actions` `.m-follow` `.a-button` `.o-noteLikeV3__iconButton` は
#   **すべて0件**だった。7月に書いたクラス名はもう存在しない。
#   このまま走らせると「no-follow-btn」を返して**1人もフォローせずに終わる**のに、
#   報告は「実行した」になる＝いつもの「成功と言いながら何も起きていない」型。
#   対策は3つ:
#     ① クラス名に頼らず、**aria-label と文字**で探す（note 側の作り替えに強い）
#     ② 複数の探し方を順に試す
#     ③ **どれも当たらなければ、その画面のボタンを全部書き出す**（次の実行で直せる）
#   ※ note 側の DOM は code からは見られない（A1）ので、②③が無いと永久に直せない。
DUMP_DIR = Path(__file__).resolve().parents[3] / "ops" / "logs"


def _dump_buttons(page, why: str, tag: str = "growth"):
    """掴めなかった画面のボタンを全部書き出す。**次に直すための唯一の材料**。"""
    try:
        DUMP_DIR.mkdir(parents=True, exist_ok=True)
        els = page.eval_on_selector_all(
            "button, a[role='button'], [role='button'], [class*='ollow']",
            """els => els.slice(0,120).map(e => ({
                 tag: e.tagName.toLowerCase(),
                 txt: (e.innerText||'').replace(/\s+/g,' ').trim().slice(0,30),
                 aria: e.getAttribute('aria-label') || '',
                 cls: (e.getAttribute('class')||'').slice(0,70)
               }))""")
        f = DUMP_DIR / f"{tag}_buttons.json"
        f.write_text(json.dumps({"why": why, "url": page.url, "buttons": els},
                                ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"DUMP:: {why} -> {f}")
    except Exception as e:
        print(f"DUMP_FAILED:: {type(e).__name__} {e}")


def do_like(page):
    """スキを付ける。aria-label に『スキ』を含み、『取り消』『見る』を含まないボタン。"""
    cands = []
    try:
        cands = page.query_selector_all("button[aria-label], [role='button'][aria-label]")
    except Exception:
        pass
    for b in cands:
        al = (b.get_attribute("aria-label") or "")
        if "スキ" not in al:
            continue
        if "取り消" in al or "見る" in al or "ユーザー" in al:
            continue          # 既にスキ済み／スキした人の一覧ボタン
        try:
            b.scroll_into_view_if_needed()
            page.wait_for_timeout(600)
            b.click()
            page.wait_for_timeout(1500)
            return True
        except Exception as e:
            return f"err:{e}"
    _dump_buttons(page, "スキのボタンが見つからない", "like")
    return "no-btn-or-already"


# フォローボタンの文字（note 側の表記ゆれをまとめて見る）
_FOLLOW_TXT = ("フォローする", "フォロー")
_FOLLOWING_TXT = ("フォロー中", "フォローをやめる")



# ★2026-11-13: Playwright の click 失敗から**理由にあたる部分だけ**を取り出す。
#   11-11 に「call log が30行付いてきて DONE 行が読めない」ので先頭80字に切ったが、
#   **先頭80字はどの失敗でも同じ定型文**（"elementHandle.click: Timeout 30000ms exceeded.
#   Call log: - attempting click action..."）で、**理由は後ろにある**。
#   そのため 11-13 の便は「8人が click でタイムアウト」までは分かったのに
#   **何に邪魔されたのかが分からなかった**。切る位置を間違えると、診断が消える。
#   実測（合成ページで確認）＝覆いがあるときは
#   `<div id="veil"></div> intercepts pointer events` が後ろのほうに入る。
_ANSI_RE = re.compile(r"\x1b?\[\d+m")
_CLICK_REASONS = (
    "intercepts pointer events",      # 何かが上に覆いかぶさっている（いちばん知りたい）
    "element is not stable",          # 動いている最中（アニメーション）
    "element is not enabled",         # 無効化されている
    "element is not visible",
    "element is outside of the viewport",
    "did not receive pointer events",
)


def _why_click_failed(e) -> str:
    s = _ANSI_RE.sub("", " ".join(str(e).split()))
    for pat in _CLICK_REASONS:
        i = s.find(pat)
        if i >= 0:
            # 直前の要素記述も一緒に返す＝**何が覆っているか**が DONE 行に出る
            return s[max(0, i - 90):i + len(pat)]
    return s[:120]

def do_follow(page, handle: str = ""):
    """記事の著者をフォローする。**クラス名を使わない**＝note の作り替えで黙って壊れない。

    ★2026-10-07（2度目の改良）: 最初の版は「ページ内で最初に見つかったフォローボタン」を
      押していた。note の記事ページは下部に**おすすめクリエイター**が並ぶので、
      スクロール位置によっては**別人をフォローしてしまう**。
      著者の handle が分かっているので、**そのプロフィールへのリンクを含むまとまりの中**に
      あるボタンだけを押す。handle が無いときだけ、従来どおり最初の1つにする。
    """
    # 画面下まで少しずつ送る（作者カードは本文の下にある）
    for _ in range(6):
        try:
            page.mouse.wheel(0, 1800)
            page.wait_for_timeout(500)
        except Exception:
            break

    js = """(handle) => {
      const texts = ['フォローする', 'フォロー'];
      const following = ['フォロー中', 'フォローをやめる'];
      // note の1ページ分の中には「おすすめのクリエイター」など**他人のフォローボタン**が並ぶ。
      // 誰のボタンかは、**ボタンのすぐ上にあるプロフィールリンク**で決める。
      const NOT_HANDLE = new Set(['search','login','signup','settings','notes','timeline',
        'explore','hashtag','api','membership','following','followers','mypage','help',
        'terms','privacy','contact','sitemap','pro','store','info','sp','magazine','interest']);
      const norm = (h) => (h || '').replace(/^https?:\/\/note\.com/, '')
        .replace(/[?#].*$/, '').replace(/\/+$/, '');
      const handleOf = (h) => {
        const p = norm(h);
        if (!/^\/[^\/]+$/.test(p)) return null;
        const s = p.slice(1);
        return NOT_HANDLE.has(s) ? null : s;
      };
      // ★2026-11-11: 祖先を **body まで上がってはいけない**。
      //   body には他人のプロフィールリンクも全部入っているので、
      //   querySelector が必ず当たり、**どのボタンも「著者のもの」と判定されていた**。
      //   実測（合成ページ）では、他人のボタンまで owns=true になり、
      //   しかも先頭が選ばれるので**別人を押しに行く**経路だった。
      //   直し方＝**最初にプロフィールリンクを含んだ祖先で打ち切る**。
      //   そこに複数人のリンクがあれば「誰のものか不明」として押さない。
      const ownerOf = (el) => {
        let n = el;
        for (let d = 0; d < 8 && n; d++) {
          n = n.parentElement;
          if (!n || n === document.body || n === document.documentElement) return null;
          const hs = Array.from(n.querySelectorAll('a[href]'))
            .map(a => handleOf(a.getAttribute('href')))
            .filter(x => x);
          const uniq = Array.from(new Set(hs));
          if (uniq.length === 0) continue;
          return uniq.length === 1 ? uniq[0] : null;
        }
        return null;
      };
      // ★見えているかどうかを **JS の側で** 見る。
      //   見えない要素を Python に渡すと scroll_into_view_if_needed が
      //   30秒待って失敗する（11-11 の便は 14人中10人がこれ＝300秒を捨てていた）。
      const visible = (el) => {
        if (el.getClientRects().length === 0) return false;
        const s = getComputedStyle(el);
        return s.visibility !== 'hidden' && s.display !== 'none' && Number(s.opacity) !== 0;
      };
      const all = Array.from(document.querySelectorAll("button, [role='button'], a[role='button']"));
      const hit = [];
      for (let i = 0; i < all.length; i++) {
        const e = all[i];
        const t = ((e.innerText || '') + ' ' + (e.getAttribute('aria-label') || '')).trim();
        const isFollowing = following.some(w => t.includes(w));
        if (!isFollowing) {
          if (!texts.some(w => t.includes(w))) continue;
          if ((e.innerText || '').trim().length > 12) continue;
        }
        const owner = ownerOf(e);
        // ★2026-11-11: 添字ではなく**要素そのものに印**を付ける。
        //   note は画面を描き直すので、JS で数えた添字と、あとから Python が
        //   数え直した添字が**ずれる**。ずれると別の要素を掴む。
        e.setAttribute('data-cc-follow-idx', String(i));
        hit.push({i, state: isFollowing ? 'following' : 'follow',
                  owns: handle ? owner === handle : false, owner, vis: visible(e)});
      }
      return hit;
    }"""
    try:
        hits = page.evaluate(js, handle or "")
    except Exception as e:
        return f"err:{e}"

    # ★2026-11-11: 「フォロー中」は **著者のボタンだけ**を見る。
    #   前は画面のどこかに1つでも「フォロー中」があれば already-following を返していた。
    #   おすすめクリエイターのカードで当たるので、**著者を未フォローのまま
    #   「もうフォロー済み」と報告していた**。11-11 の 4/14 はこれだと見ている。
    if any(h.get("state") == "following" and h.get("owns") for h in hits):
        return "already-following"
    cands = [h for h in hits if h.get("state") == "follow"]
    if not cands:
        _dump_buttons(page, "フォローのボタンが見つからない", "follow")
        return "no-follow-btn"
    owned = [h for h in cands if h.get("owns")]
    if handle and not owned:
        # 著者のものだと確認できない＝**押さない**。別人をフォローするより何もしないほうがよい。
        _dump_buttons(page, f"著者({handle})のフォローボタンを特定できない", "follow")
        return "no-author-follow-btn"
    pool = owned or cands
    # 同じ著者のボタンが隠れている方と見えている方の両方ある（note は両方描く）。
    # **見えている方を選ぶ**＝30秒の無駄待ちがそもそも起きない。
    pool = [h for h in pool if h.get("vis")] or pool
    idx = pool[0]["i"]

    try:
        # ★2026-11-11: **印で引く**（添字で引き直さない。上の JS のコメント参照）
        b = page.query_selector(f"[data-cc-follow-idx='{idx}']")
        if b is None:
            # 画面が描き直されて印ごと消えた＝**別の要素を押さない**で次へ
            return "err:target-vanished(画面が描き直された)"
        if not b.is_visible():
            # ★見えない要素は押さない。30秒待っても見えるようにはならない
            #   （11-11 の便は、ここで1人30秒×10人を捨てていた）
            return "err:not-visible(ボタンが画面に出ていない)"
        try:
            b.scroll_into_view_if_needed(timeout=5000)
        except Exception:
            # 5秒で諦める。押さずに次へ＝1人あたりの無駄を30秒から5秒に減らす
            return "err:scroll-timeout(5秒で諦めた)"
        page.wait_for_timeout(600)
        # ★2026-11-13: **click に上限をつける**。既定は30秒で、11-13 の便は
        #   8人がここで30秒ずつ待って計240秒を捨てていた（それで時間切れに見えていた）。
        b.click(timeout=8000)
        for _ in range(10):
            page.wait_for_timeout(500)
            try:
                t2 = (b.inner_text() or "") + (b.get_attribute("aria-label") or "")
            except Exception:
                t2 = ""
            if "フォロー中" in t2 or "フォローをやめる" in t2:
                return "followed"
        return "clicked"
    except Exception as e:
        return "err:" + _why_click_failed(e)


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
    戻り値: [{"a":handle,"k":key,"t":tag由来ラベル}] を DISCOVER_LIMIT 件まで。

    2026-07-28 self-fix: 従来は先頭タグ(#氷見)だけで14枠を埋め、毎便同じ人気アカウント=
    既フォロー飽和分ばかり返して新規0だった。→ (1)全タグをラウンドロビンで少数ずつ拾い、
    (2)各タグでより深くスクロール(先頭の人気=既フォロー層を越える)ことで、
    未フォローの新鮮な発信者に届かせる。follow/likeは冪等ゆえ既フォローが混じっても無害。"""
    per_tag = {}   # tag -> [ {a,k,t}, ... ]（既知/自分は除外済み）
    for tag in DISCOVER_TAGS:
        lst = []
        seen = set()
        try:
            page.goto(f"https://note.com/hashtag/{tag}", wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(3500)
            for _ in range(6):   # 深めにスクロール=人気(既フォロー)層の先へ
                page.mouse.wheel(0, 3200); page.wait_for_timeout(900)
            anchors = page.query_selector_all('a[href*="/n/n"]')
            for a in anchors:
                href = a.get_attribute("href") or ""
                m = re.search(r"/([A-Za-z0-9_]+)/n/(n[0-9a-f]+)", href)
                if not m:
                    continue
                handle, key = m.group(1), m.group(2)
                if handle == MY_HANDLE or handle in known_handles or handle in seen:
                    continue
                seen.add(handle)
                lst.append({"a": handle, "k": key, "t": f"#{tag}フィード発見"})
        except Exception as e:
            print(f"discover({tag}) err: {e}")
        per_tag[tag] = lst
    # ラウンドロビンで各タグから少しずつ→タグ横断で多様に(=新鮮率UP)
    found = {}
    idx = 0
    while len(found) < DISCOVER_LIMIT:
        progressed = False
        for tag in DISCOVER_TAGS:
            lst = per_tag.get(tag) or []
            if idx < len(lst):
                cand = lst[idx]
                if cand["a"] not in found:
                    found[cand["a"]] = cand
                progressed = True
                if len(found) >= DISCOVER_LIMIT:
                    break
        if not progressed:
            break
        idx += 1
    return list(found.values())

def read_followers(page):
    """プロフィール画面からフォロワー数を読む。

    ★2026-11-08 作り直し: これまでは「『フォロワー』を含む20字未満の行」を返すだけで、
      当たらなければ黙って "unknown" を返していた。**11-07・11-08 の2便が
      『取得できず』**で、ops/follower_log.tsv も 11-06 で止まっている。
      note の表示が変わったのだと思われるが、**何が見えていたのかが残らない**ので
      直しようがなかった（「何も無い」と「読めない」を区別できない作りだった）。
    → ①数字＋フォロワー／フォロワー＋数字の両方を拾う ②字数で切らない
      ③**外したときは、画面に『フォロワー』を含む行が何と書いてあったかを出す**。
      次の便のログを見れば、どう変わったのかが分かる。
    """
    import re as _re
    try:
        page.goto(f"https://note.com/{MY_HANDLE}", wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(4000)
        body = page.inner_text("body")
    except Exception as e:
        return f"err:{e}"
    cands = [ln.strip() for ln in body.splitlines() if "フォロワー" in ln]
    # 「1,234フォロワー」「1,234 フォロワー」「フォロワー 1,234」のどれでも数字を取る
    for ln in cands:
        m = (_re.search(r"([0-9][0-9,]*)\s*フォロワー", ln)
             or _re.search(r"フォロワー\s*([0-9][0-9,]*)", ln))
        if m:
            return f"{m.group(1).replace(',', '')}フォロワー"
    if cands:
        # ★読めなかったときは、見えていた行をそのまま出す＝次の便で直せるようにする
        print("FOLLOWERS_RAW_LINES::", " | ".join(c[:40] for c in cands[:5]))
        return "unknown(行はあるが数字が取れない)"
    print("FOLLOWERS_RAW_LINES:: （『フォロワー』を含む行が1つも無い＝"
          "ログイン切れか、画面の作りが変わった）")
    return "unknown(行が無い)"

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
                    r["follow"] = do_follow(page, tg.get("a", "")); page.wait_for_timeout(2500)
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
