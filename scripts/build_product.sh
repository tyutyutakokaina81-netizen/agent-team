#!/bin/bash
# 商品用ZIPを自動生成
# note/BOOTH販売用に、個人情報を完全除外した製品版を作成
#
# 使い方:
#   ./scripts/build_product.sh
#
# 出力:
#   ./dist/freelance-auto-YYYYMMDD.zip

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_DIR"

DATE=$(date '+%Y%m%d')
BUILD_NAME="freelance-auto-${DATE}"
BUILD_DIR="/tmp/${BUILD_NAME}"
DIST_DIR="$REPO_DIR/dist"
ZIP_PATH="$DIST_DIR/${BUILD_NAME}.zip"

echo "========================================"
echo "📦 商品版ZIP生成"
echo "========================================"
echo "出力先: $ZIP_PATH"
echo ""

# クリーン
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR" "$DIST_DIR"

# ===== scripts/ コピー（API依存なしのもののみ）=====
echo "📋 scripts/ コピー中..."
mkdir -p "$BUILD_DIR/scripts/deliver"

# ルート直下
for f in \
    application_tracker.py batch_add.py daily_report.py weekly_report.py \
    monthly_report.py rate_calculator.py email_template.py dashboard.py \
    morning.sh night.sh backup.sh auto_morning.sh open_dashboard.sh \
    install_auto_morning.sh README.md; do
    [[ -f "scripts/$f" ]] && cp "scripts/$f" "$BUILD_DIR/scripts/"
done

# plist templates
cp scripts/*.plist.template "$BUILD_DIR/scripts/" 2>/dev/null || true

# deliver/
for f in \
    README.md RULES.md new_job.py generate.py quality_check.py \
    client_review.py package.py run.py auto_next.sh auto_process.sh \
    auto_send.sh auto_check_orders.sh autopilot.sh check_orders.sh \
    save_draft.sh prompt_to_clip.sh scrutinize_order.py timer.py \
    client_profile.py user_config.py demo_full_pipeline.sh; do
    [[ -f "scripts/deliver/$f" ]] && cp "scripts/deliver/$f" "$BUILD_DIR/scripts/deliver/"
done
cp scripts/deliver/*.plist.template "$BUILD_DIR/scripts/deliver/" 2>/dev/null || true

# ===== docs/ コピー（公開可能なドキュメントのみ）=====
echo "📖 docs/ 作成中..."
mkdir -p "$BUILD_DIR/docs"

# プロジェクトドキュメント（個人情報・具体的案件名を含まないもの）
PROJECT_DIR="projects/2026-04-08_月30万自動化"
[[ -f "$PROJECT_DIR/PLAYBOOK.md" ]] && cp "$PROJECT_DIR/PLAYBOOK.md" "$BUILD_DIR/docs/"
[[ -f "$PROJECT_DIR/CHEAT_SHEET.md" ]] && cp "$PROJECT_DIR/CHEAT_SHEET.md" "$BUILD_DIR/docs/"
[[ -f "$PROJECT_DIR/daily_routine.md" ]] && cp "$PROJECT_DIR/daily_routine.md" "$BUILD_DIR/docs/"
[[ -f "$PROJECT_DIR/skill_roadmap_12months.md" ]] && cp "$PROJECT_DIR/skill_roadmap_12months.md" "$BUILD_DIR/docs/"
[[ -f "$PROJECT_DIR/A_ライティング/workflow.md" ]] && cp "$PROJECT_DIR/A_ライティング/workflow.md" "$BUILD_DIR/docs/workflow_writing.md"
[[ -f "$PROJECT_DIR/B_SNS運用代行/sales_checklist.md" ]] && cp "$PROJECT_DIR/B_SNS運用代行/sales_checklist.md" "$BUILD_DIR/docs/"
[[ -f "$PROJECT_DIR/B_SNS運用代行/prospect_list_strategy.md" ]] && cp "$PROJECT_DIR/B_SNS運用代行/prospect_list_strategy.md" "$BUILD_DIR/docs/"
[[ -f "$PROJECT_DIR/C_テンプレ販売/note_sales_copy_optimized.md" ]] && cp "$PROJECT_DIR/C_テンプレ販売/note_sales_copy_optimized.md" "$BUILD_DIR/docs/"

# ===== samples/ サンプル記事 =====
echo "📝 samples/ 作成中..."
mkdir -p "$BUILD_DIR/samples"
if [[ -f "deliveries/2026-04-21_テスト株式会社_サンプル記事執筆/drafts/article.md" ]]; then
    cp "deliveries/2026-04-21_テスト株式会社_サンプル記事執筆/drafts/article.md" "$BUILD_DIR/samples/sample_article_副業始め方.md"
fi

# ===== templates/ =====
echo "🎨 templates/ 作成中..."
mkdir -p "$BUILD_DIR/templates"

# ===== 空のdeliveries/ =====
mkdir -p "$BUILD_DIR/deliveries/_client_profiles"
touch "$BUILD_DIR/deliveries/.gitkeep"
touch "$BUILD_DIR/deliveries/_client_profiles/.gitkeep"

# ===== setup.sh 生成 =====
cat > "$BUILD_DIR/setup.sh" <<'SETUP_EOF'
#!/bin/bash
# フリーランス自動化システム セットアップ
set -e

echo "========================================"
echo "🚀 フリーランス自動化システム セットアップ"
echo "========================================"

# Python確認
if ! command -v python3 &>/dev/null; then
    echo "❌ Python 3が必要です"
    echo "   brew install python"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✅ Python $PYTHON_VERSION 検出"

# 実行権限付与
chmod +x scripts/*.py scripts/*.sh 2>/dev/null || true
chmod +x scripts/deliver/*.py scripts/deliver/*.sh 2>/dev/null || true

# フォルダ作成
mkdir -p deliveries/_client_profiles logs

# 初回CSV作成
if [[ ! -f scripts/applications.csv ]]; then
    echo "date,site,job_name,price,status,url,note" > scripts/applications.csv
    echo "✅ applications.csv 作成"
fi

echo ""
echo "========================================"
echo "🎉 セットアップ完了"
echo "========================================"
echo ""
echo "【すぐ使える3コマンド】"
echo "  python3 scripts/application_tracker.py   # 応募記録"
echo "  python3 scripts/daily_report.py          # 日次レポート"
echo "  python3 scripts/deliver/run.py            # 受注→納品パイプライン"
echo ""
echo "【自動実行を有効化（毎日20時＋Mac起動時＋1日5回通知）】"
echo "  ./scripts/install_auto_morning.sh"
echo ""
echo "【ドキュメント】"
echo "  docs/PLAYBOOK.md     - 全体マップ"
echo "  docs/CHEAT_SHEET.md  - 1ページ俯瞰"
echo "  docs/daily_routine.md - 朝〜夜の行動指針"
echo "  scripts/deliver/RULES.md - パイプライン運用ルール"
echo ""
echo "【初回おすすめ】"
echo "  python3 scripts/deliver/demo_full_pipeline.sh"
echo "  → デモ案件で動作確認"
SETUP_EOF
chmod +x "$BUILD_DIR/setup.sh"

# ===== 商品用README生成 =====
cat > "$BUILD_DIR/README.md" <<'README_EOF'
# フリーランス自動化システム

Macのターミナルで動く、受注〜納品の完全自動化ツール集。

## 🚀 クイックスタート

```bash
chmod +x setup.sh
./setup.sh
```

## 📁 ディレクトリ構成

```
.
├── setup.sh                          # ワンコマンドセットアップ
├── scripts/                          # 自動化スクリプト
│   ├── application_tracker.py        # 応募記録
│   ├── daily_report.py               # 日次レポート
│   ├── weekly_report.py              # 週次レポート
│   ├── monthly_report.py             # 月次レポート
│   ├── dashboard.py                  # HTMLダッシュボード
│   ├── rate_calculator.py            # 時給計算
│   ├── email_template.py             # メール生成
│   ├── morning.sh / night.sh         # ルーティン
│   ├── backup.sh                     # Git自動バックアップ
│   ├── auto_morning.sh               # 自動デイリー実行
│   ├── install_auto_morning.sh       # launchd登録
│   └── deliver/                      # 受注→納品パイプライン
│       ├── new_job.py                # 受注セットアップ
│       ├── generate.py               # プロンプト生成
│       ├── quality_check.py          # 品質チェック
│       ├── client_review.py          # クライアント視点レビュー
│       ├── package.py                # 納品パッケージ
│       ├── run.py                    # 統合ワークフロー
│       ├── scrutinize_order.py       # 受注精査
│       ├── autopilot.sh              # 全工程自動実行
│       └── ...（19スクリプト）
├── docs/                             # ドキュメント30+本
│   ├── PLAYBOOK.md                   # 全体マップ
│   ├── CHEAT_SHEET.md                # 1ページ俯瞰
│   ├── daily_routine.md              # 朝〜夜の行動指針
│   ├── skill_roadmap_12months.md     # 12ヶ月ロードマップ
│   ├── workflow_writing.md           # ライティング受注フロー
│   ├── sales_checklist.md            # 営業チェックリスト
│   ├── prospect_list_strategy.md     # 営業リスト戦略
│   └── note_sales_copy_optimized.md  # noteの売れる文章
├── samples/                          # サンプル記事
└── templates/                        # テンプレート
```

## 📚 最初に読むべきドキュメント

1. `docs/PLAYBOOK.md` - 全体マップと行動指針
2. `docs/CHEAT_SHEET.md` - 困ったときの1ページ
3. `scripts/deliver/RULES.md` - パイプライン運用ルール

## 🎯 基本の流れ

```
1. 受注メッセージが来た
   ↓
2. python3 scripts/deliver/scrutinize_order.py
   → 詐欺チェック＋判定＋返信テンプレ自動生成
   ↓
3. python3 scripts/deliver/new_job.py
   → 受注情報を登録
   ↓
4. python3 scripts/deliver/generate.py "<folder>"
   → Claude用プロンプトを自動生成
   ↓
5. Claude/ChatGPTに貼り付けて原稿作成
   ↓
6. ./scripts/deliver/save_draft.sh "<folder>" article.md
   → クリップボードから保存
   ↓
7. python3 scripts/deliver/quality_check.py "<folder>"
   → 自動品質チェック（11項目）
   ↓
8. python3 scripts/deliver/client_review.py "<folder>"
   → クライアント視点で評価
   ↓
9. python3 scripts/deliver/package.py "<folder>"
   → 納品ファイル＋メール＋請求メモを自動生成
   ↓
10. ./scripts/deliver/auto_send.sh "<folder>" client@example.com
    → Mail.appから送信
```

## 💰 月額課金：0円

- Python標準ライブラリのみ使用（pip不要）
- AI生成はClaude/ChatGPTのWeb版に手動コピペ（無料）
- API Key不要
- Mac標準機能のみ使用（launchd、Mail.app）

## ⚠️ 注意事項

- Mac専用（macOS 12以降推奨）
- Python 3.10以上が必要
- ターミナル操作の基本知識が必要

## 📧 サポート

購入いただいたnoteのコメント欄からお問い合わせください。
セットアップで詰まった場合、個別サポート対応します。

## 📝 ライセンス

個人利用に限ります。再配布・転売は禁止。
README_EOF

# ===== .gitignore =====
cat > "$BUILD_DIR/.gitignore" <<'GITIGNORE_EOF'
# 個人データ
scripts/applications.csv
scripts/dashboard.html
deliveries/*
!deliveries/.gitkeep
!deliveries/_client_profiles/.gitkeep
logs/
*.migration_backup
user_config.json
.env

# macOS
.DS_Store

# Python
__pycache__/
*.pyc
GITIGNORE_EOF

# ===== ZIP生成 =====
echo ""
echo "📦 ZIP圧縮中..."
cd /tmp
rm -f "$ZIP_PATH"
zip -r -q "$ZIP_PATH" "$BUILD_NAME" -x "*.DS_Store" "*/__pycache__/*" "*.pyc"

SIZE=$(du -h "$ZIP_PATH" | cut -f1)
FILE_COUNT=$(unzip -l "$ZIP_PATH" | tail -1 | awk '{print $2}')

echo ""
echo "========================================"
echo "🎉 ビルド完了"
echo "========================================"
echo ""
echo "📦 ZIP: $ZIP_PATH"
echo "   サイズ: $SIZE"
echo "   ファイル数: $FILE_COUNT"
echo ""
echo "【次のステップ】"
echo "1. ZIPを開いて内容確認:"
echo "   unzip -l $ZIP_PATH | head"
echo ""
echo "2. noteにアップロード:"
echo "   https://note.com → 有料記事作成 → ZIPを添付"
echo ""
echo "3. 販売ページ文:"
echo "   cat CPO/outputs/2026-04-21_自動化システム商品化_販売ページ.md"
echo ""

# クリーンアップ
rm -rf "$BUILD_DIR"
