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

## 次フェーズの予定

| Phase | 内容 |
|-------|------|
| P1（完了） | 記事生成 + 手動投稿 |
| **P2（本ファイル）** | **GitHub Actions 自動投稿（本文のみ）** |
| P3 | サムネ自動生成（DALL-E 3 / Imagen） |
| P4 | 文体ガイド自動更新（過去投稿スクレイピング） |
| P5 | 失敗時のSlack通知・自動Issue起票 |

---

## 参考：手動投稿で済ませる場合

Secretsを設定したくない場合は、以下の手順で手動投稿可能：

1. `CMO/outputs/YYYY-MM-DD_*_note記事.md` をテキストエディタで開く
2. note.comの新規投稿画面にコピペ
3. サムネは別途 Canva / DALL-E で生成
4. 公開ボタンを押す

所要時間：約10分。
