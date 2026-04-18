# note_uploader — note.com 完全自動投稿ツール

Playwright 製の note.com 投稿ツール。  
**タイトル → 本文 → タグ → 公開設定 → 公開ボタン押下まで完全自動化**。

## 動作モード（デフォルトはフル自動）

| モード | 起動方法 | 動作 |
|-------|---------|------|
| **FULL-AUTO**（デフォルト） | `node post_to_note.mjs <file>` | 公開ボタンまで自動押下（即時実行） |
| **REVIEW** | `node post_to_note.mjs <file> --review` | タグ追加まで自動・公開直前で停止（手動で「公開」） |
| **DRY-RUN** | `node post_to_note.mjs <file> --dry-run` | タイトル・本文入力のみ、公開設定にも進まない |

## 設計方針

- ✅ オーナーがdraftを承認した時点で内容確認は完了している前提 → 公開時点の追加確認は不要
- ✅ 投稿後にtypo等あれば note 上で編集/削除可能
- ⚠ noteの利用規約上、自動投稿は明示禁止されていないが**過度な利用はBANリスク**（1日数本までを目安）
- ✅ 初回ログインだけ手動 → セッション保存 → 以降は自動ログイン状態で起動
- ✅ セレクタ不一致など技術エラー時は自動でスクショ保存・ブラウザ維持

## 動作環境

- **オーナーのローカルPC（Mac）で実行する**（リモートサーバーでは×）
- Node.js 18以上
- Chromium ブラウザ（Playwright が自動インストール）

## セットアップ（初回のみ）

```bash
cd CDO/outputs/note_uploader

# 依存関係のインストール
npm install

# Playwright のブラウザをインストール
npm run setup

# noteにログイン（ブラウザが開くので手動でログイン）
npm run login
# → auth-state.json が保存される（このファイルは .gitignore で除外済）
```

## 使い方

### フル自動投稿

```bash
node post_to_note.mjs ../../../projects/2026-04-18_note執筆/posts/drafts/2026-04-18_Claude-Opus-4-7体験記.md
```

実行すると：
1. noteの新規投稿ページが自動で開く
2. タイトル → 本文 → タグ が自動入力
3. 「公開設定」へ自動遷移
4. 「公開」ボタン自動押下
5. 公開URLを表示してブラウザを閉じる

### 初回・セレクタ確認したいとき

```bash
node post_to_note.mjs <file> --review   # タグまで自動・公開ボタンだけ手動
node post_to_note.mjs <file> --dry-run  # タイトル・本文入力のみ
```

### 🤖 フル自動モード：watch_and_post

ターミナルで1度起動するだけで、新しいドラフトが push されるたび自動投稿します。

```bash
cd ~/agent-team/CDO/outputs/note_uploader
node watch_and_post.mjs
```

動作：
1. 60秒ごとに `git pull`
2. `posts/drafts/` に `posts/published/` にないファイルを検出したら post_to_note.mjs で自動投稿
3. 成功したら `drafts/` → `published/` へ移動、自動でコミット & プッシュ
4. 失敗したファイルはそのセッション中は再試行しない（無限ループ防止）

ターミナルを閉じると停止します。常時起動したい場合は `nohup` か LaunchAgent 化。

**常時起動例（バックグラウンド）:**
```bash
nohup node watch_and_post.mjs > ~/watch_note.log 2>&1 &
```

停止：
```bash
pkill -f watch_and_post.mjs
```

## 記事ファイルの形式（frontmatter）

```markdown
---
title: 記事のタイトル
tags:
  - Claude
  - AI
  - ClaudeCode
---

本文ここから...

段落は空行で区切る。
```

## トラブルシューティング

**「タイトル入力欄が見つかりません」エラー**
- noteのUI変更の可能性。`error_*.png` を確認
- `post_to_note.mjs` の `titleCandidates` / `bodyCandidates` セレクタを更新

**ログインが切れた**
- `npm run login` を再実行

**2要素認証 (2FA) で止まる**
- `login_setup.mjs` は手動操作なので 2FA も普通に通せる
- 認証アプリでコードを入力 → ログイン完了で自動検知

## セキュリティ注意

- `auth-state.json` は **note にログイン済の Cookie** を含む機密情報。**絶対に Git にコミットしない**（`.gitignore` で除外済）
- このフォルダを他人と共有する際は `auth-state.json` を必ず削除する
- リモートサーバーで実行しない（クレデンシャル漏洩リスク）

## 作成

CDO（2026-04-18）。  
旧プロジェクト「月30万自動化」終了に伴う方針転換、note執筆プロジェクト立ち上げ用ツールとして整備。
