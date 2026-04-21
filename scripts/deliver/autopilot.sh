#!/bin/bash
# 完全自動パイロット：受注〜納品までワンコマンド実行
#
# 使い方:
#   ./scripts/deliver/autopilot.sh <folder_name>
#
# 実行ステップ：
# 1. プロンプト生成（未生成なら）
# 2. Claude API で実作業（既存尊重）
# 3. 品質チェック
# 4. 納品パッケージ生成
# 5. 要アクション案内（送信は人間が最終確認）

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_DIR"

if [[ $# -lt 1 ]]; then
    # 進行中案件から自動検出
    ACTIVE=()
    for D in "$REPO_DIR/deliveries"/2026-*; do
        [[ -d "$D" ]] || continue
        [[ -f "$D/meta.json" ]] || continue
        STATUS=$(python3 -c "import json; print(json.load(open('$D/meta.json')).get('status', 'in_progress'))")
        if [[ "$STATUS" != "delivered_sent" ]] && [[ "$STATUS" != "delivered" ]]; then
            ACTIVE+=("$(basename "$D")")
        fi
    done

    if [[ ${#ACTIVE[@]} -eq 0 ]]; then
        echo "📭 進行中案件がありません"
        echo "   python3 scripts/deliver/new_job.py で新規登録"
        exit 0
    fi
    if [[ ${#ACTIVE[@]} -eq 1 ]]; then
        FOLDER="${ACTIVE[0]}"
        echo "📂 進行中案件を自動選択: $FOLDER"
    else
        echo "進行中案件が複数あります："
        for i in "${!ACTIVE[@]}"; do
            echo "  [$((i+1))] ${ACTIVE[$i]}"
        done
        read -p "番号: " CHOICE
        FOLDER="${ACTIVE[$((CHOICE-1))]}"
    fi
else
    FOLDER="$1"
fi

FOLDER_PATH="$REPO_DIR/deliveries/$FOLDER"
[[ -d "$FOLDER_PATH" ]] || { echo "❌ フォルダ無し: $FOLDER"; exit 1; }

echo ""
echo "============================================================"
echo "🚁 AUTOPILOT: 完全自動納品パイプライン"
echo "============================================================"
echo "案件: $FOLDER"
echo ""

# STEP 1: プロンプト生成
echo "▶ STEP 1/4: プロンプト生成"
if [[ -d "$FOLDER_PATH/prompts" ]] && [[ -n "$(ls -A "$FOLDER_PATH/prompts" 2>/dev/null)" ]]; then
    echo "  ℹ️  既存プロンプト検出、スキップ"
else
    python3 "$SCRIPT_DIR/generate.py" "$FOLDER"
fi
echo ""

# STEP 2: Claude API で実作業
echo "▶ STEP 2/4: Claude API で実作業"
if python3 "$SCRIPT_DIR/auto_write.py" "$FOLDER"; then
    echo "  ✅ 実作業完了"
else
    echo "  ⚠️  API作業スキップ（API Key未設定の可能性）"
    echo "  手動で drafts/ に原稿を配置してから再実行してください"
    exit 1
fi
echo ""

# STEP 3: 品質チェック
echo "▶ STEP 3/4: 品質チェック"
QC_OUTPUT=$(python3 "$SCRIPT_DIR/quality_check.py" "$FOLDER")
echo "$QC_OUTPUT" | tail -30

if echo "$QC_OUTPUT" | grep -q "致命的"; then
    echo ""
    echo "❌ 品質チェックで致命的な問題を検出。パイプライン停止。"
    echo "   drafts/article.md を手動で修正してから再実行"
    exit 1
fi
echo ""

# STEP 4: 納品パッケージ生成
echo "▶ STEP 4/4: 納品パッケージ生成"
python3 "$SCRIPT_DIR/package.py" "$FOLDER" 2>&1 | tail -15
echo ""

echo "============================================================"
echo "🎉 AUTOPILOT 完了"
echo "============================================================"
echo ""
echo "📂 成果物: $FOLDER_PATH/"
echo ""
echo "🎯 最終ステップ（人間の最終確認）："
echo ""
echo "  1. 納品物を確認:"
echo "     open $FOLDER_PATH/final/"
echo ""
echo "  2. 納品メールを送信（クライアントメールアドレス必須）:"
echo "     ./scripts/deliver/auto_send.sh '$FOLDER' client@example.com"
echo ""
echo "  3. 入金確認後、ステータス更新:"
echo "     python3 scripts/application_tracker.py"
