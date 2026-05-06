#!/usr/bin/env bash
# SessionStart hook: brief.md の DoD 表をセッション開始時に強制表示。
# AI が「最初に作る10本」の進捗状況を見ずに開始することを防ぐ。

set -e
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)"

BRIEF="projects/2026-04-08_月30万自動化/brief.md"

if [ ! -f "$BRIEF" ]; then
  echo '{}'
  exit 0
fi

# 「完成度チェック」セクションを抽出（### で始まる次の見出しまで）
DOD_TABLE=$(awk '
  /^### 完成度チェック/        { capture = 1; print; next }
  capture && /^---$/             { capture = 0 }
  capture && /^## /              { capture = 0 }
  capture                         { print }
' "$BRIEF")

# CLAUDE.md の DoD/「ほんとか？」プロトコル参照リマインダ
CONTEXT="【セッション開始：DoD 自動表示】

$DOD_TABLE

---

【厳守事項（CLAUDE.md より）】
1. DoD（完成の定義）：仕様書 ✅ ＋ 実体ファイル ✅ ＋ 販売／公開 ✅ の3点揃いで初めて『完成』
2. 「ほんとか？」プロトコル：完了報告の前に必ず以下3問にコマンド実行結果で答える
   Q1：仕様書だけで実体ファイルがないものはないか？（find/ls/wc -l で確認）
   Q2：『（〜は同様）』『TODO』が残っていないか？（grep -rn で確認）
   Q3：brief.md の DoD 表で ❌ の行を『完成』と報告していないか？
3. 完了報告フォーマット必須：実装した実体ファイル / 仕様のみ / 追加作業 / 誇張なし宣言
4. 『販売可能』『完成』表現は DoD を満たすときのみ使用可"

# JSON 出力（hookSpecificOutput.additionalContext で context に注入）
jq -n --arg ctx "$CONTEXT" '{
  hookSpecificOutput: {
    hookEventName: "SessionStart",
    additionalContext: $ctx
  }
}'
