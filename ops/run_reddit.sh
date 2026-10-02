#!/bin/bash
# ops/run_reddit.sh — Reddit へ手で投稿するための文面を出す（owner の Mac で実行）
#
#   cd ~/agent-team-run && bash ops/run_reddit.sh           診断（何本たまっているか）
#   cd ~/agent-team-run && bash ops/run_reddit.sh --manual  次の1本の文面を出す
#   cd ~/agent-team-run && bash ops/run_reddit.sh --posted  投稿したと記録する
#   cd ~/agent-team-run && bash ops/run_reddit.sh --undo    間違えて記録したとき戻す
#
#   板を選ぶときは --sub を足す（素材には複数の板向けが入っている）:
#     bash ops/run_reddit.sh --manual --sub r/japanlife
#
# なぜ作ったか（2026-10-02）:
#   素材が254本あって**127日間ひとつも投稿されていなかった**。X も同じ状態だったが、
#   今日 `--posted` を足したら動いた。原因は「やる気」ではなく**手順が通らないこと**だった
#   （貼り付けた改行を対話プロンプトが食って、記録まで届いていなかった）。
#   だから Reddit も**対話プロンプトを使わない**。文面を出す口と、記録する口を分ける。
#
# 投稿の作法について:
#   ・**1日1本まで**。まとめて出すと自己宣伝と見なされて削除・BANの対象になる。
#   ・subreddit ごとに規則が違う。初めて出す板は、規則を読んでから出すこと。
#   ・こちらが勝手に「投稿済み」にはしない（実績の水増しをしない）。
set -u
cd "$(dirname "$0")/.." 2>/dev/null || exit 1

SUB_WANT=""
if [ "${1:-}" = "--sub" ] || [ "${2:-}" = "--sub" ]; then
  if [ "${1:-}" = "--sub" ]; then SUB_WANT="${2:-}"; set -- "${3:-}"; else SUB_WANT="${3:-}"; fi
fi
export SUB_WANT
ARG_RAW="${1:-}"
ARG="$(printf '%s' "$ARG_RAW" | sed -e 's/[^A-Za-z-]*$//')"
case "$ARG" in
  ""|--manual|--posted|--undo) : ;;
  *) echo "✗ 知らない引数です: '${ARG_RAW}'"
     echo "   使えるのは: （なし） / --manual / --posted / --undo"
     exit 1 ;;
esac

LOG="ops/logs/reddit_posted.tsv"
mkdir -p ops/logs

PY=python3
command -v "$PY" >/dev/null 2>&1 || { echo "✗ python3 が見つかりません"; exit 1; }

if [ "$ARG" = "--undo" ]; then
  "$PY" - <<'PYEOF'
import os
LOG = "ops/logs/reddit_posted.tsv"
if not os.path.exists(LOG):
    print("記録がありません。"); raise SystemExit(0)
rows = [l for l in open(LOG, encoding="utf-8") if l.strip()]
if not rows:
    print("記録がありません。"); raise SystemExit(0)
last = rows[-1]
open(LOG, "w", encoding="utf-8").writelines(rows[:-1])
print("↩ 取り消しました:", last.strip())
print("   次に --manual を実行すると、また同じ素材が出ます。")
PYEOF
  exit 0
fi

"$PY" - "$ARG" <<'PYEOF'
import glob, json, os, re, sys, datetime

MODE = sys.argv[1] if len(sys.argv) > 1 else ""
DIR = "EN/outputs/reddit"
LOG = "ops/logs/reddit_posted.tsv"
REG = "CDO/outputs/note_publisher/published_registry.json"

posted = set()
if os.path.exists(LOG):
    for l in open(LOG, encoding="utf-8"):
        c = l.rstrip("\n").split("\t")
        if len(c) >= 2 and not l.startswith("#"):
            posted.add(c[1])

# 新しい素材から出す。古い記事の告知より、いま読める記事のほうが踏まれる。
files = sorted(glob.glob(os.path.join(DIR, "*.md")), reverse=True)
pending = [f for f in files if os.path.basename(f) not in posted]

if MODE == "":
    oldest = os.path.basename(files[0])[:10] if files else "—"
    print(f"=== Reddit の状態 ===")
    print(f"素材        : {len(files)}本")
    print(f"投稿済み    : {len(posted)}本")
    print(f"未投稿      : {len(pending)}本")
    if pending:
        print(f"次に出るもの: {os.path.basename(pending[0])[:60]}")
    print("")
    print("文面を出す  : bash ops/run_reddit.sh --manual")
    raise SystemExit(0)

if not pending:
    print("未投稿の素材がありません。"); raise SystemExit(3)

path = pending[0]
text = open(path, encoding="utf-8").read()

# 記事名 → note の URL（素材に URL が入っていないので、公開記録から引く）
url = ""
m = re.search(r"- Article: `(.+?)`", text)
if m:
    stem = m.group(1)[:-3] if m.group(1).endswith(".md") else m.group(1)
    art = os.path.join("CMO/outputs", stem + ".md")
    if os.path.exists(art) and os.path.exists(REG):
        a = open(art, encoding="utf-8").read()
        tm = re.search(r"##\s*タイトル.*?\n```\n(.+?)\n```", a, re.S)
        title = tm.group(1).strip().splitlines()[0].strip() if tm else ""
        for r in json.load(open(REG, encoding="utf-8")):
            if not r.get("unpublished") and r.get("title") == title:
                url = r.get("url", "")
                break

# 「## r/xxx」のセクションを拾う
secs = re.findall(r"##\s*(r/\S+)(.*?)(?=\n##\s|\Z)", text, re.S)
if not secs:
    print(f"✗ {os.path.basename(path)} から subreddit のセクションを読めませんでした")
    raise SystemExit(2)

want = os.environ.get("SUB_WANT", "").strip()
sub, chunk = secs[0]
if want:
    hit = [x for x in secs if x[0].lower().lstrip("r/") == want.lower().lstrip("r/")]
    if hit:
        sub, chunk = hit[0]
    else:
        print(f"⚠ この素材に {want} 向けはありません。あるのは: {', '.join(s for s, _ in secs)}")
        print(f"  {secs[0][0]} を出します。")
tm = re.search(r"\*\*Title\*\*:\s*\n```\n(.+?)\n```", chunk, re.S)
bm = re.search(r"\*\*Body\*\*:\s*\n```\n(.+?)\n```", chunk, re.S)
title = tm.group(1).strip() if tm else ""
body = bm.group(1).strip() if bm else ""
if url:
    body = body + f"\n\n{url}"

print(f"\n--- 次の素材: {os.path.basename(path)[:56]}（残り {len(pending)}本）---\n")
print(f"[板]   {sub}")
if len(secs) > 1:
    print(f"       （この素材には他に {', '.join(s for s, _ in secs[1:])} 向けもあります）")
print(f"\n[題名] {title}\n")
print("[本文]")
print(body)
print("")
if not url:
    print("⚠ note の URL が引けませんでした（まだ公開されていない記事の素材かもしれません）")
print(f"投稿先: https://www.reddit.com/{sub}/submit")
print("")
print("※ **1日1本まで**。まとめて出すと自己宣伝と見なされます。")
print("※ 初めて出す板は、先に板の規則を読むこと。")

open("/tmp/.reddit_next_body.txt", "w", encoding="utf-8").write(body)
open("/tmp/.reddit_next_file.txt", "w", encoding="utf-8").write(os.path.basename(path))

if MODE == "--posted":
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.datetime.now().isoformat()}\t{os.path.basename(path)}\t{sub}\tmanual\n")
    print(f"\n✅ 記録しました: {os.path.basename(path)[:50]}（{sub}）")
    print("   間違えて記録したときは: bash ops/run_reddit.sh --undo")
PYEOF
RC=$?
[ "$RC" -eq 3 ] && exit 0
[ "$RC" -ne 0 ] && exit "$RC"

if [ "$ARG" = "--manual" ] && command -v pbcopy >/dev/null 2>&1 && [ -f /tmp/.reddit_next_body.txt ]; then
  pbcopy < /tmp/.reddit_next_body.txt
  echo "📋 本文をクリップボードにコピーしました（Reddit の本文欄で ⌘V）"
  echo ""
  echo "投稿したら、これで記録してください:"
  echo "    cd ~/agent-team-run && bash ops/run_reddit.sh --posted"
fi

if [ "$ARG" = "--posted" ]; then
  git add -A ops/logs 2>/dev/null
  if ! git diff --cached --quiet; then
    git commit -qm "reddit: 手動投稿を記録 $(date +%F_%H%M)"
    for i in 1 2 3; do
      git push -q origin main && { echo "push しました"; break; }
      git pull --rebase -q origin main || true
      sleep $((i * 2))
    done
  fi
fi
