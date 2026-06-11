# 完全自動化セットアップ（オーナー一度きり）2026-06-09

これを設定すると、以後**手放しで回る**：ワーカーが成果を push → 安全検査 → main 自動統合 → サイト自動公開。

## 仕組み（実装済み・コード側）
```
worker(cowork/genspark) が worker/<name> に push
  → .github/workflows/worker-integrate.yml が起動
     ① 変更が許可領域(CMO/outputs, site/og, site/i18n, ops/outbox, ops/processed, drafts)だけかを検査
     ② 安全なら main へ自動マージ／許可外を触っていたら統合せず失敗(=mainは汚れない)
  → pages.yml が main を自動ビルド&公開／audit.yml が自動監査
```
→ **外部AIに write 権限を渡しても、正本(STATE/台帳/.github/CFO/CSO/秘密)は技術的に守られる。**

## あなたの設定（3ステップ・一度きり）

### 1. fine-grained PAT を作る（最小権限）
GitHub → Settings → Developer settings → **Fine-grained personal access tokens** → Generate
- Repository access: **Only select repositories → `agent-team` のみ**
- Permissions: **Contents = Read and write**（他は不要）
- 期限を設定し、トークン文字列をコピー（**repoには絶対貼らない**）

### 2. そのPATを Genspark（と必要なら cowork）に設定
- Genspark の GitHub 連携設定に上記PATを登録（Genspark側UI）。
- → これで Genspark は **worker/genspark へ自力 push** できる＝**ペーストブリッジ不要**。

### 3.（任意）cowork の公開を定期自動化
- オーナーMacの crontab に1行（毎朝8時 note 公開）：
  `0 8 * * * cd ~/agent-team && bash ops/cowork_run.sh >> ops/logs/cron.log 2>&1`

## 設定後の流れ（人手ゼロ）
- code が記事を書く→push→自動公開。
- Genspark が翻訳/調査/画像を worker/genspark に push→自動検査→main→自動公開。
- cowork が毎朝 note 公開＋SNS。
- = **あなたは結果を見るだけ。** 何かおかしければ worker-integrate が止めて知らせる。

## 安全の担保
- PATは「このrepoのContentsだけ」=他repo/設定/Secretsに触れない。
- main へ何が入るかは worker-integrate の allowlist が技術的に強制（指示だけに頼らない）。
- 全行動が git 履歴＋ops に残る＝監査可能・巻き戻し可能。
