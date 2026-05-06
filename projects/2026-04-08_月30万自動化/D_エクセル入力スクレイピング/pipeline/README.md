# pipeline/ — 柱D 自動受注パイプライン 操作ガイド

クラウドソーシングのデータ入力・スクレイピング案件を**半自動**で回すための実行手順です。
規約遵守のため「応募送信」「納品送信」「初回ログイン」だけは人手、それ以外は Claude が自動処理します。

> 規約・採算性の根拠は親フォルダの `risk_and_feasibility.md` を参照してください。

---

## 役割分担：ローカル PC と ヘッドレス（Claude / サーバー）

```
┌────────────────────────────┐    ┌────────────────────────────┐
│ オーナーのローカル PC        │    │ Claude / ヘッドレスサーバー  │
│ （GUI ブラウザが必要）        │    │ （DISPLAY 不要・追加費用ゼロ）│
│                            │    │                            │
│ ① 00_session_setup.py      │ →  │ ② 01_search.py 〜          │
│   月1回ログインしてセッショ   │    │   06_deliver.py            │
│   ン保存（人手）             │    │   保存済セッションで自動実行  │
│                            │    │                            │
│ ⑥応募ボタンを人手で押す      │    │ 各ステップは headless=True   │
│ ⑥納品ボタンを人手で押す      │    │ または純Python＋APIのみ      │
└────────────────────────────┘    └────────────────────────────┘
```

`00_session_setup.py` だけが GUI ブラウザと対話入力を要求します。それ以外は CLI のみで完結します。

---

## 必要環境

| 環境 | 必須 | 備考 |
|------|------|------|
| Python 3.10+ | ✅ | `list[dict]` 型注釈を使用 |
| `playwright` (Python) | ✅ | `01_search.py` で使用 |
| Playwright Chromium | ✅ | `python -m playwright install chromium` で取得 |
| `openpyxl` | ⚠️ Excel 案件のみ | `04_execute.py` / `05_review.py` |
| `ANTHROPIC_API_KEY` | ⚠️ 評価精度を上げる場合のみ | 未設定でもルールベースで動作 |
| GUI / `DISPLAY` | ❌ ローカル `00_*` のみ必要 | サーバー実行は不要 |

### Claude API キーについて

`02_evaluate.py` `03_apply.py` `04_execute.py` `05_review.py` `06_deliver.py` は環境変数
`ANTHROPIC_API_KEY` を読みます。

- **未設定**：ルールベース評価／テンプレート応募文／API依存ステップは空振り
- **設定**：高精度な評価・自然な応募文・スクリプト自動生成が可能

```bash
export ANTHROPIC_API_KEY=sk-ant-...   # macOS / Linux
$env:ANTHROPIC_API_KEY="sk-ant-..."   # Windows PowerShell
```

---

## 初回セットアップ（ローカル PC で実行）

### 1. 依存インストール

```bash
cd projects/2026-04-08_月30万自動化/D_エクセル入力スクレイピング/pipeline
pip install playwright openpyxl
python -m playwright install chromium
```

> **macOS のみ**：システム Chrome を持っている場合は `00_session_setup.py` が
> `channel="chrome"` で優先利用します（Google ログインのブロック回避のため）。
> 無ければ Playwright の Chromium にフォールバックします。

### 2. プラットフォームへログイン

```bash
python 00_session_setup.py            # 対話モード（両方を順に設定）
python 00_session_setup.py crowdworks # クラウドワークスのみ
python 00_session_setup.py lancers    # ランサーズのみ
```

ブラウザが立ち上がるので、**手動でログイン → ターミナルに戻って Enter**。
セッションは `../.sessions/{platform}_session.json` に保存されます（gitignore 対象）。

セッションは数日〜数週間で失効するため、検索が空振りしたら再ログインしてください。

---

## 日次運用（ヘッドレスでも実行可）

### Phase 1：検索 → 評価 → 応募文生成

```bash
python run_pipeline.py search
```

実行内容：
1. `.sessions/*.json` を読み込んで CrowdWorks / Lancers を巡回（`headless=True`）
2. 各案件を 4軸（技術／法的／採算／明確性）で 100点満点採点
3. GO / CAUTION 案件の応募文を Claude が生成
4. （GUI 環境のみ）上位3件のページをブラウザで自動オープン

**応募ボタンの送信は規約上必ず人手**で行ってください。

### Phase 2：受注後の作業実行 → 念査 → 納品

```bash
python run_pipeline.py deliver
```

実行内容：
1. 直近の `*_applications.json` から GO 案件を選択（番号入力）
2. カテゴリ別に作業実行
   - `excel_input`：openpyxl で自動入力
   - `scraping`：Claude がスクリプト生成 → サブプロセスで実行 → CSV 出力
3. 成果物の念査（空欄・フォーマット・重複・文字化け）
4. 納品メッセージを Claude が生成
5. （GUI 環境のみ）案件ページをブラウザで自動オープン

**納品ボタンの送信も規約上必ず人手**で行ってください。

---

## 個別スクリプトの直接実行

| スクリプト | 用途 | 実行例 |
|-----------|------|--------|
| `00_session_setup.py` | ログイン保存（**ローカルのみ**） | `python 00_session_setup.py` |
| `01_search.py` | 案件検索（headless OK） | `python 01_search.py crowdworks` |
| `02_evaluate.py` | 1件評価（対話 / バッチ） | `python 02_evaluate.py --file ../outputs/2026-05-06_1200_jobs.json` |
| `03_apply.py` | 応募文生成 | `python 03_apply.py` |
| `04_execute.py` | 作業実行（カテゴリ別） | パイプライン経由を推奨 |
| `05_review.py` | 念査 | `python 05_review.py ../outputs/result.csv` |
| `06_deliver.py` | 納品文生成 | パイプライン経由を推奨 |

成果物はすべて `../outputs/` に `YYYY-MM-DD_HHMM_*.json` 形式で保存されます。
`outputs/` と `.sessions/` はリポジトリの `.gitignore` 対象です。

---

## トラブルシューティング

### `python -m playwright install chromium` が `403 'Host not in allowlist'` で失敗

サンドボックス環境（Claude Code on the web 等）でネットワーク許可リストが厳しい場合、
Playwright の CDN（`cdn.playwright.dev`）がブロックされます。対処：

1. ローカル PC でインストールし、生成された `~/.cache/ms-playwright/` 配下をコピー
2. もしくは `00_session_setup.py` だけをローカルで走らせ、サンドボックス側は
   `01_search.py` 以降を `playwright` パッケージのみで実行（Chromium バイナリは要事前配布）

最も簡単なのは **ローカルPC でセッション作成 → サーバー側に `.sessions/` を持ち込む** 運用です。

### `[SKIP] {platform}: セッション未設定`

`.sessions/{platform}_session.json` が存在しません。`00_session_setup.py` を再実行してください。

### 検索結果が 0 件

セッション失効の可能性が高いです。`00_session_setup.py` で再ログインしてください。

### `ANTHROPIC_API_KEY が設定されていません`

`02_evaluate.py` と `03_apply.py` はキー無しでも動きます（ルールベース／テンプレート）。
`04_execute.py`（スクレイピング）`05_review.py`（念査）`06_deliver.py`（納品文）はキーが必須です。

### `webbrowser` で URL が開かない

ヘッドレス環境（`DISPLAY` 未設定）では正常です。表示された URL を手動で開いてください。

---

## 規約遵守のためのチェックリスト

- [ ] プロフィールに「AI補助＋人間確認」を明記したか
- [ ] 応募・納品の **送信操作は人手** で行っているか
- [ ] スクレイピング対象サイトの利用規約・robots.txt を確認したか
- [ ] クライアントに AI 利用の合意を取ったか（ランサーズはラベル付与可）
- [ ] 念査（`05_review.py`）を通してから納品しているか

詳細は `../risk_and_feasibility.md` を参照。
