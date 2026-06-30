# 保守ランブック（note / サムネ / ワークフロー）

note記事・サムネイル・GitHub Actions の保守と障害対応の手順書。
**事実ベース**（実コード/ワークフローを読んで記載）。憶測は書かない。

> 関連: `CLAUDE.md`（運用ルール・絶対制約 A1〜A7）/ `AGENTS.md`（North Star・分業）/
> `.github/workflows/`（CI 実体）/ `CDO/outputs/note_publisher/`（サムネ生成）/ `tools/`（検証）

---

## 0. 前提（A1 の壁）

| 主体 | できること |
|------|-----------|
| **code（Claude Code）** | 記事執筆・整理・検証スクリプト実行（ローカル）・台帳/STATE 管理・git/PR。**外部ネットは A1 で全遮断** |
| **GitHub Actions（クラウド）** | ネット可。サムネ生成・写真取得・Pages デプロイ・IndexNow 通知。**A1 と無関係に動く** |
| **cowork / owner** | ブラウザ・セッション認証が要る作業（note 本体への反映＝後述 §5） |

サムネ生成・写真取得・検索通知は **全部クラウド側**で完結する。code は記事 md を main に push するだけでよい。

---

## 1. サムネ生成パイプライン

### 構成（`.github/workflows/note-thumbnails.yml`）

```
push CMO/outputs/** または 手動 workflow_dispatch
  └─ Step1: generate_thumbnails.py        … AI生成（Pollinations / Gemini / OpenAI）
  └─ Step2: fetch_note_thumbnails.py      … PEXELS_API_KEY があるときだけ、不足分をフリー写真で補完
  └─ Step3:（Picsum ランダム画像フォールバックは廃止＝無関係サムネは付けない）
  └─ Commit: git add -f thumbnails/*.jpg と _provenance.json → commit → push
```

### 画像ソースの優先順（`generate_thumbnails.py` `pick_backend()`）

| 優先 | バックエンド | 条件 | 備考 |
|------|------------|------|------|
| 1 | OpenAI gpt-image-1 | `OPENAI_API_KEY` あり | 高品質・要課金。現状未設定の想定 |
| 2 | Gemini Imagen 3 | `GEMINI_API_KEY` あり | Google AI Studio 無料枠・16:9・人物生成禁止 |
| 3 | **Pollinations (FLUX)** | キー不要（既定） | 無料。レート制限/タイムアウトあり → 3回リトライ＋画像5KB未満は失敗扱い |
| 4 | Pexels フリー写真 | `PEXELS_API_KEY` あり | Step2 で AI が埋めなかった分のみ補完 |

> backend は記事ごとに切り替わらず**実行全体で1つ**（環境変数で決まる）。キーがある最上位が選ばれる。

### `_provenance.json` の役割（自己修復の心臓部）

- 場所: `CDO/outputs/note_publisher/thumbnails/_provenance.json`
- 中身: `{ "記事stem": "backend名" }`。`backend` が生成成功するたびに**都度保存**（途中失敗でも進捗が残る）。
- 「良い素性」= `GOOD_BACKENDS = {openai, gemini, pollinations}`。
- スキップ判定: 既存 `.jpg` があっても **provenance に GOOD で記録されていなければ再生成対象**にする
  （過去の picsum 等の**素性不明＝無関係サムネを1回だけ関連画像に置き換える**＝自己修復）。
- ⇒ 生成失敗した記事は provenance に載らない → **次回トリガーで自動的に再挑戦**される。

### thumbnails が gitignore でも永続する仕組み

- `.gitignore` に `CDO/outputs/note_publisher/thumbnails/` あり（=通常 add されない）。
- ワークフロー Commit ステップが `git add -f`（force）で `thumbnails/*.jpg` と `_provenance.json` を**強制追加**してコミット。
- bot のコミットは `thumbnails/` のみ触る → `note-thumbnails.yml` の paths に thumbnails は含まれない → **push ループにならない**。

### プロンプト抽出（`extract_thumb_prompt()`）

記事 md の `## サムネ用プロンプト` 見出し直後の **```コードブロック```** を抽出。
無ければ本文中の `Photorealistic` を含むコードブロックをフォールバック抽出。
**どちらも無いとサムネは生成されない**（§2-③で確認する）。

---

## 2. 障害切り分け：「サムネが生成されない / 無関係な画像が付く」

| 手順 | 確認内容 | 方法 |
|------|---------|------|
| ① ワークフロー run ログ | `対象: N本（うち素性不明の再生成: M本）` と `成功: ok / 失敗: fail` | Actions → "Generate note thumbnails" → 該当 run。`対象 0本`＝抽出失敗 or 全件 provenance 済み |
| ② API キー | `GEMINI_API_KEY` / `PEXELS_API_KEY` の有無 | Settings → Secrets and variables → Actions。無くても Pollinations で動くが、品質/補完は落ちる |
| ③ プロンプト抽出可否 | 記事に `## サムネ用プロンプト`＋```ブロックがあるか | 下記「検証コマンド」。抽出不可なら**記事側を修正**（code 作業） |
| ④ provenance 確認 | 無関係サムネが残る＝素性不明が GOOD で誤記録、または再生成失敗 | `thumbnails/_provenance.json` を見て、当該 stem の値が `picsum` 等でないか／そもそも載っているか |

### 検証コマンド（ローカル・ネット不要）

```bash
# 対象記事に対する抽出ドライラン（何本が対象になるか・実生成はしない）
cd CDO/outputs/note_publisher
python3 generate_thumbnails.py --dry-run --filter 2026-06-27

# provenance の中身を確認
cat CDO/outputs/note_publisher/thumbnails/_provenance.json
```

> Step1 はキー無し環境でも `--dry-run` で「対象N本」を確認できる（実生成は Pollinations へ出るので dry-run 推奨）。

---

## 3. 記事の必須要素

「実行して」プロトコル（`CLAUDE.md`）の完成稿が満たすべき構造。実例: `CMO/outputs/2026-06-27_note記事_土曜朝の市場散歩.md`。

| 要素 | 書式 | 役割 |
|------|------|------|
| タイトル | `## タイトル` + ```ブロック``` | note タイトル欄に貼る |
| 本文 | `## 本文` + ```ブロック``` | `[写真①〜③]` placeholder を本文中に配置（A3：実写は code 生成不可） |
| 英語要約 | `🌏 For English readers`（本文末） | 海外読者向け（A6：同パターン2連続禁止） |
| 回遊フッター | `▼ あわせて読む` + 過去記事リンク + スキ/フォロー誘導 | 既存記事への回遊。`CDO/outputs/note_footer/` で管理 |
| ハッシュタグ | `## ハッシュタグ` + ```ブロック``` | 日本語＋英語タグ |
| 事実検証ノート | `## 事実検証ノート`（✅確実 / ⚠️要確認 / 諸説あり） | A5 担保。必須 |
| **サムネ用プロンプト** | `## サムネ用プロンプト` + ```ブロック``` | §1 の抽出対象。**無いとサムネが生成されない** |
| 本文中の写真リスト | `## 本文中の写真` + `[写真X]` ごとのみんフォト検索語＋実写プロンプト | cowork/owner が note 本体に挿入する指示 |

### 検証コマンド（A4/A5 自動チェック・`tools/quality_check.py`）

> 注: `validate_note_articles.py` は存在しない。記事規則の検証は `quality_check.py` が実体。

```bash
# 社内原稿としての検査（MIX は SOFT）
python3 tools/quality_check.py CMO/outputs/2026-06-27_*.md

# 読者に出す誌面の厳格検査（サムネ/```/¥980 等の混入を HARD 扱い）
python3 tools/quality_check.py --reader <誌面.md>

# 違反のみ表示
python3 tools/quality_check.py --quiet CMO/outputs/*.md
```

検出: `[A5-HARD]`世界唯一/日本一 等（終了コード1）/ `[A5-SOFT]`必ず/絶対 等 / `[MIX]`社内痕跡 / `[PII]`既知の要伏字店名。
HARD が1件でもあれば終了コード1（CI/コミット前ゲートに使える）。

クロスポスト素材生成（Reddit/X/EN）: `python3 CDO/outputs/cross_post/gen_all.py --article <path>`。

---

## 4. 公開系ワークフロー一覧

| ワークフロー | トリガ | 役割 | 出力先 | キー/権限 |
|------------|--------|------|--------|----------|
| `pages.yml` | push main / 手動 | HP・ダッシュボード・富山ガイド・ブログ・無料ツールを GitHub Pages にビルド配信 | `_site/`（GitHub Pages） | `pages: write`, `id-token: write` |
| `note-thumbnails.yml` | push `CMO/outputs/**` / 手動 | note サムネを AI(Pollinations/Gemini)→Pexels で生成、`git add -f` でコミット | `CDO/outputs/note_publisher/thumbnails/` | `contents: write`、`GEMINI_API_KEY`/`PEXELS_API_KEY`（任意） |
| `toyama-photos.yml` | push `apps/toyama-guide/**.html` / 手動 | 富山ガイド各記事に内容に応じた Pexels フリー写真を挿入（不足分のみ） | `apps/toyama-guide/photos/` ＋ html | `contents: write`、`PEXELS_API_KEY`（**必須**・無いとスキップ） |
| `indexnow.yml` | push `apps/ai-agency-hp/**`・`apps/toyama-guide/**` / 毎週月 0:00 UTC / 手動 | sitemap.xml の URL を IndexNow（Bing/Yandex 等）へ通知。Google は非対応 | 外部 API（api.indexnow.org） | `contents: read`（キー不要・key 内蔵） |

共通: いずれも `concurrency` で多重実行を防止（`cancel-in-progress: false`）。

---

## 5. A1 の壁：note 本体への反映は code 不可

以下は **ブラウザ操作・note セッション認証が必要**で、code（A1 遮断）では実行できない。**cowork / owner の作業**。

| 作業 | 担当 | 備考 |
|------|------|------|
| 本文中への写真挿入（`[写真X]` の置換） | cowork/owner | §3 の「本文中の写真リスト」を指示として使う |
| 見出し画像（サムネ）の設定 | cowork/owner | `thumbnails/{stem}.jpg`（クラウド生成済み）を note に設定 |
| タイトル編集・記事の公開 | cowork/owner | `publish_to_note.py` 等（CLAUDE.md「公開」表）。安全ガードあり |

### 発注は `ops/inbox`

code → cowork の指示は `ops/` ファイルキューで出す（git に乗る）。

```bash
python3 ops/process_inbox.py post --from code --to cowork --type instruction \
  --title "..." --body "..."
```

ファイル名 `YYYY-MM-DD_NNN_<from>_<to>.yaml`。inbox=code→cowork、outbox=cowork→code、完了は processed/ へ move。
実例: `ops/inbox/2026-06-09_001_code_worker.yaml`（画像生成ワーカーへのサムネ発注）。

---

## 6. 復旧 早見表（症状 → 原因候補 → 対処）

| 症状 | 原因候補 | 対処 |
|------|---------|------|
| サムネが1枚も増えない | run ログ `対象 0本`＝全件 provenance 済み or 抽出失敗 | `--dry-run` で対象本数確認。0なら記事の `## サムネ用プロンプト` 有無を確認 |
| 特定記事だけサムネ無し | 記事に `## サムネ用プロンプト`＋```ブロックが無い | 記事側にプロンプトブロックを追加（code 作業）→ push で再トリガ |
| サムネが内容と無関係 | 過去の picsum 等が残存（素性不明） | provenance に GOOD 記録が無ければ次回 run で自動置換。手動なら `--force` で再生成 |
| 生成は走るが全失敗 | Pollinations のレート制限/タイムアウト、または 5KB 未満 | run を再実行（リトライ込み）。安定させたいなら `GEMINI_API_KEY` を Secrets に登録 |
| Pexels 補完が走らない | `PEXELS_API_KEY` 未設定 | Secrets に登録（無くても Pollinations で生成自体は動く） |
| 富山ガイドに写真が入らない | `toyama-photos.yml` は PEXELS_API_KEY 必須・無いとスキップ | Secrets に `PEXELS_API_KEY` を登録 |
| サムネ commit がループする | 通常は起きない（thumbnails は paths 対象外） | ワークフロー paths と「bot は thumbnails/ のみ触る」設計を確認 |
| Pages が古い/404 | `pages.yml` のビルドが該当ファイルを cp していない | `pages.yml` の Build site ステップに対象パスがあるか確認 |
| 検索エンジンに反映されない | IndexNow は Bing/Yandex 等のみ（Google 非対応） | Google は Search Console 登録が別途必要（`indexnow.yml` 冒頭コメント参照） |
| 記事に禁止語/混入物 | A5-HARD / MIX / PII | `python3 tools/quality_check.py --reader <file>` で検出して是正 |

---

## 7. 関連ファイル早見

| 用途 | パス |
|------|------|
| サムネ AI 生成（優先順・provenance 自己修復） | `CDO/outputs/note_publisher/generate_thumbnails.py` |
| サムネ Pexels 補完 | `CDO/outputs/note_publisher/fetch_note_thumbnails.py` |
| provenance（素性記録） | `CDO/outputs/note_publisher/thumbnails/_provenance.json` |
| 記事 A4/A5 検証 | `tools/quality_check.py` |
| クロスポスト一括生成 | `CDO/outputs/cross_post/gen_all.py` |
| 回遊フッター | `CDO/outputs/note_footer/` |
| code↔cowork キュー | `ops/process_inbox.py`、`ops/inbox/`、`ops/outbox/` |
| CI 実体 | `.github/workflows/{pages,note-thumbnails,toyama-photos,indexnow}.yml` |
</content>
</invoke>
