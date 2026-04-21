#!/usr/bin/env python3
"""
統合ワークフロー：全工程をワンコマンドで実行
使い方: python3 scripts/deliver/run.py [folder_name]
  folder_name省略時 → 進行中案件から選択

完全対話型・どの段階からでも再開可能。
"""

import json
import os
import subprocess
import sys
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DELIVERIES_DIR = os.path.join(SCRIPT_DIR, '..', '..', 'deliveries')


def list_jobs():
    if not os.path.exists(DELIVERIES_DIR):
        return []
    jobs = []
    for f in sorted(os.listdir(DELIVERIES_DIR), reverse=True):
        path = os.path.join(DELIVERIES_DIR, f)
        meta_path = os.path.join(path, 'meta.json')
        if os.path.isdir(path) and os.path.exists(meta_path):
            with open(meta_path, 'r', encoding='utf-8') as fp:
                meta = json.load(fp)
            jobs.append({
                'folder': f,
                'meta': meta,
                'path': path,
            })
    return jobs


def detect_stage(folder_path):
    """現在のワークフロー進捗を検出"""
    meta_path = os.path.join(folder_path, 'meta.json')
    prompts_dir = os.path.join(folder_path, 'prompts')
    drafts_dir = os.path.join(folder_path, 'drafts')
    final_dir = os.path.join(folder_path, 'final')

    if not os.path.exists(meta_path):
        return 'new'

    with open(meta_path, 'r', encoding='utf-8') as f:
        meta = json.load(f)

    if meta.get('status') == 'delivered':
        return 'invoicing'

    if os.path.exists(final_dir) and len(os.listdir(final_dir)) > 0:
        return 'packaged'

    if os.path.exists(drafts_dir) and any(
        f.endswith(('.md', '.txt', '.csv'))
        for f in os.listdir(drafts_dir)
    ):
        return 'drafted'

    if os.path.exists(prompts_dir) and len(os.listdir(prompts_dir)) > 0:
        return 'prompted'

    return 'setup'


STAGE_NAMES = {
    'new': '📭 新規（未着手）',
    'setup': '📝 受注登録済み',
    'prompted': '🤖 プロンプト生成済み',
    'drafted': '✏️  下書き保存済み',
    'packaged': '📦 納品パッケージ完成',
    'invoicing': '💰 納品済み（請求/入金待ち）',
    'completed': '✅ 完了',
}


def run_script(script, *args):
    cmd = ['python3', os.path.join(SCRIPT_DIR, script), *args]
    result = subprocess.run(cmd)
    return result.returncode == 0


def show_job_summary(job):
    meta = job['meta']
    stage = detect_stage(job['path'])
    print(f"  📋 {meta['job_title']}")
    print(f"     クライアント: {meta['client']}")
    print(f"     タイプ: {meta.get('job_type', '-')}")
    print(f"     報酬: ¥{meta.get('price', 0):,}")
    print(f"     納期: {meta.get('deadline', '-')}")
    print(f"     進捗: {STAGE_NAMES.get(stage, stage)}")


def next_action_prompt(stage, folder_name):
    """現在のステージから次のアクションを提案"""
    actions = []
    if stage == 'setup':
        actions.append(('1', 'プロンプト生成', f'generate.py', [folder_name]))
    elif stage == 'prompted':
        actions.append(('1', 'プロンプトをClaudeに貼り付け → drafts/ に保存', None, None))
        actions.append(('2', '下書き保存後、品質チェック実行', 'quality_check.py', [folder_name]))
    elif stage == 'drafted':
        actions.append(('1', '品質チェック', 'quality_check.py', [folder_name]))
        actions.append(('2', '納品パッケージ生成', 'package.py', [folder_name]))
    elif stage == 'packaged':
        actions.append(('1', '納品メール送信（delivery_email.txt を開く）', None, None))
        actions.append(('2', '請求書作成 (CFO/outputs/請求書テンプレート.md)', None, None))
    elif stage == 'invoicing':
        actions.append(('1', '入金確認後、application_tracker.py で「受注」登録', None, None))
    return actions


def main():
    print('=' * 60)
    print('🚀 受注→納品パイプライン（統合ワークフロー）')
    print('=' * 60)

    # フォルダ指定がある場合
    if len(sys.argv) >= 2:
        folder_name = sys.argv[1]
        folder_path = os.path.join(DELIVERIES_DIR, folder_name)
        if not os.path.exists(folder_path):
            print(f'❌ フォルダが見つかりません: {folder_name}')
            sys.exit(1)
    else:
        # 進行中案件の一覧表示
        jobs = list_jobs()
        active = [j for j in jobs if detect_stage(j['path']) not in ['completed']]

        print()
        print(f'進行中案件: {len(active)} 件')
        print('-' * 60)

        if not active:
            print('📭 進行中案件なし')
            print()
            answer = input('新規受注を登録しますか？ (y/N): ').strip().lower()
            if answer == 'y':
                run_script('new_job.py')
            return

        for i, job in enumerate(active):
            print(f'[{i+1}]')
            show_job_summary(job)
            print()

        print(f'[{len(active)+1}] 🆕 新規受注を登録')
        print(f'[0] 終了')
        print()

        choice = input('選択（番号）: ').strip()

        if choice == '0':
            return
        elif choice == str(len(active) + 1):
            run_script('new_job.py')
            return
        else:
            try:
                idx = int(choice) - 1
                if idx < 0 or idx >= len(active):
                    print('❌ 無効な選択')
                    return
                folder_name = active[idx]['folder']
                folder_path = active[idx]['path']
            except ValueError:
                print('❌ 無効な選択')
                return

    # 案件の進捗確認と次のアクション
    meta_path = os.path.join(folder_path, 'meta.json')
    with open(meta_path, 'r', encoding='utf-8') as f:
        meta = json.load(f)

    stage = detect_stage(folder_path)

    print()
    print('=' * 60)
    print(f'📋 {meta["job_title"]}')
    print(f'   進捗: {STAGE_NAMES.get(stage, stage)}')
    print('=' * 60)

    actions = next_action_prompt(stage, folder_name)

    if not actions:
        print('🎉 この案件は完了しています')
        return

    print()
    print('次のアクション：')
    for num, label, _, _ in actions:
        print(f'  [{num}] {label}')
    print('  [0] 戻る')

    choice = input('\n選択: ').strip()

    if choice == '0':
        return

    for num, label, script, args in actions:
        if num == choice and script:
            print()
            run_script(script, *(args or []))
            print()
            print('💡 再度 run.py を実行すると、次のステップに進めます')
            break


if __name__ == '__main__':
    main()
