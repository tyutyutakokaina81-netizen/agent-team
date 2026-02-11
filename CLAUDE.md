# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

This is a multi-agent team prompt toolkit for accelerating day-to-day document creation in Japanese business contexts. It defines a 4-role agent team (企画/本文/要約/チェック) that collaborates to produce polished internal documents.

## Structure

- `team_prompt.txt` — The core multi-agent system prompt (Japanese). Defines team roles and shared rules.
- `team_copy.sh` — Copies `team_prompt.txt` to the macOS clipboard via `pbcopy`.
- `team_show.sh` — Prints `team_prompt.txt` to stdout.

## Usage

```bash
# Copy the prompt to clipboard for pasting into an AI chat
./team_copy.sh

# View the prompt in terminal
./team_show.sh
```

## Notes

- All shell scripts use `zsh` and `set -e`.
- The prompt and all document output are in Japanese.
