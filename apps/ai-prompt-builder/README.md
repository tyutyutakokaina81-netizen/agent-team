# AIプロンプト・ビルダー / AI Prompt Builder

用途と条件を選ぶだけで、整ったAIプロンプト文を組み立てる**単一ファイルのWebツール**。
依存ゼロ・外部API不要・APIキー不要・完全クライアントサイドで動く。GitHub Pages 等にそのまま置ける。

A single-file web tool that assembles a clean AI prompt from a purpose and a few conditions.
Zero dependencies, no external API, no API key, fully client-side. Drop it on GitHub Pages as-is.

---

## ファイル構成

```
apps/ai-prompt-builder/
├── index.html   ← これ1枚で完結（HTML + CSS + JS）
└── README.md    ← このファイル
```

## 機能

- **用途を選ぶ**：メール / 記事・ブログ / 要約 / 翻訳 / コード生成 / コード説明・修正 / SNS投稿 / アイデア出し / リライト / 計画づくり / 自由入力
- **条件を指定**：トーン・長さ・対象読者・出力言語・制約（箇条書き／番号付き手順／専門用語回避／具体例／表／根拠提示／タイトル案／絵文字なし）＋追加指示
- **テンプレ内蔵**：お礼メール / ブログ記事 / 要約 / 翻訳 / コード生成 / SNS投稿 をワンクリックで前入力
- **整ったプロンプトを生成**してコピー（クリップボード API、非対応環境は自動フォールバック）
- **履歴を localStorage に保存**（最大30件・端末内のみ・クリック復元・全消去可）
- **日本語／英語のUI切替**（選択状態は維持。設定は localStorage に記憶）
- **スマホ対応**（2カラム→1カラムへ自動切替）・軽量（外部読み込みゼロ）

## 使い方

1. `index.html` をブラウザで開く（ダブルクリックでOK。サーバー不要）。
2. 左側で用途・お題・条件を選ぶ（またはテンプレをクリック）。
3. 「プロンプト生成」→ 右側に整ったプロンプトが出る → 「コピー」。
4. 生成したプロンプトを ChatGPT / Claude / Gemini など好きなAIに貼って使う。
5. 気に入ったら「履歴に保存」。

> ⚠️ このツールが作るのは「**プロンプト文**」であって最終成果物ではありません。
> AIの出力は**必ず人が内容を確認**してから使ってください。
> 氏名・住所・連絡先などの**個人情報はプロンプトに入れない**でください。

## 公開手順（GitHub Pages）

このリポジトリは既に Pages 運用があるため、最も簡単なのは2通り。

**A. 専用 Pages として出す場合**
1. リポジトリ Settings → Pages → Source を「Deploy from a branch」。
2. Branch を `main`、フォルダを `/ (root)` か、必要なら `/docs` 等へ配置。
3. `apps/ai-prompt-builder/index.html` の URL（例 `https://<user>.github.io/<repo>/apps/ai-prompt-builder/`）で公開される。

**B. 単独で出す場合**
- `index.html` を任意の静的ホスティング（Pages / Netlify / Cloudflare Pages 等）のルートに置くだけ。ビルド不要。

> 既存の `pages.yml` は `tavern.html` を `_site/index.html` にデプロイする設定です。
> このツールを既存 Pages と同時に出したい場合は、`_site/` に `apps/ai-prompt-builder/` をコピーするステップを足すか、上記Aのブランチ配信に切り替えてください（運用ポリシーは code が判断）。

## 収益化メモ（控えめ設計）

- **商品リンク**：本文下部のプロモ枠に `【商品リンク】` プレースホルダを設置済み。
  公開前に「AIプロンプト集（30本）」の販売URL（note / BOOTH 等）へ置換する。
  - 置換箇所：`index.html` 内の `href="【商品リンク】"`（1箇所）。
- **広告枠**：`<!-- ad slot -->` を1箇所だけ用意（点線枠）。
  アドネットワークや自社バナーを入れる場合はこの `div.ad` を差し替える。
- 過度な広告は離脱の原因になるため、枠は**プロモ1＋広告1**に絞っている。

## 集客との連動

- AIニッチ（"AI prompt builder" / "プロンプト 作成 ツール" 等）は検索・SNS流入が見込めるロングテール。
- ツール末尾のプロモから自社の**AIプロンプト集（30本）**へ送客 → 相互送客で商品認知を取る。
- note記事やX投稿から本ツールへリンクし、ツール → 商品の二段導線にできる。

## 安全・コンプライアンス

- 外部送信なし・トラッキングなし（広告枠を埋めるまでは完全オフライン動作）。
- 入力は localStorage（端末内）のみに保存。サーバーへ送らない。
- 文言は誇張表現を避け（「世界唯一」等は不使用）、PII を入力しない注意書きを常時表示。

## カスタマイズ

- 用途・トーン・長さ・制約・テンプレは `index.html` 先頭の
  `PURPOSES / TONES / LENGTHS / OUTLANGS / CONSTRAINTS / TEMPLATES` 配列を編集するだけで増減できる（各ラベルは `{ja, en}` 形式）。
- プロンプトの組み立てロジックは `buildPrompt()` 関数を編集する。
- 配色は `:root` の CSS 変数で一括変更できる。
