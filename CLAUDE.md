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
- エンドポイント:
  - `GET /health` → `{ ok: true, time: ISO文字列 }`
  - `GET /version` → `{ name: "agent-gateway", version: "0.1.0" }`
  - `POST /echo` → 受け取ったJSONをそのまま返す（不正JSONは 400）
  - その他は 404 → `{ error: "Not Found" }`
- ログ: `METHOD /path STATUS 処理時間ms` を stdout に出力

### 起動
- `node server.mjs`
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

## ユーザー情報

- **名前**: 藤森徹次
- **会社**: 北陸電力送配電
- **環境**: 会社PC使用のため、ローカルにWindowsデスクトップアプリは使用不可

## Notes

- All shell scripts use `zsh` with `set -e`.
- All prompts and document output are in Japanese.
- Shell scripts reference `$HOME/agent-team/` as the repo path.
