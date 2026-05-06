# iPhone から ai-auto を操作するレシピ集

iPhone の **ショートカットアプリ**（標準）から、外出先で ai-auto を確認・操作するための2系統のレシピ。

| 系統 | 接続方法 | 必要設定 | 速度 |
|------|--------|--------|------|
| **Y. HTTP API（推奨）** | mac の server.py に Web リクエスト | サーバ常駐＋トークン | 高速・GUI向き |
| **Z. SSH（補助）** | mac に SSH してコマンド実行 | mac の SSH 有効化のみ | 遅い・全機能可 |

## Y. HTTP API レシピ（推奨）

### 事前準備（mac 側・1回のみ）

1. `.env` に `AI_AUTO_TOKEN` を設定（推奨：32文字以上のランダム文字列）
   ```bash
   echo "AI_AUTO_TOKEN=$(openssl rand -hex 24)" >> ~/ai-auto/.env
   ```
2. サーバー起動：
   ```bash
   cd ~/ai-auto && ./run_server.sh        # mac内のみ
   cd ~/ai-auto && ./run_server.sh lan    # LAN 公開（同一 Wi-Fi なら iPhone から見える）
   ```
3. 外出先からも使うなら：
   - **Tailscale**（推奨・無料）：mac と iPhone の両方にインストールするだけで仮想LAN
   - **ngrok**（簡易）：`ngrok http 8765` で一時 URL 発行
   - **iCloud Private Relay は使えない**（インバウンド不可）

4. mac を常時稼働させたい場合は LaunchAgent 登録：
   ```bash
   cp ~/ai-auto/com.aiauto.server.plist ~/Library/LaunchAgents/
   launchctl load ~/Library/LaunchAgents/com.aiauto.server.plist
   ```

### iPhone ショートカット 4本

mac の IP アドレス（例：`192.168.1.10` または Tailscale `100.x.y.z`）を `<MAC_IP>` に置き換える。
ベースURLは `http://<MAC_IP>:8765`、トークンは `<TOKEN>`。

#### ① 今日のKPIを見る

| ステップ | 設定 |
|--------|------|
| 1. URLの内容を取得 | `http://<MAC_IP>:8765/kpi?token=<TOKEN>` |
| 2. クイックルック | （前ステップの結果） |

→ KPI集計（7日/30日/90日 + Level別）が画面に表示される

#### ② 今日の生成物を見る

| ステップ | 設定 |
|--------|------|
| 1. URLの内容を取得 | `http://<MAC_IP>:8765/outputs?token=<TOKEN>` |
| 2. JSONから値を取得 | キー `name`（リスト全件） |
| 3. リストから選択 | （前ステップの結果） |
| 4. URLの内容を取得 | `http://<MAC_IP>:8765/outputs/[選んだ名前]?token=<TOKEN>` |
| 5. クイックルック | （前ステップの結果） |

→ 任意ファイル本文を Markdown で表示

#### ③ 公開を記録

| ステップ | 設定 |
|--------|------|
| 1. リストから選択 | `note / paid_note / writer / ai_support / consultant / crowdworks` |
| 2. テキスト入力 | URL/案件名 |
| 3. テキスト入力 | タイトル |
| 4. 数値入力 | 収益（円） |
| 5. URLの内容を取得 | URL: `http://<MAC_IP>:8765/publish?token=<TOKEN>`<br>方法: POST<br>本文: JSON `{"kind":[1],"url":[2],"title":[3],"revenue":[4]}` |
| 6. 通知を表示 | （結果） |

→ note 公開直後に iPhone から記録 → KPI に即反映

#### ④ DRY_RUN を切り替え（緊急停止用）

| ステップ | 設定 |
|--------|------|
| 1. リストから選択 | `1 (停止) / 0 (稼働)` |
| 2. URLの内容を取得 | URL: `http://<MAC_IP>:8765/dry-run?token=<TOKEN>`<br>方法: POST<br>本文: JSON `{"value":"[選んだ値]"}` |
| 3. 通知を表示 | （結果） |

→ BAN兆候を見たら iPhone から1タップで全自動投稿停止

---

## Z. SSH レシピ（補助・実装コストゼロ）

### 事前準備（mac 側）
- システム設定 → 一般 → 共有 → 「リモートログイン」をON
- iPhone との接続は同一LANまたは Tailscale

### iPhone アプリ
- [a-Shell](https://apps.apple.com/app/a-shell/id1473805438)（無料・推奨）またはBlink Shell
- ショートカットの「シェルスクリプトを実行」（a-Shell連携）

### コマンドレシピ

| やりたいこと | コマンド |
|------------|--------|
| 今日のKPIを見る | `ssh user@<MAC_IP> 'python3 ~/ai-auto/kpi.py'` |
| 今日の生成物一覧 | `ssh user@<MAC_IP> 'ls -1t ~/ai-auto/outputs \| head -10'` |
| 最新noteを表示 | `ssh user@<MAC_IP> 'cat ~/ai-auto/outputs/$(ls -1t ~/ai-auto/outputs \| grep note_draft \| head -1)'` |
| BAN検知を実行 | `ssh user@<MAC_IP> 'python3 ~/ai-auto/ban_detector.py'` |
| サーバー停止 | `ssh user@<MAC_IP> '~/ai-auto/run_server.sh stop'` |
| 全自動を緊急停止 | `ssh user@<MAC_IP> 'sed -i "" "s/DRY_RUN=0/DRY_RUN=1/" ~/ai-auto/.env'` |
| 日曜の高単価候補を即生成 | `ssh user@<MAC_IP> 'python3 ~/ai-auto/sunday_polish.py'` |

### iPhone ショートカット（SSH版）

「ショートカット」アプリで：
1. 「SSH経由でスクリプトを実行」アクションを追加（a-Shell連携 or 標準SSH）
2. 上記コマンドを貼り付け
3. ホーム画面に追加

→ SSH 鍵認証にしておくとパスワード不要で1タップ実行

---

## ⑤ note 1タップ公開（C案・規約準拠）

GitHub から最新の `note_draft.md` を取得 → クリップボードに本文をコピー → note アプリを起動。
あとは note アプリで貼り付け→公開ボタンを押すだけ。**所要 10秒**。

### 事前設定

1. リポジトリ `tyutyutakokaina81-netizen/agent-team` の最新ドラフトURL形式：
   - `https://raw.githubusercontent.com/<OWNER>/<REPO>/<BRANCH>/daily/<YYYY-MM-DD>/note_draft.md`
2. ブランチ名・オーナー名はショートカット内で固定

### iPhone ショートカット手順

| ステップ | 設定 |
|--------|------|
| 1. 日付の取得 | フォーマット `yyyy-MM-dd`・タイムゾーン `Asia/Tokyo` |
| 2. テキスト | `https://raw.githubusercontent.com/<OWNER>/agent-team/<BRANCH>/daily/[1]/note_draft.md` |
| 3. URLの内容を取得 | URL: 前ステップ・方法: GET |
| 4. テキスト変換 | 取得した内容（Markdown 全体） |
| 5. クリップボードにコピー | （前ステップの結果） |
| 6. URLを開く | `https://note.com/notes/new`（Safari）または `note://` (note アプリのURLスキーム) |
| 7. 通知を表示 | 「note を開きました。長押しでペーストして公開してください」 |

### 動作

1. iPhone でショートカットをタップ
2. 自動的にクリップボードに今日の本文がコピーされる
3. note アプリ（or Safari）が起動
4. **本文欄を長押し → ペースト → 公開ボタン** だけ人間が押す
5. 完了

### この方式の利点

- BAN リスク **ゼロ**（note の利用規約完全準拠）
- mac 不要
- 失効しない（GitHub の Public/Private 設定だけ）
- 「公開ボタンを押した感覚」が残るのでオーナーの実行ハードルが下がる

### Private リポジトリの場合

`raw.githubusercontent.com` は GitHub Personal Access Token が必要：
- Step 3 で「ヘッダーを追加」→ `Authorization: Bearer <PAT>`
- PAT は iPhone のメモアプリに保管（パスワード管理）

---

## 推奨組み合わせ

| 用途 | 推奨方式 |
|------|--------|
| 出先でKPIを見る・公開記録 | **Y. HTTP API**（高速・GUI） |
| 緊急停止（BAN検知時） | **Y. POST /dry-run**（1タップ） |
| 任意のスクリプト実行 | **Z. SSH**（柔軟） |
| サーバートラブル時の復旧 | **Z. SSH**（必須） |

**推奨：Y を主に使い、Z を保険として残す。**
