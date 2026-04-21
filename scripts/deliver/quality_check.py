#!/usr/bin/env python3
"""
高度な品質チェック（SEO・可読性・独自性・整合性）
使い方: python3 scripts/deliver/quality_check.py <folder_name>
"""

import json
import os
import re
import sys

DELIVERIES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    '..',
    'deliveries',
)


def count_chars(text):
    """日本語を考慮した文字数カウント（空白・改行除外）"""
    return len(re.sub(r'\s', '', text))


def count_sentences(text):
    """文の数をカウント"""
    # 日本語の句点で区切り
    sentences = re.split(r'[。.!?！？]\s*', text)
    return len([s for s in sentences if s.strip()])


def avg_sentence_length(text):
    """平均文長"""
    sentences = re.split(r'[。.!?！？]\s*', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return 0
    return sum(len(s) for s in sentences) / len(sentences)


def count_paragraphs(text):
    """段落数"""
    return len([p for p in text.split('\n\n') if p.strip()])


def check_h2_h3_structure(content):
    """H2/H3 構造の整合性"""
    h2 = re.findall(r'^##\s+(.+)$', content, re.MULTILINE)
    h3 = re.findall(r'^###\s+(.+)$', content, re.MULTILINE)
    # H3がH2より多すぎる/少なすぎるを検出
    return len(h2), len(h3)


def readability_score(text):
    """簡易可読性スコア（100点満点）"""
    avg = avg_sentence_length(text)
    # 30字以下が理想
    if avg <= 30:
        score = 100
    elif avg <= 45:
        score = 90 - (avg - 30) * 2
    elif avg <= 60:
        score = 60 - (avg - 45) * 2
    else:
        score = max(0, 30 - (avg - 60))
    return round(score)


def check_article(drafts_dir, meta):
    report = {'critical': [], 'warning': [], 'ok': [], 'metrics': {}}

    if not os.path.exists(drafts_dir):
        report['critical'].append('drafts/ フォルダが存在しない')
        return report

    drafts = [f for f in os.listdir(drafts_dir) if f.endswith(('.md', '.txt'))]
    if not drafts:
        report['critical'].append('drafts/ に原稿ファイルがない')
        return report

    drafts.sort(key=lambda f: os.path.getsize(os.path.join(drafts_dir, f)), reverse=True)
    main_draft = drafts[0]
    report['ok'].append(f'原稿ファイル検出: {main_draft}')

    with open(os.path.join(drafts_dir, main_draft), 'r', encoding='utf-8') as f:
        content = f.read()

    # 基本メトリクス
    report['metrics']['文字数'] = count_chars(content)
    report['metrics']['文数'] = count_sentences(content)
    report['metrics']['平均文長'] = round(avg_sentence_length(content), 1)
    report['metrics']['段落数'] = count_paragraphs(content)

    h2_count, h3_count = check_h2_h3_structure(content)
    report['metrics']['H2見出し'] = h2_count
    report['metrics']['H3見出し'] = h3_count

    readability = readability_score(content)
    report['metrics']['可読性スコア'] = f'{readability}/100'

    # 文字数チェック
    target = int(meta['details'].get('char_count', '3000'))
    actual = report['metrics']['文字数']
    diff_pct = abs(actual - target) / target * 100

    if diff_pct > 20:
        report['critical'].append(f'文字数が目標から大きく外れている（目標:{target} / 実際:{actual} / 差:{diff_pct:.0f}%）')
    elif diff_pct > 10:
        report['warning'].append(f'文字数が目標±10%超（目標:{target} / 実際:{actual}）')
    else:
        report['ok'].append(f'文字数OK（{actual}/{target}字）')

    # キーワードチェック（完全一致＋分割マッチ両対応）
    keyword = meta['details'].get('keyword', '')
    if keyword:
        # 完全一致
        kw_count = content.count(keyword)
        # 単語分割マッチ（スペース区切りなら各単語を確認）
        kw_tokens = keyword.split()
        token_occurrences = sum(content.count(t) for t in kw_tokens) if len(kw_tokens) > 1 else 0
        # 分割バリエーション（例：「副業 始め方」→「副業の始め方」「副業を始める」等）
        # 単純に分割語全部含むか
        all_tokens_present = all(t in content for t in kw_tokens)

        kw_density = kw_count / (actual / 100) if actual else 0
        report['metrics']['キーワード密度'] = f'{kw_density:.1f}%'

        if kw_count < 3 and not all_tokens_present:
            report['warning'].append(f'キーワード出現が少ない（{keyword}: {kw_count}回）')
        elif kw_count > 30:
            report['critical'].append(f'キーワードスタッフィング疑惑（{keyword}: {kw_count}回）')
        else:
            note = ''
            if kw_count < 3 and all_tokens_present:
                note = '（分割形で存在）'
            report['ok'].append(f'キーワードOK（{kw_count}回・密度{kw_density:.1f}%{note}）')

        # タイトルにキーワードが含まれているか（分割マッチ対応）
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            title_text = title_match.group(1)
            title_has_keyword = (
                keyword in title_text
                or all(t in title_text for t in kw_tokens)
            )
            if not title_has_keyword:
                report['warning'].append(f'タイトルにメインキーワードが含まれていない')
            else:
                report['ok'].append('タイトルにキーワード含有')

    # 見出し構造
    if h2_count < 3:
        report['warning'].append(f'H2見出しが少ない（{h2_count}個・推奨4-6個）')
    elif h2_count > 8:
        report['warning'].append(f'H2見出しが多い（{h2_count}個・構成を見直し）')
    else:
        report['ok'].append(f'H2見出し構造OK（{h2_count}個）')

    if h2_count > 0 and h3_count < h2_count:
        report['warning'].append(f'H3見出しが少ない（H3 {h3_count}個 < H2 {h2_count}個）')

    # 可読性
    if readability < 50:
        report['warning'].append(f'可読性低（スコア{readability}/100・文が長すぎる可能性）')
    else:
        report['ok'].append(f'可読性OK（{readability}/100）')

    # 禁止表現
    ng_patterns = {
        '絶対': r'絶対',
        '100%': r'100%|100％',
        '必ず稼げる': r'必ず.*稼',
        '誰でも簡単に': r'誰でも.*簡単',
        '今すぐ': r'今すぐ.*\n',
    }
    found_ng = []
    for label, pattern in ng_patterns.items():
        if re.search(pattern, content):
            found_ng.append(label)

    if found_ng:
        report['warning'].append(f'誇大表現の可能性: {", ".join(found_ng)}')
    else:
        report['ok'].append('誇大表現なし')

    # メタディスクリプション
    meta_desc_match = re.search(r'メタディスクリプション[：:]\s*(.+?)(?:\n|$)', content)
    if meta_desc_match:
        meta_len = len(meta_desc_match.group(1))
        if meta_len > 160:
            report['warning'].append(f'メタディスクリプションが長い（{meta_len}字・推奨160字以内）')
        elif meta_len < 80:
            report['warning'].append(f'メタディスクリプションが短い（{meta_len}字・推奨80-160字）')
        else:
            report['ok'].append(f'メタディスクリプションOK（{meta_len}字）')

    # 繰り返し表現チェック（Markdown記号は除外）
    # --- や ### などMarkdown記号を除いてから判定
    content_clean = re.sub(r'[-=#*_|]{2,}', ' ', content)
    repetitions = re.findall(r'(\S{2,}?)(?:\s*\1){2,}', content_clean)
    # 日本語の句読点・記号のみの繰り返しも除外
    meaningful_reps = [r for r in repetitions if re.search(r'[\w一-龯ぁ-んァ-ン]', r) and len(r) >= 2]
    if meaningful_reps:
        report['warning'].append(f'繰り返し表現あり: {list(set(meaningful_reps))[:3]}')

    # 箇条書き・表の使用
    bullet_count = len(re.findall(r'^[\-\*]\s', content, re.MULTILINE))
    table_count = content.count('\n|')
    if bullet_count + table_count < 5:
        report['warning'].append(f'箇条書き・表が少ない（読みやすさ向上の余地）')
    else:
        report['ok'].append(f'構造化OK（箇条書き{bullet_count}個・表{table_count//3}個）')

    return report


def check_sns(drafts_dir, meta):
    report = {'critical': [], 'warning': [], 'ok': [], 'metrics': {}}

    drafts = [f for f in os.listdir(drafts_dir) if f.endswith(('.md', '.txt'))] if os.path.exists(drafts_dir) else []
    if not drafts:
        report['critical'].append('drafts/ に投稿ファイルがない')
        return report

    with open(os.path.join(drafts_dir, drafts[0]), 'r', encoding='utf-8') as f:
        content = f.read()

    target_count = int(meta['details'].get('post_count', '15'))
    post_count_actual = len(re.findall(r'#{2,3}\s*投稿\d+', content))

    report['metrics']['投稿数'] = f'{post_count_actual}/{target_count}'

    if post_count_actual < target_count:
        report['critical'].append(f'投稿数不足（目標:{target_count} / 実際:{post_count_actual}）')
    else:
        report['ok'].append(f'投稿数OK（{post_count_actual}件）')

    # ハッシュタグチェック
    hashtag_count = content.count('#')
    report['metrics']['ハッシュタグ総数'] = hashtag_count

    avg_hashtags = hashtag_count / post_count_actual if post_count_actual > 0 else 0
    if avg_hashtags < 5:
        report['warning'].append(f'ハッシュタグ少（平均{avg_hashtags:.1f}個/投稿）')
    else:
        report['ok'].append(f'ハッシュタグOK（平均{avg_hashtags:.1f}個/投稿）')

    # 文字数（Xは140字制限）
    if 'X' in meta['details'].get('platforms', ''):
        # X用投稿の文字数確認
        posts = re.split(r'#{2,3}\s*投稿\d+', content)[1:]
        long_posts = []
        for i, post in enumerate(posts):
            # 本文部分を抽出
            body_match = re.search(r'本文[：:]\s*\n(.*?)(?=\n\s*(?:ハッシュタグ|$))', post, re.DOTALL)
            if body_match:
                body_chars = count_chars(body_match.group(1).split('\n')[0])
                if body_chars > 140:
                    long_posts.append(i + 1)
        if long_posts:
            report['warning'].append(f'X制限超えの投稿: {long_posts[:5]}')

    return report


def print_report(report):
    if report.get('metrics'):
        print('📊 メトリクス')
        print('-' * 50)
        for k, v in report['metrics'].items():
            print(f'  {k}: {v}')
        print()

    if report.get('ok'):
        print('✅ OK項目')
        print('-' * 50)
        for line in report['ok']:
            print(f'  ✅ {line}')
        print()

    if report.get('warning'):
        print('⚠️  警告')
        print('-' * 50)
        for line in report['warning']:
            print(f'  ⚠️  {line}')
        print()

    if report.get('critical'):
        print('❌ 致命的')
        print('-' * 50)
        for line in report['critical']:
            print(f'  ❌ {line}')
        print()

    # 総合判定
    print('=' * 50)
    if report.get('critical'):
        print('❌ 納品不可：修正必須')
    elif len(report.get('warning', [])) > 3:
        print(f'⚠️  警告 {len(report["warning"])} 件：確認の上で納品判断')
    elif report.get('warning'):
        print(f'🟡 軽微な警告 {len(report["warning"])} 件：品質的にはOK')
    else:
        print('🎉 全チェック通過！納品準備OK')
    print('=' * 50)


def main():
    if len(sys.argv) < 2:
        print('使い方: python3 scripts/deliver/quality_check.py <folder_name>')
        sys.exit(1)

    folder_name = sys.argv[1]
    folder_path = os.path.join(DELIVERIES_DIR, folder_name)
    meta_path = os.path.join(folder_path, 'meta.json')

    if not os.path.exists(meta_path):
        print(f'❌ meta.json が見つかりません: {meta_path}')
        sys.exit(1)

    with open(meta_path, 'r', encoding='utf-8') as f:
        meta = json.load(f)

    drafts_dir = os.path.join(folder_path, 'drafts')

    print('=' * 50)
    print(f'🔍 品質チェック: {meta["job_title"]}')
    print(f'   タイプ: {meta.get("job_type", "-")}')
    print('=' * 50)
    print()

    job_type = meta.get('job_type', 'other')
    if job_type == 'article':
        report = check_article(drafts_dir, meta)
    elif job_type == 'sns':
        report = check_sns(drafts_dir, meta)
    else:
        print('ℹ️  このタイプの自動チェックは未対応')
        return

    print_report(report)


if __name__ == '__main__':
    main()
