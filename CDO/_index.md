# CDO インデックス（技術責任者）

## 担当業務
- プロンプト作成・管理・改善
- Claude Code活用・自動化
- 技術検証・PoC
- ツール整備・ワークフロー改善
- 新役職フォルダの自動生成

> **ルール：** ファイルを作成・更新するたびに必ず下の成果物ログに追記すること。

## 成果物ログ

| 日付 | ファイル名 | 種別 | 概要 | ステータス |
|------|-----------|------|------|-----------|
| 2026-06-07 | docs/role-division.md | 役職管理 | 役割分担の正本。Claude Code=主(執筆含む全実務)／cowork=副(ネット/ブラウザ実行の代行)。ops/inbox連携・配信二段構え | 確定 |
| 2026-06-07 | ops/（process_inbox.py・README・inbox/processed） | 連携基盤 | code↔cowork 指示キュー。cowork実装(依存ゼロCLI・YAML)を吸収して一本化 | 運用 |
| 2026-06-07 | drafts/（stage_for_publish.py・queue・published・README） | 公開基盤 | CMO/outputs→queue→cowork公開→published。cowork実装を吸収 | 運用 |
| 2026-06-09 | outputs/2026-06-09_無料AIスカウトリスト.md | 役職管理 | ②無料連携できるAIを役割別にスカウト(Jules/Pollinations/DeepSeek/Perplexity)。商用可否を明示 | 提案 |
| 2026-06-09 | site/build.py 増強 | サイト基盤 | B:ハブ3(doraemon/kanazawa-day-trips/toyama-food) E:RSS+メールCTA D:多言語(越西)+hreflang C:収益CTA F:解析。SEO+回遊+収益+多言語化 | 運用 |
| 2026-06-09 | site/i18n/doraemon-hometown.pt.md | 多言語 | リード記事ポルトガル語版(ブラジル市場)。Genspark有料化により私が巻取り。6言語化(en/vi/es/zh/th/id/pt)→/pt/自動描画+hreflang | 運用 |
| 2026-06-09 | site/i18n/doraemon-hometown.{fr,de}.md | 多言語 | リード記事 仏・独版(Issue#14)。外部AI接続が各社ブラウザ認証で止まるため私が直接実行=ゼロ操作自動化。9言語化(+fr/de)→/fr//de/自動描画+hreflang | 運用 |
| 2026-06-09 | site/i18n/doraemon-hometown.{ko,it}.md | 多言語/自動化実証 | **Julesが自動生成→worker-integrateが許可領域検査→main自動マージ→自動公開**(完全自動ループ初成功)。10言語化(+ko/it) | 運用 |
| 2026-06-09 | site/i18n/doraemon-hometown.{hi,ar}.md + build.py RTL | 多言語 | ChatGPT組込(B型ペーストブリッジ)でヒンディー・アラビア語(印度・中東=ドラえもん巨大市場)。build.pyにRTL(ar/he/fa/ur=dir=rtl)追加。12言語化 | 運用 |
| 2026-06-09 | site/i18n/doraemon-hometown.{tl,ru}.md | 多言語 | Gemini組込(B型ペーストブリッジ)でフィリピン語・ロシア語(比=ドラえもん人気+訪日多/露=大規模)。14言語化 | 運用 |
| 2026-06-09 | site/i18n/doraemon-hometown.{tr,ms,fa,bn}.md | 多言語 | Issue#17 を code が直接巻取り(オーナー外出中)。トルコ・マレー・ペルシャ(RTL)・ベンガル語。18言語化 | 運用 |
| 2026-06-09 | outputs/2026-06-09_サムネ生成プロンプト集_写真風キャラ無し.md | サムネ運用 | AI生成OKサムネ(写真風/キャラ無し/商用OK)はAI生成運用に。カテゴリ別プロンプト9種+実写必須リスト。オーナー承認ルール | 運用 |
| 2026-06-07 | tools/audit_articles.py | 監査ツール | 記事の英語/PR表記/事実検証ノート/文字数を一括点検する依存ゼロCLI(--gaps/--overseas) | 運用 |
| 2026-06-07 | docs/cowork-handoff.md | 引き継ぎ | cowork→code 全業務引き継ぎ（オーナー情報・戦略・公開済み・アフィリ・残課題） | 受領・取込済 |
| 2026-06-07 | ops/（inbox/processed/README） | 連携基盤 | code↔cowork の機械向け指示チャネル。疎通テスト001投函済 | 運用開始（疎通確認中） |
| 2026-06-06 | outputs/2026-06-06_役割分担_cowork×ClaudeCode.md | 役職管理 | 旧案（生成=cowork/検品=code）。docs/role-division.md に統合・上書き | 統合済（残置） |
| 2026-05-28 | outputs/note_publisher/ | 自動化ツール | note自動公開ヘルパー(Playwright・柱Dと同じ初回ログインのみ手動モデル)。オーナーのMacで実行 | MVP完成 |

## 進行中タスク

- note_publisher: 初回運用後にUIセレクタ調整が必要な可能性（noteのDOM変更追従）

## メモ・引き継ぎ事項

- note_publisherはCMO/outputs/の最新記事を自動選択。写真は ~/Pictures/note/YYYY-MM-DD/photo_NN.jpg 命名規則。


## 能力向上ログ

| 日付 | 上げた能力 | 成果物 |
|------|-----------|--------|
| 2026-06-07 | 記事品質の自動監査 | tools/audit_articles.py（英語/PR表記/事実検証ノート/文字数を一括点検する依存ゼロCLI） |
| 2026-06-09 | 外部AIの安全な自動連携基盤を構築・実証 | worker-integrate.yml（許可領域検査→main自動統合の安全ゲート）＋Jules直接push型を実稼働（ko/it自動公開）＋docs/auto-ops.md（自動運用ループ正本） |
| 2026-06-09 | 多AIオーケストレーション＋サイト多言語化 | Jules/ChatGPT/Gemini を役割別に起用しサイトを14言語化（+RTL対応 ar/he/fa/ur）。docs/workers-connect.md（接続正本） |
