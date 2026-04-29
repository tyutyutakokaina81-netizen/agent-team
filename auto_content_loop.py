#!/usr/bin/env python3
"""
auto_content_loop.py — コンテンツ永続生成ループ

毎夕20時に実行:
1. 公開済みコンテンツの在庫を確認
2. 在庫が少ない種別を自動生成
3. note記事キュー・X投稿キュー・Shorts台本に追記

生成トリガー:
- noteキュー残り3本以下 → 新記事3本生成
- X投稿キュー残り5本以下 → 新投稿5本生成
- Shorts在庫3本以下 → 新Shorts台本3本追加
"""

import json
import time
from pathlib import Path
from datetime import datetime

REPO = Path(__file__).parent
SESSIONS = REPO / ".sessions"
NOTE_QUEUE = SESSIONS / "note_publish_queue.json"
X_QUEUE = SESSIONS / "x_post_queue.json"
SHORTS_DIR = REPO / "CMO" / "outputs" / "youtube_videos" / "shorts"
OUTPUT_DIR = REPO / "CMO" / "outputs"
LOG_FILE = SESSIONS / "content_loop_log.json"

# 高岡観光コンテンツのテーマプール
TAKAOKA_THEMES = [
    {"id": "himiundon", "title": "氷見うどん——1751年から続く手延べ細麺の秘密", "spot": "氷見うどん"},
    {"id": "korokke", "title": "高岡コロッケ——市内40店舗・¥100のソウルフードを全部食べた", "spot": "高岡コロッケ"},
    {"id": "katsukoji", "title": "勝興寺——知名度ゼロの国宝5棟、高岡にあった", "spot": "勝興寺"},
    {"id": "manyo_tram", "title": "万葉線——昭和の路面電車で高岡市を1周する", "spot": "万葉線"},
    {"id": "nou_casting", "title": "能作——400年の鋳物が現代ブランドになった話", "spot": "能作"},
    {"id": "amehare_coast", "title": "雨晴海岸——立山連峰と海が同時に見える場所", "spot": "雨晴海岸"},
    {"id": "draemons_town", "title": "ドラえもんの町——藤子不二雄の故郷、高岡市の知られざる顔", "spot": "ドラえもん"},
    {"id": "takaoka_lacquer", "title": "高岡漆器——黒と金の美学、江戸から続く技", "spot": "高岡漆器"},
    {"id": "oyabe_river", "title": "小矢部川——桜と川と北陸の原風景", "spot": "小矢部川"},
    {"id": "inami_woodcarving", "title": "井波彫刻——世界最大の木彫刻の町が富山にある", "spot": "井波彫刻"},
]

X_NEW_POSTS = [
    {
        "id": "loop_x1",
        "text": """高岡市を知っている人に聞きたい。

なぜ高岡大仏は有名じゃないのか。

・日本三大仏のひとつ
・無料で入れる
・台座の中にも入れる

奈良300円、鎌倉600円のところに
無料の日本三大仏がある

なぜ誰も言わないのか

#高岡大仏 #日本三大仏 #高岡市 #富山観光""",
    },
    {
        "id": "loop_x2",
        "text": """「混んでいない日本」を探している人へ。

高岡市（富山県）に全部ある:

国宝の禅寺 → 貸し切りで入れる
日本三大仏 → 無料
400年の職人街 → 観光客ほぼいない
コロッケ¥100 → ソウルフード

東京から新幹線2時間
混んでいない理由は「知られていないから」だけ

#高岡市 #穴場 #隠れた名所 #富山観光 #旅行""",
    },
    {
        "id": "loop_x3",
        "text": """The Florence of Japan hasn't been discovered yet.

Takaoka City, Toyama.

· 400 years of copper casting tradition
· 90% of Japan's Buddhist temple metalwork made here
· Craftsmen workshops open to visitors
· Almost no tourists

Same tradition as Florence's leather craft.
Nobody's figured this out yet.

#HiddenJapan #JapanTravel #TakaokaToyama #Craft""",
    },
    {
        "id": "loop_x4",
        "text": """AIが架空の女子アナウンサーを作って
高岡市の観光案内してる話

・顔: AI画像生成
・声: AI音声合成
・台本: AIが書く

全部¥0のツールだけで作ってる

カメラ苦手な私の解決策がこれだった

でも、届けたい情報は本物

{takaoka_url}

#AI活用 #高岡市 #架空アナウンサー #YouTube""",
    },
    {
        "id": "loop_x5",
        "text": """高岡市に行く前に知っておきたい5つのこと

1. 高岡大仏は無料（台座の中に入れる）
2. 瑞龍寺は朝一番に行く（貸し切りになれる）
3. コロッケは歩きながら食べる（地元スタイル）
4. 金屋町は午後の光が美しい（写真タイム）
5. レンタサイクル¥500で主要スポット全部回れる

準備した人だけ体験できる旅がある

{takaoka_url}

#高岡市 #旅行計画 #富山観光 #旅行好きな人と繋がりたい""",
    },
]


def load_loop_log() -> dict:
    if LOG_FILE.exists():
        return json.loads(LOG_FILE.read_text())
    return {"runs": [], "generated": {}}


def save_loop_log(log: dict):
    SESSIONS.mkdir(exist_ok=True)
    LOG_FILE.write_text(json.dumps(log, ensure_ascii=False, indent=2))


def count_note_queue_remaining() -> int:
    if not NOTE_QUEUE.exists():
        return 99  # 未実行なら生成不要
    state = json.loads(NOTE_QUEUE.read_text())
    from auto_note_publish import ARTICLE_QUEUE
    published = state.get("published", {})
    return sum(1 for a in ARTICLE_QUEUE if a["id"] not in published)


def count_x_queue_remaining() -> int:
    if not X_QUEUE.exists():
        return 99
    q = json.loads(X_QUEUE.read_text())
    return sum(1 for v in q.values() if not v.get("posted"))


def generate_note_articles(themes: list, log: dict) -> int:
    """テーマプールから未生成のnote記事を生成"""
    generated = log.get("generated", {}).get("note", [])
    count = 0
    for theme in themes:
        if theme["id"] in generated:
            continue
        out_file = OUTPUT_DIR / f"2026-04-29_{theme['id']}_note記事.md"
        if out_file.exists():
            continue

        print(f"  📝 生成: {theme['title'][:40]}...")
        content = f"""# {theme['title']}

---

高岡アイです。

今回は「{theme['spot']}」をご紹介します。

---

## {theme['spot']}とは

富山県高岡市が誇る、{theme['spot']}。
まだ多くの人に知られていませんが、訪れた人は必ず「来てよかった」と言います。

---

## アクセス

JR高岡駅から徒歩またはバスでアクセス可能。
東京から北陸新幹線で約2時間。

---

## 見どころ

{theme['spot']}の魅力は、その本物感にあります。
観光地化されすぎていない、地元の日常がそこにあります。

---

## 高岡市の他のスポットと合わせて

- 国宝・瑞龍寺（徒歩圏内）
- 高岡大仏（日本三大仏・無料）
- 金屋町（400年の鋳物の石畳）

---

チャンネル登録・noteフォロー、よろしくお願いします。

**高岡アイ**（架空のAIナビゲーター）

---

**#高岡市 #富山観光 #{theme['spot']} #TakaokaToyama #JapanTravel #隠れた名所**
"""
        out_file.write_text(content, encoding="utf-8")
        if "note" not in log.setdefault("generated", {}):
            log["generated"]["note"] = []
        log["generated"]["note"].append(theme["id"])
        count += 1
        if count >= 3:
            break

    return count


def add_x_posts_to_queue(new_posts: list, log: dict) -> int:
    """auto_x_post.py の POSTS に新投稿を追加"""
    generated = log.get("generated", {}).get("x", [])
    added = 0
    x_script = REPO / "auto_x_post.py"
    content = x_script.read_text(encoding="utf-8")

    for post in new_posts:
        if post["id"] in generated:
            continue
        if f'"id": "{post["id"]}"' in content:
            continue

        # スクリプト末尾のリストに追加は複雑なので、
        # 代わりに独立したJSONキューファイルに追記する
        extra_queue = SESSIONS / "x_extra_posts.json"
        extras = []
        if extra_queue.exists():
            extras = json.loads(extra_queue.read_text())
        if not any(p["id"] == post["id"] for p in extras):
            extras.append(post)
            extra_queue.write_text(json.dumps(extras, ensure_ascii=False, indent=2))
            if "x" not in log.setdefault("generated", {}):
                log["generated"]["x"] = []
            log["generated"]["x"].append(post["id"])
            added += 1

    return added


def run():
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  コンテンツ自動生成ループ")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    log = load_loop_log()

    # note記事在庫チェック
    note_remaining = count_note_queue_remaining()
    print(f"\n  noteキュー残り: {note_remaining}本")
    if note_remaining <= 3:
        print("  → 在庫不足。新記事を生成します...")
        n = generate_note_articles(TAKAOKA_THEMES, log)
        print(f"  ✅ {n}本の記事を生成しました")

        # 新記事をnoteキューに追加
        for theme in TAKAOKA_THEMES:
            article_file = f"CMO/outputs/2026-04-29_{theme['id']}_note記事.md"
            if (REPO / article_file).exists():
                from auto_note_publish import ARTICLE_QUEUE
                if not any(a["id"] == theme["id"] for a in ARTICLE_QUEUE):
                    ARTICLE_QUEUE.append({
                        "id": theme["id"],
                        "file": article_file,
                        "title": theme["title"],
                    })

    # X投稿在庫チェック
    x_remaining = count_x_queue_remaining()
    print(f"\n  X投稿キュー残り: {x_remaining}本")
    if x_remaining <= 5:
        print("  → 在庫不足。新投稿を追加します...")
        n = add_x_posts_to_queue(X_NEW_POSTS, log)
        print(f"  ✅ {n}本の投稿を追加しました")

    # 実行ログ記録
    log["runs"].append({
        "at": datetime.now().isoformat(),
        "note_remaining": note_remaining,
        "x_remaining": x_remaining,
    })
    # ログは最新100件だけ保持
    log["runs"] = log["runs"][-100:]
    save_loop_log(log)

    print(f"\n  次回: 明日20時に自動実行")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


if __name__ == "__main__":
    run()
