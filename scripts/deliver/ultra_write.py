#!/usr/bin/env python3
"""
ULTRA WRITER：商業出版レベル（10000点）の記事生成システム
1記事あたり8-10回のAPI呼び出しで圧倒的品質を実現

【段階】
0. 最新リサーチ（WebSearch代替・Claude知識+α）
1. 競合分析（想定上位記事の特徴抽出）
2. ペルソナ深掘り（読者の本音を再現）
3. 構成設計（E-E-A-T全要素を盛り込んだ精密構造）
4. 初稿生成（事実出典付き）
5. ファクトチェック専門レビュー
6. SEOエディター専門レビュー
7. 読者代弁レビュー（読者役で読んでみる）
8. 独自性強化（テンプレ排除）
9. 最終ポリッシュ（流れの磨き）

API_KEY必須・1記事あたり10〜30円のコスト発生

使い方:
  python3 scripts/deliver/ultra_write.py "<folder>"
  python3 scripts/deliver/ultra_write.py "<folder>" --skip <step>  # 特定段階スキップ
"""

import json
import os
import re
import sys
import time
import urllib.request
import urllib.error


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
DELIVERIES_DIR = os.path.join(REPO_DIR, 'deliveries')

API_URL = 'https://api.anthropic.com/v1/messages'
MODEL = 'claude-sonnet-4-5'
MAX_TOKENS = 8000


# ========== プロンプトテンプレート（10段階）==========

P0_RESEARCH = """あなたは{persona}向けの「{keyword}」分野のリサーチャーです。

このキーワードに関する以下を整理してください：

1. 業界の最新トレンド（2024-2025年）：3つ
2. よく言われる定説・常識：5つ
3. 多くの人が見落としている事実：3つ
4. 信頼できる出典として引用できる組織・調査：5つ
5. 業界用語・専門用語：10個（簡単な説明付き）
6. 競合する解決策・代替案：3つ
7. 読者がつまずきやすいポイント：5つ

出力は構造化テキストで簡潔に。
"""

P1_COMPETITOR = """「{keyword}」で検索すると、上位に来るような記事の特徴を分析してください。
あなたは数千の上位記事を分析した SEO アナリストです。

以下を出力：
1. 上位記事の典型的な構成パターン（H2見出しの傾向）
2. 上位記事が必ず含む要素（数値・図表・体験談 等）
3. 上位記事が避けている表現・要素
4. ユーザーがクリックしたくなるタイトルの特徴
5. 上位記事との差別化ポイント（あなたの記事が勝つために必要なもの）

簡潔に、実践的に。
"""

P2_PERSONA = """{persona}の本音をペルソナとして詳述してください。

【記述項目】
1. デモグラフィック（年齢・職業・年収・家族構成）
2. なぜ「{keyword}」を検索するのか（直接の動機）
3. 検索する前の感情（不安・焦り・期待）
4. 過去に試したこと・失敗したこと
5. 周囲に相談できない理由
6. 記事に求めるもの（情報・共感・行動指針）
7. 読み終わった後にとるであろう行動
8. 記事を信頼するための条件

このペルソナの「本音の独白」を100字程度で書いてください。
記事執筆時は常にこのペルソナを意識します。
"""

P3_STRUCTURE = """以下の情報を統合して、商業出版レベルの記事構成を作成してください。

【リサーチ結果】
{research}

【競合分析】
{competitor_analysis}

【ペルソナ】
{persona_detail}

【基本情報】
- メインキーワード: {keyword}
- 文字数: {char_count}字
- トーン: {tone}

【構成要件】
1. タイトル案5つ（CTR最大化を意識）
2. メタディスクリプション（120字以内・キーワード含有）
3. リード文設計（300字・問題提起→解決約束→読者の利得明示）
4. H2構成6-8個（論理的順序）
5. 各H2にH3を2-3個
6. 各H2の役割と含めるべき具体例
7. まとめのCTA設計（読者の次の行動を明確に）
8. 差別化ポイント（上位記事と何が違うか）
9. 引用・データの配置案（どこに何を入れるか）

詳細かつ実行可能な構成を出してください。
"""

P4_DRAFT = """あなたはプロのSEOライターです。
以下の構成と素材を使って、{char_count}字の記事を執筆してください。

【構成】
{structure}

【リサーチ素材（出典として活用）】
{research}

【ペルソナ（常に意識）】
{persona_detail}

【執筆ルール】
- E-E-A-T完全準拠（実体験・専門性・権威性・信頼性）
- 各H2セクションに具体的な数値・事例・出典を最低1つ
- ペルソナの本音に語りかける
- テンプレフレーズ禁止（「結論から言うと」「いかがでしたか」等）
- リスキー情報には「専門家に相談を推奨」を添える
- 1段落3文以内（スマホ可読性）
- 各H2末に「ここがポイント」を1行
- 語尾は{tone}で統一

商業出版レベルの記事として執筆してください。
"""

P5_FACTCHECK = """あなたは厳格なファクトチェッカーです。
以下の記事の事実関係を検証してください。

【記事】
{article}

【検証項目】
1. 数値・統計の妥当性（存在しそうな数字か）
2. 法律・規制の言及（最新性・正確性）
3. 業界用語の使用（誤用がないか）
4. 因果関係の主張（過度な一般化がないか）
5. 比較・順位の根拠（明確な出典があるか）

【出力】
- 問題箇所のリスト（あれば）
- 修正版の該当部分
- 全体の信頼性スコア（0-100）

問題なければ「ファクト問題なし」と明示。
"""

P6_SEO = """あなたはSEO最適化のプロです。
以下の記事をSEO観点で改善してください。

【記事】
{article}

【メインキーワード】
{keyword}

【最適化項目】
1. キーワード密度（0.5〜2.0%が理想）
2. キーワードの自然な配置（タイトル・H2・冒頭・末尾）
3. 関連キーワードの自然な含有
4. 構造化された見出し（H2/H3の論理性）
5. メタディスクリプションの最適化

問題があれば改善版を出力。
無ければ「SEO問題なし」と明示。
"""

P7_READER = """あなたは{persona}の読者です。記事を実際に読んだ感想を述べてください。

【記事】
{article}

【感想項目】
1. 最初の100字で読むのをやめなかったか（フック評価）
2. 知りたかった情報が得られたか
3. 読んでいて疲れる箇所はあったか
4. 「具体的すぎて参考になる」「抽象的すぎて意味ない」のどちら寄りか
5. 読み終わって行動したくなったか
6. 友達にシェアしたくなる内容だったか

【点数】読者満足度（0-100）

満足度が80未満なら、改善すべき箇所を具体的に指摘してください。
"""

P8_UNIQUENESS = """以下の記事を「他の凡庸な記事との差別化」観点で改善してください。

【記事】
{article}

【差別化チェック項目】
1. テンプレ的フレーズの除去（「実は」「ご存知ですか」「いかがでしたか」等）
2. ありきたりな例え・比喩の置換
3. 独自の切り口・視点の追加
4. 数字・固有名詞の具体性UP
5. 読み手が「このライターは違う」と感じる要素

問題箇所を改善した全文を出力。
変更不要な部分はそのまま残してください。
省略禁止。完全な記事を出力してください。
"""

P9_POLISH = """以下の記事の最終仕上げをしてください。

【記事】
{article}

【ポリッシュ項目】
1. 文章のリズム（短文と長文のバランス）
2. 段落間のつながりの滑らかさ
3. 重複表現の除去
4. 助詞の最適化（「は」「が」「を」の選び方）
5. 冗長な修飾の削除
6. 全体の読み心地

完成版を出力（省略禁止）。
これが最終納品物となるレベルに仕上げてください。
"""


def load_env():
    env_path = os.path.join(REPO_DIR, '.env')
    if not os.path.exists(env_path):
        return
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and value and key not in os.environ:
                os.environ[key] = value


def get_api_key():
    load_env()
    key = os.environ.get('ANTHROPIC_API_KEY')
    if not key:
        print('❌ ANTHROPIC_API_KEY 未設定')
        sys.exit(1)
    return key


def call_claude(prompt, api_key, max_retries=3, label=''):
    payload = {
        'model': MODEL,
        'max_tokens': MAX_TOKENS,
        'messages': [{'role': 'user', 'content': prompt}],
    }
    data = json.dumps(payload).encode('utf-8')
    headers = {
        'x-api-key': api_key,
        'anthropic-version': '2023-06-01',
        'content-type': 'application/json',
    }
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(API_URL, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=180) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                if 'content' in result and result['content']:
                    return result['content'][0].get('text', '')
                return ''
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 2 ** (attempt + 2)
                print(f'  ⏳ レート制限。{wait}秒待機...')
                time.sleep(wait)
                continue
            error_body = e.read().decode('utf-8', errors='ignore')
            print(f'❌ {label} API エラー: {error_body[:200]}')
            return None
        except urllib.error.URLError as e:
            wait = 2 ** (attempt + 1)
            print(f'  ⏳ ネットワーク: {e.reason}。{wait}秒...')
            time.sleep(wait)
    return None


def extract_article_from_response(response, fallback):
    """レスポンスから完全版記事を抽出（省略疑い時はfallback使用）"""
    if not response:
        return fallback
    # 改善版セクションを探す
    match = re.search(r'(?:改善版|完成版|最終版|修正版)\s*[:：]?\s*\n+(.+)', response, re.DOTALL)
    if match:
        candidate = match.group(1).strip()
        # 元の80%以上の長さなら採用
        if len(candidate) >= len(fallback) * 0.7:
            return candidate
    # 全体を改善版とみなせるか
    if len(response) >= len(fallback) * 0.7 and '#' in response:
        return response
    return fallback


def extract_score(response, default=0):
    """レスポンスから点数を抽出"""
    if not response:
        return default
    matches = re.findall(r'(?:スコア|点数|評価|信頼性)\s*[:：]?\s*(\d+)', response)
    if matches:
        return int(matches[0])
    matches = re.findall(r'(\d+)\s*[/／]\s*100', response)
    if matches:
        return int(matches[0])
    return default


def save_step(folder_path, step_name, content):
    """各ステップの中間ファイル保存"""
    debug_dir = os.path.join(folder_path, '_ultra_debug')
    os.makedirs(debug_dir, exist_ok=True)
    path = os.path.join(debug_dir, f'{step_name}.md')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def ultra_write_article(folder_path, meta, api_key):
    """ULTRA記事生成（10段階）"""
    details = meta.get('details', {})
    keyword = details.get('keyword', '')
    char_count = details.get('char_count', '3000')
    persona = details.get('persona', '一般読者')
    tone = details.get('tone', '丁寧')

    print('=' * 70)
    print('🚀 ULTRA WRITER 起動（10段階・8-10回API呼び出し）')
    print('=' * 70)
    print(f'  キーワード: {keyword}')
    print(f'  文字数: {char_count}')
    print(f'  ペルソナ: {persona}')
    print()

    # ===== STEP 0: リサーチ =====
    print('📚 STEP 0/9: 業界リサーチ...')
    research = call_claude(P0_RESEARCH.format(keyword=keyword, persona=persona), api_key, label='research')
    if not research:
        return False
    save_step(folder_path, '0_research', research)
    print(f'  ✅ {len(research)}字')

    # ===== STEP 1: 競合分析 =====
    print('🔍 STEP 1/9: 競合分析...')
    competitor = call_claude(P1_COMPETITOR.format(keyword=keyword), api_key, label='competitor')
    if not competitor:
        return False
    save_step(folder_path, '1_competitor', competitor)
    print(f'  ✅ {len(competitor)}字')

    # ===== STEP 2: ペルソナ深掘り =====
    print('👤 STEP 2/9: ペルソナ深掘り...')
    persona_detail = call_claude(P2_PERSONA.format(keyword=keyword, persona=persona), api_key, label='persona')
    if not persona_detail:
        return False
    save_step(folder_path, '2_persona', persona_detail)
    print(f'  ✅ {len(persona_detail)}字')

    # ===== STEP 3: 構成設計 =====
    print('🏗️  STEP 3/9: 商業レベル構成設計...')
    structure = call_claude(P3_STRUCTURE.format(
        research=research, competitor_analysis=competitor,
        persona_detail=persona_detail, keyword=keyword,
        char_count=char_count, tone=tone,
    ), api_key, label='structure')
    if not structure:
        return False
    save_step(folder_path, '3_structure', structure)
    drafts_dir = os.path.join(folder_path, 'drafts')
    os.makedirs(drafts_dir, exist_ok=True)
    with open(os.path.join(drafts_dir, '1_structure.md'), 'w', encoding='utf-8') as f:
        f.write(structure)
    print(f'  ✅ {len(structure)}字')

    # ===== STEP 4: 初稿 =====
    print('✍️  STEP 4/9: 初稿執筆（出典付き）...')
    draft = call_claude(P4_DRAFT.format(
        structure=structure, research=research, persona_detail=persona_detail,
        char_count=char_count, tone=tone,
    ), api_key, label='draft')
    if not draft:
        return False
    save_step(folder_path, '4_draft', draft)
    print(f'  ✅ 初稿 {len(draft)}字')

    # ===== STEP 5: ファクトチェック =====
    print('🔬 STEP 5/9: ファクトチェック専門レビュー...')
    fact_review = call_claude(P5_FACTCHECK.format(article=draft), api_key, label='factcheck')
    if fact_review:
        save_step(folder_path, '5_fact_review', fact_review)
        score = extract_score(fact_review, default=80)
        print(f'  📊 信頼性スコア: {score}/100')
        if score < 80:
            improved = extract_article_from_response(fact_review, draft)
            draft = improved
            print(f'  ✏️  ファクト改善版適用')

    # ===== STEP 6: SEOエディター =====
    print('🔍 STEP 6/9: SEOエディターレビュー...')
    seo_review = call_claude(P6_SEO.format(article=draft, keyword=keyword), api_key, label='seo')
    if seo_review:
        save_step(folder_path, '6_seo_review', seo_review)
        if 'SEO問題なし' not in seo_review:
            improved = extract_article_from_response(seo_review, draft)
            draft = improved
            print(f'  ✏️  SEO改善版適用')

    # ===== STEP 7: 読者代弁レビュー =====
    print('👥 STEP 7/9: 読者代弁レビュー...')
    reader_review = call_claude(P7_READER.format(article=draft, persona=persona), api_key, label='reader')
    if reader_review:
        save_step(folder_path, '7_reader_review', reader_review)
        score = extract_score(reader_review, default=80)
        print(f'  📊 読者満足度: {score}/100')

    # ===== STEP 8: 独自性強化 =====
    print('🎨 STEP 8/9: 独自性強化...')
    unique_review = call_claude(P8_UNIQUENESS.format(article=draft), api_key, label='unique')
    if unique_review:
        save_step(folder_path, '8_unique', unique_review)
        improved = extract_article_from_response(unique_review, draft)
        if len(improved) >= len(draft) * 0.8:
            draft = improved
            print(f'  ✏️  独自性強化版適用')

    # ===== STEP 9: 最終ポリッシュ =====
    print('✨ STEP 9/9: 最終ポリッシュ...')
    polished = call_claude(P9_POLISH.format(article=draft), api_key, label='polish')
    if polished:
        save_step(folder_path, '9_polished', polished)
        improved = extract_article_from_response(polished, draft)
        if len(improved) >= len(draft) * 0.8:
            draft = improved
            print(f'  ✨ 最終版完成')

    # 保存
    final_path = os.path.join(drafts_dir, 'article.md')
    with open(final_path, 'w', encoding='utf-8') as f:
        f.write(draft)

    print()
    print('=' * 70)
    print('🎉 ULTRA WRITER 完了')
    print('=' * 70)
    print(f'  📄 最終稿: drafts/article.md（{len(draft)}字）')
    print(f'  🗂  中間ファイル: _ultra_debug/0-9_*.md')
    print()
    print('次のステップ:')
    print(f'  python3 scripts/deliver/quality_check.py "{os.path.basename(folder_path)}"')
    print(f'  python3 scripts/deliver/package.py "{os.path.basename(folder_path)}"')

    return True


def main():
    if len(sys.argv) < 2:
        print('使い方: python3 scripts/deliver/ultra_write.py <folder_name>')
        sys.exit(1)

    folder_name = sys.argv[1]
    folder_path = os.path.join(DELIVERIES_DIR, folder_name)
    if not os.path.isdir(folder_path):
        print(f'❌ フォルダ無し: {folder_name}')
        sys.exit(1)

    meta_path = os.path.join(folder_path, 'meta.json')
    with open(meta_path, 'r', encoding='utf-8') as f:
        meta = json.load(f)

    api_key = get_api_key()
    job_type = meta.get('job_type', 'other')

    if job_type != 'article':
        print(f'⚠️  ULTRA WRITER は記事タイプ専用です（現在: {job_type}）')
        sys.exit(1)

    # 既存尊重
    existing = os.path.join(folder_path, 'drafts', 'article.md')
    if os.path.exists(existing) and '--force' not in sys.argv:
        print(f'ℹ️  既存 article.md 検出。--force で上書き')
        sys.exit(0)

    if ultra_write_article(folder_path, meta, api_key):
        print('\n✅ ULTRA WRITER 成功')
    else:
        print('\n❌ ULTRA WRITER 失敗')
        sys.exit(1)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n中断されました')
        sys.exit(130)
