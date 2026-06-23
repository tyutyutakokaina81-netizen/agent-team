# F. B2Bリテーナー 納品自動化 — クライアント別 制作パイプライン

> 作成：CDO（自動化）2026-06-23
> 目的：A_高単価B2Bパッケージ（¥80K×4社で月商¥300K）の**納品をテンプレ化・自動化**し、
> **1社あたりの手間を最小化**する。社数が律速（A_§5）なので、社が増えても手数が線形に増えない仕組みを作る。
> 前提：依存ゼロ・外部ネット不可（A1）・画像生成不可（A2）。既存自動化＝
> `tools/quality_check.py`（A4/A5機械検査）/ `tools/jobs.py`（受託パイプライン）/
> `tools/make_epub.py` / `tools/collect_checks.py`（[要確認]集約）。
>
> ## 厳守（このファイルと全テンプレの前提）
> - **A4（PII禁止）**：clients/ には実名・住所・地区名・人名を書かない。業種カテゴリ・市レベルのみ。穴埋め〔　〕はオーナーが手元で記入し push しない。
> - **A5（成果保証NG）**：来客・予約・売上・検索順位の増加を約束しない。約束は「英語コンテンツ・導線を計画的に制作・運用し続ける」まで。
> - **顧客情報はコミットしない**：`clients/.gitignore` で `_template/` 以外を全除外（CFO/CSO outputs と同じ扱い）。

---

## 0. 結論（最初に）

- **作ったもの（本日・実働）**：
  1. **クライアント別フォルダ構造** `clients/<id>/{client.md, brief, style, monthly/, delivered/}` ＋ `.gitignore`（顧客情報は非コミット）＋ `_template/`（雛形一式）。
  2. **月次制作テンプレ4種**（英語記事 / 英語SNS / 英語サイト文 / 月次レポート）を `clients/_template/delivered_templates/` に配置。
  3. **リテーナー管理CLI** `tools/retainers.py`（jobs.py の発展形・依存ゼロ・テスト済み）。社別×月次サイクル×納品状況×継続課金(MRR)を1コマンドで管理。
  4. **quality_check 組み込み**：`retainers.py check` が当月成果物を `--reader` で一括検査（A4/A5ゲート）。クライアント別NG語は style.md の `ban_extra` で当てる。
- **効果**：1社の月次サイクルが「**起票→制作→機械検査→納品→請求→入金**」の6コマンドに収まる。社の状態把握は `retainers.py list` 1発（全社＋MRR＋黒字判定）。**社数が増えても管理コマンドは社あたり一定**＝A_の「社数が律速」を緩和する。

---

## 1. クライアント別フォルダ構造

```
clients/                         ← .gitignore で _template 以外を除外（顧客PII非コミット）
├── .gitignore                   ← */ を除外、_template/ README.md のみ追跡
├── README.md                    ← 運用早見表（追跡）
├── _template/                   ← 雛形一式（追跡）
│   ├── client.md                ← 社固定情報の雛形
│   ├── style/style.md           ← スタイルガイド雛形（ban_extra/tone）
│   └── delivered_templates/     ← 月次4種テンプレ（記事/SNS/サイト文/レポート）
│
└── <id>/                        ← 1社=1フォルダ（実体は非コミット）
    ├── client.md                ← plan/fee/status/since/channels/contact ＋ 業種・NG情報
    ├── brief/                   ← ヒアリング結果・素材メモ・トンマナ元情報
    ├── style/style.md           ← この社のトンマナ・表記・追加NG語
    ├── monthly/<YYYY-MM>/cycle.md   ← その月の納品サイクル（status/ノルマ/成果物リンク）
    └── delivered/<YYYY-MM>/      ← その月の納品前原稿（check の対象）
```

- **`<id>`**：英数ハイフンの短い識別子（業種カテゴリ＋連番など）。**実名・地区名を含めない（A4）**。
- **client.md / cycle.md はヘッダ駆動**（`- key: value`）。jobs.py と同じ「正規表現で読む・yaml非依存」方式で揃えた。
- **金額**はヘッダに数値で持つが、**請求書・契約の実体は CFO 管理で gitignore**（client.md にも実名は入れない）。

### なぜこの構造か
- **散らからない**：社×月で物理的に分離。「どの社の何月の何が、どこまで進んだか」が1パスで分かる。
- **テンプレと実体を分離**：`_template/` だけ追跡＝**新規社のセットアップが雛形コピーで一瞬**、かつ顧客PIIは絶対にコミットされない。
- **既存 tools と互換**：cycle.md / client.md のヘッダ形式が jobs.py と同じなので、検査・集約系（quality_check / collect_checks）がそのまま使える。

---

## 2. 月次制作テンプレ（1社の月次納品物の雛形）と埋め方

`clients/_template/delivered_templates/` に4種を用意。code/agent はこれを当月 `delivered/<YYYY-MM>/` にコピーして埋める。

| テンプレ | 中身 | 本数（プラン別） | 制作の重さ |
|---|---|---|---|
| `01_英語記事_template.md` | 英語本文＋和文下訳＋事実検証ノート | Bronze2 / Silver3 / Gold4 | 中（既存note制作と同等） |
| `02_英語SNS投稿_template.md` | 投稿セット（1投稿=1ブロック）＋投稿主体チェック | Bronze8 / Silver10 / Gold12 | 軽（記事から派生） |
| `03_英語サイト文_template.md` | ページ英語版＋インバウンド導線メモ＋更新履歴 | Bronze月1 / Silver月2 / Gold随時 | 軽〜中（初月重く以降は更新） |
| `04_月次レポート_template.md` | 実績ノルマ対比＋反応の可視化＋来月計画 | 全プラン月1 | 軽（定型集計） |

### 埋める手順（code/agent の標準オペ）
1. `retainers.py open --id <id> --month <YYYY-MM>` で当月 cycle.md を起票（ノルマチェックリスト自動生成）。
2. `client.md` の業種・`style/style.md` のトンマナ・`brief/` の素材を読む。
3. `delivered_templates/` の各テンプレを `delivered/<YYYY-MM>/` にコピーし、cycle.md のノルマ本数だけ埋める。
4. **英語要約・CTA は記事ごとに別パターン**（A6：同型反復NG）。固有名詞は style.md の確定綴りを使う。
5. `retainers.py check` で A4/A5 機械検査 → 合格したら cycle.md の成果物リンク欄に記入し `set --status delivered`。

> **量産の肝**：記事1本から SNS 3〜4投稿を派生させる。Silver（記事3＋SNS10）なら記事から大半のSNSが出る＝実質の追加制作はSNS数本分。**1社の月次制作は「実質 記事N本＋レポート1本」に圧縮**できる。

---

## 3. 自動チェックの組み込み（納品前ゲート）

### 共通ゲート（A4/A5）— `quality_check.py` をそのまま再利用
- `retainers.py check --id <id> --month <YYYY-MM>` が `delivered/<YYYY-MM>/*.md` を **`--reader`（読者に出す原稿＝厳格）** で一括検査。
- 検出：A5-HARD（世界唯一/日本一/最高級…）/ A5-SOFT（必ず/絶対…）/ MIX（社内向け・サムネ・``` 等の混入物）/ PII（既知の要伏字店名）。
- **HARD違反が1件でもあれば exit code 1**（テスト確認済み）。コミット前ゲート・CI に組み込める。

```
# 納品前の標準フロー（違反があれば 1 で止まる）
python3 tools/retainers.py check --id <id> --month 2026-07 \
  && python3 tools/retainers.py set --id <id> --month 2026-07 --status delivered
```

### クライアント別スタイルガイドの当て方
- 各社 `style/style.md` の `ban_extra:` に**その社で特に避けたい語**（例：競合名・自社で禁じた表現）をカンマ区切りで持つ。
- 現状 `retainers.py check` は **ban_extra を画面に提示**し、`quality_check`（共通A5語）と併せて目視/grep で潰せるようにしている。
- **将来の最小拡張（設計のみ）**：`quality_check.py` に `--extra "語1,語2"` 引数を足し、`retainers.py check` が `style.md` の ban_extra を渡して**社別NG語も機械検査**する。20行程度の改修で済む（A5_HARD リストに extra を合流させるだけ）。本ファイルでは設計に留め、必要時に実装。

### [要確認] の集約（事実検証）
- 記事テンプレの事実検証ノートに残った **[要確認]** は、既存 `tools/collect_checks.py` でそのまま1枚に集約 → ネットが使える cowork/オーナーが潰す（code は A1 で検証不可）。

---

## 4. 管理CLI — `tools/retainers.py`（jobs.py 発展形・実装済み）

jobs.py が「単発受託（受注→納品→入金）」なのに対し、retainers.py は**継続課金（社別×毎月くりかえす）**を管理する。

### サブコマンド
| コマンド | 役割 |
|---|---|
| `add --id <id> --plan {bronze,silver,gold} [--fee N]` | 社を登録（フォルダ構造＋client.md＋style.md を雛形生成。fee未指定はプラン標準） |
| `open --id <id> [--month YYYY-MM]` | 当月サイクル起票（cycle.md にプラン別ノルマのチェックリストを自動生成） |
| `list [--month YYYY-MM]` | 全社×当月の状態＋**MRR（継続課金合計）**＋当月入金＋黒字判定＋¥300K残 |
| `show --id <id>` | 1社の固定情報＋月次サイクル履歴 |
| `set --id <id> --month <m> --status <s>` | 状態遷移（planning→in-progress→review→delivered→invoiced→paid） |
| `check --id <id> --month <m>` | 当月成果物を quality_check に通す（A4/A5ゲート・違反で rc=1） |
| `invoice --id <id> --month <m>` | 請求済みに（金額はfeeから・実体はCFO管理） |
| `paid --id <id> --month <m> --amount N` | 入金記録＋ list を表示 |

### 設計のポイント
- **依存ゼロ・ヘッダ駆動**：jobs.py と同じ `_read_header / _set_header` 方式。yaml不要・A1で動く。
- **プラン↔ノルマを一元化**：`PLAN_QUOTA` に Bronze/Silver/Gold の記事・SNS・サイト更新本数＋標準feeを定義（A_§2のプラン定義と一致）。open 時にノルマがチェックリスト化される＝**作り忘れ防止**。
- **MRR と黒字判定**：list が継続課金合計と固定費¥5,800（jobs.py と同じ閾値）を突き合わせ、¥300K残も表示＝**営業の進捗が1画面**。
- **状態の単一ソース**：cycle.md のヘッダが「その社のその月が今どこか」の唯一の真実。STATE.md / 管制塔の手動更新を減らす。

### 動作確認（本日テスト済み）
add → open → list → set → check（A5違反で rc=1 を確認）→ invoice → paid → show を一通り実行し、
MRR集計・黒字判定・終了コード伝播まで期待通り動作することを確認（テスト用 demo 社は削除済み）。

---

## 5. どこまで人手が残るか（自動化後の残作業）

| 工程 | 担い手 | 自動化後の状態 |
|---|---|---|
| 社の登録・月次起票・状態管理 | **code（retainers.py）** | コマンド化済。手作業の台帳更新ほぼ消滅 |
| コンテンツ制作（記事/SNS/サイト文/レポート） | **code** | テンプレ＋プラン別ノルマで量産。記事から SNS 派生 |
| A4/A5 規則チェック | **code（check）** | 機械ゲート。HARD違反で自動停止 |
| **ヒアリング・素材受領** | **オーナー（CSO）** | 残る（対人・初回のみ／A1で代行不可） |
| **事実検証（[要確認]潰し）** | **cowork / オーナー** | collect_checks で集約までは自動。検証はネット必須＝残る |
| **画像・サムネ** | **オーナー / cloud** | A2で生成不可＝残る（写真は先方提供 or オーナー取得） |
| **投稿・公開・サイト反映** | **cowork / オーナー** | 媒体ログイン＝A1で代行不可＝残る（投稿代行は合意制） |
| **月次の先方確認・修正往復** | **オーナー** | A_§5の最大律速。契約で「月1回まとめ確認・修正1往復まで」に固定して圧縮 |
| **請求書発行・送付・入金確認** | **オーナー / CFO** | retainers.py は記録のみ。実体の発行・送付・着金確認は残る（PII・gitignore） |
| **英語問い合わせの受信→送信** | code下書き＋**オーナー送信** | 翻訳・返信下書きは code、受信箱アクセスと送信は残る |

> **残るのは本質的に「対人・ネット・画像・送金」だけ**＝A1/A2の物理制約と契約上の窓口に由来する部分。
> 制作・台帳・規則チェックという**反復作業は code に寄せ切った**。

---

## 6. 次アクション

| # | やること | 担い手 |
|---|---|---|
| 1 | 実顧客が付いたら `retainers.py add` → `open` で起票（PIIは〔　〕で手元記入・非push） | オーナー/code |
| 2 | 月初に全社 `open`、月末に `list` で進捗確認（管制塔の手動更新を置換） | code |
| 3 | （任意・最小）`quality_check.py --extra` を実装し ban_extra を機械検査に合流 | code |
| 4 | 月次レポートの「反応の可視化」数字は cowork/オーナーが媒体から拾って供給 | cowork/オーナー |
| 5 | 請求・契約の実体は CFO 雛形（営業エンジン 納品契約）で発行・gitignore 厳守 | オーナー/CFO |

---

*免責：本ファイルは制作・管理の自動化設計であり、法的/税務助言ではない。料金・本数・条件は目安で最終はご契約時に確定。当サービスが約束するのは「英語コンテンツ・導線を計画的に制作・運用し続けること」であり、来客・予約・売上・検索順位の増加は保証しない（A5）。実在の事業者・地区・人名は記載しない（A4）。clients/ 配下の顧客情報はコミットしない。*
