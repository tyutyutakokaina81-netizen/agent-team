#!/bin/zsh
# Skills インストールスクリプト
# 用途：CDO/outputs/skills/ 配下の SKILL.md を .claude/commands/ にコピーし、
#       Claude Code のスラッシュコマンドとして使えるようにする。
#
# 使い方：
#   ./CDO/outputs/skills/install.sh
#
# 設計意図：
#   - canonical（永続版）：CDO/outputs/skills/<name>/SKILL.md（Git管理）
#   - local（実行版）：.claude/commands/<name>.md（gitignore対象、ローカル専用）

set -e

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
SKILLS_DIR="$REPO_ROOT/CDO/outputs/skills"
COMMANDS_DIR="$REPO_ROOT/.claude/commands"

mkdir -p "$COMMANDS_DIR"

for skill_dir in "$SKILLS_DIR"/*/; do
  skill_name=$(basename "$skill_dir")
  src="$skill_dir/SKILL.md"
  dst="$COMMANDS_DIR/$skill_name.md"
  if [[ -f "$src" ]]; then
    cp "$src" "$dst"
    echo "✅ installed: /$skill_name → $dst"
  fi
done

echo ""
echo "完了。Claude Code を再起動するとスラッシュコマンドが認識されます。"
