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
) | claude
