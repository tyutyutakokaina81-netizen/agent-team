#!/usr/bin/env python3
"""
新規受注の対話型入力→作業フォルダ自動生成
使い方: python3 scripts/deliver/new_job.py

エッジケース対応：
- 必須項目の空欄を拒否
- 特殊文字を除去＆長さ制限
- 日付/数値のバリデーション
- フォルダ名重複時は連番付与
"""

import json
import os
import re
import sys
from datetime import datetime


DELIVERIES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    '..',
    'deliveries',
)


def slugify(text, max_len=40):
    """日本語含む文字列をフォルダ名用にサニタイズ"""
    if not text:
        return ''
    text = text.strip()
    # 空白・パス区切りを _ に
    text = re.sub(r'\s+', '_', text)
    text = text.replace('/', '_').replace('\\', '_')
    # 制御文字削除
    text = ''.join(c for c in text if ord(c) >= 0x20)
    # OSで使えない文字を削除
    bad = '<>:"|?*'
    for c in bad:
        text = text.replace(c, '')
    # 先頭末尾のドット・アンダースコアをトリム
    text = text.strip('._ ')
    return text[:max_len]


def validate_required(value, field_name, min_len=1):
    """必須項目の検証。失敗時は終了"""
    if not value or len(value.strip()) < min_len:
        print(f'❌ {field_name}は必須です（空欄不可）')
        sys.exit(1)
    return value.strip()


def input_required(prompt, field_name, min_len=1, max_retries=3):
    """必須入力（空欄なら再入力プロンプト）"""
    for _ in range(max_retries):
        value = input(prompt).strip()
        if value and len(value) >= min_len:
            return value
        print(f'  ⚠️ {field_name}は必須です。再入力してください。')
    print(f'❌ {field_name}の入力に失敗（{max_retries}回試行）')
    sys.exit(1)


def input_choice(prompt, valid_choices, default=None):
    """選択肢の検証"""
    for _ in range(3):
        value = input(prompt).strip()
        if not value and default is not None:
            return default
        if value in valid_choices:
            return value
        print(f'  ⚠️ {list(valid_choices)}のいずれかを入力してください')
    print('❌ 選択の入力に失敗')
    sys.exit(1)


def input_int(prompt, default=0, min_val=0, max_val=10_000_000):
    """数値入力（「円」や「,」を除去）"""
    value = input(prompt).strip()
    if not value:
        return default
    # 数字以外を削除（「5,000円」→「5000」対応）
    cleaned = re.sub(r'[^\d]', '', value)
    if not cleaned:
        print(f'  ⚠️ 数値として解釈できません。{default}を使用')
        return default
    num = int(cleaned)
    if num < min_val or num > max_val:
        print(f'  ⚠️ 範囲外の値（{num}）。{default}を使用')
        return default
    return num


def input_date(prompt, allow_empty=True):
    """日付入力（YYYY-MM-DD形式、曖昧な形式も吸収）"""
    value = input(prompt).strip()
    if not value:
        if allow_empty:
            return ''
        print('❌ 日付は必須です')
        sys.exit(1)

    # 複数フォーマット対応
    for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%Y.%m.%d', '%Y%m%d'):
        try:
            dt = datetime.strptime(value, fmt)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue
    print(f'  ⚠️ 日付形式が不正（{value}）。空欄として記録')
    return ''


def unique_folder_name(base_path):
    """フォルダ名が既に存在する場合は連番を付与"""
    if not os.path.exists(base_path):
        return base_path
    for i in range(2, 100):
        candidate = f'{base_path}_{i}'
        if not os.path.exists(candidate):
            return candidate
    # 稀に100個超え
    return f'{base_path}_{datetime.now().strftime("%H%M%S")}'


def main():
    print('=' * 50)
    print('📥 新規受注セットアップ')
    print('=' * 50)
    print()

    date = datetime.now().strftime('%Y-%m-%d')

    # 必須：クライアント名・案件名
    client = input_required('クライアント名: ', 'クライアント名')
    job_title = input_required('案件名: ', '案件名')

    # slugifyで空になっていないか最終確認
    if not slugify(client) or not slugify(job_title):
        print('❌ クライアント名または案件名にファイル名として使える文字が含まれていません')
        sys.exit(1)

    print()
    print('案件タイプ：')
    print('  1. 記事執筆（SEO記事・ブログ）')
    print('  2. SNS投稿（Instagram・X・Facebook）')
    print('  3. データ入力・リスト作成')
    print('  4. コピペ作業')
    print('  5. その他')

    type_choice = input_choice('選択（1-5）: ', {'1', '2', '3', '4', '5'})
    type_map = {
        '1': 'article', '2': 'sns', '3': 'data_entry',
        '4': 'copy_paste', '5': 'other',
    }
    job_type = type_map[type_choice]

    price = input_int('報酬金額（円）: ', default=0)
    deadline = input_date('納期（YYYY-MM-DD）: ')

    details = {}
    if job_type == 'article':
        details['keyword'] = input_required('メインキーワード: ', 'メインキーワード')
        details['char_count'] = str(input_int('文字数（例：3000）: ', default=3000, min_val=100, max_val=50000))
        details['persona'] = input('ターゲット読者: ').strip() or '一般読者'
        details['tone'] = input('トーン（丁寧/カジュアル/専門的）: ').strip() or '丁寧'
        details['reference_urls'] = input('参考URL（カンマ区切り・任意）: ').strip()
    elif job_type == 'sns':
        details['industry'] = input_required('クライアント業種: ', '業種')
        details['target'] = input('ターゲット: ').strip() or '一般顧客'
        details['post_count'] = str(input_int('投稿数（例：15）: ', default=15, min_val=1, max_val=100))
        details['platforms'] = input('媒体（Instagram/X/Facebook）: ').strip() or 'Instagram'
        details['theme'] = input('今月の訴求テーマ: ').strip() or '通常運用'
    elif job_type == 'data_entry':
        details['source'] = input_required('入力元（Webサイト/PDF等）: ', '入力元')
        details['output_format'] = input('出力形式（Excel/CSV/スプレッドシート）: ').strip() or 'Excel'
        details['count'] = str(input_int('件数: ', default=100, min_val=1))
        details['columns'] = input('列項目（カンマ区切り）: ').strip()
    elif job_type == 'copy_paste':
        details['source'] = input_required('コピー元: ', 'コピー元')
        details['destination'] = input_required('ペースト先: ', 'ペースト先')
        details['count'] = str(input_int('件数: ', default=100, min_val=1))
    else:
        details['description'] = input_required('作業内容（自由記述）: ', '作業内容')

    memo = input('その他メモ（任意）: ').strip()

    # フォルダ作成（重複時は連番）
    folder_name = f"{date}_{slugify(client)}_{slugify(job_title)}"
    folder_path = os.path.join(DELIVERIES_DIR, folder_name)
    folder_path = unique_folder_name(folder_path)
    folder_name = os.path.basename(folder_path)

    try:
        os.makedirs(folder_path, exist_ok=False)
    except OSError as e:
        print(f'❌ フォルダ作成失敗: {e}')
        sys.exit(1)

    # メタデータ保存
    meta = {
        'date': date,
        'client': client,
        'job_title': job_title,
        'job_type': job_type,
        'price': price,
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
**納期：** {deadline or '未定'}
**報酬：** ¥{price:,} ({job_type})

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
    os.makedirs(os.path.join(folder_path, 'prompts'), exist_ok=True)

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
    try:
        main()
    except KeyboardInterrupt:
        print('\n\n⚠️ 中断されました。フォルダは作成されていません。')
        sys.exit(130)
    except EOFError:
        print('\n\n❌ 入力が途中で切れました')
        sys.exit(1)
