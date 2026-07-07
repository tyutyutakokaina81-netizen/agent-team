#!/bin/bash
# ============================================================
# run_all.sh — これ1回で全部・抜け漏れなく走らせる統合ランチャー
# ============================================================
# owner が Mac のターミナルに1行貼るだけ:
#   cd ~/agent-team-run && git pull origin main -q && bash docs/run_all.sh
# （リポジトリが無くても自動 clone する。以後は配車係が毎朝自動化）
#
# この1本がやること（順に・抜け漏れ防止）:
#   0) リポジトリ準備（無ければ clone / あれば最新 main へ）
#   1) 事前点検：claude CLI / note ログイン / Playwright を確認し ✅⚠️ で明示
#   2) 配車係(dispatcher)を常駐登録（以後は毎朝7:17自動・貼り付け不要に）
#   3) ワーカー便を実行（run_worker.sh 経由・実行中3分ごとライブlog送信・二重起動ロック）
#      └ 中身: ゲート確認→有料本¥980公開→無料5本公開→有料¥300/Vol.1突破
#             →コメント自動返信→モデルA開栓(Booking)→報告&ログ送信
#   4) 終了サマリ
# 制約: ¥0 / A1(codeはブラウザ不可なのでここ=owner環境で実行) / URL報告なき公開禁止
set -u
REPO="${AGENT_TEAM_DIR:-$HOME/agent-team-run}"
REMOTE="https://github.com/tyutyutakokaina81-netizen/agent-team.git"

echo "=================================================="
echo " run_all.sh 開始 — 全工程を一括実行します"
echo "=================================================="

# ---- 0) リポジトリ準備 ----
if [ ! -d "$REPO/.git" ]; then
  echo "▶ リポジトリが無いので clone します: $REPO"
  git clone -q "$REMOTE" "$REPO" || { echo "✗ clone失敗。ネット/認証を確認してください"; exit 1; }
fi
cd "$REPO" || { echo "✗ $REPO に入れません"; exit 1; }
git pull origin main -q 2>/dev/null || echo "⚠️ git pull に失敗（オフライン?）。手元のmainで続行します"
echo "✅ 0) リポジトリ最新化: $REPO ($(git rev-parse --short HEAD))"

# ---- 1) 事前点検（抜け漏れ検知・止めずに明示） ----
echo "---- 1) 事前点検 ----"
WARN=0
CLA=$(command -v claude 2>/dev/null || ls "$HOME/.claude/local/claude" 2>/dev/null | head -1)
if [ -n "$CLA" ]; then echo "  ✅ claude CLI: $CLA"; else echo "  ✗ claude CLI が見つかりません（ワーカー実行不可）"; WARN=2; fi

PROFILE="$HOME/.note_publisher_profile"
if [ -d "$PROFILE" ] && [ -n "$(ls -A "$PROFILE" 2>/dev/null)" ]; then
  echo "  ✅ note ログインプロファイル: 有り"
else
  echo "  ⚠️ note 未ログイン → note公開は失敗します。先に1回だけ:"
  echo "       python3 CDO/outputs/note_publisher/publish_to_note.py --login"
  WARN=1
fi

if python3 -c "import playwright" 2>/dev/null; then
  echo "  ✅ Playwright: 有り"
else
  echo "  ⚠️ Playwright 未導入 → ブラウザ操作不可。導入:"
  echo "       pip3 install playwright && python3 -m playwright install chromium"
  WARN=1
fi

if [ "$WARN" -eq 2 ]; then
  echo "✗ 致命的な不足（claude CLI）。導入後に再実行してください。"
  exit 1
fi
[ "$WARN" -eq 1 ] && echo "  → 警告ありbut続行（該当タスクはワーカーが失敗として報告します）"

# ---- 2) 配車係を常駐登録（冪等） ----
echo "---- 2) 配車係(dispatcher)登録 ----"
if crontab -l 2>/dev/null | grep -q worker_dispatcher.sh; then
  echo "  ✅ 既に登録済み（毎朝7:17自動 + 5分ごと実行要求チェック）"
else
  bash docs/worker_dispatcher.sh --install && echo "  ✅ 登録しました（以後は貼り付け不要で自動運転）" || echo "  ⚠️ 登録に失敗（cron不可環境?）。手動実行は可能"
fi

# ---- 3) ワーカー便を実行（全タスク） ----
echo "---- 3) ワーカー便を実行（本公開→有料突破→無料5本→コメント返信→モデルA開栓）----"
echo "  ※実行中は無言が正常。3分ごとに ops/logs/worker_live.log が code に届きます。"
bash docs/run_worker.sh
RC=$?

# ---- 4) 終了サマリ ----
echo "=================================================="
echo " run_all.sh 終了 (worker rc=$RC)"
echo "  ・ログは自動送信済み → code が遠隔で結果を検収します"
echo "  ・配車係が常駐したので、次回からは何も貼らなくても毎朝自動で走ります"
echo "=================================================="
exit $RC
