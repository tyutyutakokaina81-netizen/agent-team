# 柱D Google OAuth課題の回避策（2026-04-13）

pipeline_server.mjs が Google OAuth でログインできない問題の解決戦略。

---

## 🔍 現状の問題

### 何が起きているか
- Playwrightで `Sign in with Google` ボタンを押すと、Googleが**自動化されたブラウザ**を検出してブロック
- クラウドワークス・ランサーズの一部ログインがGoogle OAuthに依存
- エラー：「このブラウザーは安全でない可能性があります」

### なぜ問題か
- 手動認証→セッション保存→再利用の「初回ログインのみ人手」モデルが破綻
- 自動化の肝が使えない状態

---

## 💡 解決策5選（実装優先順）

### 解決策1：メールアドレス+パスワードのログインに切り替え（推奨）

**実装：**
```python
# pipeline/00_session_setup.py を修正
# Googleログインではなくメール+パスワードでログイン

async def login_email_password(page, email, password):
    await page.goto('https://crowdworks.jp/login')
    await page.fill('input[name="username"]', email)
    await page.fill('input[name="password"]', password)
    await page.click('button[type="submit"]')
    await page.wait_for_load_state('networkidle')
```

**メリット：**
- Google OAuthを回避
- 設定が簡単
- 長期的に安定

**デメリット：**
- クライアントがGoogle SSOしか使えない場合は使えない
- 一部サイトで2FA必須

### 解決策2：手動ログイン後のセッション再利用

**実装：**
```python
# 最初の1回だけ手動でログインして cookies を保存
# 2回目以降はそのcookiesを使う

async def save_session(context, path='session.json'):
    await context.storage_state(path=path)

async def load_session(browser, path='session.json'):
    return await browser.new_context(storage_state=path)
```

**メリット：**
- Google OAuthのブロック問題を完全回避
- セッション有効期間中は自動化OK

**デメリット：**
- セッション切れ時（2週間程度）に再ログイン必要
- セッションファイルの安全な管理が必要

### 解決策3：Playwrightに人間らしい振る舞いをさせる

**実装：**
```python
# Stealth Modeの使用
from playwright_stealth import stealth_async

async def create_stealth_context(browser):
    context = await browser.new_context(
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ...',
        viewport={'width': 1280, 'height': 720},
        locale='ja-JP',
        timezone_id='Asia/Tokyo'
    )
    page = await context.new_page()
    await stealth_async(page)
    return page

# マウスの動きを人間らしく
async def human_like_click(page, selector):
    await page.hover(selector)
    await asyncio.sleep(random.uniform(0.5, 1.5))
    await page.click(selector)
```

**メリット：**
- Googleのブロックを回避できる可能性
- 根本的な解決に近い

**デメリット：**
- 追いかけっこになる（Googleも検出強化）
- 確実性が低い

### 解決策4：API経由（一部サイトで可能）

**クラウドワークスAPI：**
- 公式APIはなし
- 民間のスクレイピングAPIサービスは規約違反の可能性

**ランサーズAPI：**
- 公式APIはなし

**→ 現時点ではAPI経路は現実的でない**

### 解決策5：柱Dを諦めて柱A集中

**判断：**
- パイプラインの実運用テストに時間がかかる
- 柱Aの応募・受注を手動で回す方が早い
- 柱Dは「余力があれば挑戦」の位置づけに降格

**メリット：**
- 時間を売上獲得に集中できる
- 技術的課題に消耗しない

**デメリット：**
- 自動化の夢は遠のく
- 既に作った pipeline_server.mjs は眠ることに

---

## 🎯 推奨：解決策2（セッション保存）

### 理由
1. 根本的な自動化のメリットを維持
2. 実装難易度が低い
3. Googleのブロックを完全回避

### 実装手順

#### Step 1：手動ログインでcookies保存
```python
# save_cookies.py
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        # 通常のChromeで起動（headless=False）
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        await page.goto('https://crowdworks.jp/login')
        
        # 手動でログインする時間を確保（2分）
        print('2分以内にログインしてください...')
        await asyncio.sleep(120)
        
        # セッションを保存
        await context.storage_state(path='session_crowdworks.json')
        print('セッションを保存しました')
        
        await browser.close()

asyncio.run(main())
```

#### Step 2：保存したセッションを使って自動化
```python
# run_pipeline.py
async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # 保存したセッションをロード
        context = await browser.new_context(
            storage_state='session_crowdworks.json'
        )
        page = await context.new_page()
        
        # すでにログイン済みの状態で自動化開始
        await page.goto('https://crowdworks.jp/public/jobs/category/52')
        # ...以降の処理
```

#### Step 3：セッション有効期間の管理
```python
# セッションファイルの作成日時を確認
import os
from datetime import datetime, timedelta

def is_session_valid(path='session_crowdworks.json', days=7):
    if not os.path.exists(path):
        return False
    created = datetime.fromtimestamp(os.path.getctime(path))
    return datetime.now() - created < timedelta(days=days)
```

### セッション有効期間の目安

| サイト | セッション有効期間 |
|--------|----------------|
| クラウドワークス | 約30日 |
| ランサーズ | 約30日 |
| Google | 約2週間（操作がない場合） |

**→ 月1回の再ログインで自動化を継続可能。**

---

## ⚠️ 規約上の注意

### クラウドワークス利用規約（関連部分）
- 「自動化されたシステムを使用して、本サービスにアクセスまたは使用することを禁じる」
- **→ 応募の自動化は明確にNG**
- 案件の**閲覧・ピックアップ**までは自動化してもOK（曖昧）

### 推奨する使い方
1. **案件の抽出**：自動（問題ない範囲）
2. **応募文の生成**：AIで自動（問題なし）
3. **応募の送信**：**手動**でコピペ（規約遵守）

**→ 完全自動化は諦めて、「案件ピックアップ＋応募文生成」までの半自動化に留める。**

---

## 📋 現実的な次のステップ

### Phase 1（今週）：手動でパイプライン確認
- [ ] session_crowdworks.json の手動生成
- [ ] 01_search.py の単体実行テスト
- [ ] 02_evaluate.py の動作確認

### Phase 2（来週）：半自動化の仕組み構築
- [ ] 案件抽出→応募文生成までを自動化
- [ ] 応募は手動（規約遵守）
- [ ] 1日10分で10件の応募準備が整う状態

### Phase 3（再来週）：運用開始
- [ ] 毎朝スクリプト実行→応募候補一覧
- [ ] その場で応募10件を手動送信
- [ ] 結果をダッシュボードに記録

---

## 🚨 やってはいけないこと

- ❌ 応募の完全自動化（規約違反）
- ❌ 1分間に大量の応募送信（スパム扱い）
- ❌ 同じ応募文を連続送信（検知される）
- ❌ クライアントへの営業DMのスパム送信

**「規約遵守」と「効率化」のバランスを取る。**

---

## 💡 代替案：柱Dを別方向に転用

pipeline_server.mjs は以下の用途に転用可能：

### 案1：柱C（テンプレ販売）の集客に使う
- noteで人気記事をスクレイピング
- トレンドを分析
- 次に作るテンプレのテーマ決定

### 案2：柱B（営業リスト）の自動生成
- Google Maps / 食べログから飲食店情報を抽出
- Instagram APIで投稿頻度をチェック
- 優先度Aの店をリスト化

### 案3：情報商品としての販売
- 「Webスクレイピング自動化パイプライン」を有料販売
- エンジニア向け note / BOOTH で3,000〜5,000円
- 柱Cの新しい商品として

**→ Google OAuth問題は、柱Dの別方向転用の機会でもある。**

---

## 🎯 結論

1. **短期**：手動セッション保存で半自動化
2. **中期**：応募以外（案件抽出・評価・文章生成）は自動化
3. **長期**：柱Dを集客・リスト生成ツールに転用

Google OAuthに固執せず、別の価値を生む使い方を模索する。
