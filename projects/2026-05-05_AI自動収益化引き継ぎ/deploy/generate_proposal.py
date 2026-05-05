"""高単価案件用の提案書生成（L3・¥50K〜の継続契約案件向け）。

CrowdWorks/Lancers の通常応募文より長い、PDF/Notion提出を想定した
本格提案書フォーマット。スコープ・体制・スケジュール・見積を含む。

例:
    python3 generate_proposal.py "SNS運用代行" --client "株式会社サンプル" --budget 50000
    python3 generate_proposal.py "AI業務自動化PoC" --client "個人事業主A様" --budget 150000 --weeks 8
"""
from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

OUT = Path.home() / "ai-auto" / "outputs"


def build(project: str, client: str, monthly_budget: int, weeks: int) -> str:
    today = date.today()
    end = today + timedelta(weeks=weeks)
    return f"""# ご提案書

**案件名**：{project}
**提出先**：{client}
**提出日**：{today.isoformat()}

---

## 1. ご提案概要
{project} について、貴社の運営負荷を最小化しつつ成果が継続的に積み上がる形で、
{weeks}週間（{today.isoformat()}〜{end.isoformat()}）のご支援を提案いたします。

## 2. 解決する課題（仮説）
- 現状の運用が属人化しており、担当者の稼働がボトルネックになっている
- 数字に基づく改善サイクルが回っていない
- AI / 自動化を試したいが、社内に推進できる人材がいない

※ 初回ヒアリング（30分）で課題を確定させ、本提案を調整いたします。

## 3. ご支援スコープ

### Phase 1（Week 1-2）：現状把握と設計
- 現行業務のヒアリング（30〜60分 × 2回）
- 目標KPIの合意
- 運用フロー設計図の作成

### Phase 2（Week 3-{weeks - 2 if weeks > 4 else weeks - 1}）：実装と試運転
- 必要なテンプレ・スクリプト・ガイドの作成
- 試験運用と週次レビュー
- 改善サイクルの確立

### Phase 3（Week {weeks - 1 if weeks > 4 else weeks}-{weeks}）：定着化と引き渡し
- 運用マニュアルの作成
- 引き継ぎミーティング（60分）
- 30日間のサポート期間

## 4. 体制
- ご担当：個人事業主（私）が直接対応
- ご連絡手段：Slack / Chatwork / メール（ご希望に合わせる）
- レスポンス：2営業時間以内

## 5. スケジュール

| Phase | 期間 | マイルストーン |
|------|------|--------------|
| Phase 1 | Week 1-2 | 設計図 / KPI合意 |
| Phase 2 | Week 3-{weeks - 2 if weeks > 4 else weeks - 1} | テンプレ・運用試験 |
| Phase 3 | Week {weeks - 1 if weeks > 4 else weeks}-{weeks} | マニュアル / 引き渡し |

## 6. お見積

| 項目 | 金額 |
|------|------|
| 初期設計（Phase 1） | ¥{monthly_budget // 2:,} |
| 実装・運用支援（Phase 2） | ¥{monthly_budget:,} |
| 定着化（Phase 3） | ¥{monthly_budget // 2:,} |
| **合計** | **¥{monthly_budget * 2:,}** |

※ 月額継続契約をご希望の場合：**月額 ¥{monthly_budget:,}**（最低3ヶ月）でも対応可能です。

## 7. お支払条件
- 着手金 50%：契約締結後3営業日以内
- 残金 50%：Phase 3 完了時
- お振込（手数料貴社負担）または CrowdWorks/Lancers エスクロー

## 8. 私の実績・適性
- ライティング累計100本以上（note・ブログ・SEO記事）
- AI / 自動化スクリプト10件以上の実装実績
- 個人事業主・小規模事業者の運用設計経験
- ご相談から納品までを一気通貫で対応可能

## 9. 次のステップ
1. **本提案書のご確認**
2. **初回ヒアリング（30分・無料）の日程調整**
3. ご合意後、契約書ドラフトの送付

---

ご検討のほど、どうぞよろしくお願いいたします。

ご質問や調整希望は遠慮なくお申し付けください。
本提案書は無料でブラッシュアップいたします。
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="高単価案件用の提案書生成")
    parser.add_argument("project", help="案件名 / プロジェクト名")
    parser.add_argument("--client", default="ご担当者様", help="提出先")
    parser.add_argument("--budget", type=int, default=50000, help="月額相当の見積（円）")
    parser.add_argument("--weeks", type=int, default=8, help="支援期間（週）")
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    today = date.today().strftime("%Y-%m-%d")
    safe = args.project.replace("/", "_").replace(" ", "_")[:40]
    path = OUT / f"{today}_proposal_{safe}.md"
    path.write_text(build(args.project, args.client, args.budget, args.weeks), encoding="utf-8")
    print(f"生成完了: {path}")
    print(f"次：claude.ai に prompts/polish_prompts.md の『提案書ブラッシュアップ』を貼って整形")


if __name__ == "__main__":
    main()
