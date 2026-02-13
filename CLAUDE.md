# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

Multi-agent team prompt toolkit for accelerating document creation in Japanese business contexts. Two prompt variants define agent teams that collaborate to produce polished internal documents.

## Prompt Variants

- `team_prompt.txt` — 4-role team (企画/本文/要約/チェック). Original prompt for general document creation.
- `claude_team_v0.txt` — 3-role team (オーケストレーター/リサーチャ/ライター). Lighter variant optimized for Claude 4.6; adds diagram suggestion support.

## Clipboard Scripts

```bash
./team_copy.sh          # Copy team_prompt.txt to clipboard
./team_show.sh          # Print team_prompt.txt to stdout
./claude_copy.sh        # Copy claude_team_v0.txt to clipboard
```

## Markdown-to-PPTX Pipeline

`bin/md2ppt.py` converts structured Markdown into PowerPoint slides. Requires `python-pptx`.

```bash
python bin/md2ppt.py md/sample.md ppt/output.pptx
```

Markdown conventions for slide generation:
- `# Heading` → title slide
- `## Heading` → new content slide with that title
- `### Heading` → bold paragraph (level 0) within current slide
- `- bullet` / `  - nested` → bullet points with indentation levels
- `[図解案] text` → collected into a dedicated "図解案" slide

## Notes

- All shell scripts use `zsh` with `set -e`.
- All prompts and document output are in Japanese.
- Shell scripts reference `$HOME/agent-team/` as the repo path.
