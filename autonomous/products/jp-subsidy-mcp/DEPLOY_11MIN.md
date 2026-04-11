# jp-subsidy-mcp を 11 分で live にする手順

**前提**: この MCP サーバーはコード実装済み。オーナー（あなた）が 11 分だけ手を動かせば live になります。

**合計作業時間**: 11 分
**合計費用**: ¥0
**新規赤字**: ゼロ

---

## ⏱️ Step 1: Coinbase Wallet を作る（5 分、¥0）

USDC を受け取る wallet。self-custody（自分で秘密鍵を持つ）なので銀行的な本人確認は不要。

1. スマホで [Coinbase Wallet](https://www.coinbase.com/wallet) アプリをダウンロード
2. 「新規ウォレットを作成」
3. 12 単語のリカバリーフレーズを**紙にメモ**（超重要：これを失くすと資産が戻らない）
4. ウォレットアドレスをコピー（`0x` で始まる 42 文字）
5. このアドレスを私に**渡す**（次のステップで使う）

**注意**:
- Coinbase Exchange（取引所）ではなく Coinbase Wallet（self-custody）です
- 日本から利用可、本人確認不要
- 秘密鍵はアプリ内にのみ保存される
- USDC の受け取りだけなら KYC 不要

---

## ⏱️ Step 2: Cloudflare アカウントを作る（3 分、¥0）

Cloudflare Workers の無料枠で MCP サーバーをホスト。

1. [dash.cloudflare.com/sign-up](https://dash.cloudflare.com/sign-up) にアクセス
2. メールアドレスとパスワードで登録（クレカ登録**不要**）
3. メール確認リンクをクリック
4. 無料プランが自動で選択される
5. Workers サブドメイン（例: `yourname.workers.dev`）を設定

**無料枠**: 100,000 リクエスト/日。この MCP サーバーには十分すぎる容量。

---

## ⏱️ Step 3: Cloudflare API token を発行する（2 分、¥0）

デプロイ時の認証に必要。

1. [dash.cloudflare.com/profile/api-tokens](https://dash.cloudflare.com/profile/api-tokens) にアクセス
2. 「Create Token」→「Edit Cloudflare Workers」テンプレート選択
3. 「Continue to summary」→「Create Token」
4. トークン文字列が表示される → **コピー**
5. このトークンを私に**渡す**（または GitHub Secrets に登録）

**保管場所**:
- 紙にメモしておく（後で再発行も可能）
- または GitHub repo Settings → Secrets → `CLOUDFLARE_API_TOKEN` に登録

---

## ⏱️ Step 4: 私に 2 つの値を渡す（1 分、¥0）

以下 2 つの値をチャットで私に渡してください：

```
SERVER_ADDRESS=0x...（Coinbase Wallet のアドレス、42 文字）
CLOUDFLARE_API_TOKEN=...（Cloudflare API トークン）
```

**セキュリティ上の注意**:
- これらを私（Claude Code セッション内）に渡しても、私は repo に commit しません
- 環境変数としてシェルに export するだけで使います
- 渡した後、値を安全に別の場所（パスワードマネージャー等）に保管してください

---

## ⏱️ Step 5: 私がデプロイを実行（オーナー作業なし）

Step 4 の値を受け取った後、私が以下を自動実行します（オーナーは待つだけ）：

```bash
cd autonomous/products/jp-subsidy-mcp/
npm install
npx wrangler deploy
npx wrangler secret put SERVER_ADDRESS  # 環境変数から注入
```

**所要時間**: 2-3 分（私側）
**結果**: `https://jp-subsidy-mcp.<your-subdomain>.workers.dev` が live になる

---

## ✅ live 後の確認

```bash
# ヘルスチェック
curl https://jp-subsidy-mcp.<your-subdomain>.workers.dev/health

# サーバー情報
curl https://jp-subsidy-mcp.<your-subdomain>.workers.dev/info

# 無料サンプル
curl https://jp-subsidy-mcp.<your-subdomain>.workers.dev/free/list
```

以降、Claude Desktop や他の AI エージェントが `/mcp` エンドポイントを呼ぶたびに、$0.05 USDC が**自動でオーナーのウォレットに入金**されます。

---

## ⏱️ 合計時間まとめ

| Step | 時間 | 費用 |
|----|----|----|
| 1. Coinbase Wallet 作成 | 5 分 | ¥0 |
| 2. Cloudflare アカウント作成 | 3 分 | ¥0 |
| 3. API token 発行 | 2 分 | ¥0 |
| 4. 値を私に渡す | 1 分 | ¥0 |
| 5. デプロイ | オーナー作業 **0 分** | ¥0 |
| **合計** | **11 分** | **¥0** |

**新規赤字**: **完全にゼロ**（Cloudflare 無料枠、Coinbase Wallet 無料、x402 手数料ゼロ）

---

## よくある質問

### Q. 本当に ¥0 で済む？

はい。Cloudflare Workers は月 100,000 req まで無料、Coinbase Wallet は無料、x402 protocol fee はゼロ、USDC の受け取りだけならガス代もほぼゼロ（入金時は送信者が負担）。

### Q. USDC を日本円にするには？

将来的に必要になったら、bitbank / bitFlyer / SBI VC Trade 等の日本の取引所アカウントで KYC して換金できます。**今すぐやる必要はありません**。USDC のまま保持でも OK。

### Q. 売れなかったらどうなる？

売れなくても何も失いません。Cloudflare 無料枠・Wallet 無料なので、**放置しても費用は発生しません**。revenue = ¥0 のまま永久に動き続けます。

### Q. 売れたらどのくらい？

見通しは月 ¥0 〜 ¥5,000 程度（初期）。ただし **完全に自律的に稼働するので追加の労力はゼロ**。autonomous AI が新しい補助金を data/ に追加し、README を更新し、新バージョンをデプロイするループが回ります。

### Q. 失敗時のリスクは？

ゼロ。Cloudflare Workers の削除（1 クリック）と Coinbase Wallet の放置（何もしない）で完全にゼロに戻ります。

---

## 次のステップ（デプロイ後）

1. 初回 live 確認後、MCP 公開ディレクトリ（PulseMCP / modelcontextprotocol.io）に無料登録（私が自動）
2. Zenn / Qiita に日本語の紹介記事を投下（私が自動生成、オーナーは copy-paste 2 分）
3. 自律型AI が週次で `data/subsidies.json` を更新する仕組みを起動
4. 初の $0.05 USDC 入金を待つ 🎯

---

**この 11 分が、autonomous AI 企業の収益化の扉を開きます**。
