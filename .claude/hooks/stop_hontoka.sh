#!/usr/bin/env bash
# Stop hook: 返答終了時に AI が完了/販売可能を主張していたら検証を強制。
# 検証行為（grep/ls/wc/git log 等の Bash 実行）が直近に無ければ block して再検証を要求。

set -e
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)"

INPUT=$(cat)
TRANSCRIPT_PATH=$(echo "$INPUT" | jq -r '.transcript_path // ""')

# transcript が無い場合は軽量リマインダのみ（block しない）
if [ -z "$TRANSCRIPT_PATH" ] || [ ! -f "$TRANSCRIPT_PATH" ]; then
  jq -n '{
    hookSpecificOutput: {
      hookEventName: "Stop",
      additionalContext: "【リマインダ】完了・販売可能・動作確認の主張前に「ほんとか？」プロトコルQ1〜Q3を実行（CLAUDE.md参照）。"
    }
  }'
  exit 0
fi

# Python で transcript を解析して、直近ターンに完了主張があるかチェック
python3 - "$TRANSCRIPT_PATH" <<'PYEOF'
import json
import re
import sys

transcript_path = sys.argv[1]

# 完了主張のパターン
CLAIM_PATTERNS = [
    r'販売可能', r'販売準備完了', r'完成しました', r'完成です',
    r'完了しました', r'完了です', r'実装完了', r'動きます',
    r'動きました', r'動作確認.*済', r'OK です', r'問題ありません',
    r'達成しました', r'できました'
]

# 検証行為のパターン（直近ターンで実行されたツールコマンド）
VERIFY_PATTERNS = [
    r'\bgrep\b', r'\bfind\b', r'\bls\b', r'\bwc\b', r'\bcat\b',
    r'\bgit log\b', r'\bgit status\b', r'\bgit diff\b', r'\bjq\b',
    r'python.*-c', r'node.*-e', r'curl '
]

try:
    with open(transcript_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
except Exception:
    print(json.dumps({}))
    sys.exit(0)

# 最後の assistant ターンを取得（最新50行を確認）
# transcript は jsonl 形式
recent = lines[-100:] if len(lines) > 100 else lines
last_assistant_text = ''
recent_bash_commands = []

for line in reversed(recent):
    line = line.strip()
    if not line:
        continue
    try:
        msg = json.loads(line)
    except Exception:
        continue
    msg_type = msg.get('type', '')
    if msg_type == 'assistant':
        message = msg.get('message', {})
        content = message.get('content', [])
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    if item.get('type') == 'text':
                        last_assistant_text = item.get('text', '') + '\n' + last_assistant_text
                    elif item.get('type') == 'tool_use':
                        if item.get('name') == 'Bash':
                            cmd = item.get('input', {}).get('command', '')
                            recent_bash_commands.append(cmd)
        # 直近5ターンまで遡って収集
        if len([l for l in recent if '"type":"assistant"' in l]) > 5:
            break

# 完了主張があるか？
has_claim = any(re.search(p, last_assistant_text) for p in CLAIM_PATTERNS)

# 検証行為があるか？
all_commands = ' '.join(recent_bash_commands)
has_verify = any(re.search(p, all_commands) for p in VERIFY_PATTERNS)

if has_claim and not has_verify:
    # 完了主張あり、検証なし → BLOCK
    reason = ('【ほんとか？プロトコル違反検出】\n'
              '完了/販売可能/動作確認等の主張をしましたが、直近に検証コマンド（grep/find/ls/wc/git log 等）の実行記録がありません。\n\n'
              '以下のいずれかを実行してから再度終了してください：\n'
              '  Q1: ls/find/wc -l で実体ファイルの存在を確認\n'
              '  Q2: grep -rn で『TODO』『（〜は同様）』が残っていないか確認\n'
              '  Q3: git log で commit/push が origin と一致しているか確認\n'
              '  Q4: brief.md の DoD 表で ❌ の行が報告内容と矛盾していないか確認\n\n'
              '証拠（コマンド実行結果）を添えて再度報告してください。')
    print(json.dumps({
        "decision": "block",
        "reason": reason
    }, ensure_ascii=False))
elif has_claim and has_verify:
    # 完了主張あり、検証もあり → OK だが軽くリマインド
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "Stop",
            "additionalContext": "【検証OK】完了主張＋検証コマンド実行を確認。誇張なし宣言を完了報告に含めることを忘れないでください。"
        }
    }, ensure_ascii=False))
else:
    # 完了主張なし → 沈黙（ノイズを減らす）
    print('{}')

PYEOF
