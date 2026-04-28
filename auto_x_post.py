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

YouTubeにフル動画あります。
概要欄のリンクからどうぞ。

#高岡市 #富山観光 #YouTube #JapanTravel #TakaokaToyama""",
    },
]


def load_queue() -> dict:
    if QUEUE_FILE.exists():
        return json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    return {p["id"]: {"posted": False, "posted_at": None} for p in POSTS}


def save_queue(q: dict):
    QUEUE_FILE.parent.mkdir(exist_ok=True)
    QUEUE_FILE.write_text(json.dumps(q, ensure_ascii=False, indent=2), encoding="utf-8")


def get_note_url() -> str:
    if NOTE_URLS.exists():
        urls = json.loads(NOTE_URLS.read_text())
        return urls.get("vol1_free_article", "https://note.com")
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


def post_today():
    if not SESSION_FILE.exists():
        print("❌ セッションなし → python3 auto_x_post.py --setup を先に実行")
        sys.exit(1)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("pip install playwright && playwright install chromium")
        sys.exit(1)

    queue = load_queue()
    note_url = get_note_url()

    # 未投稿の投稿を1件選ぶ
    target = None
    for post in POSTS:
        if not queue.get(post["id"], {}).get("posted"):
            target = post
            break

    if not target:
        # 全部投稿済み → 最初からリセットして繰り返す
        print("全投稿済み → キューをリセットして最初から繰り返します")
        queue = {p["id"]: {"posted": False, "posted_at": None} for p in POSTS}
        target = POSTS[0]

    post_text = target["text"].format(note_url=note_url)
    print(f"投稿: {post_text[:50]}...")

    storage = json.loads(SESSION_FILE.read_text(encoding="utf-8"))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, slow_mo=200)
        ctx = browser.new_context(
            storage_state=storage,
            viewport={"width": 1280, "height": 900},
        )
        page = ctx.new_page()
        page.goto("https://twitter.com/compose/tweet", wait_until="networkidle", timeout=30000)
        time.sleep(3)

        # テキストエリアに入力
        for sel in [
            "[data-testid='tweetTextarea_0']",
            ".public-DraftEditor-content",
            "[contenteditable='true']",
            "div[role='textbox']",
        ]:
            el = page.query_selector(sel)
            if el:
                el.click()
                time.sleep(0.5)
                # 長文は段落ごとに分けて入力
                for line in post_text.split("\n"):
                    page.keyboard.type(line)
                    page.keyboard.press("Shift+Enter")
                    time.sleep(0.05)
                break

        time.sleep(1)

        # 投稿ボタン
        ok = False
        for sel in [
            "[data-testid='tweetButtonInline']",
            "[data-testid='tweetButton']",
            "button:has-text('ポストする')",
            "button:has-text('Tweet')",
            "button:has-text('Post')",
        ]:
            btn = page.query_selector(sel)
            if btn:
                btn.click()
                time.sleep(3)
                ok = True
                break

        if ok:
            queue[target["id"]] = {
                "posted": True,
                "posted_at": datetime.now().isoformat(),
            }
            save_queue(queue)
            print(f"✅ X投稿完了: {target['id']}")
        else:
            print("❌ 投稿ボタンが見つかりません（手動で確認してください）")

        ctx.storage_state(path=str(SESSION_FILE))
        browser.close()


if __name__ == "__main__":
    if "--setup" in sys.argv:
        setup_session()
    else:
        post_today()
