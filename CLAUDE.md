# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

Multi-agent team prompt toolkit for accelerating document creation in Japanese business contexts, combined with a zero-dependency JSON API server (`agent-gateway`).

## Repository Structure

Tracked files (checked into git):

```
agent-team/
├── CLAUDE.md                    # This file
├── README.md                    # Project overview (Japanese)
├── gateway/
│   └── server.mjs               # Zero-dependency Node.js JSON API server
├── prompts/
│   └── team_prompt.txt          # 4-role agent team prompt (Japanese)
└── scripts/
    ├── team_copy.sh             # Copy team_prompt.txt to clipboard (macOS)
    └── team_show.sh             # Print team_prompt.txt to stdout
```

Local-only files (in `.gitignore`, not tracked):

```
.claude/                         # Claude Code session state
bin/                             # md2ppt.py Markdown→PPTX converter (requires python-pptx)
md/                              # Markdown source files for slide generation
ppt/                             # Generated PowerPoint output
claude_team_v0.txt               # 3-role agent variant for Claude 4.6
claude_copy.sh                   # Copy claude_team_v0.txt to clipboard
```

## Prompt Variants

- `team_prompt.txt` (tracked) — 4-role team (企画/本文/要約/チェック). Original prompt for general document creation.
- `claude_team_v0.txt` (local-only) — 3-role team (オーケストレーター/リサーチャ/ライター). Lighter variant optimized for Claude 4.6; adds diagram suggestion support.

## Clipboard Scripts

```bash
./scripts/team_copy.sh          # Copy prompts/team_prompt.txt to clipboard (macOS pbcopy)
./scripts/team_show.sh          # Print prompts/team_prompt.txt to stdout
./claude_copy.sh                # Copy claude_team_v0.txt to clipboard (local-only)
```

## Markdown-to-PPTX Pipeline (local-only)

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

## 行動方針

### 自律的に進めてよい操作
- 調査（ファイル読み取り、コード検索、構造把握）
- 整理（情報の分類・要約・構造化）
- 下書き（ドキュメント・コードの草案作成）
- 設計（アーキテクチャ検討、方式提案）
- 提案（改善案・代替案の提示）
- コード作成（新規ファイル作成、既存ファイル編集）

### 必ず事前に確認する操作
- スクリプト・コマンドの実行（ビルド、テスト含む）
- 外部アクセス（API呼び出し、Web取得）
- 外部送信（git push、PR作成、メッセージ送信）
- 破壊的操作（ファイル削除、上書き、大規模改修、git reset等）

### 完了時のルール
- 作業完了時は必ず **レビュー依頼（承認）** を出す
- 変更内容の要約と確認ポイントを提示してからユーザー承認を得る

### 出力形式
1. **要点** — 結論・変更サマリを最初に示す
2. **詳細** — 根拠・実装内容・補足説明
3. **次アクション** — ユーザーが取るべき手順や選択肢

## agent-gateway（server.mjs）

### 概要
- `server.mjs` は依存ゼロ（Node標準のみ）の JSON API サーバー
- Node.js 組み込みモジュール `node:http` と `performance` のみ使用
- エンドポイント:
  - `GET /health` → `{ ok: true, time: ISO文字列 }`
  - `GET /version` → `{ name: "agent-gateway", version: "0.1.0" }`
  - `POST /echo` → 受け取ったJSONをそのまま返す（不正JSONは 400）
  - その他は 404 → `{ error: "Not Found" }`
- ログ: `METHOD /path STATUS 処理時間ms` を stdout に出力
- 内部エラー時は 500 → `{ error: "Internal Server Error" }`

### 実装の要点
- `json(res, status, body)` — JSON レスポンスヘルパー（Content-Length 付き）
- `readBody(req)` — Promise ベースのリクエストボディ読み取り
- `handleRequest(req, res)` — 非同期ルーティングハンドラ
- バインドアドレス: `HOST=127.0.0.1`（ローカルのみ）

### 起動
- `node gateway/server.mjs`
- `PORT` 環境変数でポート変更可能（デフォルト3000）

### 動作確認（curl）
```bash
curl -s http://127.0.0.1:${PORT:-3000}/health | python3 -m json.tool
curl -s http://127.0.0.1:${PORT:-3000}/version | python3 -m json.tool
curl -s -X POST http://127.0.0.1:${PORT:-3000}/echo \
  -H 'Content-Type: application/json' -d '{"hello":"world"}' | python3 -m json.tool
curl -s -X POST http://127.0.0.1:${PORT:-3000}/echo \
  -H 'Content-Type: application/json' -d 'not json' | python3 -m json.tool
curl -s http://127.0.0.1:${PORT:-3000}/unknown | python3 -m json.tool
```

### 運用ルール（このリポジトリ方針に合わせる）
- `server.mjs` の実行・curl での検証は「必ず事前承認」を取る
- 変更が完了したら「要点 → 詳細 → 次アクション」形式でレビュー依頼（承認）を出す

## Notes

- All shell scripts use `zsh` with `set -e`.
- All prompts and document output are in Japanese.
- Shell scripts reference `$HOME/agent-team/prompts/` for prompt files.
- No external dependencies — `server.mjs` uses only Node.js standard library.
- Clipboard scripts use macOS `pbcopy`; not compatible with Linux without modification.
- Development branch: `claude/add-claude-documentation-afn5L`
