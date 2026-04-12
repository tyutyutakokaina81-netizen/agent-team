# CLAUDE.md — 個人 Web 開発者向け

このファイルは Claude Code に対するプロジェクト指示書です。個人 Web アプリ開発を効率化します。

## プロジェクトの目的

[ここに記入：例「個人で運営する SaaS の開発・保守・改善」]

## 技術スタック

- フロントエンド：[例 Next.js 14, TypeScript, Tailwind CSS]
- バックエンド：[例 Node.js, Hono, Drizzle ORM]
- データベース：[例 PostgreSQL (Neon), Upstash Redis]
- 認証：[例 Clerk / Auth.js]
- デプロイ：[例 Vercel, Cloudflare Workers]

## 担当領域

- コード生成（TypeScript / React / Node.js）
- コードレビュー・リファクタリング提案
- バグ調査・原因特定
- テスト生成（Vitest / Playwright）
- API 設計・エンドポイント実装
- SQL クエリ最適化
- Git コミットメッセージ生成

## やらないこと

- 本番環境への直接デプロイ（必ず確認してから）
- `.env` ファイルの内容を外部送信する提案
- 依存パッケージの major バージョンの無断更新
- DB スキーマの破壊的変更（マイグレーション先確認必須）
- 実稼働中のデータ削除

## コーディング規約

- TypeScript strict mode
- インデント：スペース 2
- セミコロン：必須
- import 順：標準 → サードパーティ → 自作
- コンポーネント命名：PascalCase
- 関数命名：camelCase、動詞始まり（`get...` `create...` `handle...`）
- ファイル命名：kebab-case（`user-profile.tsx`）

## コメント方針

- 「何を」ではなく「なぜ」を書く
- 自明なコードにコメント不要
- TODO/FIXME には日付とイニシャルを添える：`// TODO(2026-04-12 CDO): キャッシュ戦略を見直す`

## テスト方針

- 新規機能はユニットテスト必須
- 既存コードの修正は該当テストの更新必須
- モック化は境界（外部 API・DB）のみ
- `describe` は「何をテストするか」、`it` は「どう動くか」

## Git ワークフロー

- ブランチ命名：`feat/...` `fix/...` `chore/...` `refactor/...`
- コミットメッセージ：Conventional Commits（`feat:` `fix:` 等）
- PR 前にローカルで `pnpm lint && pnpm test && pnpm build` を通す
- main への直接 push 禁止

## フォルダ構造（推奨）

```
project/
├── CLAUDE.md
├── src/
│   ├── app/          ← Next.js App Router
│   ├── components/   ← React コンポーネント
│   ├── lib/          ← ユーティリティ
│   ├── db/           ← DB スキーマ・クエリ
│   └── types/        ← 型定義
├── tests/
└── .env.example
```

## セキュリティチェック（各実装後）

- [ ] ユーザー入力のバリデーション済
- [ ] SQL インジェクション対策（パラメータ化クエリ）
- [ ] XSS 対策（React のエスケープに依存、`dangerouslySetInnerHTML` 禁止）
- [ ] 認証・認可チェック
- [ ] レート制限
- [ ] CSRF 対策

## エラーハンドリング方針

- ユーザー向けエラー：理解しやすい日本語
- 開発者向けログ：スタックトレース＋コンテキスト
- 外部 API エラー：リトライ回数を明示
- 500 エラー：Sentry などに自動送信
