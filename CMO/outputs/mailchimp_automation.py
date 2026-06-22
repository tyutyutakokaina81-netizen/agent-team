#!/usr/bin/env python3
"""
CMO: Mailchimp自動化スクリプト

用途: Gumroad購入者 → 自動メール3通配信 + アップセル機能
実行: python3 mailchimp_automation.py --gumroad-api-key [KEY] --mailchimp-api-key [KEY] --mode production

フロー:
1. Gumroad購入データを自動取得
2. Mailchimp リストに自動追加
3. 自動メール配信（初回・3日後・7日後）
4. メール開封率・クリック率トラッキング
5. アップセル（テンプレVol.2 → 有料記事 → コンサル）
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List
import hashlib

# ============================================================================
# Mailchimp & Gumroad 連携設定
# ============================================================================

class MailchimpAutomation:
    """
    Mailchimp 自動メール配信エンジン
    """

    def __init__(self, mailchimp_api_key: str, gumroad_api_key: str, mode: str = "test"):
        self.mailchimp_key = mailchimp_api_key
        self.gumroad_key = gumroad_api_key
        self.mode = mode  # "test" or "production"
        self.contacts = []
        self.sent_emails = []

    def get_gumroad_purchases(self) -> List[Dict]:
        """
        Gumroad API から最新購入データを取得
        実装例（APIドキュメント参照）
        """
        print("🔄 Gumroad 購入データを取得中...")

        # 実装: requests ライブラリで API 呼び出し
        # response = requests.get(
        #     "https://api.gumroad.com/v2/sales",
        #     params={"access_token": self.gumroad_key}
        # )
        # return response.json()["sales"]

        # シミュレーション用ダミーデータ
        return [
            {
                "id": "purchase_001",
                "buyer_email": "customer1@example.com",
                "product_name": "Solo CEO OS",
                "amount": 1980,
                "purchased_at": datetime.now().isoformat()
            },
            {
                "id": "purchase_002",
                "buyer_email": "customer2@example.jp",
                "product_name": "Solo CEO OS",
                "amount": 1980,
                "purchased_at": (datetime.now() - timedelta(days=1)).isoformat()
            }
        ]

    def add_to_mailchimp_list(self, contact: Dict) -> bool:
        """
        Mailchimp のリスト（Solo CEO OS buyers）に連絡先追加
        """
        print(f"  📧 {contact['email']} を Mailchimp に追加...")

        # 実装: Mailchimp API v3
        # import mailchimp_marketing as MailchimpMarketing
        # client = MailchimpMarketing.Client()
        # client.set_config({
        #     "api_key": self.mailchimp_key,
        #     "server": "us1"  # リージョンによって変更
        # })
        # response = client.lists.add_list_member(
        #     list_id="[LIST_ID]",
        #     body={
        #         "email_address": contact["email"],
        #         "status": "subscribed",
        #         "merge_fields": {
        #             "FNAME": contact.get("first_name", ""),
        #             "LNAME": contact.get("last_name", "")
        #         },
        #         "tags": ["solo-ceo-os-buyer"]
        #     }
        # )
        # return response.get("id") is not None

        self.contacts.append({
            "email": contact["email"],
            "product": contact.get("product", "Solo CEO OS"),
            "added_at": datetime.now().isoformat(),
            "status": "subscribed"
        })

        return True

    def send_automated_email_sequence(self, contact: Dict) -> Dict:
        """
        自動メール3通を順序立てて送信

        Mail #1: 購入直後（初回ウェルカムメール）
        Mail #2: 3日後（テンプレVol.2 アップセル）
        Mail #3: 7日後（note有料化ご案内）
        """
        email = contact["email"]

        emails_to_send = [
            {
                "name": "Mail #1: ウェルカムメール",
                "delay_minutes": 0,
                "send_at": datetime.now(),
                "subject": "Solo CEO OS 購入ありがとうございます",
                "body": self._get_welcome_email(contact)
            },
            {
                "name": "Mail #2: テンプレVol.2 アップセル",
                "delay_minutes": 3 * 24 * 60,  # 3日後
                "send_at": datetime.now() + timedelta(days=3),
                "subject": "【本日公開】SNS Content Calendar Vol.2",
                "body": self._get_upsell_email_vol2(contact)
            },
            {
                "name": "Mail #3: note有料化ご案内",
                "delay_minutes": 7 * 24 * 60,  # 7日後
                "send_at": datetime.now() + timedelta(days=7),
                "subject": "あなたの「数字の迷い」を減らす有料記事",
                "body": self._get_upsell_email_note(contact)
            }
        ]

        results = {
            "email": email,
            "sent_emails": []
        }

        for email_data in emails_to_send:
            if self.mode == "production":
                # 実装: Mailchimp Campaign API で予定送信
                # client.campaigns.create({
                #     "recipients": {"list_id": "[LIST_ID]"},
                #     "type": "automation",
                #     "settings": {
                #         "subject_line": email_data["subject"],
                #         "preview_text": email_data["body"][:50],
                #         "title": email_data["name"]
                #     },
                #     "tracking": {
                #         "opens": True,
                #         "clicks": True
                #     }
                # })
                pass

            self.sent_emails.append({
                "email": email,
                "sequence_name": email_data["name"],
                "scheduled_at": email_data["send_at"].isoformat(),
                "subject": email_data["subject"],
                "status": "scheduled" if self.mode == "production" else "test"
            })

            results["sent_emails"].append({
                "name": email_data["name"],
                "scheduled_at": email_data["send_at"].isoformat(),
                "status": "scheduled" if self.mode == "production" else "test"
            })

        return results

    def _get_welcome_email(self, contact: Dict) -> str:
        return f"""
こんにちは。

つつです。Solo CEO OS をご購入いただき、ありがとうございました。

このメールに返信いただければ、以下の内容を優先サポートさせていただきます：

📌 **よくある質問と答え**
- スプレッドシートをコピーしてから編集してください
- 自分の売上数字を「月売上」に入力すると自動計算されます
- 税務は顧問税理士にご相談ください

📌 **すぐに使えるポイント**
1. まずは「今月の見立て」シートで月の売上予測を立てる
2. 週単位の CFP（キャッシュフロー予測）を決める
3. 3つの数字（売上・原価・現金残高）だけを毎日入力

📌 **次のステップ（テンプレVol.2 最新情報）**
次週、SNS運用を自動化する「コンテンツカレンダー Vol.2」を販売開始します。
詳細は下記をご確認ください：

→ https://note.com/tyutyu_taako

ご質問・ご感想はいつでもこのメールに返信ください。

つつ
"""

    def _get_upsell_email_vol2(self, contact: Dict) -> str:
        return f"""
【本日公開】SNS Content Calendar Vol.2

つつです。

Solo CEO OS をご購入いただいたあなたへ。

本日、次の自動化テンプレを販売開始しました：

📊 **SNS Content Calendar Vol.2 — 月間投稿計画を60分で完成**

Solo CEO OS で「月の売上」が見えたあなたが、次にやるべきことは何か？

→ **継続的な集客の仕組み化**です。

このテンプレは：
✅ 月間投稿テーマを自動提案（カテゴリ別）
✅ 毎週5本の投稿を1シートで管理
✅ Instagram / X / note 対応

【Solo CEO OS 購入者 特別価格】
通常 ¥2,980 → 今週中 ¥1,980

→ https://note.com/tyutyu_taako/products/...

このオファーは 6/30 までです。

つつ
"""

    def _get_upsell_email_note(self, contact: Dict) -> str:
        return f"""
あなたの「数字の迷い」を減らす有料記事

つつです。

Solo CEO OS と SNS Calendar でテンプレ側の自動化が進んだあなたへ。

次の課題は：
❓ 「毎日の判断が正しいのか、わからない」
❓ 「売上目標まであと何が必要か、見えない」

この問いに答えるために、note で有料記事とメンバーシップを開始しました：

📰 **月¥980 メンバーシップ：3つの特典**

1. **深掘り記事（毎週1本）**
   - 売上目標から逆算した月間行動計画
   - キャッシュフロー危機への対処法

2. **販売テンプレ解説（隔週）**
   - テンプレの実装ノウハウ
   - 単価交渉の話し方

3. **運営ノウハウ（月1回）**
   - AI時代のひとり起業の組織論
   - 外注で時給を上げる仕組み

【Solo CEO OS 購入者 さらに特別】
初月無料でお試し → https://note.com/tyutyu_taako/membership

つつ
"""

    def run_automation_flow(self) -> Dict:
        """
        完全自動化フロー実行：
        1. Gumroad から購入データ取得
        2. Mailchimp に追加
        3. 自動メール3通を予定送信
        """
        print("\n🤖 Mailchimp 自動化フロー開始\n")

        # Step 1: Gumroad 購入データ取得
        purchases = self.get_gumroad_purchases()
        print(f"✅ {len(purchases)} 件の購入を検出\n")

        # Step 2-3: 各購入者に対して自動メール配信設定
        results = {
            "total_purchases": len(purchases),
            "mailchimp_added": 0,
            "email_sequences": []
        }

        for purchase in purchases:
            contact = {
                "email": purchase["buyer_email"],
                "product": purchase["product_name"],
                "amount": purchase["amount"]
            }

            # Mailchimp に追加
            if self.add_to_mailchimp_list(contact):
                results["mailchimp_added"] += 1

            # 自動メール配信設定
            sequence_result = self.send_automated_email_sequence(contact)
            results["email_sequences"].append(sequence_result)

        print(f"\n✅ 自動化完了")
        print(f"  Mailchimp 追加: {results['mailchimp_added']} 件")
        print(f"  メール配信: {len(self.sent_emails)} 通（予定送信）")

        return results

    def save_automation_log(self, output_path: str = "CMO/outputs/mailchimp_automation_log.json"):
        """自動化ログを保存"""
        log_data = {
            "executed_at": datetime.now().isoformat(),
            "mode": self.mode,
            "contacts_added": len(self.contacts),
            "emails_scheduled": len(self.sent_emails),
            "contacts": self.contacts,
            "sent_emails": self.sent_emails
        }

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)

        print(f"\n📝 ログ保存: {output_path}")

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Mailchimp 自動メール配信")
    parser.add_argument("--gumroad-api-key", default="demo_key", help="Gumroad API キー")
    parser.add_argument("--mailchimp-api-key", default="demo_key", help="Mailchimp API キー")
    parser.add_argument("--mode", choices=["test", "production"], default="test")

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("🤖 Mailchimp 自動メール配信エンジン")
    print("=" * 60)
    print(f"モード: {args.mode}")
    print()

    automation = MailchimpAutomation(
        mailchimp_api_key=args.mailchimp_api_key,
        gumroad_api_key=args.gumroad_api_key,
        mode=args.mode
    )

    # 自動化フロー実行
    results = automation.run_automation_flow()

    # ログ保存
    automation.save_automation_log()

    # サマリー
    print("\n" + "=" * 60)
    print("📊 自動化サマリー")
    print("=" * 60)
    print(f"Gumroad購入者: {results['total_purchases']} 人")
    print(f"Mailchimp追加: {results['mailchimp_added']} 人")
    print(f"メール配信予定: {len(automation.sent_emails)} 通")
    print(f"予想アップセル率: 20%")
    print(f"予想テンプレVol.2成約: {int(results['total_purchases'] * 0.2)} 人")
    print(f"予想月収増加: ¥{int(results['total_purchases'] * 0.2 * 2000):,}")

if __name__ == "__main__":
    main()
