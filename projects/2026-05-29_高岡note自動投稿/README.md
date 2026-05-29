# 高岡note自動投稿 パイプライン

高岡市（富山県）の食・文化の**体験記事**を、**実写サムネ**付きで
**毎日3本・違う内容で** note に**自動公開**する仕組み。

仕様の正本は [`brief.md`](./brief.md)（恒久仕様＝引き継ぎ用の記憶）。

## 構成

```
01_select_topics.py   本日の3トピックを選定（重複回避・食/文化/歴史をバランス）
02_generate_article.py 体験記事を生成（Claude API）
03_generate_thumbnail.py 実写サムネを生成（画像生成API：openai 標準）
04_publish_note.py    note へ自動公開（Playwright・初回のみ人手ログイン）
run_pipeline.py       上記を1日3本まとめて実行
```

## セットアップ

```bash
cd pipeline
pip install -r requirements.txt
python -m playwright install chromium          # 初回のみ

cp config.example.json config.json             # 設定
cp state.example.json  state.json              # トピック消化の状態

# 認証情報は .env / 環境変数で（コミット禁止）
export ANTHROPIC_API_KEY=sk-ant-...
export OPENAI_API_KEY=sk-...                    # 実写サムネ生成用

python 04_publish_note.py login                 # 初回のみ：noteに手動ログイン→セッション保存
```

## 実行

```bash
python run_pipeline.py            # 3本を「下書きまで」生成（安全既定）
python run_pipeline.py --publish  # 公開操作まで実行
```

毎日自動化するなら cron 例（毎朝7時）:
```
0 7 * * * cd /path/to/pipeline && /usr/bin/python run_pipeline.py --publish >> run.log 2>&1
```

## 実運用に必要なもの（オーナー準備・要承認）

| 項目 | 用途 |
|------|------|
| `ANTHROPIC_API_KEY` | 記事生成 |
| 画像生成APIキー（既定 `OPENAI_API_KEY`） | 実写サムネ生成 |
| note ログイン（初回のみ人手） | 自動公開 |

> 会社ルール：**スクリプト実行・外部アクセス・外部送信（公開）は必ず事前承認**。
> 認証情報が揃い承認が出るまでは「生成・下書き」までに留める。
> `04_publish_note.py` は誤爆防止のため**既定で下書き保存**にしてある。

## 注意

- note は公式投稿APIが無いため公開はブラウザ自動化。**note側UI変更でセレクタ調整が必要**になりうる。
- サムネは `no text` で生成（noteタイトルが別に乗るため）。`thumbnails/` は **gitignore**。
- 記事は実在スポット・名物のみを題材にし、**架空の店名・価格・日付は書かない**。
