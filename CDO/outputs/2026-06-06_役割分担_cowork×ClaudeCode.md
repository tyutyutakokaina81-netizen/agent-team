# 役割分担の最適化：cowork（執筆）× Claude Code（整合・最適化）

- **日付**: 2026-06-06
- **作成**: CDO（役職管理）／Claude Code セッション
- **目的**: 2エージェント並行運用での役割を最適化し、重複作業とマージ衝突をゼロにする
- **合意の場**: PR #12（連携チャネル）

---

## 1. 基本原則：「生成」と「検品」を分離する

> cowork ＝ **生成エンジン**（記事を作る）
> Claude Code ＝ **品質・整合・最適化レイヤー**（届く形に仕上げる）

二者が**同じファイルを同時に書かない**ように責務を分けることで、衝突を構造的に防ぐ。
すべての判断基準は **North Star＝海外の人に読んでもらうこと**。

---

## 2. 記事1本のライフサイクル（パイプライン）

| # | 工程 | 担当 | 出力先 |
|---|------|------|--------|
| 1 | 企画・ネタ出し（context/ideas・CAO仮説を参照） | **cowork** | （頭の中／下書き） |
| 2 | 執筆：本文＋一次英語要約＋事実検証ノート草案 | **cowork** | `CMO/outputs/YYYY-MM-DD_*.md`（新規） |
| 3 | 検品：重複・テンプレ感・誇張・PII・品質基準チェック | **Claude Code** | 同ファイルのメタ部を修正／差し戻し |
| 4 | 海外導線の標準化（英語サブタイトル・統一ハッシュタグ・Travel CTA・ローマ字+英訳） | **Claude Code** | 全記事へ横断sweep |
| 5 | スケジューリング（5本/日・食2本・カテゴリ分散・曜日最適） | **Claude Code**（CAO機能） | ファイル日付・STATE |
| 6 | 台帳同期 | **Claude Code** | `CMO/_index.md`（正本） |
| 7 | 状態記録 | **Claude Code** | `context/STATE.md` |
| 8 | 公開（実写写真の付与含む） | **オーナー**（Mac・手動） | note |

ポイント：**本文（工程2）は cowork だけが書く。メタ・導線・台帳（工程3〜7）は Claude Code だけが書く。**
工程2と工程3で同じファイルを触るが、**書く場所が違う**（本文 vs メタ/導線）。意味の変更が要るときは Claude Code が本文を直さず、PRコメントで cowork に差し戻す。

---

## 3. ファイル所有マトリクス（衝突回避の肝）

| パス | 正本 | 書き込み可 |
|------|------|-----------|
| `CMO/outputs/` 記事本文 | cowork | cowork（新規・本文）／ Claude Code（メタ・導線・日付） |
| `CMO/_index.md`（台帳） | **Claude Code** | Claude Code のみ（実ファイル走査で再生成可） |
| `context/STATE.md` | 共有 | 両者（**手動マージ・決定ログ追記式・消さない**） |
| `EN/`・海外導線テンプレ | Claude Code | Claude Code |
| `CAO/`（分析・選定） | Claude Code | Claude Code |
| 新ツール・スクリプト | 作った側 | `claude/feat-*` または `cowork/*` ブランチ |
| `company.md`・`CLAUDE.md`（ルール） | オーナー | **変更はオーナー承認必須** |

---

## 4. ブランチ運用

| 用途 | ブランチ | PR |
|------|----------|-----|
| Claude Code の整理・検品・横展開 | `claude/optimistic-gates-oqMRK`（積み増し） | #12（連携チャネル・常駐） |
| cowork の執筆 | `cowork/articles-YYYY-MM-DD` | 都度 or まとめて |
| 大規模リファクタ(10ファイル超) | `claude/refactor-<topic>` | 別PR |
| 新ツール | `claude/feat-<name>` / `cowork/feat-<name>` | 別PR |
| 公開系の破壊的変更 | `claude/breaking-<area>` | 別PR |
| 実験(main非マージ前提) | `claude/exp-<topic>` | 別PR |

---

## 5. 受け渡しプロトコル（ハンドオフ）

1. **cowork → Claude Code**：執筆完了後、PR #12 にコメント
   例：「6/14 を5本に揃えた。`cowork/articles-2026-06-14` に push。検品お願い」
2. **Claude Code**：検品 → 海外導線標準化 → スケジューリング → 台帳同期 → このブランチに commit、結果をPRにコメント
3. **台帳は cowork が触らない**（Claude Code に委ねる）。cowork が `CMO/_index.md` を編集した場合は Claude Code が再生成で上書きする。

---

## 6. 意思決定権（RACI簡易）

| 決定事項 | 決定者 | 補足 |
|----------|--------|------|
| 記事のテーマ・本文・角度 | cowork | 品質基準は遵守 |
| 公開順・5本構成・カテゴリ配分 | Claude Code | CAO機能 |
| 重複時の取捨・再配置 | Claude Code が判定 | ただし**ファイル削除はオーナー承認**（再配置=承認不要） |
| 海外導線の様式（タグ/CTA/英訳） | Claude Code | North Star直結 |
| ルール変更（company.md/CLAUDE.md） | オーナー | 承認必須 |
| 有料化・アフィリエイト等の収益施策 | オーナー＋CPO/CAO | 海外導線が育つまで保留 |

---

## 7. 衝突解決ルール

- `CMO/_index.md`：**Claude Code の実ファイル走査による再生成が正**。
- `context/STATE.md`：**両者の変更を手動マージ**。決定ログは追記式で消さない。
- 同一記事ファイルの二重編集：cowork=本文、Claude Code=メタ/導線で**領域分離**。本文の意味変更が要る検品指摘は、Claude Code が直接直さず PR コメントで cowork に差し戻す。

---

## 8. 確認したい境界（オーナー／cowork へ）

- **英語要約**：一次作成は cowork（記事ごとに別パターン＝制約A6）、Claude Code は様式の標準化と多様性チェックのみ、という分担でよいか。
- **スケジューリング**：公開順・5本構成の決定を Claude Code（CAO機能）に集約してよいか。
- 上記に異論があれば PR #12 にコメントで調整する。
