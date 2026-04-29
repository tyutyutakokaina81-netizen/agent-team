#!/usr/bin/env python3
"""
auto_repurpose.py — コンテンツ横断自動変換（¥0）

note記事 → X投稿 → Shortsスクリプト に自動変換。
1本の記事から3プラットフォーム分のコンテンツを生成する。

run_daily_auto.sh から note公開直後に実行される。
"""

import json
import re
from pathlib import Path
from datetime import datetime

REPO = Path(__file__).parent
SESSIONS = REPO / ".sessions"
SESSIONS.mkdir(exist_ok=True)
REPURPOSE_LOG = SESSIONS / "repurpose_log.json"
X_EXTRA_QUEUE = SESSIONS / "x_extra_posts.json"
SHORTS_SCRIPT_DIR = REPO / "CMO" / "outputs" / "youtube_videos" / "shorts"
SHORTS_SCRIPT_DIR.mkdir(parents=True, exist_ok=True)
NOTE_QUEUE = SESSIONS / "note_publish_queue.json"
OUTPUTS_DIR = REPO / "CMO" / "outputs"

# ─── バズルール（buzz_rules.md の定義を直接実装） ───────────────

HOOK_TEMPLATES = [
    "{spot}が、無料なの知ってた？",
    "京都より{spot}に行けばよかった",
    "日本に{spot}があることを、99%の人が知らない",
    "高岡市に{スポット}がある理由を、誰も説明していない",
    "Japan's best kept secret: {spot}",
]

JP_HASHTAGS = "#高岡市 #富山観光 #隠れた名所 #旅行好きな人と繋がりたい"
EN_HASHTAGS = "#HiddenJapan #JapanTravel #TakaokaToyama #JapanTrip"


# ─── note記事のパース ─────────────────────────────────────────

def parse_note_article(path: Path) -> dict:
    """note記事MDファイルから必要情報を抽出"""
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")

    title = ""
    spots = []
    bullets = []
    intro = ""

    for i, line in enumerate(lines):
        if line.startswith("# ") and not title:
            title = line[2:].strip()
        if line.startswith("## ") and "とは" in line:
            # ## 〇〇とは → スポット名を抽出
            spot = line[3:].replace("とは", "").strip()
            if spot:
                spots.append(spot)
        if line.startswith("- ") or line.startswith("・"):
            clean = line.lstrip("-・ ").strip()
            if clean and len(clean) < 60:
                bullets.append(clean)
        # 最初の段落を introに
        if not intro and line.strip() and not line.startswith("#"):
            intro = line.strip()

    return {
        "title": title,
        "spots": spots[:3],
        "bullets": bullets[:5],
        "intro": intro,
        "filename": path.name,
    }


# ─── X投稿生成 ───────────────────────────────────────────────

def make_x_post(article: dict, post_id: str) -> dict:
    """note記事からX投稿（140文字以内）を生成"""
    title = article["title"]
    spots = article["spots"]
    bullets = article["bullets"][:3]
    spot = spots[0] if spots else "高岡市"

    # フックの選択（記事タイトルの特徴から）
    if "無料" in title:
        hook = f"「{spot}」が無料なの、知ってた？"
    elif "円" in title or "¥" in title:
        nums = re.findall(r"¥?(\d[\d,]+)", title)
        price = f"¥{nums[0]}" if nums else ""
        hook = f"高岡 {price}で行けるの、知らなすぎる"
    elif "国宝" in title:
        hook = f"国宝「{spot}」、観光客ほぼいない"
    else:
        hook = f"{spot}——まだ誰も気づいていない"

    # 本文
    body_lines = [f"\n{hook}\n"]
    for b in bullets:
        body_lines.append(f"・{b}")

    body_lines.append(f"\n東京から新幹線2時間。混んでいない理由は「知られていないから」だけ。")
    body_lines.append(f"\n{JP_HASHTAGS}")

    text = "\n".join(body_lines)
    # 140文字超えを防ぐ（URLなし版で保持）
    if len(text) > 280:
        text = text[:277] + "..."

    return {"id": post_id, "text": text, "source": "repurpose", "from": article["filename"]}


def make_x_post_en(article: dict, post_id: str) -> dict:
    """英語版X投稿を生成"""
    title = article["title"]
    spots = article["spots"]
    spot = spots[0] if spots else "Takaoka"
    spot_en = spot  # 実際は翻訳辞書があると良いが、高岡市名はそのままでも通じる

    hook = f"Most people visit Kyoto or Tokyo."
    body = f"\nBut {spot_en} in Takaoka City has something they don't:\n"

    bullets_en_map = {
        "無料": "Entrance: FREE",
        "国宝": "National Treasure",
        "観光客": "Almost no tourists",
        "職人": "400-year craft tradition",
    }

    for b in article["bullets"][:3]:
        matched = False
        for jp, en in bullets_en_map.items():
            if jp in b:
                body += f"· {en}\n"
                matched = True
                break
        if not matched:
            body += f"· {b}\n"

    body += f"\n{EN_HASHTAGS}"

    return {"id": post_id, "text": hook + body, "source": "repurpose_en", "from": article["filename"]}


# ─── Shorts台本生成 ──────────────────────────────────────────

def make_shorts_script(article: dict, script_id: str) -> dict:
    """note記事からYouTube Shorts台本（30秒）を生成"""
    title = article["title"]
    spots = article["spots"]
    bullets = article["bullets"][:3]
    spot = spots[0] if spots else "高岡市"

    # フック（3秒・黄文字・黒背景）
    if "無料" in title:
        hook = f"{spot}が無料な理由"
    elif "国宝" in title:
        hook = f"国宝が貸し切りで見られる場所"
    else:
        hook = f"知られていない日本がある"

    # シーン構成
    scenes = []
    for i, b in enumerate(bullets):
        scenes.append({
            "index": i + 1,
            "text": b,
            "duration": 6,
            "bg_color": ["#1a237e", "#4a148c", "#1b5e20"][i % 3],
        })

    script = {
        "id": script_id,
        "title": f"【知らなかった】{title[:30]}",
        "hook": hook,
        "scenes": scenes,
        "cta": f"{spot}を詳しくみる→noteリンク",
        "hashtags": "#高岡市 #Shorts #富山観光 #隠れた名所",
        "source_article": article["filename"],
        "generated_at": datetime.now().isoformat(),
    }

    # スクリプトファイルに保存
    out_path = SHORTS_SCRIPT_DIR / f"{script_id}_script.json"
    out_path.write_text(json.dumps(script, ensure_ascii=False, indent=2))

    return script


# ─── ロジック ────────────────────────────────────────────────

def load_repurpose_log() -> dict:
    if REPURPOSE_LOG.exists():
        return json.loads(REPURPOSE_LOG.read_text())
    return {"processed": []}


def save_repurpose_log(log: dict):
    REPURPOSE_LOG.write_text(json.dumps(log, ensure_ascii=False, indent=2))


def find_latest_published_articles() -> list[Path]:
    """直近に公開されたnote記事ファイルを取得（最大3本）"""
    articles = []
    if NOTE_QUEUE.exists():
        state = json.loads(NOTE_QUEUE.read_text())
        published = state.get("published", {})
        # 公開済みIDからファイルパスを特定
        for article_id, info in published.items():
            file_path = REPO / info.get("file", "")
            if file_path.exists():
                articles.append(file_path)
    # フォールバック: outputs配下の最新md
    if not articles:
        articles = sorted(OUTPUTS_DIR.glob("*_note記事.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:3]
    return articles[:3]


def add_to_x_queue(posts: list):
    """X投稿キューに追加（重複防止）"""
    extras = []
    if X_EXTRA_QUEUE.exists():
        extras = json.loads(X_EXTRA_QUEUE.read_text())
    existing_ids = {p["id"] for p in extras}
    added = 0
    for post in posts:
        if post["id"] not in existing_ids:
            extras.append(post)
            added += 1
    X_EXTRA_QUEUE.write_text(json.dumps(extras, ensure_ascii=False, indent=2))
    return added


# ─── メイン ──────────────────────────────────────────────────

def run():
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  コンテンツ横断変換（note→X→Shorts）")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    log = load_repurpose_log()
    articles = find_latest_published_articles()

    if not articles:
        print("  変換対象の記事が見つかりません（スキップ）")
        return

    total_x = 0
    total_shorts = 0

    for art_path in articles:
        if str(art_path) in log["processed"]:
            print(f"  ✅ {art_path.name} 変換済（スキップ）")
            continue

        print(f"\n  [{art_path.name}]")
        article = parse_note_article(art_path)

        if not article["title"]:
            print("  ⚠️  タイトル取得失敗（スキップ）")
            continue

        # X投稿生成（日本語+英語）
        base_id = f"rp_{art_path.stem[:20]}"
        post_jp = make_x_post(article, f"{base_id}_jp")
        post_en = make_x_post_en(article, f"{base_id}_en")

        added = add_to_x_queue([post_jp, post_en])
        total_x += added
        print(f"  📱 X投稿追加: {added}本")

        # Shortsスクリプト生成
        script = make_shorts_script(article, f"{base_id}_short")
        total_shorts += 1
        print(f"  🎬 Shorts台本生成: {script['title'][:40]}")

        log["processed"].append(str(art_path))

    save_repurpose_log(log)

    print(f"\n  X投稿追加計: {total_x}本")
    print(f"  Shorts台本計: {total_shorts}本")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


if __name__ == "__main__":
    run()
