#!/bin/zsh
# ============================================================
# AI Auto Monetization Project — セットアップ（最適化版）
# 実行: chmod +x setup_ai_auto.sh && ./setup_ai_auto.sh
#
# 主な改善点（v0 → v1）:
#  - macOS/Linux 両対応（pbcopy/xclip, open/xdg-open を自動選択）
#  - .gitignore を自動生成し .env / logs / outputs の流出を防止
#  - publisher 系が投稿実行ログを残す（check_status と整合）
#  - launchd 二重ロード防止（macOS のみ実行、既存チェック）
#  - 共通モジュール _common.py に BASE/OUT/LOG/抽選を集約
#  - topics.json でトピックを日替わりローテーション
#  - bare except 排除・具体的例外指定
#  - set -euo pipefail でシェル堅牢化
#  - 月別ログローテーション (run-YYYY-MM.log)
# ============================================================

set -euo pipefail
BASE="$HOME/ai-auto"
echo "📁 $BASE を作成します..."
mkdir -p "$BASE"/{logs,outputs,prompts,lib,reflections}
cd "$BASE"

# ────────────────────────────────────────────────────────────
# .gitignore（最重要：APIキー・出力物を Git に入れない）
# ────────────────────────────────────────────────────────────
cat > .gitignore << 'EOF'
.env
logs/
outputs/
__pycache__/
*.pyc
.DS_Store
EOF

# ────────────────────────────────────────────────────────────
# .env テンプレート（既存があれば上書きしない）
# ────────────────────────────────────────────────────────────
if [ ! -f .env ]; then
cat > .env << 'EOF'
# APIキーをここに設定（絶対にGitにコミットしない）
OPENAI_API_KEY=sk-xxxx
NOTE_EMAIL=tyutyu.tako.kaina81@gmail.com
CW_USER=tyutyutakokaina
NOTE_URL=https://note.com/safe_canna441
CW_JOBS_URL=https://crowdworks.jp/public/jobs?order=new
EOF
echo "⚠️  .env を編集して APIキーを設定してください"
fi

# ────────────────────────────────────────────────────────────
# topics.json — トピックローテーション（日替わり）
# ────────────────────────────────────────────────────────────
if [ ! -f lib/topics.json ]; then
cat > lib/topics.json << 'EOF'
[
  {
    "theme": "高岡の夜",
    "title_candidates": [
      "高岡の夜に、静かに酒を飲む",
      "五月の高岡、風の匂い",
      "富山から見える、ゆっくりした世界"
    ],
    "keywords": ["高岡", "富山", "北陸", "夜", "路地"],
    "video_prompt": "Quiet evening street in Takaoka Japan, old Japanese residential area, warm streetlights",
    "score": 0
  },
  {
    "theme": "富山湾の朝",
    "title_candidates": [
      "富山湾の朝、漁港の音で目覚める",
      "新湊の朝市、白えびの色",
      "海に近い暮らしの速度"
    ],
    "keywords": ["富山湾", "新湊", "朝市", "白えび", "海"],
    "video_prompt": "Early morning at Toyama Bay fishing port, soft sunrise, fishermen unloading boats",
    "score": 0
  },
  {
    "theme": "立山の見える日",
    "title_candidates": [
      "立山が見える日は、空気がちがう",
      "3000mの山と、100mの暮らし",
      "雪の立山、田んぼの水鏡"
    ],
    "keywords": ["立山", "アルプス", "雪", "田んぼ", "水鏡"],
    "video_prompt": "Tateyama mountains reflected in flooded rice paddies, spring scene, cinematic wide shot",
    "score": 0
  },
  {
    "theme": "北陸の食卓",
    "title_candidates": [
      "北陸の食卓は、静かに豊かだ",
      "氷見の鰤、ます寿司、地酒",
      "観光地でない場所の、本当の味"
    ],
    "keywords": ["氷見", "鰤", "ます寿司", "地酒", "食卓"],
    "video_prompt": "Traditional Japanese dinner table in Hokuriku, fresh sashimi, sake bottle, warm light",
    "score": 0
  },
  {
    "theme": "ドラえもんの街",
    "title_candidates": [
      "ドラえもんの街で暮らすということ",
      "高岡駅前の、銅像と空",
      "藤子・F・不二雄が育った景色"
    ],
    "keywords": ["ドラえもん", "高岡", "藤子不二雄", "駅前", "銅像"],
    "video_prompt": "Doraemon statues at Takaoka station, peaceful daytime, locals passing by",
    "score": 0
  }
]
EOF
fi

# ────────────────────────────────────────────────────────────
# lib/_common.py — 共通定数・ヘルパー
# ────────────────────────────────────────────────────────────
cat > lib/_common.py << 'PYEOF'
"""共通定数とヘルパー（全スクリプトから import する）"""
from pathlib import Path
from datetime import datetime, date
import json
import platform
import shutil
import subprocess
import sys

BASE = Path.home() / "ai-auto"
OUT = BASE / "outputs"
LOG = BASE / "logs"
LIB = BASE / "lib"

OUT.mkdir(parents=True, exist_ok=True)
LOG.mkdir(parents=True, exist_ok=True)


def today_str() -> str:
    return date.today().strftime("%Y-%m-%d")


def now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H%M")


def load_topic() -> dict:
    """topics.json から score 加重で1トピックを選ぶ（反省会で score が更新される）。
    全 score が 0 なら日付ローテーション、score がついていれば最高 score を採用。"""
    topics_file = LIB / "topics.json"
    topics = json.loads(topics_file.read_text(encoding="utf-8"))
    scored = [t for t in topics if t.get("score", 0) > 0]
    if scored:
        return max(scored, key=lambda t: t.get("score", 0))
    idx = (date.today().toordinal()) % len(topics)
    return topics[idx]


def update_topic_score(theme: str, delta: int) -> None:
    """反省会の結果からトピックの score を加減する（精度向上ループの心臓部）"""
    topics_file = LIB / "topics.json"
    topics = json.loads(topics_file.read_text(encoding="utf-8"))
    for t in topics:
        if t.get("theme") == theme:
            t["score"] = t.get("score", 0) + delta
            break
    topics_file.write_text(json.dumps(topics, ensure_ascii=False, indent=2), encoding="utf-8")


def record_learning(line: str) -> Path:
    """精度向上のための学びを蓄積（generate が次回参照する）"""
    p = LIB / "learnings.md"
    if not p.exists():
        p.write_text("# 学びログ（毎日反省会で蓄積・generate が参照）\n\n", encoding="utf-8")
    with p.open("a", encoding="utf-8") as f:
        f.write(f"- {datetime.now().strftime('%Y-%m-%d %H:%M')}  {line}\n")
    return p


def load_recent_learnings(n: int = 5) -> list[str]:
    """直近 n 件の学びを返す（generate がプロンプトに反映する）"""
    p = LIB / "learnings.md"
    if not p.exists():
        return []
    lines = [ln.strip() for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip().startswith("- ")]
    return lines[-n:]


def open_url(url: str) -> bool:
    """OS判定してブラウザで URL を開く（成功なら True）"""
    system = platform.system()
    cmd = None
    if system == "Darwin":
        cmd = ["open", url]
    elif system == "Linux" and shutil.which("xdg-open"):
        cmd = ["xdg-open", url]
    elif system == "Windows":
        cmd = ["cmd", "/c", "start", "", url]
    if not cmd:
        return False
    try:
        subprocess.run(cmd, check=False)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def copy_to_clipboard(text: str) -> bool:
    """OS判定してクリップボードへコピー（成功なら True）"""
    system = platform.system()
    if system == "Darwin" and shutil.which("pbcopy"):
        cmd = ["pbcopy"]
    elif system == "Linux" and shutil.which("xclip"):
        cmd = ["xclip", "-selection", "clipboard"]
    elif system == "Linux" and shutil.which("wl-copy"):
        cmd = ["wl-copy"]
    else:
        return False
    try:
        subprocess.run(cmd, input=text.encode("utf-8"), check=True)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def record_post(kind: str, source_file: str) -> Path:
    """投稿実行ログを残す（check_status.py が参照する）"""
    p = OUT / f"posted_{today_str()}_{kind}.log"
    line = f"{datetime.now().isoformat()}\t{kind}\t{source_file}\n"
    with p.open("a", encoding="utf-8") as f:
        f.write(line)
    return p


def latest(pattern: str) -> Path | None:
    """outputs/ 内で pattern にマッチする最新ファイルを返す"""
    files = sorted(OUT.glob(pattern), reverse=True)
    return files[0] if files else None
PYEOF
touch lib/__init__.py

# ────────────────────────────────────────────────────────────
# run.sh — cron/launchd から呼ばれるメインスクリプト
# ────────────────────────────────────────────────────────────
cat > run.sh << 'EOF'
#!/bin/zsh
set -euo pipefail
cd "$HOME/ai-auto"
mkdir -p logs outputs
MONTH=$(date '+%Y-%m')
LOGFILE="logs/run-${MONTH}.log"
{
  echo "===== RUN $(date '+%Y-%m-%d %H:%M:%S') ====="
  python3 generate_daily_outputs.py
  echo "===== END $(date '+%Y-%m-%d %H:%M:%S') ====="
} >> "$LOGFILE" 2>&1
EOF
chmod +x run.sh

# ────────────────────────────────────────────────────────────
# generate_daily_outputs.py — メイン生成スクリプト
# ────────────────────────────────────────────────────────────
cat > generate_daily_outputs.py << 'PYEOF'
#!/usr/bin/env python3
"""毎日の生成物を作って outputs/ に保存する。"""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib"))
from _common import OUT, LOG, now_stamp, load_topic, load_recent_learnings  # noqa: E402

ts = now_stamp()
topic = load_topic()
learnings = load_recent_learnings(5)
date_jp = datetime.now().strftime("%Y年%m月%d日")
title = topic["title_candidates"][0]
title_alts = "\n".join(f"{i+1}. {t}" for i, t in enumerate(topic["title_candidates"]))
tags_jp = " ".join(f"#{k}" for k in topic["keywords"])
tags_en = "#JapanLife #HiddenJapan #Hokuriku"

learnings_block = ""
if learnings:
    learnings_block = "## 直近の学び（反省会から自動反映）\n" + "\n".join(learnings) + "\n\n"

note_draft = f"""# note 記事下書き — {date_jp}

{learnings_block}## テーマ: {topic['theme']}

## タイトル案（3案）
{title_alts}

## 本文（800字〜）
[ここに本文を書く]

{topic['theme']}を題材に、ふだんの暮らしの速度を書く。
都会には無い、北陸の静かな時間の流れ。
近所の人との何でもない会話、地元の食べ物、空気の匂い。

そういうものに価値があると、最近よく思う。

## 英語サブタイトル案
— A quiet day in Hokuriku, Japan ({topic['theme']})

## タグ
{tags_jp} #エッセイ #takaoka #hokuriku #hiddenjapan #japon

---

## 📮 お知らせ

### 🤝 お仕事のご相談
SEOライティング・SNS運用代行・スプレッドシート構築のご依頼を承っています。
- 単発記事執筆：¥5,000〜
- 月次SNS運用：¥30,000〜
- カスタムスプレッドシート構築：¥30,000〜
- お問い合わせ：X DM または noteコメント

### 📊 販売中のテンプレート
- Vol.1 フリーランス収支管理スプレッドシート（¥980）
- Vol.2 SNSコンテンツカレンダー（¥1,500・近日公開）
- テンプレ全部入りサブスク（月¥1,500）★お得

### 📬 メルマガ（月1配信）
北陸からのスローライフ × フリーランス自動化術を月1でお届けします。

---

*この記事は、北陸・高岡から発信しています。スキ・フォロー励みになります。*
"""

x_post = f"""📝 新しいnote記事を書きました。

{topic['theme']}についての話。
何でもない日常が、実はすごく豊かだという話。

→ [note URL をここに貼る]

{tags_jp}

---
EN: New essay — {topic['theme']} in Hokuriku, Japan.
The kind of slow life you don't find in Tokyo.
{tags_en}
"""

reddit_post = f"""**Title:**
Living in a quiet Japanese city that nobody talks about (Takaoka, Toyama) — {topic['theme']}

**Body:**
I live in Takaoka, a small city in Hokuriku, Japan.
Today I want to share about: {topic['theme']}.

It's Doraemon's hometown. You can see the 3,000m Alps and the Sea of Japan at the same time from here.
Nobody rushes. Neighbors greet you. The food is unbelievably good (fresh seafood from Toyama Bay).

I write about daily life here in Japanese (with English summaries):
https://note.com/safe_canna441

Does anyone else live somewhere "nobody knows about" but loves it?

---
Subreddits to post: r/JapanTravel r/japanlife r/SlowLiving r/NatureIsFuckingLit
"""

shorts_script = f"""# YouTube Shorts 台本 — {date_jp}

## タイトル
{title} / A quiet moment in Takaoka

## 台本（30〜60秒）
（{topic['theme']}の映像）
{topic['theme']}は、音が少ない。

（路地・風景の映像）
観光地から少し離れれば、
ふつうの暮らしが、ふつうのまま続いている。

（食事 or 自然の映像）
ここには、急ぐ人がいない。

（締めの空 or 山の映像）
東京とは、時間の流れが違う。
それが、ここが好きな理由。

## ハッシュタグ
{tags_jp} #shorts #takaoka #hiddenjapan #japanlife

## 動画プロンプト（Kling AI 用）
{topic['video_prompt']}, slow cinematic pan, no tourists,
peaceful atmosphere, muted colors, documentary style, 30 seconds
"""

# NOTE: CW応募文生成は柱D（projects/.../D_エクセル入力スクレイピング/pipeline/03_apply.py）に
# 一本化したため、本スクリプトでは生成しない。本スクリプトの責務は SNS発信（note/X/Reddit/Shorts）に限定。

files = {
    f"{ts}_note_draft.md": note_draft,
    f"{ts}_x_post.txt": x_post,
    f"{ts}_reddit_post.md": reddit_post,
    f"{ts}_youtube_short.md": shorts_script,
}

for name, body in files.items():
    (OUT / name).write_text(body, encoding="utf-8")
    print(f"✅ {name}")

with (LOG / "daily.log").open("a", encoding="utf-8") as f:
    f.write(f"{datetime.now().isoformat()}\tgenerated\t{len(files)}\ttopic={topic['theme']}\n")

print(f"\n📂 outputs/ に {len(files)} ファイル保存（テーマ: {topic['theme']}）")
print("次のステップ: outputs/ を開いて内容を確認・公開してください")
PYEOF

# ────────────────────────────────────────────────────────────
# note_publisher.py — note 下書きをクリップボードへコピー＆ブラウザ起動
# ────────────────────────────────────────────────────────────
cat > note_publisher.py << 'PYEOF'
#!/usr/bin/env python3
"""最新の note 下書きを表示・コピーし、note 新規作成ページを開く。"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib"))
from _common import latest, copy_to_clipboard, open_url, record_post  # noqa: E402

draft = latest("*_note_draft.md")
if draft is None:
    print("❌ note_draft.md が見つかりません。先に run.sh を実行してください。")
    sys.exit(1)

text = draft.read_text(encoding="utf-8")
print(f"📄 最新の下書き: {draft.name}")
print("=" * 60)
print(text)
print("=" * 60)

if copy_to_clipboard(text):
    print("✅ 下書きをクリップボードにコピーしました")
else:
    print("⚠️  クリップボード未対応の環境です（手動でコピーしてください）")

note_url = os.environ.get("NOTE_URL", "https://note.com") + "/notes/new"
if open_url("https://note.com/notes/new"):
    print("✅ noteの新規作成ページを開きました")
else:
    print(f"   👉 ブラウザで開いてください: {note_url}")

log = record_post("note", draft.name)
print(f"📝 投稿実行ログ: {log.name}")
PYEOF

# ────────────────────────────────────────────────────────────
# cw_helper.py — 削除（柱D pipeline に一本化）
# ────────────────────────────────────────────────────────────
# CW応募関連は柱D（projects/.../D_エクセル入力スクレイピング/pipeline/）が担当する。
# ~/ai-auto/ では CW 応募文を生成しないため cw_helper.py は不要。
# 互換のため、過去に生成したファイルを掃除する案内のみ残す:
if [ -f "$HOME/ai-auto/cw_helper.py" ]; then
  rm "$HOME/ai-auto/cw_helper.py"
  echo "🧹 旧 cw_helper.py を削除しました（柱D pipeline に一本化）"
fi
# 旧 cw_application 出力も掃除
find "$HOME/ai-auto/outputs" -maxdepth 1 -name "*_cw_application.txt" -delete 2>/dev/null || true

# ────────────────────────────────────────────────────────────
# daily_reflection.py — 毎日21:00の反省会（精度向上ループの心臓）
# ────────────────────────────────────────────────────────────
cat > daily_reflection.py << 'PYEOF'
#!/usr/bin/env python3
"""毎日21:00 に当日の生成・投稿を振り返り、学びを蓄積する。
- 当日の posted_*.log と outputs/ をスキャン
- インタラクティブモード（ターミナル実行時）：質問形式で反省記入
- 自動モード（cron実行時）：成果サマリのみ自動記録
- 結論として topics.json の score を加減し、次回 generate に反映
"""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib"))
from _common import (  # noqa: E402
    OUT, LOG, BASE, today_str, record_learning, update_topic_score, load_topic
)

REFLECT_DIR = BASE / "reflections"
REFLECT_DIR.mkdir(exist_ok=True)

today = today_str()
reflect_file = REFLECT_DIR / f"{today}.md"

today_files = sorted(OUT.glob(f"{today}*"))
posted = sorted(OUT.glob(f"posted_{today}_*.log"))
posted_kinds = sorted({p.name.split("_")[2].replace(".log", "") for p in posted})

today_topic = load_topic()
theme = today_topic.get("theme", "不明")

generated = len(today_files) - len(posted)
post_count = len(posted)


def auto_summary() -> str:
    return f"""# 反省会 — {today}

## 今日のテーマ
{theme}

## 自動集計
- 生成ファイル数: {generated}
- 投稿実行数: {post_count}（{', '.join(posted_kinds) or 'なし'}）

## 自動評価
{"✅ 投稿あり → score +1" if post_count > 0 else "⚠️ 投稿ゼロ → score -1"}

## 学び（手動追記欄）
- [ここに今日の学びを書く（次回generateに自動反映される）]

## 翌日アクション
- [明日やること1]
- [明日やること2]
"""


def interactive_reflection() -> str:
    print(f"\n📝 反省会 — {today}（テーマ: {theme}）")
    print(f"  生成: {generated}件 / 投稿: {post_count}件")
    print("\n3つの質問に答えてください（空Enterでスキップ）:\n")

    try:
        q1 = input("Q1. 今日効いた施策は？(例: コンサル無料相談予約1件)\n> ").strip()
        q2 = input("Q2. 今日の失敗・反省は？(例: CW応募0件)\n> ").strip()
        q3 = input("Q3. 明日変えることは？(例: 朝イチでCW応募3件)\n> ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n対話モード中断 → 自動モードで記録します")
        return auto_summary()

    body = f"""# 反省会 — {today}

## 今日のテーマ
{theme}

## 自動集計
- 生成ファイル数: {generated}
- 投稿実行数: {post_count}（{', '.join(posted_kinds) or 'なし'}）

## 効いた施策（Q1）
{q1 or '（記入なし）'}

## 失敗・反省（Q2）
{q2 or '（記入なし）'}

## 明日変えること（Q3）
{q3 or '（記入なし）'}
"""

    if q1:
        record_learning(f"効いた施策: {q1}")
    if q3:
        record_learning(f"明日試す: {q3}")

    return body


if sys.stdin.isatty():
    body = interactive_reflection()
else:
    body = auto_summary()

reflect_file.write_text(body, encoding="utf-8")

if post_count > 0:
    update_topic_score(theme, +1)
    score_msg = f"✅ {theme} score +1"
else:
    update_topic_score(theme, -1)
    score_msg = f"⚠️ {theme} score -1"

with (LOG / "reflection.log").open("a", encoding="utf-8") as f:
    f.write(f"{datetime.now().isoformat()}\t{theme}\tposts={post_count}\t{score_msg}\n")

print(f"\n📂 反省ファイル: {reflect_file.name}")
print(f"📊 {score_msg}")
print(f"📝 学びは lib/learnings.md に蓄積されます（次回 generate に自動反映）")
PYEOF

# ────────────────────────────────────────────────────────────
# weekly_review.py — 週次集計（毎週月曜）
# ────────────────────────────────────────────────────────────
cat > weekly_review.py << 'PYEOF'
#!/usr/bin/env python3
"""毎週月曜に過去7日の反省を集計し、topics scoreランキングを出す。"""
import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib"))
from _common import BASE, LIB, LOG  # noqa: E402

REFLECT_DIR = BASE / "reflections"
WEEK_DIR = BASE / "weekly_reviews"
WEEK_DIR.mkdir(exist_ok=True)

today = date.today()
week_start = today - timedelta(days=7)
review_file = WEEK_DIR / f"{today.isoformat()}_week.md"

reflections = sorted(REFLECT_DIR.glob("*.md"))
recent = [r for r in reflections if r.stem >= week_start.isoformat()]

topics_file = LIB / "topics.json"
topics = json.loads(topics_file.read_text(encoding="utf-8"))
ranked = sorted(topics, key=lambda t: t.get("score", 0), reverse=True)
ranking = "\n".join(
    f"{i+1}. {t['theme']} (score: {t.get('score', 0)})" for i, t in enumerate(ranked)
)

body = f"""# 週次レビュー — {week_start} 〜 {today}

## 今週の反省ファイル ({len(recent)}件)
{chr(10).join(f"- {r.name}" for r in recent) or "（なし）"}

## トピック score ランキング
{ranking}

## 推奨アクション
- score 最上位のテーマを来週は重点的に試す
- score がマイナスのテーマは一時除外を検討
- 学びログ (lib/learnings.md) を見直し、共通パターンを抽出
"""

review_file.write_text(body, encoding="utf-8")
print(f"📊 週次レビュー: {review_file.name}")
print(body)
PYEOF

# ────────────────────────────────────────────────────────────
# check_status.py — 今日の状況確認
# ────────────────────────────────────────────────────────────
cat > check_status.py << 'PYEOF'
#!/usr/bin/env python3
"""今日の実行状況を表示する。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib"))
from _common import OUT, LOG, today_str  # noqa: E402

today = today_str()
print(f"📊 AI Auto Status — {today}")
print("=" * 50)

daily_log = LOG / "daily.log"
if daily_log.exists():
    lines = [ln for ln in daily_log.read_text(encoding="utf-8").splitlines() if today in ln]
    print(f"✅ 今日の生成: {len(lines)}回")
    for ln in lines[-3:]:
        print(f"   {ln}")
else:
    print("❌ 生成ログなし（まだ実行されていません）")

today_files = sorted(OUT.glob(f"{today}*"))
print(f"\n📁 今日の生成ファイル: {len(today_files)}個")
for f in today_files:
    print(f"   {f.name}")

posted = sorted(OUT.glob(f"posted_{today}_*.log"))
print(f"\n🚀 今日の投稿実行: {len(posted)}件")
for p in posted:
    last = p.read_text(encoding="utf-8").strip().splitlines()[-1] if p.stat().st_size else ""
    print(f"   {p.name}\t{last}")

if len(posted) == 0:
    print("\n⚠️  本日はまだ何も投稿していません")
    print("   → python3 note_publisher.py   (note 公開)")
    print("   → CW応募は柱D pipeline で実行: ")
    print("     cd <repo>/projects/2026-04-08_月30万自動化/D_エクセル入力スクレイピング/pipeline")
    print("     python3 run_pipeline.py search")
PYEOF

# ────────────────────────────────────────────────────────────
# launchd 設定（macOS のみ・既存チェックあり）
# ────────────────────────────────────────────────────────────
if [ "$(uname)" = "Darwin" ]; then
  PLIST_PATH="$HOME/Library/LaunchAgents/com.aiAuto.daily.plist"
  REFLECT_PLIST="$HOME/Library/LaunchAgents/com.aiAuto.reflect.plist"
  WEEKLY_PLIST="$HOME/Library/LaunchAgents/com.aiAuto.weekly.plist"

  # 生成ジョブ（朝7:00・夜20:00）
  if launchctl list 2>/dev/null | grep -q "com.aiAuto.daily"; then
    echo "ℹ️  launchd daily は既にロード済み"
  else
    if [ ! -f "$PLIST_PATH" ]; then
cat > "$PLIST_PATH" << PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.aiAuto.daily</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/zsh</string>
    <string>$BASE/run.sh</string>
  </array>
  <key>StartCalendarInterval</key>
  <array>
    <dict><key>Hour</key><integer>7</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Hour</key><integer>20</integer><key>Minute</key><integer>0</integer></dict>
  </array>
  <key>StandardOutPath</key>
  <string>$BASE/logs/launchd.out.log</string>
  <key>StandardErrorPath</key>
  <string>$BASE/logs/launchd.err.log</string>
  <key>RunAtLoad</key>
  <false/>
</dict>
</plist>
PLISTEOF
    fi
    launchctl load "$PLIST_PATH" 2>/dev/null && \
      echo "✅ daily 登録完了（朝7:00 / 夜20:00 生成）" || \
      echo "⚠️  daily 登録に失敗"
  fi

  # 反省会ジョブ（毎日21:00 自動モード）
  if launchctl list 2>/dev/null | grep -q "com.aiAuto.reflect"; then
    echo "ℹ️  launchd reflect は既にロード済み"
  else
    if [ ! -f "$REFLECT_PLIST" ]; then
cat > "$REFLECT_PLIST" << PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.aiAuto.reflect</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/python3</string>
    <string>$BASE/daily_reflection.py</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>21</integer><key>Minute</key><integer>0</integer></dict>
  <key>StandardOutPath</key>
  <string>$BASE/logs/reflect.out.log</string>
  <key>StandardErrorPath</key>
  <string>$BASE/logs/reflect.err.log</string>
  <key>WorkingDirectory</key>
  <string>$BASE</string>
</dict>
</plist>
PLISTEOF
    fi
    launchctl load "$REFLECT_PLIST" 2>/dev/null && \
      echo "✅ reflect 登録完了（毎日21:00 反省会・自動モード）" || \
      echo "⚠️  reflect 登録に失敗"
  fi

  # 週次レビュー（月曜10:00）
  if launchctl list 2>/dev/null | grep -q "com.aiAuto.weekly"; then
    echo "ℹ️  launchd weekly は既にロード済み"
  else
    if [ ! -f "$WEEKLY_PLIST" ]; then
cat > "$WEEKLY_PLIST" << PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.aiAuto.weekly</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/python3</string>
    <string>$BASE/weekly_review.py</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict><key>Weekday</key><integer>1</integer><key>Hour</key><integer>10</integer><key>Minute</key><integer>0</integer></dict>
  <key>StandardOutPath</key>
  <string>$BASE/logs/weekly.out.log</string>
  <key>StandardErrorPath</key>
  <string>$BASE/logs/weekly.err.log</string>
  <key>WorkingDirectory</key>
  <string>$BASE</string>
</dict>
</plist>
PLISTEOF
    fi
    launchctl load "$WEEKLY_PLIST" 2>/dev/null && \
      echo "✅ weekly 登録完了（毎週月曜10:00 週次レビュー）" || \
      echo "⚠️  weekly 登録に失敗"
  fi
elif [ "$(uname)" = "Linux" ]; then
  echo "ℹ️  Linux 環境です。crontab に以下を登録してください:"
  echo "    0 7,20 * * * $BASE/run.sh"
  echo "    0 21 * * * /usr/bin/python3 $BASE/daily_reflection.py"
  echo "    0 10 * * 1 /usr/bin/python3 $BASE/weekly_review.py"
fi

# ────────────────────────────────────────────────────────────
# README.md
# ────────────────────────────────────────────────────────────
cat > README.md << 'EOF'
# AI Auto Monetization — ~/ai-auto/

## 責務（柱Dとの棲み分け）

このディレクトリは **SNS発信専用**（note / X / Reddit / YouTube Shorts）。
**CW・Lancers の応募/受注は柱D pipeline が担当**：
`<repo>/projects/2026-04-08_月30万自動化/D_エクセル入力スクレイピング/pipeline/`

## 2つのコマンドだけ覚える

```bash
# 1. 生成物を作る（毎日 7:00 / 20:00 自動実行）
python3 generate_daily_outputs.py

# 2. note に公開する
python3 note_publisher.py
```

## 反省会・状況確認
```bash
python3 daily_reflection.py   # 毎日 21:00 自動実行（対話モード/自動モード両対応）
python3 weekly_review.py      # 毎週月曜 10:00 自動実行
python3 check_status.py       # 任意のタイミングで現状確認
```

## ファイル構成
- `outputs/`       生成した記事・posted_*.log
- `logs/`          実行ログ（月別ローテーション: run-YYYY-MM.log）
- `lib/`           共通モジュール (_common.py)・トピック (topics.json)・学び (learnings.md)
- `reflections/`   日次反省ファイル
- `weekly_reviews/` 週次レビューファイル
- `prompts/`       プロンプトテンプレート
- `.env`           APIキー（**Git に入れない**: .gitignore 済み）

## 精度向上ループ
1. 朝/夜 generate（`learnings.md` の直近5件を反映）
2. 投稿 → posted_*.log
3. 21:00 reflection（投稿数で score 加減・学び記録）
4. 月曜10:00 weekly（scoreランキングで来週方針）

## トピックのカスタマイズ
`lib/topics.json` を編集。score が反省会で更新され、最高スコアテーマが優先選択される。

## クロスプラットフォーム
- macOS: `pbcopy` / `open` / `launchd` 自動利用
- Linux: `xclip` or `wl-copy` / `xdg-open` / `cron` 推奨

## KPI（目標・SNS発信のみ）
- note: 毎日1本公開
- YouTube Shorts: 週3本
- ※CW案件受注KPIは柱Dが管理

## note アカウント
https://note.com/safe_canna441
EOF

# ────────────────────────────────────────────────────────────
# 初回実行
# ────────────────────────────────────────────────────────────
echo ""
echo "🚀 セットアップ完了！初回生成を実行します..."
echo ""
python3 generate_daily_outputs.py
echo ""
echo "════════════════════════════════════════"
echo "✅ ~/ai-auto のセットアップが完了しました"
echo ""
echo "次のステップ:"
echo "  1. python3 note_publisher.py  → note記事を公開"
echo "  2. python3 check_status.py    → 状況確認"
echo "  3. python3 daily_reflection.py → 反省会（任意）"
echo ""
echo "  CW応募は柱D pipeline で実行:"
echo "    cd <repo>/projects/2026-04-08_月30万自動化/D_エクセル入力スクレイピング/pipeline"
echo "    python3 run_pipeline.py search"
echo "════════════════════════════════════════"
