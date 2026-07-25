#!/bin/bash
# ダブルクリックで実行できるログイン用ランチャー（macOS）。
# ~/.note_publisher_profile（ワーカーと同じブラウザ）で Reddit/Quora にログインするためのウィンドウを開く。
cd "$HOME/agent-team-run" 2>/dev/null || cd "$(dirname "$0")"
git pull origin main -q 2>/dev/null
echo "ブラウザを開きます。Reddit と Quora のタブで「Continue with Google（てつ）」でログインしてください。"
python3 CDO/outputs/note_publisher/open_for_login.py
echo ""
echo "終わりました。このウィンドウは閉じてOKです。"
