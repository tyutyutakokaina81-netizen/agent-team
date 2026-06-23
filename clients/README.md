# clients/ — B2Bリテーナー クライアント別 制作パイプライン

`tools/retainers.py` が管理する、英語発信代行（A_高単価B2Bパッケージ）の社別フォルダ。
**顧客情報はコミットしない**（`.gitignore` で `_template/` 以外を除外）。実名・住所・地区名は
ファイルに書かない（A4）。穴埋め欄〔　〕はオーナーが手元で記入し、push しない。

## 1社のフォルダ構造

```
clients/<id>/
├── client.md            ← 社の固定情報（plan/fee/業種カテゴリ/NG情報）。ヘッダで管理
├── brief/               ← ヒアリング結果・素材メモ・トンマナの元情報
├── style/style.md       ← この社のスタイルガイド（語彙・表記・追加NG語 ban_extra）
├── monthly/<YYYY-MM>/
│   └── cycle.md         ← その月の納品サイクル（status / ノルマチェック / 成果物リンク）
└── delivered/<YYYY-MM>/ ← その月の納品前原稿（記事/SNS/サイト文/レポート）。check の対象
```

`<id>` は英数ハイフンの短い識別子（業種カテゴリ＋連番など。実名・地区名を含めない＝A4）。

## 毎月の回し方（1社あたり数コマンド）

```
python3 tools/retainers.py add  --id <id> --plan silver        # 初回のみ：社を登録
python3 tools/retainers.py open --id <id> --month 2026-07      # 月初：当月サイクル起票
# … code/agent が delivered/2026-07/ に成果物を制作（cycle.md のノルマに沿って）…
python3 tools/retainers.py check --id <id> --month 2026-07     # 納品前：A4/A5 機械検査
python3 tools/retainers.py set  --id <id> --month 2026-07 --status delivered
python3 tools/retainers.py invoice --id <id> --month 2026-07   # 請求（実体はCFO管理）
python3 tools/retainers.py paid    --id <id> --month 2026-07 --amount 80000
python3 tools/retainers.py list                                # 全社×当月＋MRR＋黒字判定
```

詳細設計：`projects/2026-06-23_300K設計/F_納品自動化.md`
