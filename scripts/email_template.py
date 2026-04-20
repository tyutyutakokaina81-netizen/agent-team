#!/usr/bin/env python3
"""
メールテンプレ生成
使い方: python3 scripts/email_template.py
"""

import re

TEMPLATES = {
    'apply': '''件名：【{job_name}】応募させていただきます

{client_name} 様

はじめまして。
{my_name}と申します。

{job_summary}の件で応募させていただきます。

【対応内容】
・指示内容を正確に理解し、ミスのない作業を徹底
・ダブルチェックによる品質確保
・納期厳守・迅速な連絡対応

【稼働時間】
平日3〜5時間、土日対応可能

【ポートフォリオ】
{portfolio_url}

ご指示いただければすぐに作業開始いたします。
ご検討のほど、よろしくお願いいたします。

---
{my_name}
{email}
''',
    'delivery': '''件名：【納品のお知らせ】{job_name}

{client_name} 様

お世話になっております。
{my_name}です。

{job_name}の納品物をお送りいたします。

■ 納品内容
{deliverables}

■ 作業期間
{period}

ご確認のほど、よろしくお願いいたします。
修正点等ございましたらお知らせください。

---
{my_name}
''',
    'invoice': '''件名：【請求書送付のご案内】{year}年{month}月分

{client_name} 様

お世話になっております。
{my_name}です。

{year}年{month}月分のご請求書を添付にてお送りいたします。

■ ご請求金額：¥{amount}（税込）
■ お支払期限：{due_date}
■ お振込先：{bank_info}

ご査収のほど、よろしくお願いいたします。

---
{my_name}
''',
    'follow_up': '''件名：【先日のご依頼について】フォローアップ

{client_name} 様

お世話になっております。
{my_name}です。

先日納品いたしました{job_name}について、
お役に立てておりますでしょうか。

もし何かご不明点や追加のご要望がございましたら
お気軽にお知らせください。

また、類似のお仕事がございましたら、
引き続きお手伝いさせていただければ幸いです。

---
{my_name}
''',
}


def generate():
    print('=' * 50)
    print('📧 メールテンプレ生成')
    print('=' * 50)
    print('1. 応募メール')
    print('2. 納品メール')
    print('3. 請求書送付メール')
    print('4. フォローアップメール')

    choice = input('\n選択: ').strip()
    key_map = {'1': 'apply', '2': 'delivery', '3': 'invoice', '4': 'follow_up'}
    template_key = key_map.get(choice)

    if not template_key:
        print('❌ 無効な選択')
        return

    template = TEMPLATES[template_key]
    variables = set(re.findall(r'\{(\w+)\}', template))

    values = {}
    print(f'\n以下の項目を入力してください（Enterで空欄可）：')
    for var in sorted(variables):
        values[var] = input(f'  {var}: ').strip() or f'[{var}を記入]'

    result = template.format(**values)
    print('\n' + '=' * 50)
    print('📄 生成されたメール')
    print('=' * 50)
    print(result)
    print('=' * 50)
    print('👆 上記をコピペして使用してください')


if __name__ == '__main__':
    generate()
