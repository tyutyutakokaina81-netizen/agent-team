#!/bin/zsh
set -e

(
  echo "### SYSTEM"
  cat system/sisters.md

  echo "### AGENTS"
  cat agents/CDO.md
  cat agents/CFO.md
  cat agents/CMO.md
  cat agents/CPO.md
  cat agents/CSO.md

  echo "### TASK"
  cat task/task.md

  echo ""
  echo "### INSTRUCTION"
  echo "上記を踏まえて、今すぐ最終回答を出力せよ。構築や説明は不要。思考結果のみ出せ。"
) | claude
