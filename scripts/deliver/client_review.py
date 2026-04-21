#!/usr/bin/env python3
"""
クライアント視点での納品物チェック（API不要・無料）
納品する相手の立場に立って厳しく評価する。

クライアントが納品物を受け取った瞬間に何を見るか：
1. 第一印象（タイトル・冒頭）
2. パッと見の構造（読みやすそうか）
3. 自社サイトに公開できる状態か
4. 修正依頼を出さずに済むか
5. 次回も依頼したいレベルか

使い方:
  python3 scripts/deliver/client_review.py <folder_name>
"""

import json
import os
import re
import sys


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DELIVERIES_DIR = os.path.join(os.path.dirname(os.path.dirname(SCRIPT_DIR)), 'deliveries')


def first_impression(content):
    """第一印象：タイトルと冒頭500字でクライアントが判断する部分"""
    issues = []

    # タイトル（最初の# の行）
    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if not title_match:
        return ['❌ タイトルがない（公開不可）'], 0

    title = title_match.group(1)
    if len(title) > 32:
        issues.append(f'⚠️ タイトル長すぎ（{len(title)}字・SEO推奨32字以内）')
    if len(title) < 15:
        issues.append(f'⚠️ タイトル短すぎ（{len(title)}字・魅力不足）')

    # 冒頭500字
    intro = content[:500]
    if not re.search(r'[。．！？]', intro):
        issues.append('⚠️ 冒頭に句点なし（読みにくい）')
    if len(intro.split('\n')) < 5:
        issues.append('⚠️ 冒頭の改行が少ない（スマホで読みにくい）')

    score = 100 - len(issues) * 15
    return issues, max(0, score)


def publishability(content):
    """公開可能性：そのままサイトに上げられるか"""
    issues = []

    # 未確定の表現
    placeholders = re.findall(r'\[[^\]]+\]', content)
    if placeholders:
        issues.append(f'❌ プレースホルダー残存: {placeholders[:3]}')

    # 「TODO」や「あとで」等の作業中マーカー
    todo_patterns = ['TODO', 'todo', 'あとで', '未確定', '※修正必要', '???', '?要確認']
    for p in todo_patterns:
        if p in content:
            issues.append(f'❌ 作業中マーカー残存: 「{p}」')

    # 不自然な改行
    triple_newlines = content.count('\n\n\n\n')
    if triple_newlines > 0:
        issues.append(f'⚠️ 過剰な改行（{triple_newlines}箇所）')

    # 空のセクション
    empty_sections = re.findall(r'^#{2,}\s+.+\n+#{2,}', content, re.MULTILINE)
    if empty_sections:
        issues.append(f'❌ 空のセクション検出（{len(empty_sections)}個）')

    # AI使用の明示（透明性）
    ai_disclosed = any(w in content for w in ['AI執筆', 'AI補助', 'Claude', 'ChatGPT', '人工知能'])
    if not ai_disclosed:
        issues.append('ℹ️ AI使用の明示なし（クライアント次第）')

    score = 100 - sum(20 if i.startswith('❌') else 5 for i in issues)
    return issues, max(0, score)


def revision_risk(content, meta):
    """修正依頼リスク：クライアントが「直して」と言いそうな部分"""
    issues = []

    # キーワードがタイトルにない
    keyword = meta.get('details', {}).get('keyword', '')
    if keyword:
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            title = title_match.group(1)
            tokens = keyword.split()
            if not all(t in title for t in tokens):
                issues.append(f'⚠️ タイトルにキーワード「{keyword}」未含有 → 修正依頼確実')

    # H2が偏っている
    h2_count = len(re.findall(r'^##\s', content, re.MULTILINE))
    if h2_count < 3:
        issues.append(f'⚠️ H2が少ない（{h2_count}個） → 構成見直し依頼の可能性')
    if h2_count > 8:
        issues.append(f'⚠️ H2が多すぎ（{h2_count}個） → 整理依頼の可能性')

    # 段落が長すぎる
    long_paragraphs = [p for p in content.split('\n\n') if len(p) > 400]
    if len(long_paragraphs) > 3:
        issues.append(f'⚠️ 長い段落多数（{len(long_paragraphs)}個） → 改行依頼')

    # 表記揺れチェック（簡易）
    if 'ユーザー' in content and 'ユーザ' in content.replace('ユーザー', ''):
        issues.append('⚠️ 表記揺れ: ユーザー / ユーザ')
    if 'コンピューター' in content and 'コンピュータ' in content.replace('コンピューター', ''):
        issues.append('⚠️ 表記揺れ: コンピューター / コンピュータ')

    # 文末の単調さ
    sentences = re.split(r'[。．]', content)
    desu_count = sum(1 for s in sentences[-50:] if s.endswith('です'))
    if desu_count > 30:
        issues.append(f'⚠️ 「です」連発（後半50文中{desu_count}文）→ リズム改善依頼')

    score = 100 - len(issues) * 10
    return issues, max(0, score)


def repeat_business(content, meta):
    """次回も依頼したくなるレベルか"""
    plus = []
    minus = []

    # 具体的な数字の使用
    numbers = re.findall(r'\d+', content)
    if len(set(numbers)) >= 8:
        plus.append('✅ 具体的数字が豊富（信頼感UP）')
    elif len(set(numbers)) < 3:
        minus.append('⚠️ 数字が少ない（抽象的）')

    # 表・箇条書きの活用
    bullets = len(re.findall(r'^[\-\*]\s', content, re.MULTILINE))
    tables = content.count('\n|')
    if bullets >= 10 or tables >= 3:
        plus.append('✅ 構造化が丁寧（読者親切）')

    # CTA（行動喚起）の存在
    cta_patterns = ['まずは', '今すぐ', 'ぜひ', '挑戦', '始めて', 'やってみ']
    cta_count = sum(content.count(p) for p in cta_patterns)
    if cta_count >= 3:
        plus.append('✅ 行動喚起が明確（読者を動かす）')
    else:
        minus.append('⚠️ 行動喚起が弱い')

    # 体験談・具体例
    if any(w in content for w in ['実際に', '体験', '私の', '事例', '実例', 'ケース']):
        plus.append('✅ 具体的な事例あり（説得力UP）')
    else:
        minus.append('⚠️ 具体例が少ない（凡庸印象）')

    # 専門性の演出
    if any(w in content for w in ['調査', '統計', 'データ', 'によると', '報告']):
        plus.append('✅ データ裏付けあり（権威性）')

    score = 50 + len(plus) * 12 - len(minus) * 8
    return plus, minus, max(0, min(100, score))


def main():
    if len(sys.argv) < 2:
        print('使い方: python3 scripts/deliver/client_review.py <folder_name>')
        sys.exit(1)

    folder_name = sys.argv[1]
    folder_path = os.path.join(DELIVERIES_DIR, folder_name)

    meta_path = os.path.join(folder_path, 'meta.json')
    if not os.path.exists(meta_path):
        print(f'❌ meta.json 無し')
        sys.exit(1)

    with open(meta_path, 'r', encoding='utf-8') as f:
        meta = json.load(f)

    article_path = os.path.join(folder_path, 'drafts', 'article.md')
    if not os.path.exists(article_path):
        print(f'❌ drafts/article.md 無し')
        sys.exit(1)

    with open(article_path, 'r', encoding='utf-8') as f:
        content = f.read()

    print('=' * 60)
    print('👔 クライアント視点レビュー')
    print('=' * 60)
    print(f'  案件: {meta["job_title"]}')
    print(f'  クライアント: {meta["client"]}')
    print(f'  自分が発注した立場で読みます...')
    print()

    # 1. 第一印象
    print('━━━ 1. 第一印象（タイトル・冒頭）━━━')
    issues1, score1 = first_impression(content)
    for i in issues1: print(f'  {i}')
    print(f'  📊 スコア: {score1}/100')
    print()

    # 2. 公開可能性
    print('━━━ 2. 公開可能性（このまま使えるか）━━━')
    issues2, score2 = publishability(content)
    for i in issues2: print(f'  {i}')
    if not issues2:
        print('  ✅ 問題なし - そのまま公開可能')
    print(f'  📊 スコア: {score2}/100')
    print()

    # 3. 修正依頼リスク
    print('━━━ 3. 修正依頼が来そうか ━━━')
    issues3, score3 = revision_risk(content, meta)
    for i in issues3: print(f'  {i}')
    if not issues3:
        print('  ✅ 修正依頼の可能性低い')
    print(f'  📊 スコア: {score3}/100')
    print()

    # 4. リピート可能性
    print('━━━ 4. 次回も依頼したくなるか ━━━')
    plus, minus, score4 = repeat_business(content, meta)
    for p in plus: print(f'  {p}')
    for m in minus: print(f'  {m}')
    print(f'  📊 スコア: {score4}/100')
    print()

    # 総合判定
    total = (score1 + score2 + score3 + score4) / 4
    print('=' * 60)
    print(f'📊 総合クライアント満足度: {total:.0f}/100')
    print('=' * 60)
    if total >= 90:
        print('🎉 完璧な納品物。リピート確実。')
    elif total >= 75:
        print('✅ 良好。納品OK・小修正想定。')
    elif total >= 60:
        print('🟡 標準。修正依頼あり。改善推奨。')
    else:
        print('❌ 納品不可レベル。要全面見直し。')
    print()


if __name__ == '__main__':
    main()
