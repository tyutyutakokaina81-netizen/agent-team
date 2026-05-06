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
mkdir -p "$BASE"/{logs,outputs,prompts,lib}
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
    "video_prompt": "Quiet evening street in Takaoka Japan, old Japanese residential area, warm streetlights"
  },
  {
    "theme": "富山湾の朝",
    "title_candidates": [
      "富山湾の朝、漁港の音で目覚める",
      "新湊の朝市、白えびの色",
      "海に近い暮らしの速度"
    ],
    "keywords": ["富山湾", "新湊", "朝市", "白えび", "海"],
    "video_prompt": "Early morning at Toyama Bay fishing port, soft sunrise, fishermen unloading boats"
  },
  {
    "theme": "立山の見える日",
    "title_candidates": [
      "立山が見える日は、空気がちがう",
      "3000mの山と、100mの暮らし",
      "雪の立山、田んぼの水鏡"
    ],
    "keywords": ["立山", "アルプス", "雪", "田んぼ", "水鏡"],
    "video_prompt": "Tateyama mountains reflected in flooded rice paddies, spring scene, cinematic wide shot"
  },
  {
    "theme": "北陸の食卓",
    "title_candidates": [
      "北陸の食卓は、静かに豊かだ",
      "氷見の鰤、ます寿司、地酒",
      "観光地でない場所の、本当の味"
    ],
    "keywords": ["氷見", "鰤", "ます寿司", "地酒", "食卓"],
    "video_prompt": "Traditional Japanese dinner table in Hokuriku, fresh sashimi, sake bottle, warm light"
  },
  {
    "theme": "ドラえもんの街",
    "title_candidates": [
      "ドラえもんの街で暮らすということ",
      "高岡駅前の、銅像と空",
      "藤子・F・不二雄が育った景色"
    ],
    "keywords": ["ドラえもん", "高岡", "藤子不二雄", "駅前", "銅像"],
    "video_prompt": "Doraemon statues at Takaoka station, peaceful daytime, locals passing by"
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
    """日付に基づいて topics.json から1トピックを選ぶ（決定論的＝同日同トピック）"""
    topics_file = LIB / "topics.json"
    topics = json.loads(topics_file.read_text(encoding="utf-8"))
    idx = (date.today().toordinal()) % len(topics)
    return topics[idx]


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
from _common import OUT, LOG, now_stamp, load_topic  # noqa: E402

ts = now_stamp()
topic = load_topic()
date_jp = datetime.now().strftime("%Y年%m月%d日")
title = topic["title_candidates"][0]
title_alts = "\n".join(f"{i+1}. {t}" for i, t in enumerate(topic["title_candidates"]))
tags_jp = " ".join(f"#{k}" for k in topic["keywords"])
tags_en = "#JapanLife #HiddenJapan #Hokuriku"

note_draft = f"""# note 記事下書き — {date_jp}

## テーマ: {topic['theme']}

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

import os
note_url = os.environ.get("NOTE_URL", "https://note.com/safe_canna441")
cw_application = f"""{{案件タイトル}} の件、ぜひお手伝いさせてください。

【専門領域】
{{専門領域 例：北陸地方の地域情報・観光・移住}}に関する
SEOライティング/取材/データ整理を継続的に手がけています。

【サンプル成果物】
・{note_url}（note）
・{note_url}/n/xxx（関連記事URL を貼る）
・{note_url}/n/yyy（関連記事URL を貼る）

【今回の案件への対応方針】
1. {{案件要件1}}について：{{具体的な進め方を1-2行}}
2. {{案件要件2}}について：{{具体的な進め方を1-2行}}
3. {{納品形式}}にて、{{納期}}までに納品いたします。

【継続対応の可否】
今回の案件が問題なく完了した場合、月次/週次での継続契約も
ご相談いただけます（単価は要件に応じて柔軟にご相談）。

【ご連絡について】
平日9-18時はチャット即時返信可能です。
不明点があれば事前に確認させていただきます。

どうぞよろしくお願いいたします。

---
※ {{}} の差込項目は応募前に必ず埋めること。空欄のまま送信しない。
※ 単価¥3K未満の案件はこのv2を使わず、量重視のv1で対応する。
"""

files = {
    f"{ts}_note_draft.md": note_draft,
    f"{ts}_x_post.txt": x_post,
    f"{ts}_reddit_post.md": reddit_post,
    f"{ts}_youtube_short.md": shorts_script,
    f"{ts}_cw_application.txt": cw_application,
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
# cw_helper.py — CrowdWorks 応募文をコピー＆ブラウザ起動
# ────────────────────────────────────────────────────────────
cat > cw_helper.py << 'PYEOF'
#!/usr/bin/env python3
"""最新の CrowdWorks 応募文をクリップボードにコピーしてジョブ一覧を開く。"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib"))
from _common import latest, copy_to_clipboard, open_url, record_post  # noqa: E402

app = latest("*_cw_application.txt")
if app is None:
    print("❌ cw_application.txt が見つかりません。先に run.sh を実行してください。")
    sys.exit(1)

text = app.read_text(encoding="utf-8")
if copy_to_clipboard(text):
    print("✅ 応募文をクリップボードにコピーしました")
else:
    print("⚠️  クリップボード未対応の環境です（手動でコピーしてください）")
    print(text)

print("\n📋 応募文プレビュー:")
print("-" * 40)
print(text[:200] + "...")
print("-" * 40)

cw_url = os.environ.get("CW_JOBS_URL", "https://crowdworks.jp/public/jobs?order=new")
if open_url(cw_url):
    print("✅ CrowdWorks の新着案件ページを開きました")
else:
    print(f"   👉 ブラウザで開いてください: {cw_url}")

log = record_post("cw", app.name)
print(f"📝 応募実行ログ: {log.name}")
print("\n👆 CrowdWorks で案件を選んで、応募文を貼り付けてください")
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
    print("   → python3 cw_helper.py        (CrowdWorks 応募)")
PYEOF

# ────────────────────────────────────────────────────────────
# launchd 設定（macOS のみ・既存チェックあり）
# ────────────────────────────────────────────────────────────
if [ "$(uname)" = "Darwin" ]; then
  PLIST_PATH="$HOME/Library/LaunchAgents/com.aiAuto.daily.plist"
  if launchctl list 2>/dev/null | grep -q "com.aiAuto.daily"; then
    echo "ℹ️  launchd は既にロード済みです（再ロードは launchctl unload/load で）"
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
    <dict>
      <key>Hour</key><integer>7</integer>
      <key>Minute</key><integer>0</integer>
    </dict>
    <dict>
      <key>Hour</key><integer>20</integer>
      <key>Minute</key><integer>0</integer>
    </dict>
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
    if launchctl load "$PLIST_PATH" 2>/dev/null; then
      echo "✅ launchd 登録完了（毎日 7:00 / 20:00 に自動実行）"
    else
      echo "⚠️  launchd 登録に失敗しました（手動で launchctl load してください）"
    fi
  fi
elif [ "$(uname)" = "Linux" ]; then
  echo "ℹ️  Linux 環境です。crontab に以下を登録してください:"
  echo "    0 7,20 * * * $BASE/run.sh"
fi

# ────────────────────────────────────────────────────────────
# README.md
# ────────────────────────────────────────────────────────────
cat > README.md << 'EOF'
# AI Auto Monetization — ~/ai-auto/

## 3つのコマンドだけ覚える

```bash
# 1. 生成物を作る（毎日 7:00 / 20:00 に自動実行）
python3 generate_daily_outputs.py

# 2. note に公開する
python3 note_publisher.py

# 3. CrowdWorks に応募する
python3 cw_helper.py
```

## 状況確認
```bash
python3 check_status.py
```

## ファイル構成
- `outputs/`   生成した記事・応募文・投稿文・posted_*.log（投稿実行ログ）
- `logs/`      実行ログ（月別ローテーション: run-YYYY-MM.log）
- `lib/`       共通モジュール (_common.py) とトピック (topics.json)
- `prompts/`   プロンプトテンプレート
- `.env`       APIキー（**Git に入れない**: .gitignore 済み）

## トピックのカスタマイズ
`lib/topics.json` を編集すると、日替わりで生成内容のテーマが変わります。
（日付の通し番号でトピックを決定論的に選択）

## クロスプラットフォーム
- macOS: `pbcopy` / `open` / `launchd` 自動利用
- Linux: `xclip` or `wl-copy` / `xdg-open` / `cron` 推奨

## KPI（目標）
- note: 毎日1本公開
- CrowdWorks: 毎日1件応募
- YouTube Shorts: 週3本

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
echo "  2. python3 cw_helper.py       → CrowdWorksに応募"
echo "  3. python3 check_status.py    → 状況確認"
echo "════════════════════════════════════════"
