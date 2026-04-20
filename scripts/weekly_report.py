#!/usr/bin/env python3
"""
週次レポート生成
使い方: python3 scripts/weekly_report.py
"""

import csv
import os
from datetime import datetime, timedelta
from collections import defaultdict

CSV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'applications.csv')


def load_applications():
    if not os.path.exists(CSV_FILE):
        print(f'❌ {CSV_FILE} が見つかりません')
        return None
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def analyze_week(applications, days_ago=7):
    today = datetime.now()
    period_start = today - timedelta(days=days_ago)

    week_apps = []
    for a in applications:
        try:
            d = datetime.strptime(a.get('date', ''), '%Y-%m-%d')
            if d >= period_start:
                week_apps.append(a)
        except ValueError:
            continue

    stats = {
        'total_applications': len(week_apps),
        'replies': len([a for a in week_apps if a.get('status') in ['返信', '受注']]),
        'orders': len([a for a in week_apps if a.get('status') == '受注']),
        'revenue': sum(int(a.get('price', 0) or 0) for a in week_apps if a.get('status') == '受注'),
        'by_site': defaultdict(lambda: {'apps': 0, 'orders': 0, 'revenue': 0}),
        'daily': defaultdict(int),
    }

    for a in week_apps:
        site = a.get('site', 'unknown')
        date = a.get('date', '')
        stats['by_site'][site]['apps'] += 1
        stats['daily'][date] += 1
        if a.get('status') == '受注':
            stats['by_site'][site]['orders'] += 1
            stats['by_site'][site]['revenue'] += int(a.get('price', 0) or 0)

    return stats


def print_report(stats):
    print('=' * 50)
    print(f'📊 週次レポート（過去7日間）')
    print('=' * 50)

    print(f'\n【全体サマリー】')
    print(f'  総応募数: {stats["total_applications"]}件')
    print(f'  返信数: {stats["replies"]}件')
    print(f'  受注数: {stats["orders"]}件')
    print(f'  売上: ¥{stats["revenue"]:,}')

    if stats['total_applications'] > 0:
        reply_rate = stats['replies'] / stats['total_applications'] * 100
        win_rate = stats['orders'] / stats['total_applications'] * 100
        print(f'  返信率: {reply_rate:.1f}%')
        print(f'  受注率: {win_rate:.1f}%')

    if stats['by_site']:
        print(f'\n【サイト別実績】')
        for site, data in stats['by_site'].items():
            apps = data['apps']
            orders = data['orders']
            rate = orders / apps * 100 if apps > 0 else 0
            print(f'  {site}:')
            print(f'    応募 {apps}件 / 受注 {orders}件 ({rate:.0f}%) / 売上 ¥{data["revenue"]:,}')

    if stats['daily']:
        print(f'\n【日別応募推移】')
        today = datetime.now()
        for i in range(6, -1, -1):
            date = (today - timedelta(days=i)).strftime('%Y-%m-%d')
            count = stats['daily'].get(date, 0)
            bar = '█' * count if count > 0 else '·'
            print(f'  {date}: {bar} {count}件')

    # 目標達成率
    weekly_goal = 75000  # 月30万 ÷ 4週
    progress = stats['revenue'] / weekly_goal * 100 if weekly_goal > 0 else 0
    print(f'\n【目標達成率】')
    print(f'  週目標: ¥{weekly_goal:,}')
    print(f'  実績:   ¥{stats["revenue"]:,}')
    print(f'  達成率: {progress:.1f}%')

    if progress < 50:
        print(f'  💡 応募数を倍に増やすことを推奨')
    elif progress < 100:
        print(f'  💪 単価アップを意識しよう')
    else:
        print(f'  🎉 目標達成！ 単価交渉のタイミング')

    print('=' * 50)


def main():
    applications = load_applications()
    if applications is None:
        return
    stats = analyze_week(applications)
    print_report(stats)


if __name__ == '__main__':
    main()
