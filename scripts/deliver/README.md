# 受注→納品パイプライン（v2：品質向上版）

AI（Claude）に貼るだけで作業が進む半自動化システム。
**1案件あたり3時間→35分の時短。**

---

## 🚀 最速コマンド

```bash
python3 scripts/deliver/run.py
```

これ1つで全フロー対応。進行中案件を一覧→選択→次のアクション実行。

---

## 🏗️ アーキテクチャ

```
[受注]
   ↓ new_job.py（対話式）
[deliveries/YYYY-MM-DD_client_job/ 自動生成]
   ↓ generate.py
[prompts/ にClaudeプロンプト自動生成]
   ↓ 手動：Claudeに貼り付け→drafts/ に保存
[drafts/]
   ↓ quality_check.py（メトリクス付きチェック）
[品質OK？]
   ↓ package.py
[final/ に納品ファイル + delivery_email.txt 生成]
   ↓ 手動：メール送信
[invoice_note.md → 請求書発行]
   ↓ 手動：請求書送付 → 入金確認
[application_tracker.py で売上記録]
```

---

## 📋 スクリプト一覧

| スクリプト | 機能 |
|---------|------|
| **run.py** | 統合ワークフロー（推奨エントリポイント） |
| new_job.py | 新規受注セットアップ |
| generate.py | 案件タイプ別プロンプト生成 |
| quality_check.py | 高度な品質チェック（SEO/可読性/独自性） |
| package.py | 納品ファイル＆メール生成 |
| timer.py | 作業時間トラッカー（実時給計算） |
| client_profile.py | クライアント別プロファイル管理 |

---

## 📝 使い方

### 1. 受注したら
```bash
python3 scripts/deliver/run.py
# → [1] 🆕 新規受注を登録
```

対話式で入力：
- クライアント名
- 案件名
- 案件タイプ
- 報酬・納期
- タイプ別の詳細（記事なら キーワード/文字数/ペルソナ）

### 2. 作業開始（時間計測したい場合）
```bash
python3 scripts/deliver/timer.py start "2026-04-21_クライアント名_案件名"
```

### 3. プロンプト生成→Claudeで生成
```bash
python3 scripts/deliver/run.py
# → 案件選択 → [1] プロンプト生成
```

`prompts/` の .md を開いてClaudeに貼り付け → 結果を `drafts/` に保存。

### 4. 品質チェック
```bash
python3 scripts/deliver/run.py
# → 案件選択 → [2] 品質チェック
```

**自動計測される指標：**
- 文字数（目標との差分）
- キーワード密度
- 可読性スコア（100点満点）
- H2/H3 見出し構造
- 誇大表現検出
- メタディスクリプション長
- 繰り返し表現
- 箇条書き・表の使用状況

### 5. 作業終了
```bash
python3 scripts/deliver/timer.py stop "2026-04-21_クライアント名_案件名"
# → 実時給が自動計算される
```

### 6. 納品パッケージ
```bash
python3 scripts/deliver/run.py
# → 案件選択 → [2] 納品パッケージ生成
```

自動生成：
- `final/` に日付付き納品ファイル
- `delivery_email.txt` に納品メール下書き
- `invoice_note.md` に請求メモ

### 7. クライアントプロファイル管理
```bash
python3 scripts/deliver/client_profile.py list         # 一覧
python3 scripts/deliver/client_profile.py view 会社名  # 詳細
python3 scripts/deliver/client_profile.py edit 会社名  # 編集
```

リピートクライアントの好み・NG・過去実績を蓄積→次回案件で自動反映。

---

## ✨ v2 品質向上ポイント

### 1. 統合オーケストレーター
- `run.py` で全工程をワンコマンド管理
- 案件の進捗を自動検出→次のアクション提案

### 2. 高度な品質チェック
- 文字数だけでなく **可読性スコア** を算出
- **キーワード密度** を%で表示
- **繰り返し表現** を自動検出
- **誇大表現** を正規表現で発見

### 3. 実時給の可視化
- `timer.py` で実作業時間を計測
- 報酬÷実時間で**本当の時給**を表示
- 次回案件の単価判断に活用

### 4. クライアント別カスタマイズ
- リピートクライアントの好みを蓄積
- トーン・NGワード・好みの構成を記録
- 次回案件で自動反映

---

## 🎯 効率化の効果

| 工程 | 手動 | v2半自動 |
|------|------|---------|
| 受注情報整理 | 10分 | 3分 |
| プロンプト作成 | 15分 | 10秒 |
| 記事執筆（3000字） | 2時間 | 30分 |
| 品質チェック | 20分 | 1分（詳細メトリクス付き） |
| 納品準備 | 15分 | 10秒 |
| **合計** | **3時間** | **35分** |

**1件あたり2時間以上の時短。月20件なら40時間の節約＝時給2000円換算で月8万円の時間的価値。**

---

## ⚠️ 自動化できないこと（人間が必須）

- 案件の具体的な要件理解
- クライアント独自のトーン調整
- 事実確認・数字チェック
- 最終的な文章の品質判断
- クライアントとのコミュニケーション
- 倫理的・法的な適切性判断

---

## 📁 生成されるファイル構造

```
deliveries/
├── _client_profiles/             # クライアントプロファイル（client_profile.py）
│   └── XX株式会社.json
└── 2026-04-21_クライアント_案件名/
    ├── meta.json                 # 案件メタデータ
    ├── README.md                 # 案件サマリ
    ├── timer.json                # 作業時間ログ
    ├── prompts/                  # Claudeプロンプト（自動生成）
    │   ├── 1_structure.md
    │   └── 2_body.md
    ├── drafts/                   # 下書き（手動保存）
    │   └── article_draft.md
    ├── final/                    # 納品ファイル（自動生成）
    │   └── 20260421_案件名.md
    ├── delivery_email.txt        # 納品メール下書き
    └── invoice_note.md           # 請求メモ
```
