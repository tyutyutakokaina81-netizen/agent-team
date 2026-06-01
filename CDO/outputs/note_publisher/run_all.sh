#!/bin/zsh
# run_all.sh — エンドツーエンド自動化
# 1. git pull
# 2. サムネ画像を生成（OpenAI または Gemini）
# 3. 未公開記事を一括公開（text-only）
# 4. 公開済み記事に後追いでサムネ添付
#
# 使い方:
#   ./run_all.sh               # 全部実行
#   ./run_all.sh --skip-gen    # サムネ生成だけ飛ばす
#   ./run_all.sh --skip-pub    # 公開だけ飛ばす（既公開のサムネ後付けだけ）
#   ./run_all.sh --skip-attach # サムネ添付だけ飛ばす
#   ./run_all.sh --filter 2026-06-01  # 指定日のみ全工程
set -u

SCRIPT_DIR="${0:A:h}"
cd "$SCRIPT_DIR" || exit 1

SKIP_GEN=0
SKIP_PUB=0
SKIP_ATTACH=0
FILTER=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-gen)    SKIP_GEN=1;    shift ;;
    --skip-pub)    SKIP_PUB=1;    shift ;;
    --skip-attach) SKIP_ATTACH=1; shift ;;
    --filter)      FILTER="$2";   shift 2 ;;
    -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "未知のオプション: $1" >&2; exit 2 ;;
  esac
done

banner() { print -P "\n%F{cyan}========== $* ==========%f"; }

# --- API キーの事前確認 ---
if (( ! SKIP_GEN )); then
  if [[ -z "${OPENAI_API_KEY:-}" && -z "${GEMINI_API_KEY:-}" ]]; then
    print -P "%F{yellow}⚠  画像生成APIキーが未設定。サムネ生成を飛ばします（--skip-gen 相当）%f"
    print -P "    export OPENAI_API_KEY=sk-..."
    print -P "    または export GEMINI_API_KEY=..."
    SKIP_GEN=1
  fi
fi

# --- (1) サムネ画像生成 ---
if (( ! SKIP_GEN )); then
  banner "STEP 1/3  サムネ画像生成"
  if [[ -n "$FILTER" ]]; then
    python3 generate_thumbnails.py --filter "$FILTER" || true
  else
    python3 generate_thumbnails.py || true
  fi
fi

# --- (2) 公開ループ ---
if (( ! SKIP_PUB )); then
  banner "STEP 2/3  未公開記事を公開"
  if [[ -n "$FILTER" ]]; then
    ./publish_all.sh --date "$FILTER" || true
  else
    ./publish_all.sh || true
  fi
fi

# --- (3) サムネ後追い添付 ---
if (( ! SKIP_ATTACH )); then
  banner "STEP 3/3  公開済み記事に後追いでサムネ添付"
  if [[ -n "$FILTER" ]]; then
    python3 attach_thumbnails.py --filter "$FILTER" --skip-existing || true
  else
    python3 attach_thumbnails.py --skip-existing || true
  fi
fi

banner "ALL DONE"
