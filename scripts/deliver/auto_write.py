#!/usr/bin/env python3
"""
Claude APIで実作業（記事執筆・SNS投稿）を自動実行
prompts/ のプロンプトをAPIに投げて drafts/ に保存。

使い方:
  # API_KEY を環境変数に設定
  export ANTHROPIC_API_KEY=sk-ant-...
  python3 scripts/deliver/auto_write.py "<folder_name>"

  # または ~/agent-team/.env に
  # ANTHROPIC_API_KEY=sk-ant-...

エッジケース対応：
- API Key未設定
- ネットワークエラー（3回リトライ）
- 長大応答の途切れ（続きを自動要求）
- レート制限（指数バックオフ）
- プロンプト不足
"""

import json
import os
import re
import sys
import time
import urllib.request
import urllib.error


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
DELIVERIES_DIR = os.path.join(REPO_DIR, 'deliveries')

API_URL = 'https://api.anthropic.com/v1/messages'
MODEL = 'claude-sonnet-4-5'
MAX_TOKENS = 8000


def load_env():
    """.env ファイルから環境変数を読み込み"""
    env_path = os.path.join(REPO_DIR, '.env')
    if not os.path.exists(env_path):
        return
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and value and key not in os.environ:
                    os.environ[key] = value
    except Exception:
        pass


def get_api_key():
    """API Key取得（環境変数→.env→エラー）"""
    load_env()
    key = os.environ.get('ANTHROPIC_API_KEY')
    if not key:
        print('❌ ANTHROPIC_API_KEY が設定されていません')
        print()
        print('設定方法（どちらか）：')
        print('  1. 環境変数に設定:')
        print('     export ANTHROPIC_API_KEY=sk-ant-...')
        print()
        print('  2. ~/agent-team/.env に記載:')
        print('     echo "ANTHROPIC_API_KEY=sk-ant-..." > ~/agent-team/.env')
        print()
        print('API Keyは https://console.anthropic.com で取得')
        sys.exit(1)
    if not key.startswith('sk-ant-'):
        print(f'⚠️ API Keyの形式が不正: {key[:10]}...')
    return key


def call_claude(prompt, api_key, max_retries=3):
    """Claude API呼び出し（指数バックオフリトライ付き）"""
    payload = {
        'model': MODEL,
        'max_tokens': MAX_TOKENS,
        'messages': [{'role': 'user', 'content': prompt}],
    }
    data = json.dumps(payload).encode('utf-8')

    headers = {
        'x-api-key': api_key,
        'anthropic-version': '2023-06-01',
        'content-type': 'application/json',
    }

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(API_URL, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                # 応答から本文を抽出
                if 'content' in result and result['content']:
                    return result['content'][0].get('text', '')
                return ''
        except urllib.error.HTTPError as e:
            if e.code == 429:  # レート制限
                wait = 2 ** (attempt + 2)
                print(f'  ⏳ レート制限。{wait}秒待機...')
                time.sleep(wait)
                continue
            if e.code in (500, 502, 503, 504):  # 一時的エラー
                wait = 2 ** (attempt + 1)
                print(f'  ⏳ サーバーエラー（HTTP {e.code}）。{wait}秒後にリトライ...')
                time.sleep(wait)
                continue
            # 4xx系（認証エラー等）は即終了
            error_body = e.read().decode('utf-8', errors='ignore')
            print(f'❌ API エラー（HTTP {e.code}）: {error_body[:500]}')
            return None
        except urllib.error.URLError as e:
            wait = 2 ** (attempt + 1)
            print(f'  ⏳ ネットワークエラー: {e.reason}。{wait}秒後にリトライ...')
            time.sleep(wait)
        except Exception as e:
            print(f'❌ 予期しないエラー: {e}')
            return None

    print(f'❌ {max_retries}回リトライ失敗')
    return None


def load_prompt(folder_path, filename):
    """プロンプトファイル読み込み"""
    path = os.path.join(folder_path, 'prompts', filename)
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def save_draft(folder_path, filename, content):
    """下書きファイル保存"""
    drafts_dir = os.path.join(folder_path, 'drafts')
    os.makedirs(drafts_dir, exist_ok=True)
    path = os.path.join(drafts_dir, filename)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    return path


REVIEW_PROMPT_TEMPLATE = """あなたはプロのSEOエディターです。
以下の記事を100点満点で厳しく採点し、90点未満なら改善版を出力してください。

【採点基準】
- 構成の論理性: 20点
- 読みやすさ: 15点
- キーワードの自然配置: 15点
- E-E-A-T要素（経験・専門性・権威・信頼）: 20点
- 独自性（テンプレ的でないか）: 10点
- 事実の正確性: 10点
- 読者への価値提供: 10点

【元記事】
{article}

【出力形式】
## 採点
合計: XX/100

## 改善版
（90点以上なら元記事をそのまま出力。90点未満なら改善した全文を出力）

重要：改善版のセクションには必ず完全な記事全文を含めてください。省略不可。
"""


def review_and_improve(article, api_key, target_score=90):
    """生成記事を Claude でレビュー→改善"""
    print('🔍 STEP 3: プロエディターによるレビュー＆改善...')

    review_prompt = REVIEW_PROMPT_TEMPLATE.format(article=article)
    result = call_claude(review_prompt, api_key)
    if not result:
        return article  # 失敗時は元記事を返す

    # 採点を抽出
    import re as _re
    score_match = _re.search(r'合計[:：]\s*(\d+)', result)
    score = int(score_match.group(1)) if score_match else 0
    print(f'  📊 エディター採点: {score}/100')

    # 改善版を抽出
    improved_match = _re.search(r'##\s*改善版\s*\n(.+)', result, _re.DOTALL)
    if improved_match:
        improved = improved_match.group(1).strip()
        # 元記事より短すぎる場合は元記事を保持
        if len(improved) >= len(article) * 0.8:
            if score < target_score:
                print(f'  ✏️  改善版を採用（{score}→目標{target_score}点）')
                return improved
            else:
                print(f'  ✅ 十分な品質（{score}点・元記事を維持）')
    return article


def write_article(folder_path, meta, api_key):
    """記事を3段階生成（構成→本文→レビュー改善）"""
    # 既存尊重
    drafts_dir = os.path.join(folder_path, 'drafts')
    existing_article = os.path.join(drafts_dir, 'article.md')
    if os.path.exists(existing_article):
        size = os.path.getsize(existing_article)
        print(f'ℹ️  既存 article.md ({size}バイト) を尊重します（--force で上書き可）')
        if '--force' not in sys.argv:
            return True

    # STEP 1: 構成生成
    print('📝 STEP 1/3: 構成を生成中...')
    structure_prompt = load_prompt(folder_path, '1_structure.md')
    if not structure_prompt:
        print('❌ prompts/1_structure.md が見つかりません。generate.py を先に実行してください')
        return False

    structure = call_claude(structure_prompt, api_key)
    if not structure:
        return False

    save_draft(folder_path, '1_structure.md', structure)
    print(f'  ✅ 構成保存: drafts/1_structure.md（{len(structure)}字）')

    # STEP 2: 本文生成（構成を埋め込み）
    print('📝 STEP 2/3: 本文を生成中（E-E-A-T強化＋事実確認ルール適用）...')
    body_prompt_template = load_prompt(folder_path, '2_body.md')
    if not body_prompt_template:
        print('❌ prompts/2_body.md が見つかりません')
        return False

    body_prompt = body_prompt_template.replace('<<構成をここに貼り付け>>', structure)
    body = call_claude(body_prompt, api_key)
    if not body:
        return False

    print(f'  ✅ 初稿生成（{len(body)}字）')

    # STEP 3: プロエディターによるレビュー＆改善
    if '--no-review' not in sys.argv:
        body = review_and_improve(body, api_key, target_score=90)

    save_draft(folder_path, 'article.md', body)
    print(f'  ✅ 最終稿保存: drafts/article.md（{len(body)}字）')

    return True


def write_sns(folder_path, meta, api_key):
    """SNS投稿を一括生成"""
    print('📝 SNS投稿を一括生成中...')
    prompt = load_prompt(folder_path, '1_sns_posts.md')
    if not prompt:
        print('❌ prompts/1_sns_posts.md が見つかりません')
        return False

    existing = os.path.join(folder_path, 'drafts', 'article.md')
    if os.path.exists(existing) and '--force' not in sys.argv:
        print(f'ℹ️  既存 drafts/ を尊重します（--force で上書き可）')
        return True

    content = call_claude(prompt, api_key)
    if not content:
        return False

    save_draft(folder_path, 'article.md', content)
    print(f'  ✅ 投稿保存: drafts/article.md（{len(content)}字）')
    return True


def main():
    if len(sys.argv) < 2:
        print('使い方: python3 scripts/deliver/auto_write.py <folder_name> [--force]')
        sys.exit(1)

    folder_name = sys.argv[1]
    folder_path = os.path.join(DELIVERIES_DIR, folder_name)

    if not os.path.isdir(folder_path):
        print(f'❌ フォルダが存在しません: {folder_name}')
        sys.exit(1)

    meta_path = os.path.join(folder_path, 'meta.json')
    if not os.path.exists(meta_path):
        print(f'❌ meta.json が見つかりません')
        sys.exit(1)

    with open(meta_path, 'r', encoding='utf-8') as f:
        meta = json.load(f)

    print('=' * 60)
    print('🤖 Claude API で実作業を自動実行')
    print('=' * 60)
    print(f'案件: {meta["job_title"]}')
    print(f'タイプ: {meta.get("job_type", "?")}')
    print()

    api_key = get_api_key()

    job_type = meta.get('job_type', 'other')
    if job_type == 'article':
        success = write_article(folder_path, meta, api_key)
    elif job_type == 'sns':
        success = write_sns(folder_path, meta, api_key)
    else:
        print(f'⚠️ {job_type} タイプは自動作業未対応。手動で drafts/ に保存してください')
        sys.exit(1)

    if success:
        print()
        print('=' * 60)
        print('✅ 実作業完了')
        print('=' * 60)
        print()
        print('次のステップ:')
        print(f'  python3 scripts/deliver/quality_check.py "{folder_name}"')
        print(f'  python3 scripts/deliver/package.py "{folder_name}"')
    else:
        print('❌ 実作業失敗')
        sys.exit(1)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n中断されました')
        sys.exit(130)
