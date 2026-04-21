#!/usr/bin/env python3
"""
納品ファイル生成＆納品メール作成
使い方: python3 scripts/deliver/package.py <folder_name>

エッジケース対応：
- meta.json不在/壊れJSON/必須フィールド欠落を検証
- drafts空/大量ファイルを安全に処理
- 同名ファイルは連番付与で上書き回避
- ファイル名の特殊文字を完全サニタイズ
"""

import json
import os
import re
import shutil
import sys
from datetime import datetime

DELIVERIES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    '..',
    'deliveries',
)

VALID_EXTENSIONS = ('.md', '.txt', '.csv', '.xlsx', '.docx', '.pdf')
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


def sanitize_filename(name, max_len=50):
    """ファイル名用にサニタイズ"""
    if not name:
        return 'untitled'
    # 特殊文字削除
    name = re.sub(r'[<>:"|?*\\/]', '_', name)
    # 制御文字削除
    name = ''.join(c for c in name if ord(c) >= 0x20)
    # 連続アンダースコアを1つに
    name = re.sub(r'_+', '_', name)
    name = name.strip('._ ')
    return name[:max_len] or 'untitled'


def unique_path(base_path):
    """既存ならbasename_2.md等に変更"""
    if not os.path.exists(base_path):
        return base_path
    base, ext = os.path.splitext(base_path)
    for i in range(2, 100):
        candidate = f'{base}_{i}{ext}'
        if not os.path.exists(candidate):
            return candidate
    return f'{base}_{datetime.now().strftime("%H%M%S")}{ext}'


def load_meta(meta_path):
    """meta.jsonを読み込み・検証"""
    if not os.path.exists(meta_path):
        print(f'❌ meta.json が見つかりません: {meta_path}')
        sys.exit(1)

    try:
        with open(meta_path, 'r', encoding='utf-8') as f:
            meta = json.load(f)
    except json.JSONDecodeError as e:
        print(f'❌ meta.json が不正なJSON: {e}')
        sys.exit(1)
    except UnicodeDecodeError:
        print(f'❌ meta.json が UTF-8 ではない')
        sys.exit(1)

    # 必須フィールド
    required = ['client', 'job_title', 'job_type']
    missing = [k for k in required if k not in meta]
    if missing:
        print(f'❌ meta.jsonに必須フィールド不足: {missing}')
        sys.exit(1)

    # デフォルト補完
    meta.setdefault('date', datetime.now().strftime('%Y-%m-%d'))
    meta.setdefault('price', 0)
    meta.setdefault('details', {})
    meta.setdefault('status', 'in_progress')
    return meta


DELIVERY_EMAIL_ARTICLE = """件名：【納品のお知らせ】{job_title}

{client} 様

お世話になっております。
[あなたのお名前]です。

{job_title}の納品物をお送りいたします。

■ 納品内容
・記事本文（{char_count}字）
・タイトル案
・メタディスクリプション

■ 作業期間
{period}

■ 特記事項
{notes}

ご確認のほど、よろしくお願いいたします。
修正点等ございましたらお知らせください。

---
[あなたのお名前]
[メールアドレス]
"""

DELIVERY_EMAIL_SNS = """件名：【納品のお知らせ】{job_title}

{client} 様

お世話になっております。
[あなたのお名前]です。

{job_title}の{post_count}投稿分の納品物をお送りいたします。

■ 納品内容
・投稿文×{post_count}本
・ハッシュタグ選定済み
・画像用テキスト案

■ 作業期間
{period}

■ 予約投稿について
Bufferやストーリーズで順次予約投稿いたします。

ご確認のほど、よろしくお願いいたします。
内容のご調整があればお知らせください。

---
[あなたのお名前]
[メールアドレス]
"""

DELIVERY_EMAIL_DEFAULT = """件名：【納品のお知らせ】{job_title}

{client} 様

お世話になっております。
[あなたのお名前]です。

{job_title}の納品物をお送りいたします。

■ 作業期間
{period}

ご確認のほど、よろしくお願いいたします。

---
[あなたのお名前]
[メールアドレス]
"""


def main():
    if len(sys.argv) < 2:
        print('使い方: python3 scripts/deliver/package.py <folder_name>')
        sys.exit(1)

    folder_name = sys.argv[1]
    folder_path = os.path.join(DELIVERIES_DIR, folder_name)

    if not os.path.isdir(folder_path):
        print(f'❌ フォルダが存在しません: {folder_name}')
        sys.exit(1)

    meta = load_meta(os.path.join(folder_path, 'meta.json'))

    drafts_dir = os.path.join(folder_path, 'drafts')
    final_dir = os.path.join(folder_path, 'final')
    os.makedirs(final_dir, exist_ok=True)

    print('=' * 50)
    print(f'📦 納品パッケージ生成: {meta["job_title"]}')
    print('=' * 50)

    # drafts検証
    if not os.path.isdir(drafts_dir):
        print(f'❌ drafts フォルダが存在しません: {drafts_dir}')
        sys.exit(1)

    try:
        all_drafts = os.listdir(drafts_dir)
    except PermissionError:
        print(f'❌ drafts フォルダ読み込み権限なし')
        sys.exit(1)

    drafts = []
    for f in all_drafts:
        if not f.lower().endswith(VALID_EXTENSIONS):
            continue
        fpath = os.path.join(drafts_dir, f)
        # 大きすぎるファイルはスキップ
        if os.path.getsize(fpath) > MAX_FILE_SIZE:
            print(f'  ⚠️  スキップ: {f}（サイズ超過）')
            continue
        # 空ファイルもスキップ
        if os.path.getsize(fpath) == 0:
            print(f'  ⚠️  スキップ: {f}（空ファイル）')
            continue
        drafts.append(f)

    if not drafts:
        print('❌ drafts に納品可能なファイルがない')
        print(f'   対応拡張子: {VALID_EXTENSIONS}')
        sys.exit(1)

    # 複数あれば最大サイズのものをメインに（ただし全部コピー）
    drafts.sort(key=lambda f: os.path.getsize(os.path.join(drafts_dir, f)), reverse=True)

    # 納品ファイル名の安全な生成
    date = datetime.now().strftime('%Y%m%d')
    safe_title = sanitize_filename(meta["job_title"], max_len=30)

    copied = []
    seen_names = set()
    for draft in drafts:
        ext = os.path.splitext(draft)[1].lower()
        # 同じ拡張子が複数あれば連番
        base = f'{date}_{safe_title}{ext}'
        if base in seen_names:
            for i in range(2, 100):
                candidate = f'{date}_{safe_title}_{i}{ext}'
                if candidate not in seen_names:
                    base = candidate
                    break
        seen_names.add(base)

        src = os.path.join(drafts_dir, draft)
        dst = os.path.join(final_dir, base)
        dst = unique_path(dst)  # final側にも既存なら連番

        try:
            shutil.copy2(src, dst)
            copied.append(os.path.basename(dst))
            print(f'✅ 納品ファイル: final/{os.path.basename(dst)}')
        except (PermissionError, OSError) as e:
            print(f'  ⚠️  コピー失敗（{draft}）: {e}')

    if not copied:
        print('❌ 1つもコピーできませんでした')
        sys.exit(1)

    # 納品メール生成
    job_type = meta.get('job_type', 'other')
    email_vars = {
        'job_title': meta['job_title'],
        'client': meta['client'],
        'period': f"{meta['date']} 〜 {date[:4]}-{date[4:6]}-{date[6:]}",
        'notes': meta.get('memo') or 'なし',
    }

    try:
        if job_type == 'article':
            email_vars['char_count'] = meta.get('details', {}).get('char_count', '?')
            email = DELIVERY_EMAIL_ARTICLE.format(**email_vars)
        elif job_type == 'sns':
            email_vars['post_count'] = meta.get('details', {}).get('post_count', '?')
            email = DELIVERY_EMAIL_SNS.format(**email_vars)
        else:
            email = DELIVERY_EMAIL_DEFAULT.format(**email_vars)
    except KeyError as e:
        print(f'  ⚠️  メールテンプレ変数不足: {e}。デフォルトを使用')
        email = DELIVERY_EMAIL_DEFAULT.format(**email_vars)

    email_path = os.path.join(folder_path, 'delivery_email.txt')
    with open(email_path, 'w', encoding='utf-8') as f:
        f.write(email)
    print(f'✅ 納品メール: delivery_email.txt')

    # 請求書メモ
    invoice_note = f"""# 請求メモ

受注日: {meta['date']}
納品日: {date[:4]}-{date[4:6]}-{date[6:]}
クライアント: {meta['client']}
案件: {meta['job_title']}
報酬: ¥{meta.get('price', 0):,}

## 次のステップ
1. 納品メール送信
2. 検収確認
3. 請求書発行（CFO/outputs/請求書テンプレート.md 参照）
4. 入金確認
5. application_tracker.py でステータス更新
"""
    invoice_path = os.path.join(folder_path, 'invoice_note.md')
    with open(invoice_path, 'w', encoding='utf-8') as f:
        f.write(invoice_note)
    print(f'✅ 請求メモ: invoice_note.md')

    # ステータス更新
    meta['status'] = 'delivered'
    meta['delivery_date'] = datetime.now().strftime('%Y-%m-%d')
    with open(os.path.join(folder_path, 'meta.json'), 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print()
    print('=' * 50)
    print('🎉 納品パッケージ完成')
    print('=' * 50)
    print()
    print('送付する内容：')
    print(f'  📂 フォルダ: {folder_path}')
    print(f'  📄 納品物: {final_dir}')
    for f in copied:
        print(f'     - {f}')
    print(f'  📧 メール下書き: {email_path}')
    print()
    print('次のアクション：')
    print('1. delivery_email.txt の [ ] を埋めて送信')
    print('2. クライアント検収後、請求書送付（CFO/outputs/請求書テンプレート.md）')
    print('3. 入金確認したら application_tracker.py で「受注」→売上登録')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n中断されました')
        sys.exit(130)
