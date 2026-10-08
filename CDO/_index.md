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
| 2026-07-01 | outputs/note_publisher/check_thumbnail_coverage.py, 2026-07-01_サムネ監視_運用手順.md | 監視/運用 | サムネ取りこぼし監視の定例化。記事×thumbnails/*.jpg×_provenance.json(GOOD_BACKENDS)を突合し未取得一覧と充足率を出す読み取り専用スクリプト(依存ゼロ・ネット不要)＋週1/記事追加後にnote-thumbnails.ymlをworkflow_dispatch再実行で自己修復する手順。初回集計=144本中104本(72.2%) | 完了 |
| 2026-06-29 | 2026-06-29_note記事_検索最適化チェックリスト.md | 書式/ガイド | 今後のnote記事を最初から検索最適化で作る恒久標準（タイトル/冒頭/見出し/タグ/回遊/英語/事実検証）。過去記事手編集に頼らず新規が放置で流入を取る。L1標準化版 | 完了 |
| 2026-05-28 | outputs/note_publisher/ | 自動化ツール | note自動公開ヘルパー(Playwright・柱Dと同じ初回ログインのみ手動モデル)。オーナーのMacで実行 | MVP完成 |
| 2026-06-23 | apps/invoice-generator/index.html, README.md | Webツール | 依存ゼロ単一HTMLの請求書ジェネレーター(localStorage保存・印刷PDF・インボイス注記・商品リンク/ad slot)。GitHub Pages公開可。検索流入×テンプレ商品の相互送客フック付き | 完成 |

## 進行中タスク

- note_publisher: 初回運用後にUIセレクタ調整が必要な可能性（noteのDOM変更追従）

| 2026-08-21 | site_audit/audit_pages.py (+README) | ツール/監査 | 「能力向上」→Pages発見インフラを1コマンドで機械監査する常設ツールを新設(ゼロ依存・exit code対応・CIゲート化可)。sitemap網羅/リンク切れ/hreflang(x-default)/孤立/アセット実在の6項目。初回実行で10ページのx-default欠落を検知→修正しerrors=0。競合回避でnote_publisher外の新レーンに配置 | 運用中 |

| 2026-08-21 | site_audit: --fix + site-audit.yml | 自動化/自己修復 | owner「なぜ自動で直さないのか」→検知だけでなく自動修復を実装。--fix(x-default補完・トップへの非相互hreflang削除・idempotent)＋CIワークフローでpush毎に自己修復しbotがcommit。残56件の非相互を自動解消(warnings56→0)。機械で直せない致命的欠陥のみjob失敗で可視化 | 運用中 |
| 2026-09-30 | ops/inline_english.py, note_publisher/append_english.py, ops/backfill_english.sh, ops/build_english_todo.py | 到達修復/検査 | オーナー「記事の閲覧が伸び悩み」→数えて発見＝**英語要約が公開本文に1文字も入っていなかった**。publisher は `## 本文` 直下のブロックだけを note に貼るのに、英語要約はブロックの外に書いていた（9/1以降60本全滅・累計141本）。md 141本を本文ブロックへ移し、公開済み96本は**全置換せず末尾に足す**append_english.py を新設（全置換だと本文中の写真が消える）。go.sh 3.5) に組み込み8本/回で自動消化。R36 で再発を監視（窓なし・370本OK） | 運用中 |
| 2026-10-08 | note_publisher/fetch_note_comments.py（修正） | バグ修正/診断 | `ops/comments_now.sh`（`--rescan --limit 0`＝244本を間隔なし連続goto）の結果を見て発見＝保存されていた--debug HTML 75件中**61件がCloudFrontの403 Request blocked**だった。この遮断ページの`<title>`はnoteの殻タイトルと一致しないため「描画された」と誤判定され、本文ゼロのままextract_commentsに渡って**「セレクタ外れ」として誤報告**されていた（今回の22件もほぼこれ）。→ 遮断ページを専用に検出し、検出したら巡回を即打ち切り（セレクタ外れに混ぜない）／goto間に1.2秒の間隔を追加。あわせて、コメント本文API(`fetch_comments_via_api`)が4エンドポイント全滅(200/total_count:0)だった5記事を調査→埋め込みデータに**数値のnoteId**（alnumのnote_keyとは別物）が同じ記事ブロック内にあると判明、API候補に数値ID版を追加（**未検証＝codeはA1でnote.comを呼べないため、cowork側の次回実行で確認要**） | 要検証 |
| 2026-10-08 | ops/check_requirements.py（修正）, CMO/outputs/2026-10-08_note記事_届いていなかった_234本の裏側.md | バグ修正/検査 | R17(文体の反復)が「直近10日28本すべてが同じ締めの骨格」という意味のない1件を出していたので検算→**二重のバグ**が原因だった。①`_jp_body`が本文ブロック全体（フォロー導線＋Englishまで）を読んでおり、R36移行後は最終段落が常に英語になる。日本語キープリストの正規表現が英語を「◯」1字に潰すため**全記事が同じ骨格に収束**していた→最初の「――」区切りより前だけを見るよう修正。②`_en_summary`が旧「## English Summary」（ブロック外）を探したままで、R36移行後は**常にNoneを返し続けていた**＝CQOが追加した英語側の反復検知(_seen_en/_EN_PHRASES)がR36移行以来ずっと死んでいた。→ 本文ブロック内の`【English】`見出し以降を読むよう修正。直したら**本物の反復が出た**＝3記事が英語要約を"I live in Takaoka, in Toyama,..."で始めていた（2本は公開済みで直せない、1本(届いていなかった)は未公開だったので書き換えてbody_stats.py --syncで字数メタを同期）。③修正の副作用で`_has_unpublished`の既存バグも表に出た＝EN側の反復は記事名に`(EN)`を付けて積むが、比較時に外していなかったため**公開済み記事も毎回「未公開」と誤判定**（これも`_en`が空だった間は実行されず隠れていた）。3つとも「作ったが実際には一度も動いていなかった」型 | 完了 |

## メモ・引き継ぎ事項

- note_publisherはCMO/outputs/の最新記事を自動選択。写真は ~/Pictures/note/YYYY-MM-DD/photo_NN.jpg 命名規則。

## 2026-09-23 能力開発（オーナー指示「各役員は能力開発して」）

- `.claude/agents/cdo.md` に能力開発2件を追記（**黙って失敗する書き方の目録5種**＝tee が終了コードを飲む／`$VAR`＋全角で変数名が吸収される／環境パスの決め打ち／cron の PATH／末尾改行なしの追記。＋**他人のUIを自動化するときの作法4点**＝probe先行・範囲を特定してから読む・読めなければNone・クラス名変化のフォールバック）
