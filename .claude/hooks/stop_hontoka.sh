#!/usr/bin/env bash
# Stop hook (改良版): 直前のユーザーメッセージ以降の全アシスタントターンを対象に
# 完了主張と検証行為の有無を判定する。ターン跨ぎの誤発火を防ぐ。

set -e
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)"

INPUT=$(cat)
TRANSCRIPT_PATH=$(echo "$INPUT" | jq -r '.transcript_path // ""')

if [ -z "$TRANSCRIPT_PATH" ] || [ ! -f "$TRANSCRIPT_PATH" ]; then
  jq -n '{
    hookSpecificOutput: {
      hookEventName: "Stop",
      additionalContext: "【リマインダ】完了主張前に「ほんとか？」プロトコルQ1〜Q3を実行（CLAUDE.md参照）。"
    }
  }'
  exit 0
fi

python3 - "$TRANSCRIPT_PATH" <<'PYEOF'
import json
import re
import sys

transcript_path = sys.argv[1]

CLAIM_PATTERNS = [
    r'販売可能', r'販売準備完了', r'完成しました', r'完成です',
    r'完了しました', r'完了です', r'実装完了', r'動きます',
    r'動きました', r'動作確認.*済', r'達成しました', r'できました',
    r'押すべきは', r'実証された', r'修正度.*%',
]

VERIFY_PATTERNS = [
    r'\bgrep\b', r'\bfind\b', r'\bls\b', r'\bwc\b', r'\bcat\b',
    r'\bgit\s+log\b', r'\bgit\s+status\b', r'\bgit\s+diff\b',
    r'\bgit\s+show\b', r'\bjq\b', r'python3?\s+-c', r'node\s+-e',
    r'curl ', r'\bawk\b', r'\bsed\b',
]

try:
    with open(transcript_path, 'r', encoding='utf-8') as f:
        all_lines = f.readlines()
except Exception:
    print(json.dumps({}))
    sys.exit(0)

# 最後の "user" メッセージの行番号を見つける（そこから先が「現在のターン」）
last_user_idx = -1
for i in range(len(all_lines) - 1, -1, -1):
    line = all_lines[i].strip()
    if not line:
        continue
    try:
        msg = json.loads(line)
    except Exception:
        continue
    # type=="user" だが system-reminder のみ含む行は除外
    if msg.get('type') == 'user':
        # message.content が tool_result のみなら user 入力ではないため次へ
        content = msg.get('message', {}).get('content', [])
        is_real_user = False
        if isinstance(content, str):
            is_real_user = True
        elif isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    if item.get('type') == 'text' and item.get('text'):
                        # system-reminder のみのメッセージは除外
                        if 'tool_use_id' not in item:
                            is_real_user = True
                            break
                elif isinstance(item, str):
                    is_real_user = True
                    break
        if is_real_user:
            last_user_idx = i
            break

# 現在のターン範囲（last_user_idx より後の全エントリ）
current_turn = all_lines[last_user_idx + 1:] if last_user_idx >= 0 else all_lines[-100:]

assistant_text = ''
bash_commands = []

for line in current_turn:
    line = line.strip()
    if not line:
        continue
    try:
        msg = json.loads(line)
    except Exception:
        continue
    if msg.get('type') != 'assistant':
        continue
    message = msg.get('message', {})
    content = message.get('content', [])
    if isinstance(content, list):
        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get('type') == 'text':
                assistant_text += item.get('text', '') + '\n'
            elif item.get('type') == 'tool_use':
                if item.get('name') == 'Bash':
                    cmd = item.get('input', {}).get('command', '')
                    bash_commands.append(cmd)

has_claim = any(re.search(p, assistant_text) for p in CLAIM_PATTERNS)
all_cmds = ' '.join(bash_commands)
has_verify = any(re.search(p, all_cmds) for p in VERIFY_PATTERNS)

if has_claim and not has_verify:
    reason = ('【ほんとか？プロトコル違反検出】\n'
              '完了/動作/達成等の主張をしましたが、このターン内に検証コマンド'
              '（grep/find/ls/wc/git log/cat 等）の実行記録がありません。\n\n'
              '以下のいずれかを実行して証拠を添えてください：\n'
              '  Q1: ls/find/wc -l で実体ファイルの存在を確認\n'
              '  Q2: grep -rn で『TODO』『（〜は同様）』が残っていないか確認\n'
              '  Q3: git log で commit/push が origin と一致しているか確認\n'
              '  Q4: brief.md の DoD 表で ❌ の行が報告内容と矛盾していないか確認')
    print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))
elif has_claim and has_verify:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "Stop",
            "additionalContext": "【検証OK】完了主張＋検証コマンド実行を確認。誇張なし宣言を完了報告に含めることを忘れないでください。"
        }
    }, ensure_ascii=False))
else:
    print('{}')
PYEOF
