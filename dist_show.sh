#!/usr/bin/env bash
# dist 一覧表示ラッパー（macOS のターミナル auto-link 回避用）
# 使い方:
#   cd ~/agent-team && bash dist_show.sh
set -e
cd "$(dirname "$0")"
python3 projects/2026-04-08_月30万自動化/今すぐ収益化/list_publish_targets.py
