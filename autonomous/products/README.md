# autonomous/products/

自立型AI会社が deploy する実プロダクトを置くディレクトリ。

各プロダクトは独立したフォルダで、以下を含む：
- コード（TypeScript / JavaScript）
- `wrangler.toml`（Cloudflare Workers 設定）
- `data/`（seed データ）
- `README.md`
- `DEPLOY_*.md`（デプロイ手順書）

## 現在のプロダクト

| プロダクト | 状態 | 月次想定収益 | デプロイ方法 |
|----|----|----|----|
| [jp-subsidy-mcp](./jp-subsidy-mcp/) | 実装済・未デプロイ | ¥0 〜 ¥5,000 | [DEPLOY_11MIN.md](./jp-subsidy-mcp/DEPLOY_11MIN.md) |

## 新プロダクトの追加方針

1. **Cloudflare Workers 無料枠** で動くこと（月 100,000 req 以内）
2. **x402 protocol** で収益化すること（USDC 自動決済）
3. **日本語特化 or 富山特化** のニッチを狙うこと
4. **autonomous AI が自動更新できる** 構造にすること
5. **オーナーの新規赤字ゼロ** を守ること

## 収益の流れ

```
AI エージェントが MCP ツールを呼ぶ
  ↓
Cloudflare Workers で受信
  ↓
x402 payment middleware が $0.XX USDC を要求
  ↓
エージェントのウォレットが USDC を支払う
  ↓
x402 facilitator が on-chain 決済（Base ネットワーク、2 秒）
  ↓
USDC がオーナーの Coinbase Wallet address に入金
  ↓
Worker がレスポンスを返す
```

手数料はゼロ、仲介業者はゼロ、銀行振込はゼロ。完全に Web ネイティブ。
