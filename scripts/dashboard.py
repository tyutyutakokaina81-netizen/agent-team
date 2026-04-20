#!/usr/bin/env python3
"""
HTMLダッシュボード生成
使い方: python3 scripts/dashboard.py
    → dashboard.html をブラウザで開く
"""

import csv
import os
from datetime import datetime, timedelta
from collections import defaultdict

CSV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'applications.csv')
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dashboard.html')


def load_applications():
    if not os.path.exists(CSV_FILE):
        return []
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def calculate_stats(apps):
    today = datetime.now().strftime('%Y-%m-%d')
    this_month = datetime.now().strftime('%Y-%m')

    today_apps = [a for a in apps if a.get('date') == today]
    month_apps = [a for a in apps if a.get('date', '').startswith(this_month)]

    total_orders = len([a for a in apps if a.get('status') == '受注'])
    total_revenue = sum(int(a.get('price', 0) or 0) for a in apps if a.get('status') == '受注')
    month_revenue = sum(int(a.get('price', 0) or 0) for a in month_apps if a.get('status') == '受注')

    site_stats = defaultdict(lambda: {'apps': 0, 'orders': 0})
    for a in apps:
        site = a.get('site', 'unknown')
        site_stats[site]['apps'] += 1
        if a.get('status') == '受注':
            site_stats[site]['orders'] += 1

    daily_counts = defaultdict(int)
    for a in apps:
        daily_counts[a.get('date', '')] += 1

    recent_dates = []
    today_dt = datetime.now()
    for i in range(13, -1, -1):
        date = (today_dt - timedelta(days=i)).strftime('%Y-%m-%d')
        recent_dates.append((date, daily_counts.get(date, 0)))

    return {
        'total_apps': len(apps),
        'today_apps': len(today_apps),
        'month_apps': len(month_apps),
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'month_revenue': month_revenue,
        'win_rate': (total_orders / len(apps) * 100) if apps else 0,
        'month_progress': (month_revenue / 300000 * 100) if month_revenue else 0,
        'site_stats': dict(site_stats),
        'recent_dates': recent_dates,
        'recent_apps': sorted(apps, key=lambda x: x.get('date', ''), reverse=True)[:10],
    }


def generate_html(stats):
    recent_apps_html = '\n'.join([
        f'''<tr>
          <td>{a.get('date', '')}</td>
          <td>{a.get('site', '')}</td>
          <td>{a.get('job_name', '')}</td>
          <td class="right">¥{int(a.get('price', 0) or 0):,}</td>
          <td><span class="badge badge-{_status_class(a.get('status', ''))}">{a.get('status', '')}</span></td>
        </tr>'''
        for a in stats['recent_apps']
    ])

    site_rows = '\n'.join([
        f'''<tr>
          <td>{site}</td>
          <td class="right">{data['apps']}</td>
          <td class="right">{data['orders']}</td>
          <td class="right">{(data['orders']/data['apps']*100) if data['apps'] else 0:.1f}%</td>
        </tr>'''
        for site, data in stats['site_stats'].items()
    ])

    max_count = max([c for _, c in stats['recent_dates']], default=1) or 1
    chart_bars = '\n'.join([
        f'''<div class="bar-group">
          <div class="bar" style="height: {(count/max_count*100):.0f}%"></div>
          <div class="bar-label">{count}</div>
          <div class="bar-date">{date[-5:]}</div>
        </div>'''
        for date, count in stats['recent_dates']
    ])

    progress = min(stats['month_progress'], 100)

    html = f'''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>月30万自動化ダッシュボード</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Hiragino Sans", sans-serif;
    background: #f5f7fa;
    color: #1a202c;
    padding: 20px;
    line-height: 1.6;
  }}
  .container {{ max-width: 1100px; margin: 0 auto; }}
  h1 {{
    font-size: 28px;
    margin-bottom: 8px;
    color: #1a365d;
  }}
  .subtitle {{
    color: #718096;
    font-size: 14px;
    margin-bottom: 24px;
  }}
  .grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
    margin-bottom: 24px;
  }}
  .card {{
    background: white;
    padding: 20px;
    border-radius: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  }}
  .card-label {{
    color: #718096;
    font-size: 13px;
    margin-bottom: 8px;
  }}
  .card-value {{
    font-size: 28px;
    font-weight: 700;
    color: #1a365d;
  }}
  .card-value.success {{ color: #38a169; }}
  .card-value.warning {{ color: #d69e2e; }}
  .card-sub {{
    font-size: 12px;
    color: #a0aec0;
    margin-top: 4px;
  }}
  .progress-container {{
    background: white;
    padding: 24px;
    border-radius: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    margin-bottom: 24px;
  }}
  .progress-title {{
    font-size: 14px;
    color: #718096;
    margin-bottom: 12px;
  }}
  .progress-bar {{
    background: #edf2f7;
    border-radius: 20px;
    overflow: hidden;
    height: 32px;
    position: relative;
  }}
  .progress-fill {{
    background: linear-gradient(90deg, #48bb78, #38a169);
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: flex-end;
    padding-right: 12px;
    color: white;
    font-weight: 600;
    font-size: 13px;
    transition: width 0.5s;
  }}
  .section {{
    background: white;
    padding: 24px;
    border-radius: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    margin-bottom: 24px;
  }}
  .section-title {{
    font-size: 18px;
    margin-bottom: 16px;
    color: #1a365d;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
  }}
  th, td {{
    padding: 10px;
    text-align: left;
    border-bottom: 1px solid #e2e8f0;
    font-size: 14px;
  }}
  th {{
    background: #f7fafc;
    color: #4a5568;
    font-weight: 600;
  }}
  .right {{ text-align: right; }}
  .badge {{
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 600;
  }}
  .badge-apply {{ background: #e2e8f0; color: #4a5568; }}
  .badge-reply {{ background: #bee3f8; color: #2b6cb0; }}
  .badge-order {{ background: #c6f6d5; color: #22543d; }}
  .badge-lost {{ background: #fed7d7; color: #742a2a; }}
  .chart {{
    display: flex;
    align-items: flex-end;
    height: 160px;
    gap: 8px;
    margin-top: 16px;
    padding: 0 10px;
  }}
  .bar-group {{
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    height: 100%;
  }}
  .bar {{
    width: 100%;
    background: #4299e1;
    border-radius: 4px 4px 0 0;
    min-height: 2px;
    margin-top: auto;
  }}
  .bar-label {{ font-size: 11px; color: #4a5568; margin-top: 4px; }}
  .bar-date {{ font-size: 10px; color: #a0aec0; }}
  .refresh {{
    background: #4299e1;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 13px;
  }}
  .footer {{
    text-align: center;
    color: #a0aec0;
    font-size: 12px;
    margin-top: 32px;
  }}
</style>
</head>
<body>
  <div class="container">
    <h1>📊 月30万自動化 ダッシュボード</h1>
    <div class="subtitle">最終更新: {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>

    <div class="grid">
      <div class="card">
        <div class="card-label">今月の売上</div>
        <div class="card-value success">¥{stats['month_revenue']:,}</div>
        <div class="card-sub">目標 ¥300,000</div>
      </div>
      <div class="card">
        <div class="card-label">今月の応募</div>
        <div class="card-value">{stats['month_apps']}</div>
        <div class="card-sub">件</div>
      </div>
      <div class="card">
        <div class="card-label">累計受注</div>
        <div class="card-value success">{stats['total_orders']}</div>
        <div class="card-sub">件</div>
      </div>
      <div class="card">
        <div class="card-label">累計応募</div>
        <div class="card-value">{stats['total_apps']}</div>
        <div class="card-sub">件</div>
      </div>
      <div class="card">
        <div class="card-label">受注率</div>
        <div class="card-value {'success' if stats['win_rate'] >= 10 else 'warning'}">{stats['win_rate']:.1f}%</div>
        <div class="card-sub">累計</div>
      </div>
      <div class="card">
        <div class="card-label">今日の応募</div>
        <div class="card-value">{stats['today_apps']}</div>
        <div class="card-sub">件</div>
      </div>
    </div>

    <div class="progress-container">
      <div class="progress-title">📈 月30万目標の進捗（{stats['month_progress']:.1f}%）</div>
      <div class="progress-bar">
        <div class="progress-fill" style="width: {progress}%">{progress:.0f}%</div>
      </div>
    </div>

    <div class="section">
      <div class="section-title">📅 過去14日の応募推移</div>
      <div class="chart">
        {chart_bars}
      </div>
    </div>

    <div class="section">
      <div class="section-title">🌐 サイト別実績</div>
      <table>
        <thead>
          <tr><th>サイト</th><th class="right">応募</th><th class="right">受注</th><th class="right">受注率</th></tr>
        </thead>
        <tbody>
          {site_rows if site_rows else '<tr><td colspan="4" style="text-align:center;color:#a0aec0;">データなし</td></tr>'}
        </tbody>
      </table>
    </div>

    <div class="section">
      <div class="section-title">📋 最近の応募（10件）</div>
      <table>
        <thead>
          <tr><th>日付</th><th>サイト</th><th>案件名</th><th class="right">報酬</th><th>ステータス</th></tr>
        </thead>
        <tbody>
          {recent_apps_html if recent_apps_html else '<tr><td colspan="5" style="text-align:center;color:#a0aec0;">データなし</td></tr>'}
        </tbody>
      </table>
    </div>

    <div class="footer">
      Generated by agent-team / 更新: python3 scripts/dashboard.py
    </div>
  </div>
</body>
</html>
'''
    return html


def _status_class(status):
    mapping = {
        '応募': 'apply',
        '返信': 'reply',
        '受注': 'order',
        '失注': 'lost',
    }
    return mapping.get(status, 'apply')


def main():
    apps = load_applications()
    stats = calculate_stats(apps)
    html = generate_html(stats)

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f'✅ ダッシュボード生成完了: {OUTPUT_FILE}')
    print(f'   ブラウザで開く:')
    print(f'   open {OUTPUT_FILE}  (Mac)')


if __name__ == '__main__':
    main()
