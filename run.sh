#!/bin/zsh
set -e

(
  printf "### SYSTEM\n"
  cat system/sisters.md

  printf "\n### AGENTS\n"
  for f in $(ls agents/*.md | sort); do
    printf "\n## %s\n" "$(basename "$f")"
    cat "$f"
  done

  printf "\n### TASK\n"
  cat task/task.md

  cat <<'EOF'

### INSTRUCTION
必ず以下の順で出力せよ：
① りん（技術・結論）
② しおり（法的・リスク）
③ あかね（体験・価値）
④ 統合結論（最終判断）

説明・構築・前置きは禁止。最終回答のみ出力せよ。
EOF
) | claude
