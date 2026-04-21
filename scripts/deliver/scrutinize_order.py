#!/usr/bin/env python3
"""
受注内容自動精査ツール
受注メッセージ・案件詳細を貼り付けて実行すると、
リスク判定・スコア算出・返信文生成まで自動実行。

使い方:
  # 対話式（推奨）
  python3 scripts/deliver/scrutinize_order.py

  # ファイルから精査
  python3 scripts/deliver/scrutinize_order.py --file order.txt

  # クリップボードから精査（Macのみ）
  python3 scripts/deliver/scrutinize_order.py --clipboard

エッジケース対応：
- 空入力・異常長入力
- 非UTF-8文字
- 無関係なテキスト
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
LOG_DIR = os.path.join(REPO_DIR, 'logs')
SCRUTINY_LOG = os.path.join(LOG_DIR, 'scrutiny.jsonl')


# ========== 判定ルール ==========

# レッドフラグ：即座に拒否・距離を置くべき
RED_FLAGS = {
    'LINE誘導': [
        r'LINE.*(ID|登録|追加)',
        r'ラインで',
        r'line.*(friend|add)',
    ],
    '登録料・初期費用': [
        r'登録料',
        r'初期費用',
        r'入会金',
        r'教材費',
        r'システム利用料',
        r'保証金',
    ],
    '非現実的な収入': [
        r'月収\s*(100|\d{3})万',
        r'簡単に\s*\d+万',
        r'誰でも.*稼げる',
        r'確実に.*稼げる',
        r'1日\s*\d+万',
    ],
    '外部サイト誘導': [
        r'https?://[^\s]*(bit\.ly|tinyurl|t\.co)',
        r'TELEGRAM',
        r'WhatsApp',
    ],
    '曖昧な業務内容': [
        r'^(詳細は.{0,5}後ほど|興味のある方|まずは連絡)',
    ],
    '個人情報要求': [
        r'身分証.*(写真|画像|提出)',
        r'口座(番号|情報).*先に',
        r'マイナンバー.*先に',
    ],
    'アダルト・グレー': [
        r'アダルト',
        r'アフィリエイト.*保証',
        r'投資案件',
        r'仮想通貨.*紹介',
    ],
}

# イエローフラグ：警告・要確認
YELLOW_FLAGS = {
    '曖昧な単価': [r'単価.*応相談', r'詳細は(契約後|採用後)'],
    '短納期': [r'本日中', r'数時間以内', r'今日中'],
    '修正無制限': [r'修正\s*無制限', r'何度でも.*修正'],
    '著作権全譲渡': [r'著作権.*完全譲渡', r'著作者人格権.*不行使'],
    '過度な秘密保持': [r'SNS.*投稿.*禁止', r'実績.*公表.*不可'],
}

# グリーンフラグ：プロ感ある案件
GREEN_FLAGS = {
    '明確な単価': [r'\d+,?\d+円', r'¥\s*\d+'],
    '具体的納期': [r'\d{1,2}月\d{1,2}日', r'\d+日以内'],
    '明確な成果物': [r'\d+文字', r'\d+記事', r'\d+投稿'],
    '継続性示唆': [r'継続', r'長期', r'月\d+本'],
    '実績開示OK': [r'ポートフォリオ.*(OK|可)'],
}


def get_clipboard():
    """Macのクリップボード取得"""
    try:
        result = subprocess.run(['pbpaste'], capture_output=True, text=True, timeout=5)
        return result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ''


def scan_patterns(text, patterns):
    """パターンマッチで該当フラグを返す"""
    found = {}
    for label, regex_list in patterns.items():
        matches = []
        for regex in regex_list:
            m = re.search(regex, text, re.IGNORECASE | re.MULTILINE)
            if m:
                matches.append(m.group(0)[:50])
        if matches:
            found[label] = matches
    return found


def extract_price(text):
    """単価抽出（複数の表現対応）"""
    patterns = [
        r'単価[^\d]*(\d{1,3}(?:,\d{3})*|\d+)円',
        r'報酬[^\d]*(\d{1,3}(?:,\d{3})*|\d+)円',
        r'(\d{1,3}(?:,\d{3})*|\d+)円\s*/\s*(記事|本|件|時間)',
        r'¥\s*(\d{1,3}(?:,\d{3})*|\d+)',
    ]
    prices = []
    for p in patterns:
        for m in re.finditer(p, text):
            price_str = re.sub(r'[^\d]', '', m.group(1))
            if price_str:
                prices.append(int(price_str))
    return prices


def extract_char_count(text):
    """文字数抽出"""
    matches = re.findall(r'(\d{1,3}(?:,\d{3})*|\d+)\s*(文字|字)', text)
    counts = []
    for num_str, _ in matches:
        num = int(re.sub(r'[^\d]', '', num_str))
        if 100 <= num <= 100000:
            counts.append(num)
    return counts


def calculate_score(text, red_flags, yellow_flags, green_flags, prices, char_counts):
    """0-100のスコア算出"""
    score = 50  # 中立から開始

    # レッドフラグ：大幅減点
    score -= len(red_flags) * 30

    # イエローフラグ：中程度の減点
    score -= len(yellow_flags) * 10

    # グリーンフラグ：加点
    score += len(green_flags) * 8

    # 単価の妥当性
    if prices and char_counts:
        max_price = max(prices)
        max_chars = max(char_counts)
        if max_chars > 0:
            yen_per_char = max_price / max_chars
            if yen_per_char >= 1.0:
                score += 15  # 文字単価1円以上は優良
            elif yen_per_char >= 0.5:
                score += 5
            elif yen_per_char < 0.2:
                score -= 20  # 極端に低単価

    # テキスト長（長い案件詳細=情報豊富）
    if len(text) > 500:
        score += 5
    elif len(text) < 100:
        score -= 10  # 情報不足

    return max(0, min(100, score))


def judge(score, red_flags):
    """スコアから判定"""
    if red_flags:
        return ('reject', '❌ 拒否推奨', 'レッドフラグ検出。応募しない。')
    if score >= 75:
        return ('accept', '✅ 応募推奨', '優良案件。積極的に応募')
    if score >= 55:
        return ('review', '🟡 検討', '条件確認後に判断')
    if score >= 40:
        return ('caution', '⚠️ 要注意', '何かリスクあり。慎重に判断')
    return ('reject', '❌ 応募非推奨', 'スコア低い。見送り推奨')


def generate_reply(judgment, red_flags, yellow_flags):
    """判定に応じた返信テンプレ生成"""
    if judgment == 'accept':
        return """はじめまして。
ご案件を拝見し、ぜひお手伝いさせていただきたく応募いたします。

ご提示の条件で問題なく対応可能です。
以下の点を徹底いたします：
・指示内容を正確に理解した上での作業
・納期厳守・前倒し納品
・迅速な連絡対応（数時間以内の返信）

【ポートフォリオ】
[あなたのURL]

ご指示いただければすぐに作業開始いたします。
ご検討のほど、よろしくお願いいたします。
"""
    elif judgment == 'review':
        return """はじめまして。
ご案件を拝見しました。

応募前に以下の点を確認させてください：

1. 具体的な作業範囲（修正回数の上限含む）
2. 納期の詳細
3. 支払いタイミング（納品後〇日以内）
4. 著作権の取り扱い

上記が明確になれば、ご提示の条件で対応可能です。
ご確認のほど、よろしくお願いいたします。
"""
    elif judgment == 'caution':
        concerns = ', '.join(yellow_flags.keys()) if yellow_flags else '条件不明瞭'
        return f"""ご連絡ありがとうございます。

以下の点について、ご提案させていただきます：

■ 確認させていただきたい点
（{concerns}）
1. 契約条件の書面明示
2. 修正回数の上限設定
3. 支払いタイミングの明確化

上記が合意できれば、お仕事を進めさせていただきます。
"""
    else:  # reject
        if red_flags:
            return """ご連絡ありがとうございます。

検討させていただきましたが、今回は見送らせていただきます。

ご縁がありましたら、また別の機会によろしくお願いいたします。
"""
        return """ご連絡ありがとうございます。

検討させていただきましたが、
今回はスケジュールの都合により見送らせていただきます。

ありがとうございました。
"""


def print_report(text, result):
    """精査レポート表示"""
    print('=' * 60)
    print('🔍 受注内容 精査レポート')
    print('=' * 60)
    print(f'  日時: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print(f'  テキスト長: {len(text)}文字')
    print()

    print('【判定】')
    print(f'  スコア: {result["score"]}/100')
    print(f'  判定: {result["label"]}')
    print(f'  理由: {result["reason"]}')
    print()

    if result['red_flags']:
        print('🚨 レッドフラグ（即拒否案件）')
        for label, examples in result['red_flags'].items():
            print(f'  ❌ {label}')
            for ex in examples[:2]:
                print(f'       例: {ex}')
        print()

    if result['yellow_flags']:
        print('⚠️  イエローフラグ（要確認）')
        for label, examples in result['yellow_flags'].items():
            print(f'  ⚠️  {label}')
            for ex in examples[:2]:
                print(f'       例: {ex}')
        print()

    if result['green_flags']:
        print('✅ グリーンフラグ（プロ案件）')
        for label, examples in result['green_flags'].items():
            print(f'  ✅ {label}（{len(examples)}箇所）')
        print()

    if result['prices']:
        print(f'💰 検出単価: {[f"¥{p:,}" for p in result["prices"]]}')
    if result['char_counts']:
        print(f'📝 検出文字数: {result["char_counts"]}')
        if result['prices'] and result['char_counts']:
            max_price = max(result['prices'])
            max_chars = max(result['char_counts'])
            if max_chars > 0:
                rate = max_price / max_chars
                print(f'📊 文字単価: ¥{rate:.2f}/字')
    print()

    print('=' * 60)
    print('📧 返信テンプレ（該当する方を使用）')
    print('=' * 60)
    print(result['reply_template'])
    print('=' * 60)


def save_log(text, result):
    """ログ保存"""
    os.makedirs(LOG_DIR, exist_ok=True)
    log_entry = {
        'timestamp': datetime.now().isoformat(timespec='seconds'),
        'text_length': len(text),
        'text_preview': text[:200],
        'score': result['score'],
        'judgment': result['judgment'],
        'red_flags': list(result['red_flags'].keys()),
        'yellow_flags': list(result['yellow_flags'].keys()),
        'green_flags': list(result['green_flags'].keys()),
        'prices': result['prices'],
        'char_counts': result['char_counts'],
    }
    with open(SCRUTINY_LOG, 'a', encoding='utf-8') as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')


def scrutinize(text):
    """本体：テキストを受け取り精査"""
    if not text or len(text.strip()) < 20:
        return None

    red_flags = scan_patterns(text, RED_FLAGS)
    yellow_flags = scan_patterns(text, YELLOW_FLAGS)
    green_flags = scan_patterns(text, GREEN_FLAGS)
    prices = extract_price(text)
    char_counts = extract_char_count(text)

    score = calculate_score(text, red_flags, yellow_flags, green_flags, prices, char_counts)
    judgment, label, reason = judge(score, red_flags)
    reply_template = generate_reply(judgment, red_flags, yellow_flags)

    return {
        'score': score,
        'judgment': judgment,
        'label': label,
        'reason': reason,
        'red_flags': red_flags,
        'yellow_flags': yellow_flags,
        'green_flags': green_flags,
        'prices': prices,
        'char_counts': char_counts,
        'reply_template': reply_template,
    }


def get_input_text():
    """入力ソースから案件テキストを取得"""
    args = sys.argv[1:]

    if '--file' in args:
        idx = args.index('--file')
        if idx + 1 >= len(args):
            print('❌ --file の後にファイルパスを指定してください')
            sys.exit(1)
        path = args[idx + 1]
        if not os.path.exists(path):
            print(f'❌ ファイルが見つかりません: {path}')
            sys.exit(1)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            print(f'❌ ファイルがUTF-8ではありません: {path}')
            sys.exit(1)

    if '--clipboard' in args:
        text = get_clipboard()
        if not text:
            print('❌ クリップボードが空、もしくはpbpaste非対応')
            sys.exit(1)
        return text

    # 対話式
    print('=' * 60)
    print('🔍 受注内容 精査ツール')
    print('=' * 60)
    print('案件内容を貼り付けてください')
    print('（複数行可。終わったら空行でEnterを2回押す）')
    print()

    lines = []
    empty_count = 0
    try:
        while True:
            line = input()
            if line.strip() == '':
                empty_count += 1
                if empty_count >= 2:
                    break
            else:
                empty_count = 0
            lines.append(line)
    except EOFError:
        pass

    return '\n'.join(lines)


def main():
    if '--help' in sys.argv or '-h' in sys.argv:
        print(__doc__)
        sys.exit(0)

    text = get_input_text()

    if not text or len(text.strip()) < 20:
        print('❌ テキストが短すぎます（20文字以上必要）')
        sys.exit(1)

    # 極端に長い場合は警告して切り詰め
    if len(text) > 20000:
        print(f'⚠️  テキストが非常に長い（{len(text)}文字）。先頭20000字で精査します。')
        text = text[:20000]

    result = scrutinize(text)
    if result is None:
        print('❌ 精査失敗')
        sys.exit(1)

    print()
    print_report(text, result)

    # ログ保存
    save_log(text, result)
    print()
    print(f'📝 ログ: {SCRUTINY_LOG}')

    # 判定に応じた次のアクション提案
    print()
    if result['judgment'] == 'accept':
        print('🚀 次のアクション:')
        print('  1. 上記返信テンプレをコピー→クライアントに送信')
        print('  2. 受注確定後: python3 scripts/deliver/new_job.py')
    elif result['judgment'] == 'reject':
        print('🚫 次のアクション:')
        print('  1. 上記返信テンプレで丁寧に辞退')
        print('  2. 応募トラッカーでステータス「失注」に更新')
    else:
        print('🤔 次のアクション:')
        print('  1. 上記返信テンプレで条件確認')
        print('  2. 返信内容を見て再判断')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n\n中断されました')
        sys.exit(130)
