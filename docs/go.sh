#!/bin/bash
# ============================================================
# go.sh — 一発でセットアップ＆公開（owner「まとめてコード書いて」2026-07-11）
# 使い方（Macのターミナルに1行）:
#   git clone https://github.com/tyutyutakokaina81-netizen/agent-team.git ~/agent-team-run 2>/dev/null; cd ~/agent-team-run && git pull origin main -q && bash docs/go.sh
# これ1つで: ①note未ログインなら一度だけログイン ②自動運転を常駐 ③今すぐ実行(記事公開)
# ============================================================
set -u
# スクリプトの場所からリポジトリrootへ移動（どこから呼んでも動く）
cd "$(cd "$(dirname "$0")/.." && pwd)" || { echo "✗ リポジトリに移動できません"; exit 1; }
echo "=================================================="
echo " go.sh 開始 — セットアップ＆公開を一括実行"
echo " 作業フォルダ: $(pwd)"
echo "=================================================="

# 最新化
git pull origin main -q 2>/dev/null || echo "⚠️ git pull 失敗（オフライン?）。手元のmainで続行。"

# ---- ① note ログイン確認（未ログインなら一度だけ・ブラウザが開く）----
PROFILE="$HOME/.note_publisher_profile"
if [ ! -d "$PROFILE" ] || [ -z "$(ls -A "$PROFILE" 2>/dev/null)" ]; then
  echo ""
  echo "▶ note が未ログインです。ログイン画面（ブラウザ）を開きます。"
  echo "  → いつもの note アカウントでログインしてください（1回きり・以後は自動）。"
  python3 CDO/outputs/note_publisher/publish_to_note.py --login \
    || echo "⚠️ ログイン処理でエラー。メッセージを確認してください（Playwright未導入なら下の指示に従う）。"
else
  echo "✅ note ログイン済み（プロファイル有り）。"
fi

# ---- ② 自動運転を常駐（再起動しても動く）----
echo ""
echo "▶ 自動運転(オートパイロット)を常駐させます..."
bash docs/install_autopilot.sh || echo "⚠️ オートパイロット設置でエラー。上のメッセージを確認。"

# ---- ③ 今すぐ実行（記事公開・積んだ便を消化）----
echo ""
echo "▶ ワーカーを今すぐ実行します（記事公開・積んだ全タスク）..."
bash docs/run_all.sh

echo ""
echo "=================================================="
echo " go.sh 完了。上に出た結果（✅ / ⚠️ / 公開URL）を確認してください。"
echo " 以後は Mac を起動しておくだけで自動運転します。"
echo "=================================================="
