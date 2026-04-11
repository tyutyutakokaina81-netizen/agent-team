# autonomous/state/

自律ループが **クロスラン（実行間）で共有する状態** を置くディレクトリ。

`CFO/research/` や `CSO/research/` は `.gitignore` 対象で local-only。
一方、自律ループはリモート（GitHub Actions 等）でも動くため、
**Git で履歴管理される永続ストレージ** が必要。このディレクトリがそれ。

## 構成

```
autonomous/state/
├── budget/
│   ├── daily_spend.json    ← budget_guard.mjs が自動生成（日次）
│   └── monthly_spend.json  ← budget_guard.mjs が自動生成（月次）
└── (memory.json 等、将来追加)
```

## 原則

- **書き込むのは自律ループのみ** — 人間は原則編集しない（読み取りは自由）
- **機密情報は置かない** — すべて公開リポジトリにコミットされる前提
- **記録は追記型** — 過去データを消さない、改変しない（audit 可能性を保つ）
- **容量は小さく保つ** — 1ファイルは数十 KB まで。肥大化したら週次でローテート
