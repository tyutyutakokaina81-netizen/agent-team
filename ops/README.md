# ops/ — エージェント間の指示・報告キュー

Claude Code と Cowork の間で **構造化された指示と報告**をやり取りするための
ファイルベース非同期キュー。git に乗るので両者から参照可能。

## ディレクトリ

```
ops/
├── inbox/        ← Code → Cowork の指示キュー（Cowork が pickup）
├── outbox/       ← Cowork → Code の報告キュー（Code が pickup）
├── processed/    ← 処理済（受け手が move する）
├── logs/         ← 実行ログ（公開バッチの結果等）
├── process_inbox.py  ← 最小限のCLIヘルパー
└── README.md
```

## ディレクトリの使い分け（2026-06-07 確定）

| 方向 | 投函先 | 用途 |
|---|---|---|
| Code → Cowork | `inbox/` | 「これ公開して」「英語刷新して」等の指示 |
| Cowork → Code | `outbox/` | 「N件公開完了」「エラーN件」等の報告 |
| 完了済タスク | `processed/` | inbox/outbox 問わず done したものを移動 |
| 実行ログ | `logs/` | バッチ処理の詳細ログ（trace level） |

`process_inbox.py` は `inbox/` `outbox/` 両方を扱う。
`--to code` で自分宛フィルタ → outbox の報告も拾える。

## ファイル命名

```
YYYY-MM-DD_NNN_<from>_<to>.yaml
```

- `YYYY-MM-DD` — 投函日
- `NNN` — 同日連番（001, 002, ...）
- `<from>` — `cowork` / `code` / `owner`
- `<to>` — `cowork` / `code` / `owner`

例：`2026-06-07_001_cowork_code.yaml`

## ファイル形式（YAML フロントマター + Markdown 本文）

```markdown
---
id: 2026-06-07_001
from: cowork
to: code
created: 2026-06-07T08:30:00+09:00
priority: normal       # urgent / normal / low
type: instruction      # instruction / report / question
status: open           # open / in-progress / done
title: 6/14 の記事を5本に揃えてください
---

# 本文（自由形式 Markdown）

詳細・背景・期待する出力など。受け手が読んで動けるように書く。
```

## CLI（process_inbox.py）

依存ゼロの Python 3 スクリプト。PyYAML は使わず簡易パーサで frontmatter を読む。

```bash
# 未処理の指示を一覧
python3 ops/process_inbox.py list

# 自分宛だけ
python3 ops/process_inbox.py list --to code

# 1件の詳細表示
python3 ops/process_inbox.py show 2026-06-07_001

# 自分が引き受ける（status: open → in-progress）
python3 ops/process_inbox.py take 2026-06-07_001

# 完了して processed/ に移動（結果サマリを末尾に追記）
python3 ops/process_inbox.py done 2026-06-07_001 --result "5本揃えてcommit済み"

# 新しい指示を投函
python3 ops/process_inbox.py post \
  --from code --to cowork \
  --type instruction --priority normal \
  --title "drafts/queue/ を pickup して公開してください" \
  --body "queue にある2本を note に公開し、published/ に移動してください"
```

## 運用ルール

- **指示の単位を小さく保つ**：1ファイル = 1タスク
- **処理完了したら必ず move**：`inbox/` に残すと未処理に見える
- **結果サマリは必須**：done 時に結果を追記しないと監査できない
- **`status` フィールドは編集する**：取り組み中は `in-progress` にして衝突回避
- **削除はしない**：`processed/` に残して履歴として保持

## 日次自動公開と安全ゲート（2026-06-19 確定）

オーナーのMacで launchd により `cowork_run.sh` を毎朝実行する自動公開系。
6/12インシデント（無人公開で81本の重複/未来日付が公開）の再発防止として
**3段の安全装置**を備える。

| 装置 | 役割 | 解除方法 |
|---|---|---|
| 本番公開ゲート | `ops/PUBLISH_ENABLED` が無ければ全件 `--draft`（下書きのみ・本番公開しない） | `touch ops/PUBLISH_ENABLED` で本番ON／`rm` でOFF |
| 未来日付ガード | ファイル名日付が今日より未来のキューはスキップ | （自動・解除不要） |
| 冪等化 | `published_log.tsv` で同一記事の二重公開を防止 | 再公開時のみ `publish_to_note.py --force` |

### 導入手順（オーナーのMacで一度だけ）

```bash
bash ops/install_publish_schedule.sh        # 既定 08:00。--draft で安全起動（本番公開しない）
# note側の棚卸し（再開条件①③）完了を確認してから：
touch ops/PUBLISH_ENABLED                    # 本番公開を有効化
```

> **既定は安全（本番公開OFF）**。フラグを立てるまで何回起動しても下書き保存に留まる。
> 公開対象は `drafts/queue/*.md`。公開できたものは `drafts/published/` へ移動。

## PR コメントとの使い分け

- **PR コメント**：人間（オーナー）が読む議論・方針確認
- **`ops/inbox/`**：エージェント間の機械的なタスク発注・完了報告

両方を併用する想定。PR コメントで合意した方針を `ops/inbox/` でタスク化する。
