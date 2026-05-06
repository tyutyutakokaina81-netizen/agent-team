#!/usr/bin/env bash
# PreToolUse Bash hook: git commit のメッセージを検査し、
# 「販売可能」「完成」「完了」等の語と brief.md の ❌（DoD 未達）が
# 同時に存在するコミットを 拒否する。
#
# 誤爆回避：commit 以外の bash コマンドは全てスルー。
# 「完了報告」のような中立語は許可（具体的な誇張語のみブロック）。

set -e

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // ""')

# git commit でなければスルー
if ! echo "$COMMAND" | grep -qE 'git[[:space:]]+commit'; then
  exit 0
fi

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)"

# コミットメッセージ全体（heredoc 含む）から禁止語を検出
FORBIDDEN_PATTERN='販売可能|そのまま売れる|即販売|即売れる|リリース可能|完璧に|100%完成'

if ! echo "$COMMAND" | grep -qE "$FORBIDDEN_PATTERN"; then
  # 禁止語なし → 通す
  exit 0
fi

# 禁止語あり → brief.md に ❌ が残っていないか確認
BRIEF_FILES=$(find projects -name "brief.md" 2>/dev/null)
HAS_INCOMPLETE=0

for BRIEF in $BRIEF_FILES; do
  # 完成度チェック表セクション内の ❌ を検出
  if awk '
    /^### 完成度チェック/{capture=1}
    capture && /^---$/{capture=0}
    capture && /^## /{capture=0}
    capture && /❌/{found=1}
    END{exit !found}
  ' "$BRIEF" 2>/dev/null; then
    HAS_INCOMPLETE=1
    INCOMPLETE_BRIEF="$BRIEF"
    break
  fi
done

if [ "$HAS_INCOMPLETE" -eq 1 ]; then
  # 違反検出：禁止語 ＋ DoD 未達 → 拒否
  REASON=$(cat <<EOF
【コミット拒否：DoD 違反】

このコミットメッセージに以下の禁止語が含まれています：
  パターン：${FORBIDDEN_PATTERN}

しかし brief.md の DoD 表に ❌（未達）の項目が残っています：
  ${INCOMPLETE_BRIEF}

CLAUDE.md「販売可能と言ってよい条件」より：
  「販売可能」「リリース可能」「即売れる」と表現してよいのは
  以下の全てを満たすときのみ：
    1. 購入者がそのまま使える形式でファイルが存在する
    2. 価格・販売チャネル・公開URLが確定している
    3. オーナーの追加作業が「アップロード操作」のみ

対応：以下のいずれかを選んでください
  A) コミットメッセージから禁止語を削除（「販売準備完了」「仕様完了」等に置き換え）
  B) brief.md の DoD 表で ❌ → ✅ に更新（実体が本当に揃っている場合）
EOF
)

  jq -n --arg r "$REASON" '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: $r
    }
  }'
  exit 0
fi

# 禁止語あり ＋ DoD 全達成 → ask（人間確認）
jq -n '{
  hookSpecificOutput: {
    hookEventName: "PreToolUse",
    permissionDecision: "ask",
    permissionDecisionReason: "コミットメッセージに『販売可能』等の強い表現が含まれています。本当に DoD（仕様書＋実体＋販売チャネル）を全て満たしていますか？"
  }
}'
