# 公開自動化（note + X）

オーナーのボタン押し滞留を解消するための半自動化スクリプト群。
費用 ¥0（Playwright のみ・既存の柱D セッション方式と同じ）。

---

## ステップ

### 1. 初回セッション設定（1 回だけ・約 3 分）

```bash
cd projects/2026-04-08_月30万自動化/automation
python3 00_session_setup.py
```

ブラウザが開くので：
- note にログイン → ターミナルで Enter
- X にログイン → ターミナルで Enter

セッションは `.sessions/{note,x}_session.json` に保存（gitignore 対象）。

### 2. 一括実行（約 5-10 分）

```bash
python3 run_all.py
```

順次：
1. Vol.2 を note 公開（タイトル・本文・タグ自動入力 → 価格・公開ボタンは手動）
2. Vol.3 を note 公開（同上）
3. X ツイート 1（Vol.2 告知）→ 30 秒待機
4. X ツイート 2（Vol.3 告知）→ 30 秒待機
5. X ツイート 3（シリーズ告知）

---

## 個別実行

```bash
python3 publish_note.py vol2     # Vol.2 のみ note 公開
python3 publish_note.py vol3     # Vol.3 のみ
python3 publish_note.py all      # 両方

python3 post_x.py 1              # ツイート 1 のみ
python3 post_x.py 2
python3 post_x.py 3
python3 post_x.py all            # 全 3 種
```

---

## 半自動の理由（規約遵守）

- note：自身のアカウントへの投稿は規約上問題ないが、**最終公開ボタンは人手** で押す（誤公開防止＋規約遵守）
- X：自動投稿に対する規約が厳しい（特に連続投稿）。**スクリプトは入力までで、ポストボタンは人手**
- 連続投稿は 30 秒以上の間隔を強制

---

## トラブル

| 症状 | 対応 |
|------|------|
| `セッション未保存` | `00_session_setup.py` 再実行 |
| タイトル／本文欄が見つからない | サイト構造変更の可能性。手動入力で完了 → スクリプト終了時 Enter |
| ログインを再要求された | `.sessions/*.json` を削除して `00_session_setup.py` 再実行 |

---

## 実装メモ

- 依存: `playwright>=1.40`（柱D の `requirements.txt` と共有）
- セッションは `.sessions/` 配下、`.gitignore` で保護
- すべて Python 標準ライブラリ＋ Playwright のみ。**外部 API 呼び出しゼロ**
