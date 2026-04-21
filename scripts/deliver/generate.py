#!/usr/bin/env python3
"""
案件タイプ別プロンプト自動生成
使い方: python3 scripts/deliver/generate.py <folder_name>
"""

import json
import os
import sys

DELIVERIES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    '..',
    'deliveries',
)


ARTICLE_STRUCTURE_PROMPT = """以下の条件でSEO記事の構成を作成してください。

【基本情報】
- メインキーワード：{keyword}
- 文字数：{char_count}字
- 想定読者：{persona}
- トーン：{tone}
{reference}

【構成の要件】
1. タイトル案3つ（32字以内・キーワード含む）
2. メタディスクリプション（120字以内）
3. リード文の方向性（300字）
4. H2見出し4-6個
5. 各H2に紐づくH3見出し2-3個
6. まとめのCTA方針

出力は以下の形式で：

# タイトル案
1. ～
2. ～
3. ～

# メタディスクリプション
～

# リード文の方向性
～

# 記事構成
## H2-1：～
  ### H3-1-1：～
  ### H3-1-2：～
## H2-2：～
  ### H3-2-1：～
（以下続く）

# まとめのCTA方針
～
"""

ARTICLE_BODY_PROMPT = """以下の構成に基づいて、{char_count}字のSEO記事を執筆してください。

【構成】
<<構成をここに貼り付け>>

【執筆ルール】
- 読者の悩みに共感→解決を提示する流れ
- 箇条書き・表を積極活用
- 1段落3文以内
- 専門用語は解説を添える
- 語尾は「{tone}」で統一
- 各H2セクション末に「ここがポイント」を1行添える
- 結論を先に・根拠を後に（PREP法）
- 想定読者：{persona}

執筆してください。
"""

SNS_PROMPT = """あなたは{industry}のSNS投稿を代行しています。
{post_count}本の投稿文をまとめて作成してください。

【クライアント情報】
- 業種：{industry}
- ターゲット：{target}
- ブランドトーン：親しみやすく・プロフェッショナル

【投稿媒体】
{platforms}

【今月の訴求テーマ】
{theme}

【各投稿に含めること】
1. 本文（Instagram: 改行多め・絵文字3-5個 / X: 140字以内）
2. ハッシュタグ10-15個
3. 画像用テキスト案（1行のキャッチコピー）

【投稿テーマのバリエーション（{post_count}本）】
以下のテーマをバランスよく使う：
- 新メニュー/新サービス紹介
- スタッフ紹介
- お客様の声
- 業界の豆知識
- 裏側公開
- 季節ネタ
- キャンペーン告知
- Q&A
- ビフォーアフター
- 日常の一コマ

【出力形式】
### 投稿1
テーマ：～
本文：
～

ハッシュタグ：#～ #～ #～

画像テキスト：～

---

（{post_count}本を順に出力）
"""

DATA_ENTRY_PROMPT = """以下のデータ入力タスクの設計書を作成してください。

【案件情報】
- 入力元：{source}
- 出力形式：{output_format}
- 件数：{count}
- 列項目：{columns}

【設計書の内容】
1. 作業手順（ステップごと）
2. 入力元から取得する情報のマッピング
3. フォーマット変換のルール
4. チェック項目（データ精度確保）
5. 納品時の注意事項

効率化できる部分があれば、具体的なプログラミング（PythonやExcel関数）での自動化提案も含めてください。
"""


def load_meta(folder_path):
    meta_path = os.path.join(folder_path, 'meta.json')
    if not os.path.exists(meta_path):
        print(f'❌ meta.json が見つかりません: {meta_path}')
        sys.exit(1)
    with open(meta_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_article_prompts(meta):
    d = meta['details']
    reference = ''
    if d.get('reference_urls'):
        reference = f"- 参考URL：{d['reference_urls']}"

    structure = ARTICLE_STRUCTURE_PROMPT.format(
        keyword=d.get('keyword', ''),
        char_count=d.get('char_count', '3000'),
        persona=d.get('persona', ''),
        tone=d.get('tone', '丁寧'),
        reference=reference,
    )

    body = ARTICLE_BODY_PROMPT.format(
        char_count=d.get('char_count', '3000'),
        tone='です・ます調' if d.get('tone') == '丁寧' else d.get('tone', 'です・ます調'),
        persona=d.get('persona', ''),
    )

    return {
        '1_structure.md': structure,
        '2_body.md': body,
    }


def generate_sns_prompts(meta):
    d = meta['details']
    prompt = SNS_PROMPT.format(
        industry=d.get('industry', ''),
        target=d.get('target', ''),
        post_count=d.get('post_count', '15'),
        platforms=d.get('platforms', 'Instagram'),
        theme=d.get('theme', ''),
    )
    return {'1_sns_posts.md': prompt}


def generate_data_entry_prompts(meta):
    d = meta['details']
    prompt = DATA_ENTRY_PROMPT.format(
        source=d.get('source', ''),
        output_format=d.get('output_format', 'Excel'),
        count=d.get('count', ''),
        columns=d.get('columns', ''),
    )
    return {'1_workflow_design.md': prompt}


def main():
    if len(sys.argv) < 2:
        print('使い方: python3 scripts/deliver/generate.py <folder_name>')
        print()
        print('利用可能なフォルダ：')
        if os.path.exists(DELIVERIES_DIR):
            for f in sorted(os.listdir(DELIVERIES_DIR)):
                if os.path.isdir(os.path.join(DELIVERIES_DIR, f)):
                    print(f'  {f}')
        sys.exit(1)

    folder_name = sys.argv[1]
    folder_path = os.path.join(DELIVERIES_DIR, folder_name)

    if not os.path.exists(folder_path):
        print(f'❌ フォルダが見つかりません: {folder_path}')
        sys.exit(1)

    meta = load_meta(folder_path)
    job_type = meta.get('job_type', 'other')

    print('=' * 50)
    print(f'🤖 プロンプト生成: {meta["job_title"]}')
    print(f'   タイプ: {job_type}')
    print('=' * 50)

    if job_type == 'article':
        prompts = generate_article_prompts(meta)
    elif job_type == 'sns':
        prompts = generate_sns_prompts(meta)
    elif job_type == 'data_entry':
        prompts = generate_data_entry_prompts(meta)
    elif job_type == 'copy_paste':
        print('📝 コピペ作業はプロンプト生成不要です。')
        print('   直接作業して drafts/ に保存してください。')
        sys.exit(0)
    else:
        print('⚠️  「その他」タイプはプロンプトテンプレ未対応です。')
        print('   手動で drafts/ に作業成果物を保存してください。')
        sys.exit(0)

    prompts_dir = os.path.join(folder_path, 'prompts')
    os.makedirs(prompts_dir, exist_ok=True)

    for filename, content in prompts.items():
        prompt_path = os.path.join(prompts_dir, filename)
        with open(prompt_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'✅ 生成: {prompt_path}')

    print()
    print('=' * 50)
    print('次のステップ')
    print('=' * 50)
    print('1. prompts/ 内のプロンプトをClaudeに貼り付け')
    print('2. 生成結果を drafts/ に保存')
    print('3. 人間レビュー・編集')
    print('4. python3 scripts/deliver/quality_check.py "{}"'.format(folder_name))
    print()


if __name__ == '__main__':
    main()
