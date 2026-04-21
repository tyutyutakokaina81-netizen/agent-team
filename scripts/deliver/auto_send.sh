#!/bin/bash
# 納品メール自動送信（macOS Mail.app 経由）
# ユーザーの設定済みメールアカウントから送信
#
# 使い方:
#   ./scripts/deliver/auto_send.sh <folder_name> <to_email>
#   例: ./scripts/deliver/auto_send.sh "2026-04-21_xxx" client@example.com

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_DIR"

if [[ $# -lt 2 ]]; then
    echo "使い方: $0 <folder_name> <to_email>"
    echo "例: $0 '2026-04-21_xxx_xxx' client@example.com"
    exit 1
fi

FOLDER="$1"
TO_EMAIL="$2"
FOLDER_PATH="$REPO_DIR/deliveries/$FOLDER"
EMAIL_FILE="$FOLDER_PATH/delivery_email.txt"

# 検証
if [[ ! -f "$EMAIL_FILE" ]]; then
    echo "❌ 納品メールが見つかりません: $EMAIL_FILE"
    echo "   先に package.py を実行してください"
    exit 1
fi

# メールアドレスの形式チェック
if ! [[ "$TO_EMAIL" =~ ^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$ ]]; then
    echo "❌ 無効なメールアドレス: $TO_EMAIL"
    exit 1
fi

# 件名・本文を分離
SUBJECT=$(head -1 "$EMAIL_FILE" | sed 's/^件名：//; s/^Subject: //')
BODY=$(tail -n +2 "$EMAIL_FILE")

# 添付ファイル（final/ 内の納品ファイル）
ATTACHMENTS=()
FINAL_DIR="$FOLDER_PATH/final"
if [[ -d "$FINAL_DIR" ]]; then
    for f in "$FINAL_DIR"/*; do
        [[ -f "$f" ]] && ATTACHMENTS+=("$f")
    done
fi

echo "========================================"
echo "📧 納品メール送信"
echo "========================================"
echo "宛先: $TO_EMAIL"
echo "件名: $SUBJECT"
echo "本文: ${#BODY}文字"
echo "添付: ${#ATTACHMENTS[@]}件"
for a in "${ATTACHMENTS[@]}"; do
    echo "  - $(basename "$a")"
done
echo "========================================"
echo ""

# 最終確認
read -p "送信しますか？ (y/N): " CONFIRM
if [[ "$CONFIRM" != "y" ]] && [[ "$CONFIRM" != "Y" ]]; then
    echo "送信をキャンセルしました"
    exit 0
fi

# osascript で Mail.app 経由送信
if ! command -v osascript &>/dev/null; then
    echo "❌ osascript が使えません（Mac以外）"
    exit 1
fi

# 添付ファイル用のAppleScript生成
ATTACH_SCRIPT=""
for a in "${ATTACHMENTS[@]}"; do
    ATTACH_SCRIPT="$ATTACH_SCRIPT
        make new attachment with properties {file name:\"$a\"} at after the last paragraph"
done

osascript <<OSA_EOF
tell application "Mail"
    set newMessage to make new outgoing message with properties {subject:"$SUBJECT", content:"$BODY" & return}
    tell newMessage
        make new to recipient at end of to recipients with properties {address:"$TO_EMAIL"}
        $ATTACH_SCRIPT
    end tell
    send newMessage
end tell
OSA_EOF

if [[ $? -eq 0 ]]; then
    echo ""
    echo "✅ 送信完了: $TO_EMAIL"
    echo ""

    # ステータス更新
    META="$FOLDER_PATH/meta.json"
    if [[ -f "$META" ]]; then
        python3 -c "
import json
with open('$META') as f: m = json.load(f)
m['email_sent'] = '$(date -Iseconds)'
m['status'] = 'delivered_sent'
with open('$META', 'w') as f: json.dump(m, f, ensure_ascii=False, indent=2)
print('✅ meta.json 更新: status=delivered_sent')
"
    fi
else
    echo "❌ 送信失敗"
    exit 1
fi
