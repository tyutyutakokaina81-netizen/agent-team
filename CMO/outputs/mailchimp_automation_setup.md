# Mailchimp 自動メール設定
## Gumroad 購入者フォローアップ自動化

> **目標**: Solo CEO OS 購入者への自動メール3通で、関連テンプレ購入・note有料化へのアップセル化を達成

**セットアップ日**: 2026-06-24  
**優先度**: 🔴 Stage 1 最優先（+12点）  
**期限**: 6/30までに稼働確認完了

---

## セットアップ手順

### Step 1: Mailchimp リスト作成（オーナー 5分）

1. mailchimp.com にログイン
2. **Audience** → **Create Audience** → 新規リスト「Solo CEO OS buyers」作成
3. リスト設定：
   - デフォルト FROM: `tyutyu.tako.kaina81@gmail.com`
   - デフォルト返信先: `tyutyu.tako.kaina81@gmail.com`
   - 言語: 日本語

### Step 2: Zapier で Gumroad → Mailchimp 自動連携

```
Trigger: Gumroad New Purchase
Action: Mailchimp Add/Update Contact
```

**設定詳細**：
- Gumroad API Key: Settings → API より取得
- Mailchimp API Key: Account → Extras → API keys より取得
- 自動追加フィールド：
  - Email: `{email}`
  - 名前: `{buyer_name}` or "Solo CEO OS 購入者"
  - Tags: `"Solo CEO OS", "Gumroad", "高額顧客"`

### Step 3: オートメーション設定（Mailchimp または Zapier）

**方式 A: Mailchimp ネイティブオートメーション（推奨・シンプル）**

1. **Mailchimp Audience** → **Automations** → **Create Automation**
2. Trigger: **"リストに追加されたとき"**
3. メール3通を設定：

| # | 送信タイミング | テンプレ | 目的 |
|---|----------|---------|------|
| 1 | 追加直後 | ウェルカムメール | 購入確認＋ダウンロードリンク |
| 2 | +3日後 | アップセルメール Vol.2 | SNS Calendar 販売開始案内 |
| 3 | +7日後 | note有料化ご案内 | メンバーシップ招待 |

**方式 B: Zapier 複数アクション（カスタマイズ性高）**

- Step 1: Gumroad Purchase トリガー
- Step 2: Delay 3 days
- Step 3: Mailchimp Send Email
- ※ Step 2-3 の複数回設定で3通目対応

---

## 自動メール テンプレート集

### Mail #1: ウェルカムメール（購入直後）

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━
Solo CEO OS 購入ありがとうございます
━━━━━━━━━━━━━━━━━━━━━━━━━━━

こんにちは。

つつです。Solo CEO OS をご購入いただき、ありがとうございました。

このメールに返信いただければ、以下の内容を優先サポートさせていただきます：

📌 **よくある質問と答え**
- スプレッドシートをコピーしてから編集してください
- 自分の売上数字を「月売上」に入力すると自動計算されます
- 税務は顧問税理士にご相談ください（このテンプレは経営判断ツール）

📌 **すぐに使えるポイント**
1. まずは「今月の見立て」シートで月の売上予測を立てる
2. 週単位の CFP（キャッシュフロー予測）を決める
3. 3つの数字（売上・原価・現金残高）だけを毎日入力

📌 **次のステップ（テンプレVol.2 最新情報）**
次週、SNS運用を自動化する「コンテンツカレンダー Vol.2」を販売開始します。
詳細は下記をご確認ください：

→ https://note.com/tyutyu_taako （プロフィールで最新情報）

ご質問・ご感想はいつでもこのメールに返信ください。
あなたのフィードバックが次の改善につながります。

つつ

━━━━━━━━━━━━━━━━━━━━━━━━━━━
Solo CEO OS — フリーランス月商追跡スプレッドシート
無料セットアップ相談受付中
```

### Mail #2: アップセルメール Vol.2（3日後）

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━
【本日公開】SNS Content Calendar Vol.2
━━━━━━━━━━━━━━━━━━━━━━━━━━━

つつです。

Solo CEO OS をご購入いただいたあなたへ。

本日、次の自動化テンプレを販売開始しました：

📊 **SNS Content Calendar Vol.2 — 月間投稿計画を60分で完成**

Solo CEO OS で「月の売上」が見えたあなたが、次にやるべきことは何か？

→ **継続的な集客の仕組み化**です。

このテンプレは：
✅ 月間投稿テーマを自動提案（カテゴリ別）
✅ 毎週5本の投稿を1シートで管理
✅ Instagram / X / note 対応

【Solo CEO OS 購入者 特別価格】
通常 ¥2,980 → 今週中 ¥1,980

→ https://note.com/tyutyu_taako/products/...
（リンクはVol.2公開時に更新）

このオファーは 6/30 までです。

つつ
```

### Mail #3: note有料化ご案内（7日後）

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━
あなたの「数字の迷い」を減らす有料記事
━━━━━━━━━━━━━━━━━━━━━━━━━━━

つつです。

Solo CEO OS と SNS Calendar でテンプレ側の自動化が進んだあなたへ。

次の課題は：
❓ 「毎日の判断が正しいのか、わからない」
❓ 「売上目標まであと何が必要か、見えない」

この問い に答えるために、note で有料記事とメンバーシップを開始しました：

📰 **月¥980 メンバーシップ：3つの特典**

1. **深掘り記事（毎週1本）**
   - 売上目標から逆算した月間行動計画
   - キャッシュフロー危機への対処法
   - 継続率向上の実践ログ

2. **販売テンプレ解説（隔週）**
   - Vol.2・Vol.3 の実装ノウハウ
   - 実際の営業メール・提案資料の作り方
   - 単価交渉の話し方

3. **運営ノウハウ（月1回）**
   - AI時代のひとり起業の組織論
   - 外注で時給を上げる仕組み
   - 月30万目指す具体ロードマップ

【Solo CEO OS 購入者 さらに特別】
初月無料でお試し → https://note.com/tyutyu_taako/membership

つつ
```

---

## 実装チェックリスト

### オーナー実施（Mac 側）

- [ ] Mailchimp 新規アカウント作成（既に持っていたら Skip）
- [ ] 「Solo CEO OS buyers」リスト作成
- [ ] Gumroad API Key を取得
- [ ] Mailchimp API Key を取得

### Zapier 側（オーナーまたは CDO）

- [ ] Zapier で Gumroad → Mailchimp 接続テスト
- [ ] 初回テスト購入で自動メール受信確認

### メール内容調整（CMO）

- [ ] 3つのテンプレを note プロフィール情報で更新（URL差し替え）
- [ ] ターゲット読者への言葉遣い調整
- [ ] Solo CEO OS 実績・お客様の声を追記（CSO協力）

### 稼働確認（オーナー）

- [ ] 6/24-6/26 の期間に誰か1人テスト購入 → メール受信確認
- [ ] テンプレ URL が正しくクリック可能か確認
- [ ] Gmail スパムフォルダに入っていないか確認

---

## KPI トラッキング（CAO 担当）

| 指標 | 目標 | 計測方法 |
|------|------|--------|
| メール到達率 | 95%以上 | Mailchimp Dashboard |
| 開封率 | 30%以上 | Mailchimp Analytics |
| クリック率（CTA） | 5%以上 | Mailchimp / Gumroad |
| アップセル率 | 20%以上 | Vol.2 購入数 ÷ Solo CEO OS 購入数 |

---

## 参考：Zapier テンプレ（zap.com 検索用）

```
Trigger: Gumroad — New Purchase
Filter: {product_id} = "Solo CEO OS"
Action 1: Mailchimp — Add/Update Contact
Action 2: Delay — 3 days
Action 3: Mailchimp — Send Email (Mail #2)
Action 4: Delay — 4 days
Action 5: Mailchimp — Send Email (Mail #3)
```

---

## コスト

| ツール | 費用 | 用途 |
|--------|------|------|
| Mailchimp | ¥0（無料プラン最初500連絡先まで） | メール配信 |
| Zapier | ¥0-300/月（無料＆有料版） | Gumroad 自動連携 |

**合計**: ¥0-300/月（初期段階は ¥0）

---

**オーナー確認事項**：  
上記テンプレをベースに、実際の note URL・Gumroad 情報を差し替えて実装してください。  
メール #2 は Vol.2 販売開始日（6/30 予定）に合わせて配信時刻を調整。
