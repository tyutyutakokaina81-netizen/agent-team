#!/bin/bash
# ワンコマンドで「次のステップ」を自動実行する究極の自動化
# 使い方: ./scripts/deliver/auto_next.sh [folder_name]

set -e

REPO_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_DIR"
SCRIPT_DIR="$REPO_DIR/scripts/deliver"

# フォルダ選択
if [[ $# -ge 1 ]]; then
    FOLDER="$1"
else
    # 進行中案件を自動検出
    ACTIVE_JOBS=()
    for D in "$REPO_DIR/deliveries"/2026-*; do
        [[ -d "$D" ]] || continue
        [[ -f "$D/meta.json" ]] || continue
        # delivered 以外を抽出
        STATUS=$(python3 -c "import json; print(json.load(open('$D/meta.json')).get('status', 'in_progress'))")
        if [[ "$STATUS" != "delivered" ]]; then
            ACTIVE_JOBS+=("$(basename "$D")")
        fi
    done

    if [[ ${#ACTIVE_JOBS[@]} -eq 0 ]]; then
        echo "📭 進行中案件がありません"
        echo "   新規受注を登録するには："
        echo "     python3 scripts/deliver/new_job.py"
        exit 0
    fi

    if [[ ${#ACTIVE_JOBS[@]} -eq 1 ]]; then
        FOLDER="${ACTIVE_JOBS[0]}"
        echo "📂 進行中案件: $FOLDER"
    else
        echo "進行中案件が複数あります。選択してください："
        for i in "${!ACTIVE_JOBS[@]}"; do
            echo "  [$((i+1))] ${ACTIVE_JOBS[$i]}"
        done
        read -p "番号: " CHOICE
        FOLDER="${ACTIVE_JOBS[$((CHOICE-1))]}"
    fi
fi

FOLDER_PATH="$REPO_DIR/deliveries/$FOLDER"

if [[ ! -d "$FOLDER_PATH" ]]; then
    echo "❌ フォルダが見つかりません: $FOLDER"
    exit 1
fi

# 現在のステージを検出
STAGE="setup"
[[ -d "$FOLDER_PATH/prompts" ]] && [[ -n "$(ls -A "$FOLDER_PATH/prompts" 2>/dev/null)" ]] && STAGE="prompted"
[[ -d "$FOLDER_PATH/drafts" ]] && [[ -n "$(ls -A "$FOLDER_PATH/drafts" 2>/dev/null)" ]] && STAGE="drafted"
[[ -d "$FOLDER_PATH/final" ]] && [[ -n "$(ls -A "$FOLDER_PATH/final" 2>/dev/null)" ]] && STAGE="packaged"

echo ""
echo "========================================"
echo "🚀 自動次ステップ実行"
echo "   案件: $FOLDER"
echo "   現状: $STAGE"
echo "========================================"
echo ""

case "$STAGE" in
    setup)
        echo "→ プロンプト生成を実行します"
        python3 "$SCRIPT_DIR/generate.py" "$FOLDER"
        echo ""
        echo "========================================"
        echo "次回: このコマンドを再実行するとプロンプトをクリップボードにコピーします"
        echo "========================================"
        ;;
    prompted)
        # drafts/ の状態で次のプロンプトを判定
        if [[ ! -f "$FOLDER_PATH/drafts/1_structure.md" ]]; then
            PROMPT="1_structure.md"
            echo "→ 構成プロンプトをクリップボードにコピーします"
        elif [[ -f "$FOLDER_PATH/prompts/2_body.md" ]] && [[ ! -f "$FOLDER_PATH/drafts/article.md" ]]; then
            PROMPT="2_body.md"
            echo "→ 本文プロンプトをクリップボードにコピーします"
        else
            echo "→ 品質チェックを実行します"
            python3 "$SCRIPT_DIR/quality_check.py" "$FOLDER"
            exit 0
        fi
        bash "$SCRIPT_DIR/prompt_to_clip.sh" "$FOLDER" "$PROMPT"
        ;;
    drafted)
        echo "→ 品質チェックを実行します"
        python3 "$SCRIPT_DIR/quality_check.py" "$FOLDER"
        echo ""
        echo "========================================"
        echo "品質OKなら次にこれを実行："
        echo "  python3 scripts/deliver/package.py '$FOLDER'"
        echo "========================================"
        ;;
    packaged)
        echo "→ 既に納品パッケージ完成"
        echo ""
        echo "送信メール: $FOLDER_PATH/delivery_email.txt"
        echo "納品ファイル: $FOLDER_PATH/final/"
        ;;
esac
