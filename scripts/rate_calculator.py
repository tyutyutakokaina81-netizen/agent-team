#!/usr/bin/env python3
"""
時給・採算性計算ツール
使い方: python3 scripts/rate_calculator.py
"""

PLATFORM_FEES = {
    'cw': 0.20,
    'crowdworks': 0.20,
    'lancers': 0.165,
    'mama': 0.0,
    'mamaworks': 0.0,
    'coconala': 0.22,
    'direct': 0.0,
}


def calculate():
    print('=' * 50)
    print('💰 時給・採算性計算')
    print('=' * 50)

    try:
        price = int(input('報酬額（円）: ').strip())
        hours = float(input('想定作業時間（時間）: ').strip())
    except ValueError:
        print('❌ 数値を入力してください')
        return

    platform_key = input('プラットフォーム（cw/lancers/mama/coconala/direct）: ').strip().lower()
    fee_rate = PLATFORM_FEES.get(platform_key, 0)

    fee = price * fee_rate
    net_income = price - fee
    hourly_rate = net_income / hours if hours > 0 else 0

    print('\n【計算結果】')
    print(f'  報酬総額: ¥{price:,}')
    print(f'  手数料: ¥{fee:,.0f}（{fee_rate*100:.1f}%）')
    print(f'  実収入: ¥{net_income:,.0f}')
    print(f'  想定作業時間: {hours}時間')
    print(f'  時給: ¥{hourly_rate:,.0f}/h')

    print('\n【採算判定】')
    if hourly_rate >= 3000:
        print('  ✅ 優良案件：即応募すべき')
    elif hourly_rate >= 2000:
        print('  👍 良い案件：応募推奨')
    elif hourly_rate >= 1000:
        print('  🤔 普通：検討の余地あり')
    elif hourly_rate >= 500:
        print('  ⚠️ 安い：評価作りなら応募可')
    else:
        print('  ❌ 採算割れ：スキップ推奨')

    print('=' * 50)


if __name__ == '__main__':
    calculate()
