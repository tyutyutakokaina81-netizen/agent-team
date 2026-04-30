#!/usr/bin/env python3
"""
auto_x_post.py — X(Twitter)に毎日1本自動投稿

前提:
  pip install playwright && playwright install chromium
  初回: python3 auto_x_post.py --setup  でセッション保存

動作:
  - 投稿キュー(x_post_queue.json)から未投稿の1本を選んで投稿
  - 投稿済みはフラグを立てて管理
  - note URL は .sessions/note_article_urls.json から自動差し込み
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

SESSION_FILE = Path(__file__).parent / ".sessions" / "x_session.json"
QUEUE_FILE = Path(__file__).parent / ".sessions" / "x_post_queue.json"
NOTE_URLS = Path(__file__).parent / ".sessions" / "note_article_urls.json"

# ── バズ設計ルール ────────────────────────────────────────
# 1. フック: 最初の1行で「え？」と思わせる（数字・逆張り・意外性）
# 2. 本文: 箇条書きで読みやすく、スクロール止める情報密度
# 3. CTA: note/YouTube URLを自然に差し込む
# 4. ハッシュタグ: 3〜5個（多すぎ→スパム判定）
# 5. 英語投稿: 週2本（#HiddenJapan #JapanTravel で国際リーチ）
# 6. スレッド: 5連投稿で情報量を増やし滞在時間を上げる
# ──────────────────────────────────────────────────────────

POSTS = [
    {
        "id": "p1",
        "text": """フリーランス1年目の確定申告、
正直ヤバかった😇

・どの案件がいくらだったか覚えてない
・経費の領収書がバラバラ
・結局ざっくり申告して怯えながら提出

これ全部解決するスプレッドシートを
980円で公開しました。

Googleスプレッドシートに毎月5分入力するだけで
年間収支・経費・案件別時給が全部自動計算されます。

👇 note で販売中（コピーしてすぐ使える）
{note_url}

#フリーランス #確定申告 #スプレッドシート""",
    },
    {
        "id": "p2",
        "text": """フリーランスの収支管理、
Excelで自作してたけど限界だった

→ こういうの欲しかった、を全部詰めた

✅ 収入・経費を入力→年間サマリー自動生成
✅ 案件ごとの「実質時給」が自動計算される
✅ 確定申告の準備資料がそのまま出来上がる
✅ Googleスプレッドシートなのでスマホでも使える

¥980 / コピーしてすぐ使える

👇
{note_url}

#フリーランス #副業 #家計管理""",
    },
    {
        "id": "p3",
        "text": """以前の私の確定申告準備：

📁 バラバラなExcelファイル
📱 LINEのメモに書いた収入
🧾 封筒にぐしゃぐしゃの領収書
😇 3月になってから全部見直す地獄

今：

毎月5分スプレッドシートに入力するだけ

去年の1月に何の案件でいくら稼いだか、
今すぐ3秒で確認できる

テンプレ ¥980 → {note_url}

#フリーランス #確定申告 #時短""",
    },
    {
        "id": "p4",
        "text": """「無料テンプレたくさんあるのに
なんで980円払うの？」

無料テンプレ使い続けた理由：
→ 自分の案件に合わせるのが面倒で結局続かない

¥980 で買った理由：
→ フリーランス向けに最初から設計されてる
→ 経費科目も日本の確定申告に合わせてある
→ 一度入れれば毎年使い回せる

年に1回の確定申告を楽にする
980円の投資と思えばコスパよすぎる

👇
{note_url}

#フリーランス #副業 #スプレッドシート""",
    },
    {
        "id": "p5",
        "text": """フリーランス2年目で気づいたこと

月収が増えても「手取りがいくらか」
ちゃんと把握できてる人、少ない

・クラウドワークスの手数料20%
・消費税の扱い
・経費で落とせる分

全部計算したら意外と残らない😅

Googleスプレッドシートで全部見える化するテンプレ
→ ¥980 {note_url}

#フリーランス #クラウドワークス #副業""",
    },
    {
        "id": "t1",
        "text": """日本三大仏のひとつが、無料で入れることを知っていますか。

富山県高岡市の「高岡大仏」。
奈良・鎌倉と並ぶ日本三大仏なのに、外国人観光客がほぼいない。

しかも台座の内部に入れる。
回廊には仏画、大火を生き延びた先代大仏のお顔も。

東京から新幹線2時間。
行ったことない人、損してます。

#高岡市 #富山観光 #JapanTravel #高岡大仏""",
    },
    {
        "id": "t2",
        "text": """京都は混んでる。奈良も混んでる。

同じ「本物の日本」が、
人混みゼロで体験できる場所がある。

富山県・高岡市。

・国宝の禅寺（瑞龍寺）
・日本三大仏（高岡大仏）
・400年続く鋳物の石畳（金屋町）

全部、静かに歩ける。
外国人に教えたくないけど、教える。

👇 詳しく書きました
{takaoka_url}

#高岡市 #隠れた名所 #北陸観光 #TakaokaToyama""",
    },
    {
        "id": "t3",
        "text": """In Takaoka, you can make your own tin bowl.
400-year-old craft. Still alive.

富山・高岡の金屋町では、
錫の打ち出し体験ができる。

石畳の路地に鋳物工房が並んで、
職人が今も現役で働いてる。

観光客がほとんどいないから
職人と話せる。それが一番の体験。

#高岡市 #金屋町 #JapanCraft #伝統工芸 #北陸""",
    },
    {
        "id": "t4",
        "text": """高岡に行ったら食べてほしいもの3つ

① 高岡コロッケ（¥100前後）
→ 市内40店舗で買える、歩き食いが正解

② 氷見うどん
→ 1751年から続く細うどん、喉ごしが別格

③ 地元の豆腐屋の豆腐
→ 大豆の甘みとなめらかさ、スーパーと全然違う

全部合わせても¥1,500以内で収まる。

#高岡グルメ #富山グルメ #食べ歩き #高岡コロッケ""",
    },
    {
        "id": "t5",
        "text": """「外国人が来ない本物の日本」を動画にした。

富山県高岡市——
国宝・瑞龍寺 / 高岡大仏 / 金屋町 / 氷見うどん

新幹線で東京から2時間なのに、
観光客が少なくて、静かで、本物がある。

詳しくはnoteで書きました👇
{takaoka_url}

#高岡市 #富山観光 #YouTube #JapanTravel #TakaokaToyama""",
    },
    # ── バズ狙い 追加10本 ─────────────────────────────────
    {
        "id": "b1",
        "text": """高岡市 日帰り旅
全部で¥2,450 だった

内訳:
・瑞龍寺（国宝） ¥500
・高岡大仏（日本三大仏） ¥0
・金屋町 ¥0
・コロッケ×3 ¥300
・氷見うどん ¥750
・万葉線 ¥800
・お土産（銅製小物） ¥100

「本物の日本」をこの値段で体験できる場所
まだあったんだ

#高岡市 #富山観光 #旅行好きな人と繋がりたい #穴場""",
    },
    {
        "id": "b2",
        "text": """【衝撃】高岡大仏、台座の中に入れる

これ知ってた人いる？

高岡大仏（日本三大仏）
→ 外観はよく知られてる
→ でも台座の「回廊」は知られてない

中に入ると:
・仏画が飾られてる
→ ひんやりした空間
→ 先代大仏のお顔（火災で焼けた）が安置されてる

しかも全部タダ
拝観料: ¥0

#高岡大仏 #高岡市 #日本三大仏 #知らなかった""",
    },
    {
        "id": "b3",
        "text": """「京都行くくらいなら高岡行けばよかった」
と言った友人の話

友人A（京都旅行後）:
「写真撮るのに20分並んだ。疲れた」

友人B（高岡旅行後）:
「国宝の禅寺、貸し切りで入れた」
「大仏、無料だった」
「コロッケ100円で最高だった」

同じ「本物の日本」なのに
この差は何なのか

→ ただ「知られていない」だけ

詳しくはこちら👇
{takaoka_url}

#高岡市 #旅行 #穴場 #京都""",
    },
    {
        "id": "b4",
        "text": """日本で「人混みゼロの国宝」に会いたいなら高岡

瑞龍寺（富山県高岡市）

✅ 国宝3棟（山門・仏殿・法堂）
✅ 1609年建立、江戸時代の完全形
✅ 春: 桜と国宝建築
✅ 冬: 雪×国宝（絶景）
✅ 平日午前: ほぼ貸し切り

拝観料 ¥500
混み具合 ほぼゼロ

知名度が低いのが逆にラッキー

#瑞龍寺 #高岡市 #国宝 #隠れた名所 #富山観光""",
    },
    {
        "id": "b5",
        "text": """高岡の「職人体験」が意外とすごい

金屋町（400年続く鋳物の町）でできること:

① 錫（すず）の酒器づくり体験 ¥3,850〜
② 鋳物工房の見学（無料）
③ 職人と話せる（観光客が少ないから）

能作（鋳物ブランド）の本社工場見学も無料

「工場で職人が作ったもの」を
その場で買える

これ、フィレンツェの革細工と同レベルの体験

#金屋町 #高岡市 #伝統工芸 #JapanCraft #体験""",
    },
    # ── 英語投稿 5本 ─────────────────────────────────────
    {
        "id": "e1",
        "text": """Japan's 3 Great Buddhas.
Most people know 2.

1. Nara Daibutsu — ¥600
2. Kamakura Daibutsu — ¥300
3. Takaoka Daibutsu — ¥0

The third one is FREE.
And you can walk INSIDE the pedestal.

Almost no tourists.
2 hours from Tokyo by Shinkansen.

#HiddenJapan #JapanTravel #TakaokaToyama #JapanTrip""",
    },
    {
        "id": "e2",
        "text": """Kyoto: Crowded. Expensive. Beautiful.
Takaoka: Empty. Cheap. Also Beautiful.

What Takaoka has:
→ National Treasure Zen Temple (¥500)
→ One of Japan's 3 Great Buddhas (FREE)
→ 400-year-old copper craft town (FREE)

What it doesn't have:
→ Tourist crowds

2hrs from Tokyo. Almost nobody goes.
That's the point.

#HiddenJapan #JapanTravel #Toyama #TakaokaToyama""",
    },
    {
        "id": "e3",
        "text": """A day trip to Takaoka cost me ¥2,450 ($16).

Here's the breakdown:
· Zuiryuji Temple (National Treasure) — ¥500
· Takaoka Buddha (Great Buddha) — FREE
· Kanayamachi craft street — FREE
· Korokke (local croquette ×3) — ¥300
· Himi udon noodles — ¥750
· Tram — ¥800

National treasure + Great Buddha + artisan street
for $16 total.

Japan still has hidden places like this.

#JapanBudgetTravel #HiddenJapan #TakaokaToyama""",
    },
    {
        "id": "e4",
        "text": """In this town, 90% of Japan's Buddhist temple
copper goods are made.

Takaoka City, Toyama.
Craftsmen have been doing this for 400 years.

You can watch them work.
You can try it yourself.
Almost no tourists.

It's the Florence of Japan.
Nobody has figured that out yet.

#Takaoka #JapanCraft #HiddenJapan #TravelJapan #Toyama""",
    },
    {
        "id": "e5",
        "text": """An AI announcer who doesn't exist
is introducing a city that tourists haven't discovered.

That's this channel.

高岡アイ (Ai Takaoka) — fictional.
Takaoka City — very real.

National treasure temple, Great Buddha, copper town,
amazing food. All in one city.

2 hours from Tokyo. Almost no crowds.

#HiddenJapan #AIContent #TakaokaToyama #JapanTravel""",
    },
]


# ── Xスレッド投稿データ ───────────────────────────────────
THREADS = [
    {
        "id": "thread_takaoka_complete",
        "tweets": [
            """高岡市のこと、ほとんどの人が知らなすぎる。

国宝あり、日本三大仏あり、400年の職人街あり。
なのに観光客がほぼいない。

なぜそうなのか、そしてどう行くかを整理した🧵""",

            """① 国宝・瑞龍寺

江戸時代初期に建てられた禅宗の寺。
山門・仏殿・法堂の3棟すべてが国宝。

京都の有名な禅寺と比べて:
→ 拝観料 半額以下（¥500）
→ 混み具合 1/100
→ 写真: 思い通りに撮れる""",

            """② 高岡大仏

奈良・鎌倉と並ぶ「日本三大仏」のひとつ。

知られていない事実:
・拝観料: ¥0（無料）
・台座の中に入れる（回廊あり）
・仏画と先代大仏のお顔が安置されてる

東京から新幹線2時間の場所に、
無料で入れる日本三大仏がある。""",

            """③ 金屋町

1609年から続く鋳物の職人街。
石畳と千本格子の路地が400年前のまま残ってる。

全国の仏具の約90%が高岡産。
東大寺の香炉も、伊勢神宮の神具も、高岡製がある。

工房見学: 無料
職人体験: ¥3,850〜""",

            """④ アクセス＆費用

東京 → 北陸新幹線かがやき → 新高岡（約2時間）
日帰り旅の総費用: ¥2,450〜

瑞龍寺500+大仏0+金屋町0+コロッケ300+うどん750+電車800

「本物の日本」を¥2,450で体験できる。
まだ知られていないだけ。

{takaoka_url}""",
        ],
    },
]


ALL_IDS = [p["id"] for p in POSTS] + [t["id"] for t in THREADS]


def load_queue() -> dict:
    if QUEUE_FILE.exists():
        return json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    return {id_: {"posted": False, "posted_at": None} for id_ in ALL_IDS}


def save_queue(q: dict):
    QUEUE_FILE.parent.mkdir(exist_ok=True)
    QUEUE_FILE.write_text(json.dumps(q, ensure_ascii=False, indent=2), encoding="utf-8")


def get_note_url(key: str = "vol1_free_article") -> str:
    if NOTE_URLS.exists():
        urls = json.loads(NOTE_URLS.read_text())
        return urls.get(key, urls.get("vol1_free_article", "https://note.com"))
    return "https://note.com"


def get_takaoka_url() -> str:
    """高岡観光記事のURL（複数あれば最新を使う）"""
    keys = ["kyoto_vs_takaoka", "youtube_open", "zuiryuji", "daibutsu", "kanayamachi"]
    if NOTE_URLS.exists():
        urls = json.loads(NOTE_URLS.read_text())
        for k in keys:
            if k in urls:
                return urls[k]
    return "https://note.com"


def setup_session():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("pip install playwright && playwright install chromium")
        sys.exit(1)

    SESSION_FILE.parent.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context()
        page = ctx.new_page()
        page.goto("https://twitter.com/login")
        print("ブラウザでX(Twitter)にログインしてください。")
        print("ログイン完了後、Enterを押してください...")
        input()
        ctx.storage_state(path=str(SESSION_FILE))
        browser.close()
    print(f"✅ セッション保存: {SESSION_FILE}")


def extract_x_cookies():
    try:
        import browser_cookie3
        cookies = list(browser_cookie3.chrome(domain_name=".twitter.com"))
        if not cookies:
            cookies = list(browser_cookie3.chrome(domain_name=".x.com"))
        if not cookies:
            return False
        state = {
            "cookies": [
                {"name": c.name, "value": c.value,
                 "domain": c.domain if c.domain.startswith(".") else f".{c.domain}",
                 "path": c.path or "/", "secure": bool(c.secure),
                 "httpOnly": False, "sameSite": "Lax"}
                for c in cookies if c.value
            ],
            "origins": [],
        }
        SESSION_FILE.parent.mkdir(exist_ok=True)
        SESSION_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))
        return True
    except Exception:
        return False


def _type_text(page, text: str):
    """テキストエリアにテキストを入力（改行対応）"""
    for sel in ["[data-testid='tweetTextarea_0']", "div[role='textbox']",
                ".public-DraftEditor-content", "[contenteditable='true']"]:
        el = page.query_selector(sel)
        if el:
            el.click()
            time.sleep(0.3)
            for line in text.split("\n"):
                page.keyboard.type(line)
                page.keyboard.press("Shift+Enter")
                time.sleep(0.03)
            return True
    return False


def _click_post(page) -> bool:
    for sel in ["[data-testid='tweetButtonInline']", "[data-testid='tweetButton']",
                "button:has-text('ポストする')", "button:has-text('Post')"]:
        btn = page.query_selector(sel)
        if btn:
            btn.click()
            time.sleep(3)
            return True
    return False


def _open_compose(page):
    """X の投稿画面を開く"""
    # compose/post に直接アクセス（最も確実）
    page.goto("https://x.com/compose/post", wait_until="domcontentloaded", timeout=30000)
    time.sleep(3)

    # テキストエリアを待機（最大8秒）
    textarea_sels = [
        "[data-testid='tweetTextarea_0']",
        "[data-testid='tweetTextarea_0_label']",
        "div[role='textbox'][aria-multiline='true']",
        "[contenteditable='true']",
    ]
    for sel in textarea_sels:
        try:
            el = page.wait_for_selector(sel, timeout=5000)
            if el and el.is_visible():
                el.click()
                time.sleep(0.5)
                return
        except Exception:
            continue

    # フォールバック: ホームの投稿ボックス
    page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=30000)
    time.sleep(4)
    for sel in ["[data-testid='tweetTextarea_0']", "[placeholder*='今どうしてる']",
                "[placeholder*=\"What's happening\"]", "[contenteditable='true']"]:
        try:
            el = page.wait_for_selector(sel, timeout=3000)
            if el:
                el.click()
                time.sleep(0.5)
                return
        except Exception:
            continue


def post_single(page, text: str) -> bool:
    """単発ツイートを投稿"""
    _open_compose(page)
    _type_text(page, text)
    return _click_post(page)


def post_thread(page, tweets: list[str]) -> bool:
    """スレッド投稿（最初のツイートに返信を連鎖させる）"""
    # 1ツイート目
    _open_compose(page)
    time.sleep(1)
    _type_text(page, tweets[0])

    # 「もっと追加」ボタンでスレッドを追加
    for tweet in tweets[1:]:
        for sel in ["[data-testid='addButton']", "button:has-text('追加')",
                    "button[aria-label*='追加']", "div[data-testid='addButton']"]:
            btn = page.query_selector(sel)
            if btn:
                btn.click()
                time.sleep(1)
                break
        # 新しいテキストエリア（最後の一つ）に入力
        textareas = page.query_selector_all("[data-testid^='tweetTextarea_']")
        if textareas:
            last = textareas[-1]
            last.click()
            time.sleep(0.3)
            for line in tweet.split("\n"):
                page.keyboard.type(line)
                page.keyboard.press("Shift+Enter")
                time.sleep(0.03)

    return _click_post(page)


def post_today():
    if not SESSION_FILE.exists():
        print("  🍪 XセッションをChromeから取得中...")
        if not extract_x_cookies():
            print("  ❌ Xセッション取得失敗（ChromeでX.comにログインしてください）")
            return

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        import subprocess
        for cmd in [
            [sys.executable, "-m", "pip", "install", "playwright", "-q", "--break-system-packages"],
            [sys.executable, "-m", "pip", "install", "playwright", "-q"],
        ]:
            if subprocess.run(cmd, capture_output=True).returncode == 0:
                break
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium",
                        "--with-deps"], capture_output=True)
        from playwright.sync_api import sync_playwright

    queue = load_queue()
    note_url = get_note_url()
    takaoka_url = get_takaoka_url()

    # 未投稿を選択（POSTS → THREADS の順）
    target_post = None
    target_thread = None

    # 週1回スレッドを挟む（7の倍数回目）
    posted_count = sum(1 for v in queue.values() if v.get("posted"))
    if posted_count % 7 == 6:
        for th in THREADS:
            if not queue.get(th["id"], {}).get("posted"):
                target_thread = th
                break

    if not target_thread:
        for post in POSTS:
            if not queue.get(post["id"], {}).get("posted"):
                target_post = post
                break

    if not target_post and not target_thread:
        # extra_posts（auto_repurpose.pyが生成した追加投稿）を確認
        extra_file = QUEUE_FILE.parent / "x_extra_posts.json"
        if extra_file.exists():
            extras = json.loads(extra_file.read_text())
            for ex in extras:
                if not ex.get("posted"):
                    target_post = ex
                    print(f"  extra投稿を使用: {ex['id']}")
                    break

    if not target_post and not target_thread:
        print("全投稿済み → キューリセット")
        queue = {id_: {"posted": False, "posted_at": None} for id_ in ALL_IDS}
        target_post = POSTS[0]

    storage = json.loads(SESSION_FILE.read_text(encoding="utf-8"))

    with sync_playwright() as p:
        # Chromeの実際のプロファイルから起動（cookie自動引き継ぎ）
        import tempfile, shutil as _shutil
        chrome_user_data = Path.home() / "Library/Application Support/Google/Chrome"
        _skip = {"SingletonSocket","SingletonLock","SingletonCookie","RunningChromeVersion","lockfile"}
        if chrome_user_data.exists():
            _tmp = Path(tempfile.mkdtemp()) / "chrome_x"
            _shutil.copytree(chrome_user_data, _tmp, dirs_exist_ok=True,
                             ignore=_shutil.ignore_patterns(*_skip))
            browser = p.chromium.launch_persistent_context(
                str(_tmp), headless=True, slow_mo=100,
                args=["--disable-blink-features=AutomationControlled"],
                viewport={"width": 1280, "height": 900},
            )
            page = browser.new_page()
        else:
            browser = p.chromium.launch(headless=True, slow_mo=150)
            ctx = browser.new_context(storage_state=storage,
                                       viewport={"width": 1280, "height": 900})
            page = ctx.new_page()

        if target_thread:
            tweets = [t.format(note_url=note_url, takaoka_url=takaoka_url)
                      for t in target_thread["tweets"]]
            print(f"スレッド投稿: {target_thread['id']} ({len(tweets)}連)")
            ok = post_thread(page, tweets)
            if ok:
                queue[target_thread["id"]] = {"posted": True,
                                               "posted_at": datetime.now().isoformat()}
                save_queue(queue)
                print(f"✅ スレッド投稿完了")
            else:
                print("❌ スレッド投稿失敗")

        elif target_post:
            post_text = target_post["text"].format(
                note_url=note_url, takaoka_url=takaoka_url)
            print(f"投稿: {post_text[:60].strip()}...")
            ok = post_single(page, post_text)
            if ok:
                queue[target_post["id"]] = {"posted": True,
                                             "posted_at": datetime.now().isoformat()}
                save_queue(queue)
                # extra_posts の場合もフラグを更新
                extra_file = QUEUE_FILE.parent / "x_extra_posts.json"
                if extra_file.exists():
                    extras = json.loads(extra_file.read_text())
                    for ex in extras:
                        if ex["id"] == target_post["id"]:
                            ex["posted"] = True
                            ex["posted_at"] = datetime.now().isoformat()
                    extra_file.write_text(json.dumps(extras, ensure_ascii=False, indent=2))
                print(f"✅ 投稿完了: {target_post['id']}")
            else:
                print("❌ 投稿失敗（ログイン確認 or セレクタ変更）")

        # セッション保存（persistent_contextの場合はctxなし）
        try:
            ctx.storage_state(path=str(SESSION_FILE))
        except Exception:
            pass
        browser.close()


if __name__ == "__main__":
    if "--setup" in sys.argv:
        print("Xセッション取得中...")
        extract_x_cookies()
        print("完了")
    elif "--status" in sys.argv:
        q = load_queue()
        posted = [k for k, v in q.items() if v.get("posted")]
        print(f"投稿済み: {len(posted)}/{len(ALL_IDS)}件")
        for id_ in ALL_IDS:
            mark = "✅" if id_ in posted else "⬜"
            print(f"  {mark} {id_}")
    else:
        post_today()
