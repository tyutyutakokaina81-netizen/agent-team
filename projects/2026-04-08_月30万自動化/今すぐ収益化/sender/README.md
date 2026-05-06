# 柱A/B 半自動送信ツール

## 概要
コールドアウトリーチを **半自動で送信** するツール。  
※ 完全自動ではない（オーナーが認証情報・ターゲットリストを設定して実行）。

## ディレクトリ構成
```
sender/
├── README.md          ← このファイル
├── send.py            ← メインスクリプト
├── targets.csv        ← 送信先（オーナーが入力）
├── templates/         ← メールテンプレ JSON
│   ├── A-1.json       ← 柱A: オウンドメディア更新停滞型
│   └── B-1.json       ← 柱B: 飲食店向け Instagram
└── logs/
    └── send_log.csv   ← 送信履歴（自動生成）
```

## セットアップ

### 1. 環境変数を設定（.env または直接 export）
```bash
# Gmail を使う場合（アプリパスワード推奨）
export SMTP_HOST=smtp.gmail.com
export SMTP_PORT=587
export SMTP_USER=your-gmail@gmail.com
export SMTP_PASS=your-app-password   # ※通常パスワードではなく「アプリパスワード」

# 送信者情報（特定電子メール法 必須項目）
export SENDER_NAME="あなたの氏名"
export SENDER_EMAIL=your-email@example.com
export SENDER_BUSINESS="個人事業主：あなたの氏名"
export SENDER_ADDRESS="〒XXX-XXXX 東京都..."
export UNSUBSCRIBE_URL=""  # 任意。無ければメール内で「配信停止と返信してください」と表示される
```

### 2. ターゲットリストを作成
`targets.csv` を編集し、実際の企業情報を入力：

| 列 | 内容 | 例 |
|---|------|---|
| company | 会社名 | 株式会社XXX |
| name | 担当者名 | 山田太郎 |
| email | 送信先メール | xxx@example.com |
| template_id | 使用するテンプレID | A-1 / B-1 等 |
| industry | 業種 | IT / 飲食 等 |
| media_name | メディア名（A系で使用） | XXXメディア |
| keyword | 検索キーワード | SEO対策 |
| role | 宛名敬称 | ご担当者様 / オーナー様 |
| competitor | 競合社名（A-2で使用） | （任意） |
| note | メモ | 初回コンタクト |

### 3. ターゲットの調査
1日5社程度を手動調査して `targets.csv` に追加：
- 会社HPの「お問い合わせ」フォーム or 公開メール
- LinkedIn 公開プロフィール
- Wantedly / Eight 等のビジネスSNS

## 使い方

### プレビュー（必須・最初に実行）
```bash
cd projects/2026-04-08_月30万自動化/今すぐ収益化/sender/
python send.py --dry-run
```
件名・本文がレンダリングされるか確認。

### 実送信
```bash
# 1日5件まで・30秒間隔で送信
python send.py --send --max 5 --interval 30
```

### 送信履歴の確認
```bash
cat logs/send_log.csv
```

## 安全機能

| 機能 | 動作 |
|------|------|
| 重複送信防止 | 同じ email × 同じ template_id は再送しない |
| 1日上限 | --max オプションで送信数を制限（推奨：5〜10件/日） |
| 送信間隔 | --interval で間隔を制御（推奨：30秒以上） |
| 環境変数チェック | 認証情報が無いと send モードで起動不可 |
| 法令遵守 | 全メール末尾に事業者名・住所・配信停止方法を自動付与 |

## 法令・倫理

### 特定電子メール法（迷惑メール防止法）
- 送信者は事業者名・住所・配信停止方法を明示する義務あり（自動付与済）
- **無差別な大量送信は違法**。個別調査して文面をパーソナライズすること
- 受信拒否の意思表示後の再送は禁止

### 推奨運用
- 1日10社以下に絞る
- 1企業に同じテンプレを2回以上送らない
- 反応が無くても2週間後に1度だけリマインドメール（しつこくしない）
- 各企業のサイトを必ず事前確認し、事業内容に合わせて文面を1〜2文変更

## トラブルシュート

### Q: SMTP 認証エラー
A: Gmail の場合、通常パスワードでは認証できない。  
   Google アカウント設定 →「セキュリティ」→「アプリ パスワード」を生成して使用。

### Q: 送信が遅い
A: --interval を短くできるが、30秒未満はスパム判定リスク。

### Q: targets.csv が ASCII 化けする
A: UTF-8 (BOM なし) で保存。Excel から保存する場合は「CSV UTF-8」を選択。

## 次のステップ
1. オーナーが targets.csv に実ターゲットを30件追加
2. dry-run で内容確認
3. 1日5件ペースで送信開始（6日で30件完了）
4. 返信が来たら 03_cold_outreach_pillar_a_b.md の「返信対応フロー」を参照
