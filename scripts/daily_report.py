#!/usr/bin/env python3
"""
日次レポート自動生成スクリプト
使い方: python3 scripts/daily_report.py
"""

import csv
import os
from datetime import datetime, timedelta
from collections import defaultdict

CSV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'applications.csv')


def load_applications():
    if not os.path.exists(CSV_FILE):
        print(f"❌ {CSV_FILE} が見つかりません。")
        print("   先に application_tracker.py で応募を記録してください。")
        return None
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def analyze_today(applications):
    today = datetime.now().strftime('%Y-%m-%d')
    today_apps = [a for a in applications if a.get('date') == today]
    stats = {
        'applications': len(today_apps),
        'replies': len([a for a in today_apps if a.get('status') in ['返信', '受注']]),
        'orders': len([a for a in today_apps if a.get('status') == '受注']),
        'by_site': defaultdict(int),
    }
    for app in today_apps:
        stats['by_site'][app.get('site', 'unknown')] += 1
    return stats


def analyze_week(applications):
    week_ago = datetime.now() - timedelta(days=7)
    week_apps = []
    for a in applications:
        try:
            d = datetime.strptime(a.get('date', ''), '%Y-%m-%d')
            if d >= week_ago:
                week_apps.append(a)
        except ValueError:
            continue
    return {
        'applications': len(week_apps),
        'orders': len([a for a in week_apps if a.get('status') == '受注']),
        'revenue': sum(int(a.get('price', 0) or 0) for a in week_apps if a.get('status') == '受注'),
    }


def print_report(today_stats, week_stats):
    print('=' * 50)
    print(f"📊 日次レポート（{datetime.now().strftime('%Y-%m-%d')}）")
    print('=' * 50)
    print('\n【今日の実績】')
    print(f"  応募数: {today_stats['applications']}件")
    print(f"  返信数: {today_stats['replies']}件")
    print(f"  受注数: {today_stats['orders']}件")

    if today_stats['by_site']:
        print('\n【サイト別応募】')
        for site, count in today_stats['by_site'].items():
            print(f"  {site}: {count}件")

    print('\n【今週の実績】')
    print(f"  応募数: {week_stats['applications']}件")
    print(f"  受注数: {week_stats['orders']}件")
    print(f"  売上: ¥{week_stats['revenue']:,}")

    if week_stats['applications'] > 0:
        win_rate = (week_stats['orders'] / week_stats['applications']) * 100
        print(f"  受注率: {win_rate:.1f}%")

    print('=' * 50)


def main():
    applications = load_applications()
    if applications is None:
        return
    today_stats = analyze_today(applications)
    week_stats = analyze_week(applications)
    print_report(today_stats, week_stats)


if __name__ == '__main__':
    main()
