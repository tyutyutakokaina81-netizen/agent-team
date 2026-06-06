# ops/ — エージェント間 指示チャネル（機械向け）

Claude Code（主）と cowork（副）の**非同期な依頼・報告**をファイルで受け渡す。
PR #12 のコメントは「オーナー向け・方針議論」、ここは「エージェント間の実行依頼・結果報告」。

詳細な役割分担は `docs/role-division.md` を参照。

## ディレクトリ

```
ops/
├── inbox/        ← 未処理の依頼
├── processed/    ← 処理済み（消さず移動・末尾に結果サマリを追記）
└── README.md
```

## ファイル名

```
YYYY-MM-DD_NNN_<from>_<to>.md     例: 2026-06-07_001_claude-code_cowork.md
```

## ファイル形式（YAML frontmatter + 本文）

```markdown
---
id: 2026-06-07_001
from: claude-code        # claude-code / cowork
to: cowork
created: 2026-06-07T09:00:00+09:00
priority: normal         # urgent / normal / low
type: instruction        # instruction / report / question
status: open             # open / in-progress / done
---

# タイトル

本文。対象ファイルのパス・条件を具体的に書く。
```

## 運用ルール

| アクション | 誰が | やり方 |
|---|---|---|
| 依頼を出す | 主に Claude Code → cowork | `inbox/` に新規ファイルを commit |
| 引き受ける | 受け手 | frontmatter を `status: in-progress` に編集 + commit |
| 完了する | 受け手 | `processed/` に移動 + 本文末尾に結果サマリを追記 + commit |
| 未処理確認 | どちらも | `ls ops/inbox/` |

> まず `inbox/` の往復テスト1件で疎通を確認してから本運用する。
