#!/usr/bin/env python3
"""
作業時間トラッカー（start/stop）
案件の実作業時間を計測→実時給を算出
使い方:
  python3 scripts/deliver/timer.py start <folder_name>
  python3 scripts/deliver/timer.py stop <folder_name>
  python3 scripts/deliver/timer.py status <folder_name>
"""

import json
import os
import sys
from datetime import datetime

DELIVERIES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    '..',
    'deliveries',
)


def load_timer(folder_path):
    path = os.path.join(folder_path, 'timer.json')
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'sessions': [], 'current_start': None}


def save_timer(folder_path, data):
    path = os.path.join(folder_path, 'timer.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def total_minutes(timer_data):
    """全セッションの合計分数"""
    total = 0
    for s in timer_data.get('sessions', []):
        total += s.get('minutes', 0)
    return total


def format_duration(minutes):
    h = minutes // 60
    m = minutes % 60
    return f'{h}時間{m}分'


def start(folder_path):
    timer = load_timer(folder_path)
    if timer.get('current_start'):
        print(f'⚠️  既に作業中です（開始: {timer["current_start"]}）')
        print('   stop を実行してから start してください')
        return

    now = datetime.now().isoformat(timespec='seconds')
    timer['current_start'] = now
    save_timer(folder_path, timer)

    total = total_minutes(timer)
    print(f'⏱️  作業開始: {now}')
    print(f'📊 これまでの累計: {format_duration(total)}')


def stop(folder_path, meta):
    timer = load_timer(folder_path)
    if not timer.get('current_start'):
        print('⚠️  まだ作業開始していません')
        return

    start_time = datetime.fromisoformat(timer['current_start'])
    end_time = datetime.now()
    minutes = int((end_time - start_time).total_seconds() / 60)

    if minutes < 1:
        print('⚠️  作業時間が1分未満。記録をスキップ。')
        timer['current_start'] = None
        save_timer(folder_path, timer)
        return

    timer['sessions'].append({
        'start': timer['current_start'],
        'end': end_time.isoformat(timespec='seconds'),
        'minutes': minutes,
    })
    timer['current_start'] = None
    save_timer(folder_path, timer)

    total = total_minutes(timer)
    price = meta.get('price', 0)
    hourly = (price / (total / 60)) if total > 0 else 0

    print(f'⏱️  作業終了: {end_time.isoformat(timespec="seconds")}')
    print(f'📝 セッション時間: {format_duration(minutes)}')
    print(f'📊 累計時間: {format_duration(total)}')
    if price > 0:
        print(f'💰 現時点の実時給: ¥{hourly:,.0f}/h（報酬¥{price:,}想定）')


def status(folder_path, meta):
    timer = load_timer(folder_path)
    total = total_minutes(timer)
    price = meta.get('price', 0)

    print('=' * 40)
    print(f'📊 時間トラッカー')
    print('=' * 40)

    if timer.get('current_start'):
        start_dt = datetime.fromisoformat(timer['current_start'])
        elapsed = int((datetime.now() - start_dt).total_seconds() / 60)
        print(f'🟢 作業中（開始: {timer["current_start"][11:16]}）')
        print(f'   経過: {format_duration(elapsed)}')
    else:
        print('⚪ 停止中')

    print(f'📅 セッション数: {len(timer.get("sessions", []))}')
    print(f'⏱️  累計時間: {format_duration(total)}')

    if price > 0 and total > 0:
        hourly = price / (total / 60)
        print(f'💰 実時給: ¥{hourly:,.0f}/h')
        print(f'   報酬: ¥{price:,}')

    print()
    if timer.get('sessions'):
        print('📝 セッション履歴')
        for i, s in enumerate(timer['sessions'][-5:], 1):
            start = s['start'][11:16]
            end = s['end'][11:16]
            mins = s['minutes']
            print(f'   [{i}] {start}-{end} ({format_duration(mins)})')


def main():
    if len(sys.argv) < 3:
        print('使い方:')
        print('  python3 scripts/deliver/timer.py start <folder_name>')
        print('  python3 scripts/deliver/timer.py stop <folder_name>')
        print('  python3 scripts/deliver/timer.py status <folder_name>')
        sys.exit(1)

    action = sys.argv[1]
    folder_name = sys.argv[2]
    folder_path = os.path.join(DELIVERIES_DIR, folder_name)
    meta_path = os.path.join(folder_path, 'meta.json')

    if not os.path.exists(meta_path):
        print(f'❌ 案件フォルダが見つかりません: {folder_name}')
        sys.exit(1)

    with open(meta_path, 'r', encoding='utf-8') as f:
        meta = json.load(f)

    if action == 'start':
        start(folder_path)
    elif action == 'stop':
        stop(folder_path, meta)
    elif action == 'status':
        status(folder_path, meta)
    else:
        print(f'❌ 無効なアクション: {action}')
        sys.exit(1)


if __name__ == '__main__':
    main()
