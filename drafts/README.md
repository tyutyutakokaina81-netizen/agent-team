# drafts/ — note 公開のステージング

Claude Code が公開可能と判断した記事をここに置き、Cowork が pickup して
note.com に公開してから `published/` に移動する。

## なぜ分けるか

Claude Code は **note.com に到達できない**（外部ネット遮断＋ブラウザなし）。
note 公開ができるのは Cowork（Chrome 拡張・ブラウザセッション保持）のみ。
よって両者の橋渡しとして staging area が必要。

## ディレクトリ

```
drafts/
├── README.md             ← このファイル
├── queue/                ← 公開待ち（Code が staging）
├── published/            ← 公開済（Cowork が移動）
└── stage_for_publish.py  ← CMO/outputs/ → queue/ コピーヘルパー
```

## ワークフロー

### Step 1: Claude Code が staging

```bash
# 単一記事
python3 drafts/stage_for_publish.py CMO/outputs/2026-06-14_note記事_xxx.md

# 日付指定で全件
python3 drafts/stage_for_publish.py --date 2026-06-14

# 公開済みは自動スキップ（drafts/published/ にあるものは無視）
```

### Step 2: Cowork が pickup

Cowork は定期実行で：

1. `drafts/queue/*.md` を全件読む
2. 各記事を note.com に公開（Chrome 拡張・保存済セッション）
3. 成功 → `drafts/queue/X.md` → `drafts/published/X.md` に移動
4. 失敗 → queue に残し `ops/process_inbox.py post` でエラー報告

### Step 3: 完了報告

Cowork は `ops/inbox/` に完了レポートを投函（[ops/README.md](../ops/README.md) 参照）。

Claude Code は次回起動時にレポートを読み、`CMO/_index.md` のステータスを
「完了（公開待ち）」→「公開済」に更新する。

## ファイル形式

`drafts/queue/` のファイルは `CMO/outputs/` の単純コピー。書式は同じ。

```markdown
# タイトル（H1）

英語サブタイトル（任意）

本文...

[写真1]
本文続き...

## 英語要約

...

## 事実検証ノート

- ✅ 確実: ...
- ⚠️ 要確認: ...
```

Cowork は H1 をタイトル、それ以降を本文として note に投稿する。
`[写真X]` placeholder は手を加えず空のまま投稿（オーナーが web で後付け）。

## 失敗時のリカバリ

| 状況 | 対応 |
|---|---|
| 記事の構造エラー（H1なし等） | Cowork が `ops/inbox/` にエラー報告 → Code が修正して再 stage |
| note 側の障害（500等） | Cowork が queue に残してリトライ予定を `ops/inbox/` に報告 |
| 重複投稿の疑い | `drafts/published/` に同名ファイルがあれば Cowork はスキップ |
| 公開後に問題発覚 | オーナーが note 側で手動削除 → `drafts/published/X.md` を `queue/` に戻して再投稿 |

## 注意

- **`drafts/published/` には書き込まない**（Cowork のみ書き込み権限）
- **同一ファイル名で `queue/` と `published/` の両方には置かない**
- staging は冪等：既に published にあるものは stage 時にスキップされる
