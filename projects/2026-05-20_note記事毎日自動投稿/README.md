# note記事 毎日自動投稿パイプライン

> 「Chatに毎回認証情報を貼る」のではなく、GitHub Secretsに一度登録するだけで、以降は完全自動で note.com に毎日1記事投稿する仕組み。

## 全体像

```
毎朝 07:00 JST
    │
    ▼
GitHub Actions (.github/workflows/daily-note-post.yml)
    │
    ▼
post_to_note.py
    ├─ CMO/outputs/ から未投稿の最新記事を選ぶ
    ├─ playwright で note.com にログイン
    ├─ タイトル＋本文を入力して公開
    └─ state/posted.json に投稿履歴を記録
```

---

## オーナーが最初の1回だけやること（5分）

### Step 1: GitHub Secrets を設定

リポジトリの **Settings → Secrets and variables → Actions → New repository secret** で以下を登録。

#### パターンA: ID/パスワード方式（簡単・推奨初期値）

| Secret名 | 値 |
|---------|---|
| `NOTE_EMAIL` | noteログイン用メールアドレス |
| `NOTE_PASSWORD` | noteログイン用パスワード |

#### パターンB: セッションcookie方式（より安全・2FA回避）

| Secret名 | 値 |
|---------|---|
| `NOTE_SESSION_COOKIE` | noteログイン済みブラウザから取得したcookie JSON |

cookieは以下の手順で取得：
1. Chrome等で note.com にログイン
2. DevTools (F12) → Application タブ → Cookies → `https://note.com`
3. 全行を選択して JSON 形式でエクスポート（拡張機能「EditThisCookie」が便利）
4. 取得したJSONを丸ごと `NOTE_SESSION_COOKIE` の値として貼り付け

### Step 2: 動作確認（手動実行）

GitHub の **Actions** タブ → **daily-note-post** → **Run workflow** から手動で起動。

初回は `dry_run: true` を指定してログイン確認のみを行うことを推奨。

```
Run workflow
  article_path: (空)
  dry_run: true
```

成功すれば、次から `dry_run: false` で本番投稿。

### Step 3: スケジュール起動の確認

設定後、翌朝 07:00 JST に自動で動きます。初日はActionsログをチェック。

---

## 失敗時のデバッグ

- Actions実行ログを確認
- 失敗時は `note-post-debug` というArtifactにスクリーンショットが保存される（7日間保持）
- note.comのUI変更でセレクタが壊れた場合、`scripts/post_to_note.py` の `*_selectors` リストを更新

---

## セキュリティについて

- 認証情報はGitHub Secrets内で暗号化保管され、ワークフロー実行時のみ環境変数として注入されます
- リポジトリのコードからは参照できますが、ログには出力されません
- パスワード方式の場合、定期的なパスワードローテーションを推奨します
- セッションcookie方式の場合、cookieは2〜3週間で失効するため、その都度更新が必要です

---

## 既知の制約

1. **2FA / CAPTCHA**: パスワード方式の場合、note.comが2FAやCAPTCHAを挟む可能性があります。その場合はcookie方式に切替てください。
2. **note.comのUI変更**: セレクタが壊れる可能性があり、その場合はスクリーンショット付きでIssueを起票してください。
3. **画像（サムネ）**: 現バージョンは記事本文のみ投稿します。サムネ自動生成は次フェーズで実装。

---

## 実装状況

| Phase | 内容 | 状態 | スクリプト |
|-------|------|------|----------|
| P1 | 記事の手動執筆 | 完了 | （CMO作業） |
| P2 | GitHub Actions 自動投稿 | 完了 | `post_to_note.py` |
| P3 | 記事自動生成（Claude） | 完了 | `generate_article.py` |
| P4 | サムネ自動生成（DALL-E 3） | 完了 | `generate_thumbnail.py` |
| P5 | 過去サムネ取得・文体ガイド自動化 | 完了（要cookie） | `fetch_past_thumbnails.py` |
| P6 | 失敗時のSlack通知・自動Issue起票 | 未実装 | — |

## 必要なGitHub Secrets（全部入り）

| Secret名 | 必須 | 用途 |
|---------|------|-----|
| `NOTE_EMAIL` | 必須(A) | noteログイン用メール |
| `NOTE_PASSWORD` | 必須(A) | noteログイン用パスワード |
| `NOTE_SESSION_COOKIE` | 必須(B) | 上記の代替（cookie方式・2FA回避） |
| `ANTHROPIC_API_KEY` | 必須 | Claudeで記事生成 |
| `OPENAI_API_KEY` | 任意 | DALL-E 3でサムネ生成（なければ本文のみ投稿） |

(A) と (B) はどちらか一方でOK。両方あればcookieを優先。

## 手動実行のモード

GitHub Actions の **Run workflow** ボタンで以下を選べます：

- `full`: 記事生成 → サムネ生成 → 投稿（本番運用と同じ）
- `generate_only`: 記事生成のみ（投稿はせず、リポジトリにコミットだけ）
- `post_only`: 既存記事を投稿のみ（`article_path` も指定）
- `dry_run`: ログイン確認のみ、投稿なし

## 過去サムネを取得して文体・スタイルガイドを生成

```bash
NOTE_SESSION_COOKIE='[{"name":"...","value":"...",...}]' \
  python projects/2026-05-20_note記事毎日自動投稿/scripts/fetch_past_thumbnails.py
```

実行後、`assets/thumbnail_reference/` に過去サムネ画像が保存され、
`assets/style_guide.md` が過去タイトル一覧から自動生成されます。
以降の記事生成・サムネ生成はこれを参照してスタイルを寄せます。

---

## 参考：手動投稿で済ませる場合

Secretsを設定したくない場合は、以下の手順で手動投稿可能：

1. `CMO/outputs/YYYY-MM-DD_*_note記事.md` をテキストエディタで開く
2. note.comの新規投稿画面にコピペ
3. サムネは別途 Canva / DALL-E で生成
4. 公開ボタンを押す

所要時間：約10分。
