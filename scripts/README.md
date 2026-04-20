# 自動化スクリプト集

使い方メモ。すべてPython 3.10+で動く（標準ライブラリのみ）。

## セットアップ

```bash
chmod +x scripts/*.py
```

## スクリプト一覧

### 1. daily_report.py — 日次レポート
```bash
python3 scripts/daily_report.py
```
昨日＋今週の応募・受注・売上を集計。

### 2. rate_calculator.py — 時給計算
```bash
python3 scripts/rate_calculator.py
```
案件の時給・採算性を30秒で判定。

### 3. application_tracker.py — 応募記録
```bash
python3 scripts/application_tracker.py
```
応募を対話式で記録。ステータス更新・統計も可能。

### 4. email_template.py — メール生成
```bash
python3 scripts/email_template.py
```
応募・納品・請求・フォローアップのメールを対話式で生成。

## 朝のルーティン

```bash
python3 scripts/daily_report.py      # 昨日の実績
python3 scripts/application_tracker.py  # 今日の記録
```

## 案件判定時

```bash
python3 scripts/rate_calculator.py   # 時給計算
```

## メール書く時

```bash
python3 scripts/email_template.py    # テンプレ生成
```

## データファイル

`scripts/applications.csv` に応募ログが蓄積される（.gitignore対象）。
