#!/usr/bin/env python3
"""
納品ファイル生成＆納品メール作成
使い方: python3 scripts/deliver/package.py <folder_name>
"""

import json
import os
import shutil
import sys
from datetime import datetime

DELIVERIES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    '..',
    'deliveries',
)


DELIVERY_EMAIL_ARTICLE = """件名：【納品のお知らせ】{job_title}

{client} 様

お世話になっております。
[あなたのお名前]です。

{job_title}の納品物をお送りいたします。

■ 納品内容
・記事本文（{char_count}字）
・タイトル案
・メタディスクリプション

■ 作業期間
{period}

■ 特記事項
{notes}

ご確認のほど、よろしくお願いいたします。
修正点等ございましたらお知らせください。

---
[あなたのお名前]
[メールアドレス]
"""

DELIVERY_EMAIL_SNS = """件名：【納品のお知らせ】{job_title}

{client} 様

お世話になっております。
[あなたのお名前]です。

{job_title}の{post_count}投稿分の納品物をお送りいたします。

■ 納品内容
・投稿文×{post_count}本
・ハッシュタグ選定済み
・画像用テキスト案

■ 作業期間
{period}

■ 予約投稿について
Bufferやストーリーズで順次予約投稿いたします。

ご確認のほど、よろしくお願いいたします。
内容のご調整があればお知らせください。

---
[あなたのお名前]
[メールアドレス]
"""


def main():
    if len(sys.argv) < 2:
        print('使い方: python3 scripts/deliver/package.py <folder_name>')
        sys.exit(1)

    folder_name = sys.argv[1]
    folder_path = os.path.join(DELIVERIES_DIR, folder_name)
    meta_path = os.path.join(folder_path, 'meta.json')

    if not os.path.exists(meta_path):
        print(f'❌ meta.json が見つかりません')
        sys.exit(1)

    with open(meta_path, 'r', encoding='utf-8') as f:
        meta = json.load(f)

    drafts_dir = os.path.join(folder_path, 'drafts')
    final_dir = os.path.join(folder_path, 'final')
    os.makedirs(final_dir, exist_ok=True)

    print('=' * 50)
    print(f'📦 納品パッケージ生成: {meta["job_title"]}')
    print('=' * 50)

    # drafts の最新ファイルを final にコピー
    if not os.path.exists(drafts_dir):
        print(f'❌ drafts フォルダが空: {drafts_dir}')
        sys.exit(1)

    drafts = [f for f in os.listdir(drafts_dir) if f.endswith(('.md', '.txt', '.csv', '.xlsx'))]
    if not drafts:
        print('❌ drafts に納品可能なファイルがない')
        sys.exit(1)

    # 日付付きファイル名で final に配置
    date = datetime.now().strftime('%Y%m%d')
    copied = []
    for draft in drafts:
        ext = os.path.splitext(draft)[1]
        new_name = f'{date}_{meta["job_title"][:20]}{ext}'.replace('/', '_').replace(' ', '_')
        src = os.path.join(drafts_dir, draft)
        dst = os.path.join(final_dir, new_name)
        shutil.copy(src, dst)
        copied.append(new_name)
        print(f'✅ 納品ファイル: final/{new_name}')

    # 納品メール生成
    job_type = meta.get('job_type', 'other')

    email_vars = {
        'job_title': meta['job_title'],
        'client': meta['client'],
        'period': f"{meta['date']} 〜 {date[:4]}-{date[4:6]}-{date[6:]}",
        'notes': 'なし',
    }

    if job_type == 'article':
        email_vars['char_count'] = meta['details'].get('char_count', '?')
        email = DELIVERY_EMAIL_ARTICLE.format(**email_vars)
    elif job_type == 'sns':
        email_vars['post_count'] = meta['details'].get('post_count', '?')
        email = DELIVERY_EMAIL_SNS.format(**email_vars)
    else:
        email = f"""件名：【納品のお知らせ】{meta['job_title']}

{meta['client']} 様

お世話になっております。
[あなたのお名前]です。

{meta['job_title']}の納品物をお送りいたします。

ご確認のほど、よろしくお願いいたします。

---
[あなたのお名前]
"""

    email_path = os.path.join(folder_path, 'delivery_email.txt')
    with open(email_path, 'w', encoding='utf-8') as f:
        f.write(email)
    print(f'✅ 納品メール: delivery_email.txt')

    # 請求書メモ
    invoice_note = f"""# 請求メモ

受注日: {meta['date']}
納品日: {date[:4]}-{date[4:6]}-{date[6:]}
クライアント: {meta['client']}
案件: {meta['job_title']}
報酬: ¥{meta['price']:,}

## 次のステップ
1. 納品メール送信
2. 検収確認
3. 請求書発行（CFO/outputs/請求書テンプレート.md 参照）
4. 入金確認
5. application_tracker.py でステータス更新
"""
    invoice_path = os.path.join(folder_path, 'invoice_note.md')
    with open(invoice_path, 'w', encoding='utf-8') as f:
        f.write(invoice_note)
    print(f'✅ 請求メモ: invoice_note.md')

    # ステータス更新
    meta['status'] = 'delivered'
    meta['delivery_date'] = datetime.now().strftime('%Y-%m-%d')
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print()
    print('=' * 50)
    print('🎉 納品パッケージ完成')
    print('=' * 50)
    print()
    print('送付する内容：')
    print(f'  📂 フォルダ: {folder_path}')
    print(f'  📄 納品物: {final_dir}')
    for f in copied:
        print(f'     - {f}')
    print(f'  📧 メール下書き: {email_path}')
    print()
    print('次のアクション：')
    print('1. delivery_email.txt の [ ] を埋めて送信')
    print('2. クライアント検収後、請求書送付（CFO/outputs/請求書テンプレート.md）')
    print('3. 入金確認したら application_tracker.py で「受注」→売上登録')


if __name__ == '__main__':
    main()
