"""
02b_fraud_check.py — 詐欺検出（ローカル辞書のみ・外部API不使用）

2層チェック:
  層1: クライアント詐欺 — 案件文・タイトル・クライアント情報の詐欺パターン検出
  層2: 対象サイト詐欺   — 案件文からURL抽出→ブランド偽装・怪しいTLD等を判定

使い方:
  # ライブラリとして
  from importlib import import_module
  fc = import_module("02b_fraud_check")
  result = fc.assess(job_text, meta=job)

  # CLI（単体テスト用）
  echo "案件テキスト" | python 02b_fraud_check.py

出力:
  {
    "risk_level": "SAFE" | "SUSPICIOUS" | "FRAUD",
    "findings": [{"layer": 1|2, "category": "...", "severity": "critical|high|medium|low",
                  "evidence": "...", "description": "..."}],
    "auto_block": bool,
    "explanation": "..."
  }
"""

import json
import re
import sys
from urllib.parse import urlparse


# ─────────────────────────────────────────────
# 層1: クライアント詐欺パターン
# ─────────────────────────────────────────────

CLIENT_FRAUD_PATTERNS = [
    # 振り込め詐欺・受取代行系（critical: 犯罪加担リスク）
    {
        "category": "remittance_fraud",
        "severity": "critical",
        "keywords": [
            "受け取り代行", "受取代行", "送金代行", "出金代行",
            "口座貸", "口座を貸", "名義貸", "名義を貸",
            "代理受領", "振込代行", "荷物受取", "荷受け代行",
        ],
        "description": "振り込め詐欺・マネーロンダリング加担リスク",
    },
    # 前払い詐欺（critical: オーナーが被害者）
    {
        "category": "upfront_payment",
        "severity": "critical",
        "keywords": [
            "保証金", "前払金", "前払い金", "初期費用",
            "登録料", "教材費", "入会金", "認定料",
            "システム利用料", "サポート料を先に",
        ],
        "description": "典型的な副業詐欺（保証金・前払い要求）",
    },
    # MLM・マルチ商法（critical）
    {
        "category": "mlm",
        "severity": "critical",
        "keywords": [
            "ネットワークビジネス", "マルチレベル", "紹介制度",
            "ダウン構築", "アップライン", "権利収入", "不労所得",
            "MLM", "連鎖販売",
        ],
        "description": "マルチ商法・ネットワークビジネス勧誘",
    },
    # プラットフォーム外連絡誘導（high: 規約違反・詐欺の温床）
    {
        "category": "external_contact",
        "severity": "high",
        "keywords": [
            "LINE登録", "LINE@", "公式LINE", "ライン登録",
            "Telegram", "WhatsApp", "Signal", "Discord DM",
            "メールで直接", "外部サイトへ", "DMで連絡",
            "@追加してください",
        ],
        "description": "プラットフォーム外への連絡誘導（規約違反・詐欺の温床）",
    },
    # 仮想通貨・外貨支払い（high: 追跡不可）
    {
        "category": "crypto_payment",
        "severity": "high",
        "keywords": [
            "仮想通貨で支払", "暗号資産で支払", "ビットコイン支払",
            "BTC支払", "USDT", "ETH支払", "バイナンス", "Binance",
        ],
        "description": "仮想通貨支払い（トラブル時追跡不可）",
    },
    # 違法・グレー業務（high）
    {
        "category": "illegal_work",
        "severity": "high",
        "keywords": [
            "在籍確認代行", "逆SEO", "誹謗中傷",
            "口コミ操作", "レビュー工作", "評価水増し",
            "サクラ募集", "出会い系サポート",
        ],
        "description": "違法・グレーゾーン業務",
    },
    # 海外代理人募集（medium-high: 詐欺常套）
    {
        "category": "overseas_proxy",
        "severity": "high",
        "keywords": [
            "海外在住のクライアント", "海外からの代理",
            "日本での代理人", "海外本社の日本窓口",
        ],
        "description": "海外詐欺の日本代理人募集パターン",
    },
]

# 高収入保証系（正規表現で金額付きパターンを検出）
EASY_MONEY_REGEXES = [
    (r"1日[0-9０-９]+万[円]?(?:以上)?(?:稼|保証|確定)", "high",
     "1日N万円保証の典型的な詐欺文言"),
    (r"月[0-9０-９]+万[円]?(?:以上)?保証", "high",
     "月収保証の典型的な詐欺文言"),
    (r"スマホ[だの]?[けみ]で[0-9０-９]+万", "high",
     "スマホだけで稼げる系の詐欺文言"),
    (r"誰でも[0-9０-９]+万", "high",
     "誰でも稼げる系の詐欺文言"),
    (r"コピペ[だの]?[けみ]で[月日]?[0-9０-９]*万?", "high",
     "コピペで稼げる系の詐欺文言"),
    (r"クリック(?:する)?だけで[0-9０-９]+", "high",
     "クリックだけで稼げる系の詐欺文言"),
    (r"完全在宅で月[0-9０-９]+万", "medium",
     "完全在宅月収保証系の文言"),
]


# ─────────────────────────────────────────────
# 層2: 対象サイト詐欺パターン
# ─────────────────────────────────────────────

# タイポスクワッティング検出対象の有名ブランド
KNOWN_BRANDS = [
    "amazon", "rakuten", "paypay", "mercari", "yahoo", "google",
    "apple", "microsoft", "line", "facebook", "instagram", "twitter",
    "smbc", "mufg", "mizuho", "jpbank", "yucho", "resona",
    "jcb", "visa", "mastercard", "americanexpress",
    "docomo", "softbank", "nhk", "jreast", "jrwest",
    "netflix", "spotify",
]

# 正規ドメイン許容リスト（ブランド偽装判定から除外）
LEGITIMATE_DOMAINS = {
    "amazon": ["amazon.co.jp", "amazon.com"],
    "rakuten": ["rakuten.co.jp", "rakuten.com", "rakuten.ne.jp"],
    "paypay": ["paypay.ne.jp"],
    "mercari": ["mercari.com", "jp.mercari.com"],
    "yahoo": ["yahoo.co.jp", "yahoo.com", "yahoo-net.jp"],
    "google": ["google.com", "google.co.jp", "googleusercontent.com"],
    "apple": ["apple.com"],
    "microsoft": ["microsoft.com"],
    "line": ["line.me", "linecorp.com"],
    "smbc": ["smbc.co.jp"],
    "mufg": ["mufg.jp", "bk.mufg.jp"],
    "mizuho": ["mizuhobank.co.jp"],
    "jpbank": ["jp-bank.japanpost.jp"],
    "yucho": ["jp-bank.japanpost.jp"],
    "jcb": ["jcb.co.jp"],
    "docomo": ["docomo.ne.jp"],
    "softbank": ["softbank.jp"],
    "nhk": ["nhk.or.jp", "nhk.jp"],
    "netflix": ["netflix.com"],
    "spotify": ["spotify.com"],
}

# 詐欺に多用される格安/無料TLD
SUSPICIOUS_TLDS = [
    ".xyz", ".top", ".work", ".cf", ".tk", ".ml", ".ga",
    ".click", ".loan", ".bid", ".win", ".racing", ".download",
]

URL_PATTERN = re.compile(r'https?://[^\s\'"<>（）、。」]+[^\s\'"<>（）、。」.,]')

# URLでない裸のドメイン（http://無し）を抽出するパターン
# 2〜5ラベル・末尾TLDは2〜6文字のアルファベット限定
# re.ASCIIで日本語と境界が正しく認識されるようにする
BARE_DOMAIN_PATTERN = re.compile(
    r'\b([a-zA-Z][-a-zA-Z0-9]*(?:\.[a-zA-Z0-9][-a-zA-Z0-9]*){0,4}\.[a-zA-Z]{2,6})\b',
    re.ASCII,
)


def extract_urls(text: str) -> list:
    """テキストからhttp(s)://付きURLを抽出（重複排除）"""
    return list(dict.fromkeys(URL_PATTERN.findall(text)))


def extract_bare_domains(text: str) -> list:
    """http://無しのドメイン候補を抽出。誤検出を避けるため詐欺指標と合致する場合のみ使用する。"""
    candidates = BARE_DOMAIN_PATTERN.findall(text)
    # 明らかに非ドメインなパターンを除外（ファイル名・バージョン等）
    excluded_endings = (".py", ".js", ".ts", ".mjs", ".md", ".json", ".csv", ".txt",
                        ".xlsx", ".xls", ".doc", ".docx", ".pdf", ".png", ".jpg",
                        ".jpeg", ".gif", ".svg", ".zip", ".tar", ".gz")
    out = []
    for d in candidates:
        low = d.lower()
        if low.endswith(excluded_endings):
            continue
        if re.match(r"^v?\d+(\.\d+)+$", low):  # バージョン番号 (1.2.3, v2.0)
            continue
        out.append(low)
    return list(dict.fromkeys(out))


def _is_legitimate_domain(host: str, brand: str) -> bool:
    """ホストがブランドの正規ドメインまたはそのサブドメインか判定"""
    legits = LEGITIMATE_DOMAINS.get(brand, [])
    for legit in legits:
        if host == legit or host.endswith("." + legit):
            return True
    return False


def analyze_url(url: str) -> list:
    """URL1件を詐欺性の観点で分析"""
    findings = []
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        scheme = (parsed.scheme or "").lower()
    except Exception:
        return findings
    if not host:
        return findings

    # 1. HTTPS非対応
    if scheme == "http" and not host.startswith("localhost"):
        findings.append({
            "layer": 2, "category": "no_https", "severity": "medium",
            "evidence": url[:80],
            "description": "HTTPS非対応（通信が暗号化されていない）",
        })

    # 2. IPアドレス直指定
    if re.match(r"^\d+\.\d+\.\d+\.\d+$", host):
        findings.append({
            "layer": 2, "category": "ip_direct", "severity": "high",
            "evidence": host,
            "description": "IPアドレス直指定（ドメインを隠している）",
        })

    # 3. 怪しいTLD
    for tld in SUSPICIOUS_TLDS:
        if host.endswith(tld):
            findings.append({
                "layer": 2, "category": "suspicious_tld", "severity": "high",
                "evidence": f"{host} (TLD={tld})",
                "description": f"詐欺サイトに多用されるTLD（{tld}）",
            })
            break

    # 4. ブランド偽装（タイポスクワッティング）
    for brand in KNOWN_BRANDS:
        if brand not in host:
            continue
        if _is_legitimate_domain(host, brand):
            break  # 正規ドメインなので以降のブランドチェックも不要
        findings.append({
            "layer": 2, "category": "brand_spoofing", "severity": "critical",
            "evidence": host,
            "description": f"有名ブランド「{brand}」を含む非公式ドメイン（フィッシング疑い）",
        })
        break

    # 5. 異常に深い/長いサブドメイン（5階層以上 または 80文字以上）
    if host.count(".") >= 5 or len(host) >= 80:
        findings.append({
            "layer": 2, "category": "long_subdomain", "severity": "medium",
            "evidence": host[:100],
            "description": "異常に深い/長いサブドメイン構造（フィッシング典型）",
        })

    # 6. ハイフン過多（4つ以上）
    if host.count("-") >= 4:
        findings.append({
            "layer": 2, "category": "excessive_hyphens", "severity": "low",
            "evidence": host,
            "description": "ハイフンが異常に多い（紛らわしいドメイン）",
        })

    return findings


# ─────────────────────────────────────────────
# 個別チェック関数
# ─────────────────────────────────────────────

def _check_client_patterns(text: str) -> list:
    """層1: クライアント詐欺パターンのキーワードマッチ"""
    findings = []
    for p in CLIENT_FRAUD_PATTERNS:
        matched = [k for k in p["keywords"] if k in text]
        if matched:
            findings.append({
                "layer": 1,
                "category": p["category"],
                "severity": p["severity"],
                "evidence": "「" + "」「".join(matched[:3]) + "」",
                "description": p["description"],
            })
    # 金額付き詐欺文言の正規表現
    for rx, severity, desc in EASY_MONEY_REGEXES:
        m = re.search(rx, text)
        if m:
            findings.append({
                "layer": 1,
                "category": "easy_money_regex",
                "severity": severity,
                "evidence": m.group(0),
                "description": desc,
            })
    return findings


def _check_meta(meta) -> list:
    """メタデータ（クライアント評価等）から詐欺兆候を検出"""
    if not meta:
        return []
    findings = []
    reviews = meta.get("client_reviews")
    if reviews is not None:
        try:
            if int(reviews) == 0:
                findings.append({
                    "layer": 1, "category": "zero_reviews", "severity": "medium",
                    "evidence": "reviews=0",
                    "description": "クライアント評価0件（新規/捨てアカウントの可能性）",
                })
        except (ValueError, TypeError):
            pass
    rating = meta.get("client_rating")
    if rating is not None:
        try:
            if float(rating) < 3.0:
                findings.append({
                    "layer": 1, "category": "low_rating", "severity": "high",
                    "evidence": f"rating={rating}",
                    "description": "クライアント評価が極端に低い（3.0未満）",
                })
        except (ValueError, TypeError):
            pass
    return findings


def _check_bare_domain(domain: str) -> list:
    """裸ドメイン1件を分析。誤検出防止のため詐欺指標ヒット時のみ報告。"""
    findings = []
    d = domain.lower()
    # 怪しいTLD
    for tld in SUSPICIOUS_TLDS:
        if d.endswith(tld):
            findings.append({
                "layer": 2, "category": "suspicious_tld", "severity": "high",
                "evidence": f"{d} (TLD={tld})",
                "description": f"詐欺サイトに多用されるTLD（{tld}）",
            })
            break
    # ブランド偽装
    for brand in KNOWN_BRANDS:
        if brand in d and not _is_legitimate_domain(d, brand):
            findings.append({
                "layer": 2, "category": "brand_spoofing", "severity": "critical",
                "evidence": d,
                "description": f"有名ブランド「{brand}」を含む非公式ドメイン（フィッシング疑い）",
            })
            break
    return findings


def _check_target_urls(text: str) -> list:
    """層2: 案件文中のURL/裸ドメインを分析"""
    findings = []
    url_hosts = set()
    # http(s)://付きURLを分析
    for url in extract_urls(text)[:10]:
        findings.extend(analyze_url(url))
        try:
            url_hosts.add((urlparse(url).hostname or "").lower())
        except Exception:
            pass
    # 裸ドメインを分析（URL済みは除外、詐欺指標合致のみ報告）
    for domain in extract_bare_domains(text)[:15]:
        if domain in url_hosts:
            continue
        findings.extend(_check_bare_domain(domain))
    return findings


def _determine_risk_level(findings: list):
    """findingsから総合リスクレベルとauto_blockを決定"""
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for f in findings:
        sev = f.get("severity", "low")
        counts[sev] = counts.get(sev, 0) + 1

    # critical 1件以上 → FRAUD（自動除外）
    if counts["critical"] >= 1:
        return "FRAUD", True
    # high 2件以上 → FRAUD
    if counts["high"] >= 2:
        return "FRAUD", True
    # high 1件 → SUSPICIOUS（人間確認）
    if counts["high"] >= 1:
        return "SUSPICIOUS", False
    # medium 2件以上 → SUSPICIOUS
    if counts["medium"] >= 2:
        return "SUSPICIOUS", False
    return "SAFE", False


# ─────────────────────────────────────────────
# 公開API
# ─────────────────────────────────────────────

def assess(job_text: str, meta=None) -> dict:
    """案件の詐欺リスクを総合評価する。"""
    full_text = job_text or ""
    if meta:
        full_text += "\n" + (meta.get("title") or "")
        full_text += "\n" + (meta.get("budget_text") or "")

    findings = []
    findings.extend(_check_client_patterns(full_text))
    findings.extend(_check_meta(meta))
    findings.extend(_check_target_urls(full_text))

    risk_level, auto_block = _determine_risk_level(findings)

    if risk_level == "FRAUD":
        explanation = "詐欺の可能性が極めて高く、自動除外対象です"
    elif risk_level == "SUSPICIOUS":
        explanation = "詐欺の疑いあり。応募前に要確認"
    else:
        explanation = "明らかな詐欺指標は検出されませんでした"

    return {
        "risk_level": risk_level,
        "findings": findings,
        "auto_block": auto_block,
        "explanation": explanation,
    }


def format_findings(findings: list) -> str:
    """findingsを人間が読める形式に整形"""
    if not findings:
        return "（検出なし）"
    lines = []
    sev_icon = {"critical": "🚨", "high": "⚠️ ", "medium": "⚠ ", "low": "・"}
    for f in findings:
        icon = sev_icon.get(f.get("severity", "low"), "・")
        lines.append(f"  {icon}[{f.get('category','')}] {f.get('description','')} — {f.get('evidence','')}")
    return "\n".join(lines)


# ─────────────────────────────────────────────
# CLI（単体テスト用）
# ─────────────────────────────────────────────

if __name__ == "__main__":
    if not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        print("案件テキストを貼り付けてください（Ctrl-Dで送信）:")
        text = sys.stdin.read()
    result = assess(text)
    print("\n" + "═" * 60)
    print(f"  判定: {result['risk_level']}  (auto_block={result['auto_block']})")
    print("═" * 60)
    print(f"  {result['explanation']}")
    if result["findings"]:
        print("\n  【検出された兆候】")
        print(format_findings(result["findings"]))
    print()
    print(json.dumps(result, ensure_ascii=False, indent=2))
