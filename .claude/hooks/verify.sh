#!/usr/bin/env bash
# verify.sh — 任意呼び出しの DoD 検証スクリプト。
# AI が完了報告の前に必ず呼ぶ運用を CLAUDE.md で義務化。
# 違反項目を列挙し、0件なら exit 0、1件以上なら exit 1。

set -e
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)"

VIOLATIONS=()

# ───────────────────────────────────────
# 検査1：未実装プレースホルダの残留
# ───────────────────────────────────────
PLACEHOLDER=$(grep -rn -E "（.*同様.*続く）|（.*個）$|（.*続く）$|TODO|FIXME|未実装|途中" \
  --include="*.md" --include="*.py" --include="*.mjs" \
  --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=.claude 2>/dev/null \
  | grep -vE 'CLAUDE\.md|verify\.sh|hooks/' \
  || true)

if [ -n "$PLACEHOLDER" ]; then
  VIOLATIONS+=("【未実装プレースホルダ残留】")
  while IFS= read -r line; do
    VIOLATIONS+=("  $line")
  done <<< "$PLACEHOLDER"
fi

# ───────────────────────────────────────
# 検査2：brief.md の ❌ 一覧
# ───────────────────────────────────────
for BRIEF in $(find projects -name "brief.md" 2>/dev/null); do
  INCOMPLETE=$(awk '
    /^### 完成度チェック/{capture=1; next}
    capture && /^---$/{capture=0}
    capture && /^## /{capture=0}
    capture && /❌/{print}
  ' "$BRIEF" 2>/dev/null || true)
  if [ -n "$INCOMPLETE" ]; then
    VIOLATIONS+=("【DoD 未達項目（$BRIEF）】")
    while IFS= read -r line; do
      VIOLATIONS+=("  $line")
    done <<< "$INCOMPLETE"
  fi
done

# ───────────────────────────────────────
# 検査3：仕様書とCSV実体の対応（Vol.X.md vs Vol.X*.csv）
# ───────────────────────────────────────
TEMPLATE_DIR="projects/2026-04-08_月30万自動化/C_テンプレ販売"
if [ -d "$TEMPLATE_DIR" ]; then
  for spec in "$TEMPLATE_DIR"/vol*.md; do
    [ -f "$spec" ] || continue
    name=$(basename "$spec" .md)
    vol_num=$(echo "$name" | grep -oE '^vol[0-9]+' || echo "")
    [ -z "$vol_num" ] && continue

    # Vol.4 は意図的にバンドル（実体なし）なのでスキップ
    if [ "$vol_num" = "vol4" ]; then continue; fi

    # 仕様書内に「CSV」「Excel」「スプレッドシート」記述がある場合、
    # 同じ vol 番号の .csv ファイルが存在することを期待
    if grep -qE 'CSV|Excel|スプレッドシート|シート1|シート2' "$spec" 2>/dev/null; then
      csv_count=$(ls "$TEMPLATE_DIR/${vol_num}"*.csv 2>/dev/null | wc -l)
      if [ "$csv_count" -eq 0 ]; then
        VIOLATIONS+=("【仕様書のみ・実体なし】 $name は CSV/Excel 設計を記述しているが ${vol_num}*.csv が存在しない")
      fi
    fi
  done
fi

# ───────────────────────────────────────
# 検査4：origin と local の同期確認
# ───────────────────────────────────────
BRANCH=$(git branch --show-current 2>/dev/null || echo "")
if [ -n "$BRANCH" ]; then
  LOCAL=$(git rev-parse "$BRANCH" 2>/dev/null || echo "")
  REMOTE=$(git rev-parse "origin/$BRANCH" 2>/dev/null || echo "")
  if [ -n "$LOCAL" ] && [ -n "$REMOTE" ] && [ "$LOCAL" != "$REMOTE" ]; then
    VIOLATIONS+=("【origin と local が不一致】 push が必要：local=$LOCAL origin=$REMOTE")
  fi
fi

# ───────────────────────────────────────
# 検査5：未コミットの変更
# ───────────────────────────────────────
DIRTY=$(git status -s 2>/dev/null || true)
if [ -n "$DIRTY" ]; then
  VIOLATIONS+=("【未コミットの変更あり】")
  while IFS= read -r line; do
    VIOLATIONS+=("  $line")
  done <<< "$DIRTY"
fi

# ───────────────────────────────────────
# 結果出力
# ───────────────────────────────────────
if [ ${#VIOLATIONS[@]} -eq 0 ]; then
  echo "✅ verify.sh: 全ての検査をパス（DoD 達成）"
  exit 0
fi

echo "❌ verify.sh: ${#VIOLATIONS[@]}件の違反を検出"
echo ""
for v in "${VIOLATIONS[@]}"; do
  echo "$v"
done
exit 1
