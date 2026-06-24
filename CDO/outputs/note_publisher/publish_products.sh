#!/bin/bash
# 有料デジタル商品を note に「下書き自動投稿」する1コマンドランナー（オーナーのMacで実行）
# 収益化セーフティ：有料ライン/価格が自動セットできない時は公開せず下書きで止まる（タダ公開防止）。
#
# 使い方:
#   初回だけ:  ./publish_products.sh --login     # ブラウザが開く→noteにログイン（1回だけ）
#   以後:      ./publish_products.sh             # 2商品を下書き自動作成（公開ボタンは押さない）
#
# 公開は note 画面で「有料ライン位置＋価格」を確認して手動で。理由＝有料設定はnote側UIの最終確認が要るため。
set -e
cd "$(dirname "$0")"

REPO_ROOT="$(cd ../../.. && pwd)"
PROJ="$REPO_ROOT/projects/2026-06-23_収益化_AIひとり会社商品"

if [ "$1" = "--login" ]; then
  python3 publish_paid_note.py --login
  exit 0
fi

echo "===== ① AI業務自動化プロンプト集 Vol.1（¥980・下書き） ====="
python3 publish_paid_note.py --article "$PROJ/prompt_pack/note_ready.md" \
  --tags "AI,業務効率化,プロンプト,フリーランス,個人事業主" || echo "→ ①はスキップ/失敗（画面を確認）"

echo ""
echo "===== ② ひとり会社 実務テンプレ集（¥980・下書き） ====="
python3 publish_paid_note.py --article "$PROJ/template_kit/note_ready.md" \
  --tags "フリーランス,個人事業主,テンプレート,業務効率化,確定申告の準備" || echo "→ ②はスキップ/失敗（画面を確認）"

echo ""
echo "✅ 完了：noteの「下書き」に2商品が入りました。"
echo "   各記事を開いて、有料ライン（ここから有料）の位置と価格¥980を確認し、手動で公開してください。"
echo "   公開後、note記事URLを store.html の BUY{} に貼れば購入ボタンが有効化されます。"
