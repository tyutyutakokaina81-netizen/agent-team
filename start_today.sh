#!/bin/bash
# start_today.sh — 今日まわす作業を1本で。Macで `bash start_today.sh` だけ。
#   ① git lock掃除＆同期 → ② 今日の記事を公開 → ③ 営業発注と素材の場所を表示 → ④ 黒字メーター
# code(私)は外部不可。①②は自動、③の営業送付＝あなた/cowork、が役割分担。
set -uo pipefail
cd "$(cd "$(dirname "$0")" && pwd)" || exit 1

echo "==================== ① git 掃除＆同期 ===================="
find .git -name '*.lock' -delete 2>/dev/null || true
git pull origin main || { echo "✗ 同期失敗。lockが残っていないか確認。"; }

echo ""
echo "==================== ② 今日の記事を公開（ブラウザが開く）===================="
echo "  ※ note にログイン済み前提。公開したくなければ Ctrl+C で中断。"
if [ -d "$HOME/.note_publisher_profile" ]; then
  python3 CDO/outputs/note_publisher/publish_to_note.py --text-only || echo "  ⚠️ 公開でエラー/中断（後述の素材は使えます）"
else
  echo "  初回のみログインが要ります → 一度だけ:  python3 CDO/outputs/note_publisher/publish_to_note.py --login"
fi

echo ""
echo "==================== ③ 売る（営業）— ここはあなた/coworkの手 ===================="
echo "--- cowork宛の未処理発注 ---"
python3 ops/process_inbox.py list --to cowork 2>/dev/null || echo "  (process_inbox 実行不可)"
echo ""
echo "--- 営業ですぐ使う素材（コピペして送る）---"
echo "  提案書    : projects/2026-06-23_B2B英語発信代行_営業エンジン/提案書/提案書_レートカード.md"
echo "  営業文    : projects/2026-06-23_B2B英語発信代行_営業エンジン/営業文/コールド営業文_業種別.md"
echo "  お試し見本: projects/2026-06-23_B2B英語発信代行_営業エンジン/お試しサンプル/"
echo "  高単価設計: projects/2026-06-23_300K設計/A_高単価B2Bパッケージ.md"
echo "  起動指示  : ops/cowork_kickoff_2026-06-23_sell.md"

echo ""
echo "==================== ④ 黒字メーター（受注が入ったら）===================="
python3 tools/jobs.py list 2>/dev/null || echo "  (案件なし)"

echo ""
echo "==================== 完了 ===================="
echo "次の一手：上の『営業文』をコピーして、見込み事業者に数件送る＝¥300Kの唯一の道。"
