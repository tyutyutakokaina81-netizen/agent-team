#!/usr/bin/env bash
# Stop hook (高精度版): 直前のアシスタント出力に「完了」「完成」「販売可能」等の
# 主張が含まれているかを transcript から検出し、検証コマンド未実行なら
# decision: "block" でセルフチェックを強制する。
#
# 誤爆回避：単なる相槌・質問・進捗報告では発火しない。
# 完了主張が含まれる場合のみブロック。

set -e

INPUT=$(cat)
TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path // ""')

# transcript が無いセッション（テスト等）は何もしない
if [ -z "$TRANSCRIPT" ] || [ ! -f "$TRANSCRIPT" ]; then
  jq -n '{}'
  exit 0
fi

# 直近のアシスタントメッセージのテキストを抽出
LAST_ASSISTANT_TEXT=$(
  tac "$TRANSCRIPT" \
  | jq -r 'select(.type=="assistant" and .message.content) | .message.content[]? | select(.type=="text") | .text' 2>/dev/null \
  | head -50 \
  || echo ""
)

# 完了主張パターン（誇張・楽観報告の典型）
COMPLETION_CLAIM_PATTERN='完了報告|販売可能|そのまま売れる|即販売|リリース可能|完成しました|完成です|動作確認済|動くはず|動くと思う'

# 検証実行パターン（直近で grep/find/ls/wc/git log/curl 等を実行していれば OK）
VERIFICATION_PATTERN='ls .*\.csv|wc -l|grep -c|find .*-type|git log|git show|cat .*\.md.*head|curl '

# 完了主張なし → 何もしない
if ! echo "$LAST_ASSISTANT_TEXT" | grep -qE "$COMPLETION_CLAIM_PATTERN"; then
  jq -n '{}'
  exit 0
fi

# 完了主張あり → 直近10個のツール実行（Bash）を検査
RECENT_BASH=$(
  tac "$TRANSCRIPT" \
  | jq -r 'select(.type=="assistant" and .message.content) | .message.content[]? | select(.type=="tool_use" and .name=="Bash") | .input.command' 2>/dev/null \
  | head -10 \
  || echo ""
)

# 検証コマンドが直近にあれば OK（自己検証済とみなす）
if echo "$RECENT_BASH" | grep -qE "$VERIFICATION_PATTERN"; then
  jq -n '{}'
  exit 0
fi

# 違反検出：完了主張あり ＋ 検証コマンドなし → ブロック
REASON='【ほんとか？プロトコル違反検知】

直前の応答に「完了」「販売可能」「完成」等の主張が含まれていますが、
直近で検証コマンド（ls/find/wc/grep/git log 等）を実行した形跡がありません。

返答を終える前に、CLAUDE.md「ほんとか？プロトコル」のQ1〜Q3に
コマンド実行結果（客観証拠）で答えてください：

  Q1：仕様書だけで実体ファイルがないものはないか？
       → 例：ls projects/.../C_テンプレ販売/vol*.csv | wc -l
  Q2：『（〜は同様）』『TODO』が残っていないか？
       → 例：grep -rn -E "（.*同様.*続く）|TODO" --include="*.md"
  Q3：brief.md の DoD 表で ❌ の行を『完成』と報告していないか？
       → 例：grep -A30 "完成度チェック" projects/.../brief.md

検証実行後、結果を踏まえて報告内容を修正するか、
そのまま正しいことが確認できたら証拠を示しながら再報告してください。'

jq -n --arg r "$REASON" '{
  decision: "block",
  reason: $r
}'
