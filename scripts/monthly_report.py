#!/usr/bin/env python3
"""
月次レポート生成
使い方: python3 scripts/monthly_report.py [YYYY-MM]
"""

import csv
import os
import sys
from datetime import datetime
from collections import defaultdict

CSV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'applications.csv')


def load_applications():
    if not os.path.exists(CSV_FILE):
        print(f'❌ {CSV_FILE} が見つかりません')
        return None
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def analyze_month(applications, target_ym=None):
    if target_ym is None:
        target_ym = datetime.now().strftime('%Y-%m')

    month_apps = [a for a in applications if a.get('date', '').startswith(target_ym)]

    stats = {
        'target_month': target_ym,
        'total_applications': len(month_apps),
        'replies': len([a for a in month_apps if a.get('status') in ['返信', '受注']]),
        'orders': len([a for a in month_apps if a.get('status') == '受注']),
        'revenue': sum(int(a.get('price', 0) or 0) for a in month_apps if a.get('status') == '受注'),
        'by_site': defaultdict(lambda: {'apps': 0, 'orders': 0, 'revenue': 0}),
    }

    for a in month_apps:
        site = a.get('site', 'unknown')
        stats['by_site'][site]['apps'] += 1
        if a.get('status') == '受注':
            stats['by_site'][site]['orders'] += 1
            stats['by_site'][site]['revenue'] += int(a.get('price', 0) or 0)

    return stats


def print_report(stats):
    print('=' * 50)
    print(f'📊 月次レポート（{stats["target_month"]}）')
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

    if stats['orders'] > 0:
        avg_unit_price = stats['revenue'] / stats['orders']
        print(f'  平均単価: ¥{avg_unit_price:,.0f}')

    if stats['by_site']:
        print(f'\n【サイト別実績】')
        for site, data in sorted(stats['by_site'].items(), key=lambda x: -x[1]['revenue']):
            apps = data['apps']
            orders = data['orders']
            rate = orders / apps * 100 if apps > 0 else 0
            print(f'  {site}:')
            print(f'    応募 {apps}件 / 受注 {orders}件 ({rate:.0f}%)')
            print(f'    売上 ¥{data["revenue"]:,}')

    # 目標達成率
    monthly_goal = 300000
    progress = stats['revenue'] / monthly_goal * 100 if monthly_goal > 0 else 0
    print(f'\n【月目標達成率】')
    print(f'  月目標: ¥{monthly_goal:,}')
    print(f'  実績:   ¥{stats["revenue"]:,}')
    print(f'  達成率: {progress:.1f}%')

    # プログレスバー
    bar_length = 30
    filled = int(bar_length * min(progress / 100, 1.0))
    bar = '█' * filled + '░' * (bar_length - filled)
    print(f'  [{bar}]')

    # アドバイス
    print(f'\n【改善提案】')
    if progress < 10:
        print(f'  💡 まずは評価5件の獲得を最優先')
        print(f'  💡 タスク形式の案件にも参加')
    elif progress < 30:
        print(f'  💡 応募数を週20件以上に')
        print(f'  💡 単価3,000円以上に絞る')
    elif progress < 70:
        print(f'  💪 リピート率向上を意識')
        print(f'  💪 継続案件の獲得を狙う')
    elif progress < 100:
        print(f'  🎯 単価アップのタイミング')
        print(f'  🎯 柱B営業を本格化')
    else:
        print(f'  🎉 目標達成！次のステージへ')
        print(f'  🎉 直接契約に切り替え検討')

    print('=' * 50)


def main():
    target_ym = sys.argv[1] if len(sys.argv) > 1 else None

    applications = load_applications()
    if applications is None:
        return

    stats = analyze_month(applications, target_ym)
    print_report(stats)


if __name__ == '__main__':
    main()
