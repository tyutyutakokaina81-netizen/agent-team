#!/bin/zsh
# publish_all.sh — Mac側で日次バッチ公開を堅牢に回すラッパー
#
# 何ができるか:
#  1. git lock 自動解除 → pull リトライ
#  2. CMO/outputs/ から未公開記事を検出
#  3. 1本ずつ publish_to_note.py --text-only で公開
#  4. 失敗してもループは止めずに次へ
#  5. 公開済みログ (.published.log) に記録、二重投稿を防止
#  6. 全体結果サマリを最後に表示
#
# 使い方:
#  ./publish_all.sh                # 全未公開を順に
#  ./publish_all.sh --date YYYY-MM-DD  # 指定日のみ
#  ./publish_all.sh --max 3        # 最大3本まで
#  ./publish_all.sh --dry-run      # 何を公開するか表示するだけ
#  ./publish_all.sh --reset        # 公開済みログを消す（再投稿したいとき）

set -u

# ---- 設定 ----
SCRIPT_DIR="${0:A:h}"
REPO_DIR="${SCRIPT_DIR}/../../.."
ARTICLES_DIR="${REPO_DIR}/CMO/outputs"
PUBLISHED_LOG="${SCRIPT_DIR}/.published.log"
PUBLISHED_TITLES="${SCRIPT_DIR}/.published_titles.log"
# 現在チェックアウト中のブランチを自動採用（旧: 固定ブランチ名をハードコードしていてpull失敗の原因だった）
BRANCH="$(git -C "${REPO_DIR}" rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)"
SLEEP_BETWEEN=10

DATE_FILTER=""
MAX_COUNT=0
DRY_RUN=0
RESET=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --date)    DATE_FILTER="$2"; shift 2 ;;
    --max)     MAX_COUNT="$2";   shift 2 ;;
    --dry-run) DRY_RUN=1;        shift ;;
    --reset)   RESET=1;          shift ;;
    -h|--help)
      grep '^#' "$0" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    *) echo "未知のオプション: $1" >&2; exit 2 ;;
  esac
done

log()  { print -P "%F{cyan}[$(date +%H:%M:%S)]%f $*"; }
ok()   { print -P "%F{green}✓%f $*"; }
warn() { print -P "%F{yellow}⚠%f  $*"; }
fail() { print -P "%F{red}✗%f $*"; }

# 記事mdからタイトル（メイン:／## タイトル 直下の```ブロック先頭行）を取り出す
article_title() {
  python3 - "$1" <<'PY'
import re, sys
t = open(sys.argv[1], encoding="utf-8").read()
m = re.search(r"メイン.*?\n```\n(.+?)\n```", t, re.S) or re.search(r"##\s*タイトル.*?\n```\n(.+?)\n```", t, re.S)
print(m.group(1).strip().splitlines()[0].strip() if m else "")
PY
}

# ---- reset ----
if (( RESET )); then
  if [[ -f "$PUBLISHED_LOG" ]]; then
    cp "$PUBLISHED_LOG" "${PUBLISHED_LOG}.bak.$(date +%Y%m%d%H%M%S)"
    : > "$PUBLISHED_LOG"
    ok "公開済みログをリセット（バックアップ取得済み）"
  else
    ok "公開済みログは元々空"
  fi
  [[ -f "$PUBLISHED_TITLES" ]] && : > "$PUBLISHED_TITLES"
  ok "タイトル重複ログもリセット"
  exit 0
fi

# ---- git lock 自動解除 ----
LOCK="${REPO_DIR}/.git/index.lock"
if [[ -f "$LOCK" ]]; then
  if pgrep -f "git " >/dev/null 2>&1; then
    fail "他のgitプロセスが動いています。終了を待ってから再実行してください。"
    ps -ef | grep "git " | grep -v grep
    exit 1
  fi
  warn "残置 index.lock を削除"
  rm -f "$LOCK"
fi

# ---- git pull（リトライ） ----
log "git pull origin $BRANCH"
cd "$REPO_DIR" || { fail "REPO_DIR に cd できません: $REPO_DIR"; exit 1; }

pull_ok=0
for attempt in 1 2 3 4; do
  if git pull origin "$BRANCH" 2>&1; then
    pull_ok=1
    break
  fi
  wait=$(( 2 ** attempt ))
  warn "pull 失敗 (attempt=$attempt) → ${wait}s 待って再試行"
  sleep "$wait"
done
(( pull_ok )) || { fail "git pull が4回失敗。中止。"; exit 1; }
ok "pull 完了"

# ---- 未公開記事を収集 ----
touch "$PUBLISHED_LOG" "$PUBLISHED_TITLES"

typeset -a candidates
if [[ -n "$DATE_FILTER" ]]; then
  candidates=("$ARTICLES_DIR"/${DATE_FILTER}_note記事_*.md(N))
else
  candidates=("$ARTICLES_DIR"/2026-*_note記事_*.md(N))
fi

typeset -a queue
typeset -A seen_titles
for f in "${candidates[@]}"; do
  base="${f:t}"
  grep -qxF "$base" "$PUBLISHED_LOG" && continue        # ファイル名で既公開ならスキップ
  title="$(article_title "$f")"
  if [[ -n "$title" ]]; then
    # タイトルが既公開 or 同一runで既出 → 重複公開（6/12インシデント）を防ぐ
    if grep -qxF "$title" "$PUBLISHED_TITLES" || [[ -n "${seen_titles[$title]:-}" ]]; then
      warn "重複タイトルをスキップ: ${base}（同題: ${title}）"
      continue
    fi
    seen_titles[$title]=1
  fi
  queue+="$f"
done

if (( ${#queue[@]} == 0 )); then
  ok "未公開なし。すべて公開済み（or 該当記事なし）。"
  exit 0
fi

log "公開キュー: ${#queue[@]}本"
for f in "${queue[@]}"; do print "  - ${f:t}"; done

if (( DRY_RUN )); then
  ok "dry-run: 公開は行いません"
  exit 0
fi

if (( MAX_COUNT > 0 )) && (( ${#queue[@]} > MAX_COUNT )); then
  queue=("${queue[@]:0:$MAX_COUNT}")
  warn "--max=$MAX_COUNT で先頭 $MAX_COUNT 本に絞ります"
fi

# ---- 順次公開 ----
cd "$SCRIPT_DIR" || exit 1

typeset -i success=0 failed=0
typeset -a failed_files

for f in "${queue[@]}"; do
  base="${f:t}"
  log "公開開始: $base"

  if python3 publish_to_note.py --article "$f" --text-only 2>&1 | tee "/tmp/note_publish_last.log"; then
    print "$base" >> "$PUBLISHED_LOG"
    title="$(article_title "$f")"
    [[ -n "$title" ]] && print "$title" >> "$PUBLISHED_TITLES"
    ok "完了: $base"
    success+=1
  else
    fail "失敗: $base"
    failed+=1
    failed_files+="$base"
  fi

  if (( success + failed < ${#queue[@]} )); then
    log "${SLEEP_BETWEEN}s 待機..."
    sleep "$SLEEP_BETWEEN"
  fi
done

# ---- サマリ ----
print ""
print "=================================================="
ok "成功: $success / ${#queue[@]}"
if (( failed > 0 )); then
  fail "失敗: $failed"
  for ff in "${failed_files[@]}"; do print "  - $ff"; done
  print ""
  warn "最後の失敗ログ: /tmp/note_publish_last.log"
  exit 1
fi
ok "全件公開完了"
