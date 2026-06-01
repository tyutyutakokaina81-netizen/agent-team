# note自動公開ヘルパー（オーナーのMacで実行）

「実行して」プロトコルの**最後の1ピース＝note公開**を自動化するツール。
私のクラウドコンテナはnoteに接続できない（ネット遮断＋ログイン非共有）ため、
**あなたのMac上で**Playwrightを使い、保存済みセッションでnoteに自動投稿する。

## クイック使用（推奨）

未公開記事を1コマンドで全部公開：

```
cd ~/agent-team/CDO/outputs/note_publisher
./publish_all.sh
```

`publish_all.sh` がやること：
- `index.lock` の自動解除
- `git pull` を最大4回リトライ（2/4/8/16秒）
- 未公開記事を `.published.log` で管理（二重投稿防止）
- 1本ずつ `publish_to_note.py --text-only` で投稿
- 失敗しても止まらず次へ進む。最後にサマリ表示

オプション：
- `--date 2026-06-01`：その日付の記事だけ
- `--max 3`：先頭N本だけ
- `--dry-run`：何を投稿するか表示のみ
- `--reset`：公開済みログをクリア（再投稿用）

柱D（エクセル入力スクレイピング）と同じ「**初回ログインのみ手動、以後は再利用**」モデル。

---

## ファイル
| ファイル | 役割 |
|---|---|
| `publish_to_note.py` | 本体（Playwrightでnote投稿） |
| `setup.sh` | 初回セットアップ（Playwrightインストール） |
| `README.md` | 本ファイル |

---

## 一連の流れ（運用イメージ）

```
[私が CMO/outputs/ に記事を作成・push]
        ↓
[あなた] git pull
        ↓
[あなた] スマホ等で撮った写真を  ~/Pictures/note/2026-05-28/  に
          photo_01.jpg, photo_02.jpg, ... の名前で配置
        ↓
[あなた] python3 publish_to_note.py --photos ~/Pictures/note/2026-05-28/
        ↓
[Chromiumが起動して自動投稿。あなたは見ているだけ]
        ↓
[公開完了]
```

---

## 初回セットアップ（一度だけ）

```bash
cd CDO/outputs/note_publisher
chmod +x setup.sh
./setup.sh
```

これで Playwright と Chromium がインストールされる。

### 初回ログイン（一度だけ）

```bash
python3 publish_to_note.py --login
```

Chromium が立ち上がるので **noteに手動でログイン** → ターミナルで Enter。
セッションが `~/.note_publisher_session.json` に保存され、以後は自動。

---

## 通常運用：公開する

### 写真の準備
記事内の `[写真①][写真②]...` のplaceholderに対応する画像を、ディレクトリに
**順番通り**に置く：

```
~/Pictures/note/2026-05-28/
├── photo_01.jpg   ← [写真①] かつサムネ（見出し画像）に使用
├── photo_02.jpg   ← [写真②]
├── photo_03.jpg   ← [写真③]
├── photo_04.jpg   ← [写真④]
└── photo_05.jpg   ← [写真⑤]
```

拡張子は `.jpg / .jpeg / .png / .heic` に対応。

### 公開コマンド

```bash
# 最新記事を写真ディレクトリ指定で公開
python3 publish_to_note.py --photos ~/Pictures/note/2026-05-28/

# 特定の記事を指定
python3 publish_to_note.py \
  --article CMO/outputs/2026-05-28_note記事_おとぎの森公園_世界が会いに来ていた.md \
  --photos ~/Pictures/note/2026-05-28/

# 下書き保存だけ（公開ボタンを押さず、最終確認用）
python3 publish_to_note.py --photos ~/Pictures/note/2026-05-28/ --draft
```

---

## 仕組み（何をしているか）

1. `CMO/outputs/` の最新 `*_note記事_*.md` を選択（または `--article` で指定）
2. mdから「メイン」直下のタイトルと「## 本文」直下の本文ブロックを抽出
3. 本文中の `[写真X]` placeholder を順番に検出
4. 保存済みセッションでChromiumを起動 → `note.com/notes/new` を開く
5. タイトル入力 → 本文を貼りながら placeholder の位置で写真をアップロード
6. 写真① を見出し画像（サムネ）に設定
7. 「公開」ボタンをクリック（`--draft` 指定時はスキップ）

---

## ⚠️ 重要な注意事項

### MVP段階であること
- 初版は**最小実装**です。noteのUI（ボタンのaria-label、CSS構造）に依存しており、
  noteのアップデートで動かなくなる可能性があります。
- 失敗箇所は画面に出るので、止まったら手動で続行 → 後でセレクタを調整してください。

### noteの利用規約
- noteは公式に自動投稿APIを提供していません。
- このツールはオーナー自身のログインセッションでブラウザを操作する**ブラウザ自動化**です。
  通常のブラウザ操作と同等の挙動ですが、規約上の解釈は自己責任でお願いします。
- **連投・スパム的な使い方はしない**こと（1日数本までの通常運用を想定）。

### セキュリティ
- セッションファイル `~/.note_publisher_session.json` は**あなたのMac内にのみ保存**されます。
- リポジトリにはコミットされません（`.gitignore` 確認不要、リポジトリ外のパス）。
- 共有マシンでは使わないでください。

### コンテナ（クラウドCode）からは動きません
- このスクリプトは **オーナーのMacで動かす前提**です。
- 私（Claude）のクラウドコンテナはnoteに接続不可なので、ここでは実行できません。

---

## トラブルシューティング

| 症状 | 対処 |
|---|---|
| `Playwrightが未インストール` | `./setup.sh` を実行 |
| `初回ログインがまだです` | `python3 publish_to_note.py --login` |
| 写真が貼られない | `--photos` のパスを確認／`photo_01.jpg` 命名を確認 |
| ボタン自動クリック失敗 | 画面で手動操作。失敗箇所のセレクタをCDOに報告 → スクリプト改修 |
| ログインセッション切れ | `python3 publish_to_note.py --login` で再ログイン |

---

## 「実行して」プロトコルとの繋がり

オーナー側の運用：

```
あなた: 「実行して」
    ↓
私(Claude): 記事作成 → CMO/outputs/ にpush
    ↓
あなた: git pull && python3 publish_to_note.py --photos ...
    ↓
公開完了
```

将来：あなたのMacでgitフックや`fswatch`でCMO/outputs/の更新を検知して
このスクリプトを自動起動すれば、`git pull`すら不要の完全自動になります（v2予定）。
