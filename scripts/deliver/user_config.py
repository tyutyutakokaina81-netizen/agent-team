#!/usr/bin/env python3
"""
ユーザー設定（名前・メール等）の管理
~/agent-team/user_config.json に保存。.gitignore対象。

使い方:
  python3 scripts/deliver/user_config.py view  # 現在の設定を表示
  python3 scripts/deliver/user_config.py edit  # 設定を編集

メールテンプレ等で [あなたのお名前] [メールアドレス] を自動展開するのに使う。
"""

import json
import os
import sys

CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'user_config.json',
)

DEFAULT_CONFIG = {
    'name': '',
    'email': '',
    'phone': '',
    'bank_info': '',
    'invoice_number': '',  # インボイス登録番号（任意）
    'address': '',
}


def load_config():
    if not os.path.exists(CONFIG_PATH):
        return dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
        # デフォルト補完
        for key, value in DEFAULT_CONFIG.items():
            config.setdefault(key, value)
        return config
    except (json.JSONDecodeError, UnicodeDecodeError):
        print(f'⚠️ {CONFIG_PATH} が壊れています。デフォルト値を使用')
        return dict(DEFAULT_CONFIG)


def save_config(config):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    os.chmod(CONFIG_PATH, 0o600)  # 権限を制限（本人のみ読み書き）


def view():
    config = load_config()
    print('=' * 50)
    print('👤 ユーザー設定')
    print('=' * 50)
    print(f'  名前:               {config.get("name") or "（未設定）"}')
    print(f'  メール:             {config.get("email") or "（未設定）"}')
    print(f'  電話:               {config.get("phone") or "（未設定）"}')
    print(f'  住所:               {config.get("address") or "（未設定）"}')
    print(f'  口座情報:           {config.get("bank_info") or "（未設定）"}')
    print(f'  インボイス登録番号: {config.get("invoice_number") or "（未設定）"}')
    print('=' * 50)
    print(f'保存先: {CONFIG_PATH}')


def edit():
    config = load_config()
    print('ユーザー設定を編集します（Enterで既存値を維持）')
    print()

    for key, prompt in [
        ('name', '名前'),
        ('email', 'メールアドレス'),
        ('phone', '電話番号'),
        ('address', '住所'),
        ('bank_info', '口座情報（例: ○○銀行 △△支店 普通 1234567）'),
        ('invoice_number', 'インボイス登録番号（任意）'),
    ]:
        current = config.get(key, '')
        new_value = input(f'{prompt} [{current}]: ').strip()
        if new_value:
            config[key] = new_value

    save_config(config)
    print()
    print('✅ 保存完了')
    view()


def get_config():
    """他のスクリプトから呼び出すためのヘルパー"""
    return load_config()


def apply_placeholders(text):
    """テンプレ文字列のプレースホルダーを実際の値で置換"""
    config = load_config()
    replacements = {
        '[あなたのお名前]': config.get('name', '[あなたのお名前]'),
        '[メールアドレス]': config.get('email', '[メールアドレス]'),
        '[電話番号]': config.get('phone', '[電話番号]'),
        '[住所]': config.get('address', '[住所]'),
        '[口座情報]': config.get('bank_info', '[口座情報]'),
    }
    for placeholder, value in replacements.items():
        if value and not value.startswith('['):
            text = text.replace(placeholder, value)
    return text


def main():
    if len(sys.argv) < 2:
        print('使い方:')
        print('  python3 scripts/deliver/user_config.py view')
        print('  python3 scripts/deliver/user_config.py edit')
        sys.exit(1)

    action = sys.argv[1]
    if action == 'view':
        view()
    elif action == 'edit':
        edit()
    else:
        print(f'❌ 無効なアクション: {action}')
        sys.exit(1)


if __name__ == '__main__':
    main()
