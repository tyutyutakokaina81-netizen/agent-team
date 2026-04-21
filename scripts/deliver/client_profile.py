#!/usr/bin/env python3
"""
クライアント別プロファイル管理
過去の案件からクライアントの好み・NG事項を蓄積
使い方:
  python3 scripts/deliver/client_profile.py view <client_name>
  python3 scripts/deliver/client_profile.py edit <client_name>
  python3 scripts/deliver/client_profile.py list
"""

import json
import os
import sys

PROFILES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    '..',
    'deliveries',
    '_client_profiles',
)


def ensure_dir():
    os.makedirs(PROFILES_DIR, exist_ok=True)


def safe_filename(name):
    return name.replace('/', '_').replace('\\', '_').replace(' ', '_')[:50]


def load_profile(client_name):
    ensure_dir()
    path = os.path.join(PROFILES_DIR, f'{safe_filename(client_name)}.json')
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        'client_name': client_name,
        'tone_preference': '',
        'ng_words': [],
        'preferred_structure': '',
        'past_jobs': [],
        'notes': '',
    }


def save_profile(client_name, profile):
    ensure_dir()
    path = os.path.join(PROFILES_DIR, f'{safe_filename(client_name)}.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)


def view(client_name):
    profile = load_profile(client_name)
    print('=' * 50)
    print(f'📋 クライアントプロファイル: {client_name}')
    print('=' * 50)
    print(f'トーン: {profile.get("tone_preference") or "-"}')
    print(f'NGワード: {", ".join(profile.get("ng_words", [])) or "-"}')
    print(f'好みの構成: {profile.get("preferred_structure") or "-"}')
    print(f'メモ: {profile.get("notes") or "-"}')
    print()
    past_jobs = profile.get('past_jobs', [])
    if past_jobs:
        print(f'📜 過去の案件（{len(past_jobs)}件）')
        for j in past_jobs[-5:]:
            print(f'   - {j.get("date")}: {j.get("title")} (¥{j.get("price", 0):,})')


def edit(client_name):
    profile = load_profile(client_name)
    print(f'クライアント「{client_name}」のプロファイル編集')
    print('（Enter で既存値維持）')
    print()

    new_tone = input(f'トーン [{profile.get("tone_preference")}]: ').strip()
    if new_tone:
        profile['tone_preference'] = new_tone

    new_ng = input(f'NGワード（カンマ区切り） [{", ".join(profile.get("ng_words", []))}]: ').strip()
    if new_ng:
        profile['ng_words'] = [w.strip() for w in new_ng.split(',')]

    new_structure = input(f'好みの構成 [{profile.get("preferred_structure")}]: ').strip()
    if new_structure:
        profile['preferred_structure'] = new_structure

    new_notes = input(f'メモ [{profile.get("notes")}]: ').strip()
    if new_notes:
        profile['notes'] = new_notes

    save_profile(client_name, profile)
    print(f'✅ 保存しました')


def list_all():
    ensure_dir()
    files = [f for f in os.listdir(PROFILES_DIR) if f.endswith('.json')]
    if not files:
        print('📭 プロファイル未作成')
        return

    print('=' * 50)
    print(f'📋 クライアント一覧（{len(files)}件）')
    print('=' * 50)

    for f in sorted(files):
        with open(os.path.join(PROFILES_DIR, f), 'r', encoding='utf-8') as fp:
            p = json.load(fp)
        past = len(p.get('past_jobs', []))
        print(f'  {p["client_name"]}: 過去{past}件')


def main():
    if len(sys.argv) < 2:
        print('使い方:')
        print('  python3 scripts/deliver/client_profile.py list')
        print('  python3 scripts/deliver/client_profile.py view <client_name>')
        print('  python3 scripts/deliver/client_profile.py edit <client_name>')
        sys.exit(1)

    action = sys.argv[1]

    if action == 'list':
        list_all()
    elif action == 'view' and len(sys.argv) >= 3:
        view(sys.argv[2])
    elif action == 'edit' and len(sys.argv) >= 3:
        edit(sys.argv[2])
    else:
        print('❌ 引数が不足しています')
        sys.exit(1)


if __name__ == '__main__':
    main()
