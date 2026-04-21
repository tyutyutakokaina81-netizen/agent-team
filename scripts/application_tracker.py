#!/usr/bin/env python3
"""
応募トラッカー（対話式）
使い方: python3 scripts/application_tracker.py

エッジケース対応：
- 旧フォーマットCSV（url/note列欠如）を自動マイグレーション
- 特殊文字をサニタイズ
- 数値変換失敗時はデフォルト0
- ステータス値を制限
"""

import csv
import os
import re
import sys
from datetime import datetime

CSV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'applications.csv')
FIELDNAMES = ['date', 'site', 'job_name', 'price', 'status', 'url', 'note']
VALID_STATUSES = ['応募', '返信', '受注', '失注', '選考中', '保留']


def sanitize_text(text, max_len=200):
    """CSV用のテキストサニタイズ"""
    if text is None:
        return ''
    # 制御文字を削除
    text = ''.join(c for c in str(text) if ord(c) >= 0x20 or c in '\n')
    return text.strip()[:max_len]


def safe_int(value, default=0):
    """数値変換（「5,000円」等も吸収）"""
    if value is None:
        return default
    s = str(value).strip()
    if not s:
        return default
    cleaned = re.sub(r'[^\d-]', '', s)
    try:
        return int(cleaned) if cleaned and cleaned != '-' else default
    except ValueError:
        return default


def init_csv():
    """CSV新規作成（既存なら何もしない）"""
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(FIELDNAMES)
        print(f'✅ {CSV_FILE} を作成しました')


def migrate_csv():
    """旧フォーマットを新フォーマットに移行"""
    if not os.path.exists(CSV_FILE):
        return

    try:
        with open(CSV_FILE, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
    except UnicodeDecodeError:
        print('⚠️  CSVがUTF-8ではありません。バックアップして再作成します')
        os.rename(CSV_FILE, CSV_FILE + '.bak')
        init_csv()
        return

    if not rows:
        return

    header = rows[0]
    # 既に新フォーマット
    if header == FIELDNAMES:
        return

    # 旧フォーマットから移行
    print(f'ℹ️  CSV フォーマットを移行します（旧列数:{len(header)} → 新列数:{len(FIELDNAMES)}）')
    old_fields = header
    new_rows = [FIELDNAMES]
    for row in rows[1:]:
        # 足りない列は空で補完
        new_row = []
        for field in FIELDNAMES:
            if field in old_fields:
                idx = old_fields.index(field)
                new_row.append(row[idx] if idx < len(row) else '')
            else:
                new_row.append('')
        new_rows.append(new_row)

    # バックアップ→書き換え
    os.rename(CSV_FILE, CSV_FILE + '.migration_backup')
    with open(CSV_FILE, 'w', encoding='utf-8', newline='') as f:
        csv.writer(f).writerows(new_rows)
    print(f'✅ 移行完了（バックアップ: {CSV_FILE}.migration_backup）')


def read_rows():
    """CSV読み込み（空/壊れ対応）"""
    if not os.path.exists(CSV_FILE):
        return []
    try:
        with open(CSV_FILE, 'r', encoding='utf-8') as f:
            return list(csv.DictReader(f))
    except (UnicodeDecodeError, csv.Error) as e:
        print(f'❌ CSV読み込みエラー: {e}')
        return []


def add_application():
    print('\n📝 新規応募を記録')

    date = input('日付（YYYY-MM-DD、空白で今日）: ').strip() or datetime.now().strftime('%Y-%m-%d')
    # 日付バリデーション
    for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%Y%m%d'):
        try:
            date = datetime.strptime(date, fmt).strftime('%Y-%m-%d')
            break
        except ValueError:
            continue
    else:
        print(f'  ⚠️ 日付形式が不正。今日の日付を使用')
        date = datetime.now().strftime('%Y-%m-%d')

    site = sanitize_text(input('サイト（cw/lancers/mama等）: '), max_len=30)
    if not site:
        print('  ⚠️ サイト名は必須です')
        return

    job_name = sanitize_text(input('案件名: '), max_len=200)
    if not job_name:
        print('  ⚠️ 案件名は必須です')
        return

    price = safe_int(input('報酬額: '))
    status = sanitize_text(input('ステータス（応募/返信/受注/失注）: ') or '応募', max_len=20)
    if status not in VALID_STATUSES:
        print(f'  ⚠️ 無効なステータス「{status}」→「応募」に変換')
        status = '応募'

    url = sanitize_text(input('URL（任意）: '), max_len=500)
    note = sanitize_text(input('メモ（任意）: '), max_len=500)

    try:
        with open(CSV_FILE, 'a', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([date, site, job_name, str(price), status, url, note])
        print(f'✅ 記録しました: {job_name}')
    except PermissionError:
        print('❌ CSV書き込み権限なし（Excelで開いている可能性）')
    except Exception as e:
        print(f'❌ 書き込みエラー: {e}')


def update_status():
    print('\n🔄 ステータス更新')
    keyword = sanitize_text(input('更新する案件名（部分一致）: '), max_len=200)
    if not keyword:
        print('  ⚠️ キーワードは必須です')
        return

    new_status = sanitize_text(input('新しいステータス: '), max_len=20)
    if new_status not in VALID_STATUSES:
        print(f'  ⚠️ 無効なステータス。{VALID_STATUSES}のいずれかを入力してください')
        return

    rows = read_rows()
    if not rows:
        print('❌ CSVにデータがありません')
        return

    updated_count = 0
    for row in rows:
        if keyword in row.get('job_name', ''):
            row['status'] = new_status
            print(f"  ✏️ 更新: {row['job_name']} → {new_status}")
            updated_count += 1

    if updated_count == 0:
        print(f'  ℹ️ 一致する案件がありません: {keyword}')
        return

    try:
        with open(CSV_FILE, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)
        print(f'✅ {updated_count}件 更新しました')
    except PermissionError:
        print('❌ CSV書き込み権限なし')


def show_stats():
    rows = read_rows()
    total = len(rows)
    orders = len([r for r in rows if r.get('status') == '受注'])
    revenue = sum(safe_int(r.get('price', 0)) for r in rows if r.get('status') == '受注')

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
    rows = read_rows()
    if not rows:
        print('  （データなし）')
        return
    for row in rows[-10:]:
        print(f"  {row.get('date', '')} [{row.get('status', '')}] {row.get('site', '')}: {row.get('job_name', '')}")


def main():
    init_csv()
    migrate_csv()

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
    try:
        main()
    except KeyboardInterrupt:
        print('\n\n中断されました')
        sys.exit(130)
    except EOFError:
        print('\n\n入力が途切れました')
        sys.exit(1)
