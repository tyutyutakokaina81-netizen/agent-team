#!/usr/bin/env python3
"""
新規受注の対話型入力→作業フォルダ自動生成
使い方: python3 scripts/deliver/new_job.py
"""

import json
import os
from datetime import datetime


DELIVERIES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    '..',
    'deliveries',
)


def slugify(text):
    """日本語含む文字列をフォルダ名用にサニタイズ"""
    text = text.strip().replace(' ', '_').replace('/', '_').replace('\\', '_')
    # 使えない文字を削除
    bad = '<>:"|?*'
    for c in bad:
        text = text.replace(c, '')
    return text[:40]


def main():
    print('=' * 50)
    print('📥 新規受注セットアップ')
    print('=' * 50)

    date = datetime.now().strftime('%Y-%m-%d')

    print()
    client = input('クライアント名: ').strip()
    job_title = input('案件名: ').strip()
    print()
    print('案件タイプ：')
    print('  1. 記事執筆（SEO記事・ブログ）')
    print('  2. SNS投稿（Instagram・X・Facebook）')
    print('  3. データ入力・リスト作成')
    print('  4. コピペ作業')
    print('  5. その他')

    type_choice = input('選択（1-5）: ').strip()
    type_map = {
        '1': 'article',
        '2': 'sns',
        '3': 'data_entry',
        '4': 'copy_paste',
        '5': 'other',
    }
    job_type = type_map.get(type_choice, 'other')

    price = input('報酬金額（円）: ').strip() or '0'
    deadline = input('納期（YYYY-MM-DD）: ').strip()

    details = {}
    if job_type == 'article':
        details['keyword'] = input('メインキーワード: ').strip()
        details['char_count'] = input('文字数（例：3000）: ').strip()
        details['persona'] = input('ターゲット読者: ').strip()
        details['tone'] = input('トーン（丁寧/カジュアル/専門的）: ').strip()
        details['reference_urls'] = input('参考URL（カンマ区切り・任意）: ').strip()
    elif job_type == 'sns':
        details['industry'] = input('クライアント業種: ').strip()
        details['target'] = input('ターゲット: ').strip()
        details['post_count'] = input('投稿数（例：15）: ').strip()
        details['platforms'] = input('媒体（Instagram/X/Facebook）: ').strip()
        details['theme'] = input('今月の訴求テーマ: ').strip()
    elif job_type == 'data_entry':
        details['source'] = input('入力元（Webサイト/PDF等）: ').strip()
        details['output_format'] = input('出力形式（Excel/CSV/スプレッドシート）: ').strip()
        details['count'] = input('件数: ').strip()
        details['columns'] = input('列項目（カンマ区切り）: ').strip()
    elif job_type == 'copy_paste':
        details['source'] = input('コピー元: ').strip()
        details['destination'] = input('ペースト先: ').strip()
        details['count'] = input('件数: ').strip()
    else:
        details['description'] = input('作業内容（自由記述）: ').strip()

    memo = input('その他メモ（任意）: ').strip()

    # フォルダ作成
    folder_name = f"{date}_{slugify(client)}_{slugify(job_title)}"
    folder_path = os.path.join(DELIVERIES_DIR, folder_name)
    os.makedirs(folder_path, exist_ok=True)

    # メタデータ保存
    meta = {
        'date': date,
        'client': client,
        'job_title': job_title,
        'job_type': job_type,
        'price': int(price) if price.isdigit() else 0,
        'deadline': deadline,
        'details': details,
        'memo': memo,
        'status': 'in_progress',
    }

    meta_path = os.path.join(folder_path, 'meta.json')
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    # README.md 作成
    readme_content = f"""# {job_title}

**クライアント：** {client}
**受注日：** {date}
**納期：** {deadline}
**報酬：** ¥{int(price):,} ({job_type})

## 作業内容

"""
    for k, v in details.items():
        readme_content += f"- **{k}**: {v}\n"
    if memo:
        readme_content += f"\n## メモ\n{memo}\n"

    readme_content += f"""

## 📋 ワークフロー

次のコマンドを実行してください：

```bash
python3 scripts/deliver/generate.py "{folder_name}"
```

これにより Claude プロンプトが生成されます。

## ✅ 進捗チェックリスト

- [ ] プロンプト生成（generate.py）
- [ ] Claudeで下書き作成
- [ ] 人間レビュー
- [ ] 品質チェック（quality_check.py）
- [ ] 納品ファイル生成（package.py）
- [ ] 納品メール送信
- [ ] 請求書送付
- [ ] 入金確認
"""

    readme_path = os.path.join(folder_path, 'README.md')
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)

    # サブディレクトリ作成
    os.makedirs(os.path.join(folder_path, 'drafts'), exist_ok=True)
    os.makedirs(os.path.join(folder_path, 'final'), exist_ok=True)

    print()
    print('=' * 50)
    print('✅ 受注セットアップ完了')
    print('=' * 50)
    print(f'📂 作業フォルダ: {folder_path}')
    print()
    print('次のステップ：')
    print(f'  python3 scripts/deliver/generate.py "{folder_name}"')
    print()


if __name__ == '__main__':
    main()
