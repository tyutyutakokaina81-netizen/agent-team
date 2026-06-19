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
| 2026-06-19 | ops/cowork_run.sh, ops/install_publish_schedule.sh | 自動化設定 | 日次自動公開を「安全ゲート付き」で設定。①本番公開ゲート（ops/PUBLISH_ENABLED無ければ--draft）②未来日付スキップ③冪等化。既定は本番公開OFF。launchd毎朝08:00。導入はオーナーがMacで実行 | 完了 |
| 2026-06-20 | outputs/note_publisher/note_cleanup_all.py | 新ツール（一括） | 自己完結・1コマンドで掃除準備を全部実行：note一覧取得→重複検出→台帳突合→reconcile_report.md＋manifest出力。cwd非依存。--note-export で手動一覧フォールバック可。オフライン経路E2E検証OK（重複/孤児/未公開/manifest全て正） | 完了 |
| 2026-06-20 | outputs/note_publisher/export_note_list.py | 新ツール | 掃除の入口。ログイン済みChromeプロファイルでnote記事一覧を自動スクロール取得→TSV(note_id+title)化。reconcile_ledger.pyの入力を手コピペ無しで生成。note_id抽出ロジック検証ALL PASS（DOM依存部はMac実機で要確認） | 完了 |
| 2026-06-20 | outputs/note_publisher/reconcile_ledger.py | 新ツール | 再開条件①②支援。note公開一覧（TSV/タイトル）を入力に「重複タイトル検出／note↔ソース突合（公開済・未公開・出所不明）／manifest自動生成」を行う。依存ゼロ。合成データ検証OK（重複/孤児/未公開を正しく分類） | 完了 |
| 2026-06-20 | outputs/note_publisher/publish_to_note.py + published_titles_manifest.txt | ツール強化 | 再開条件③を充足。タイトル完全一致の冪等ガードを追加（別ファイル/別日付でも同タイトルなら公開ブロック・--forceで解除）。照合元=published_log.tsv＋published_titles_manifest.txt（note実態タイトルをMac側で維持）。6/14重複インシデント再発防止。単体検証ALL PASS | 完了 |
| 2026-06-19 | outputs/note_publisher/publish_to_note.py | ツール強化 | 閲覧数回復策の一環。未来日付ガード（未来日付記事の自動公開を既定で禁止・--allow-futureで解除）＋冪等化（published_log.tsvで二重公開防止・--forceで解除）を実装。6/12インシデント再発防止＝再開条件②を充足 | 完了 |
| 2026-05-28 | outputs/note_publisher/ | 自動化ツール | note自動公開ヘルパー(Playwright・柱Dと同じ初回ログインのみ手動モデル)。オーナーのMacで実行 | MVP完成 |

## 進行中タスク

- note_publisher: 初回運用後にUIセレクタ調整が必要な可能性（noteのDOM変更追従）

## メモ・引き継ぎ事項

- note_publisherはCMO/outputs/の最新記事を自動選択。写真は ~/Pictures/note/YYYY-MM-DD/photo_NN.jpg 命名規則。
