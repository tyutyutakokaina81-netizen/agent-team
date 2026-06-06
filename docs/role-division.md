# Claude Code（主）× cowork（副）役割分担

最終更新: 2026-06-07

## 位置づけ（オーナー確定 2026-06-06）

- **Claude Code = 主担当（primary）／オーナーの指示先**
  オーナーは**基本 Claude Code に直接指示を出す**。プロジェクトの実務を一手に担う：
  企画・執筆・整理・台帳・分析・重複監査・海外導線・git/PR・リポジトリ運営・
  公開パイプラインの「設計と判断」まで全部。
- **cowork = 副（sub・補助実行／クラウド処理担当）**
  Claude Code が物理的にできない「外部ネット／ブラウザ／セッション認証／定期実行／並列バッチ」など
  **クラウド処理が最適なタスクの"実行"だけ**を、Claude Code からの依頼に応じて代行する。
  コンテンツ・ファイルの所有や、公開可否・順序などの**判断はしない**。

> オーナー方針（2026-06-06）：「cowork はあくまでサブ。基本は code に指示。
> クラウド処理が最適なものだけ cowork。全部 Claude Code に引き継ぎ」。
> 旧案（PR #12 の「執筆=cowork」案、cowork の co-equal 案）はこの確定で上書き。

### 「全部引き継ぎ」の正確な意味（違和感の解消）

物理制約上、「全部」には1点だけ例外がある：

- **判断・制作は全部 Claude Code**（企画・執筆・整理・素材・公開可否や順序の判断）。
- **実行の最後の一歩（外部配信）だけは Claude Code にはできない** → cowork（or オーナー手動）。
- **配信は二段構え**：通常は cowork が実行、cowork が動けない時は**オーナーが `publish_to_note.py` で手動**。
  最重要工程（＝海外配信）を1点に依存させない。
- **記事をどこで作るかは問わない**（オーナーは結果＝海外読者を重視）。
  ただし**品質基準の遵守と `CMO/_index.md` の台帳整合は Claude Code が担保**する。

## なぜこの分担か（能力の事実）

- **Claude Code**：リポジトリ直アクセス／git・gh／コード実行／構造化読み書き／記事執筆の実績。
  **ただし外部ネット遮断（note 等 403）・ブラウザ不可・画像生成不可・定期実行不可。**
- **cowork**：ブラウザ自動化／セッション Cookie 保持／スケジューラ／並列実行が可能。
  → Claude Code の手が届かない「実行」だけを補助する。

判断基準はすべて **North Star＝海外の人に記事を読んでもらうこと**。

---

## 1. Claude Code（主）が担う＝原則すべて

- 企画・ネタ出し（`context/` 参照）
- **記事執筆（CMO 役職）**：本文・英語要約・事実検証ノート。`CMO/outputs/` の新規・追記
- 整理・重複監査・テンプレ感セルフチェック・整合性
- **海外導線（North Star 直結）**：英語サブタイトル・統一ハッシュタグ・Travel CTA・ローマ字+英訳。`EN/` 素材生成
- スケジューリング：5本/日・食2本・カテゴリ分散・曜日最適
- 台帳 `CMO/_index.md`（正本・実ファイル走査で再生成可）、各役職 `_index.md`
- `context/STATE.md` 等メモリファイル
- リポジトリ運営：`CLAUDE.md`/`company.md`/`.gitignore`/`prompt.md`/フック/ツール
  （`note_publisher`・`cross_post` 等の**コード正本**）
- git・PR・コメント・コンフリクト解消
- データ分析設計（CAO）：PV・国別・英語比率の集計設計（**生の数値取得は cowork が代行**して書き戻し）
- **公開パイプラインの設計と判断**：何を・いつ・どの順で公開するか。素材（記事・サムネ prompt・クロスポスト文）の用意

## 2. cowork（副）が担う＝Claude Code にできない「実行」だけ

依頼は `ops/inbox/` 経由。cowork は受けて実行し、結果を `ops/processed/` に書き戻す。

- **note.com への公開実行**（`publish_to_note.py` 相当）・サムネ後追い添付
- **X / Reddit 投稿**（`EN/outputs/` の素材を使用）
- アクセス解析画面の取得（PV・国別セッション・リファラ）→ リポジトリに書き戻し
- 定期実行（毎朝のモニタ等）・大量バッチの並列実行
- セッション認証が要る代理アクセス全般

### cowork がやらないこと（すべて Claude Code に投げる）

| やらない | 投げ先 |
|---|---|
| 記事本文の執筆 | Claude Code（CMO 役職） |
| ファイル・スクリプト生成 | Claude Code |
| `_index.md` の編集 | Claude Code（正本） |
| PR 作成・コメント・マージ | Claude Code |
| `context/STATE.md` の編集 | Claude Code |
| 公開可否・公開順・本数の判断 | Claude Code（cowork は実行のみ） |

---

## 3. 連携インターフェース：`ops/inbox/`（機械）＋ PR #12（人間議論）

```
ops/
├── inbox/            ← 未処理の依頼（YAML frontmatter + Markdown 本文）
├── processed/        ← 処理済み（消さず移動・結果サマリ追記）
├── process_inbox.py  ← 依存ゼロ CLI（list / show / take / done / post）
└── README.md         ← フォーマット仕様・CLI 使い方（正本）
```

- **フォーマットと CLI の詳細は `ops/README.md`**（cowork 実装を採用）。形式は **YAML frontmatter + Markdown 本文の `.yaml`**。
- 依頼: `python3 ops/process_inbox.py post --from code --to cowork --title ... --body ...`
- 受領→完了: `take <id>` → `done <id> --result "..."`（自動で `processed/` へ移動）
- **PR #12 コメント**：オーナー向け・方針議論／**`ops/inbox/`**：エージェント間の機械的な依頼・報告（主に主→副の実行依頼）

---

## 4. 衝突回避・所有ルール

| 領域 | 正本 | 編集可能 |
|---|---|---|
| `CMO/outputs/*.md`（記事本文） | Claude Code | Claude Code |
| `CMO/_index.md`（台帳） | **Claude Code** | Claude Code のみ（再生成可） |
| `context/STATE.md`（メモリ） | **Claude Code** | Claude Code（cowork は原則触らない） |
| `CDO/outputs/note_publisher/` 等ツール | Claude Code | Claude Code |
| `ops/inbox/`, `ops/processed/` | なし | 両方 |
| ブランチ命名 | - | `claude/*`=Claude Code（主）、`cowork/*`=cowork（副）。main 連携は Claude Code 主導 |

---

## 5. 公開フロー（主→副）＝ `drafts/` ステージング

詳細手順は `drafts/README.md`（正本）。要約：

1. **Claude Code**：執筆 → `CMO/outputs/` → 公開可否・順を判断 → `python3 drafts/stage_for_publish.py --date YYYY-MM-DD` で `drafts/queue/` へ staging
2. **Claude Code**：`ops/process_inbox.py post` で cowork へ公開依頼
3. **cowork**：`drafts/queue/*.md` を pickup → note 公開 → `drafts/published/` へ移動 → `ops/inbox/` に完了レポート
4. **Claude Code**：レポートを読み `CMO/_index.md` を「公開済」に更新

> 公開の最終 go/no-go はオーナー（外向き・センシティブ）。配信は二段構え（cowork／不調時オーナー手動 `publish_to_note.py`）。

---

## 6. 次のステップ

1. 本ドキュメントを正本化（`docs/role-division.md`）。旧案（CDO の役割分担メモ、cowork の co-equal 案）は本書に統合。
2. `ops/inbox/` は cowork 実装（CLI＋YAML）を採用。疎通は `sample-task.yaml` で確認可。
3. 2 週間運用し見直す（KPI：海外読者の流入、指示の取りこぼし数）。

> 関連：業務の全体引き継ぎは `docs/cowork-handoff.md`（オーナー情報・記事戦略・公開済み記事・アフィリ・残課題）。
