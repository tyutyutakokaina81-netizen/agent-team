#!/usr/bin/env python3
"""
応募トラッカー（対話式）
使い方: python3 scripts/application_tracker.py
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
        print(f'✅ {CSV_FILE} を作成しました')


def add_application():
    print('\n📝 新規応募を記録')
    date = input('日付（YYYY-MM-DD、空白で今日）: ').strip() or datetime.now().strftime('%Y-%m-%d')
    site = input('サイト（cw/lancers/mama等）: ').strip()
    job_name = input('案件名: ').strip()
    price = input('報酬額: ').strip() or '0'
    status = input('ステータス（応募/返信/受注/失注）: ').strip() or '応募'
    url = input('URL（任意）: ').strip()
    note = input('メモ（任意）: ').strip()

    with open(CSV_FILE, 'a', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([date, site, job_name, price, status, url, note])

    print(f'✅ 記録しました: {job_name}')


def update_status():
    print('\n🔄 ステータス更新')
    keyword = input('更新する案件名（部分一致）: ').strip()
    new_status = input('新しいステータス: ').strip()

    rows = []
    updated_count = 0
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if keyword in row.get('job_name', ''):
                row['status'] = new_status
                print(f"  ✏️ 更新: {row['job_name']} → {new_status}")
                updated_count += 1
            rows.append(row)

    with open(CSV_FILE, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    print(f'✅ {updated_count}件 更新しました')


def show_stats():
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    total = len(rows)
    orders = len([r for r in rows if r.get('status') == '受注'])
    revenue = sum(int(r.get('price', 0) or 0) for r in rows if r.get('status') == '受注')

    print('\n' + '=' * 50)
    print('📊 統計')
    print('=' * 50)
    print(f'総応募数: {total}件')
    print(f'受注数: {orders}件')
    if total > 0:
        print(f'受注率: {orders/total*100:.1f}%')
    print(f'総売上: ¥{revenue:,}')
    print('=' * 50)


def list_recent():
    print('\n📋 最近の応募（最新10件）')
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    for row in rows[-10:]:
        print(f"  {row.get('date')} [{row.get('status')}] {row.get('site')}: {row.get('job_name')}")


def main():
    init_csv()

    while True:
        print('\n' + '=' * 50)
        print('🎯 応募トラッカー')
        print('=' * 50)
        print('1. 新規応募を記録')
        print('2. ステータス更新')
        print('3. 統計表示')
        print('4. 最近の応募を表示')
        print('5. 終了')

        choice = input('\n選択: ').strip()

        if choice == '1':
            add_application()
        elif choice == '2':
            update_status()
        elif choice == '3':
            show_stats()
        elif choice == '4':
            list_recent()
        elif choice == '5':
            break
        else:
            print('❌ 無効な選択')

    print('👋 お疲れ様でした！')


if __name__ == '__main__':
    main()
