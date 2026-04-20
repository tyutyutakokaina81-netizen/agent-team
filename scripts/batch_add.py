#!/usr/bin/env python3
"""
複数応募を一気に追加するスクリプト
使い方: python3 scripts/batch_add.py
"""

import csv
import os
from datetime import datetime

CSV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'applications.csv')
FIELDNAMES = ['date', 'site', 'job_name', 'price', 'status', 'url', 'note']


def init_csv():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(FIELDNAMES)


def batch_add():
    """カンマ区切りの複数行を一気に追加"""
    print('=' * 50)
    print('📝 一括応募記録（複数行入力）')
    print('=' * 50)
    print('形式: サイト,案件名,報酬額')
    print('例:   cw,データ入力,3000')
    print('')
    print('1行ずつ入力して、最後に空行でEnter:')
    print('')

    rows = []
    date = datetime.now().strftime('%Y-%m-%d')

    while True:
        line = input().strip()
        if not line:
            break
        parts = line.split(',')
        if len(parts) < 3:
            print('  ❌ 形式エラー。「サイト,案件名,報酬額」')
            continue
        site, job_name, price = parts[0].strip(), parts[1].strip(), parts[2].strip()
        rows.append([date, site, job_name, price, '応募', '', ''])
        print(f'  ✓ {site}: {job_name} (¥{price})')

    if not rows:
        print('❌ 何も記録されませんでした')
        return

    with open(CSV_FILE, 'a', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    print(f'\n✅ {len(rows)}件の応募を一括記録しました')


if __name__ == '__main__':
    init_csv()
    batch_add()
