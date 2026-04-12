"""
test_evaluate.py — 02_evaluate.py のルールベース評価のテスト

実行:
  cd projects/2026-04-08_月30万自動化/D_エクセル入力スクレイピング/pipeline
  python -m pytest test_evaluate.py -v
  # or
  python -m unittest test_evaluate -v
"""

import unittest
import sys
from pathlib import Path

# パイプラインディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from importlib import import_module
evaluate_mod = import_module("02_evaluate")
_rule_based_evaluate = evaluate_mod._rule_based_evaluate
evaluate = evaluate_mod.evaluate
run = evaluate_mod.run


class TestRuleBasedEvaluate(unittest.TestCase):
    """_rule_based_evaluate() のテスト"""

    # ─────────────────────────────────────
    # 技術実現性（technical）
    # ─────────────────────────────────────

    def test_excel_keyword_scores_high_technical(self):
        result = _rule_based_evaluate("エクセルにデータ入力する仕事です")
        self.assertEqual(result["scores"]["technical"], 25)

    def test_csv_keyword_scores_high_technical(self):
        result = _rule_based_evaluate("CSVファイルの整理をお願いします")
        self.assertEqual(result["scores"]["technical"], 25)

    def test_scraping_keyword_scores_medium_technical(self):
        result = _rule_based_evaluate("Webサイトからデータをスクレイピングする作業")
        self.assertEqual(result["scores"]["technical"], 20)

    def test_captcha_reduces_technical_score(self):
        result = _rule_based_evaluate("エクセル入力ですがcaptcha認証があるサイトです")
        self.assertLessEqual(result["scores"]["technical"], 15)

    # ─────────────────────────────────────
    # 法的リスク（legal）
    # ─────────────────────────────────────

    def test_public_info_scores_high_legal(self):
        result = _rule_based_evaluate("公開情報をまとめる作業です")
        self.assertEqual(result["scores"]["legal"], 25)

    def test_personal_info_scores_low_legal(self):
        result = _rule_based_evaluate("個人情報を収集してリスト化する作業です")
        self.assertEqual(result["scores"]["legal"], 5)

    def test_fraud_keyword_scores_zero_legal(self):
        result = _rule_based_evaluate("詐欺に関する調査データの入力")
        self.assertEqual(result["scores"]["legal"], 0)

    # ─────────────────────────────────────
    # 採算性（profitability）
    # ─────────────────────────────────────

    def test_high_price_scores_high_profitability(self):
        result = _rule_based_evaluate("データ入力", meta={"budget_text": "¥15,000"})
        self.assertEqual(result["scores"]["profitability"], 25)

    def test_medium_price_scores_medium_profitability(self):
        result = _rule_based_evaluate("データ入力", meta={"budget_text": "¥7,000"})
        self.assertEqual(result["scores"]["profitability"], 20)

    def test_low_price_scores_low_profitability(self):
        result = _rule_based_evaluate("データ入力", meta={"budget_text": "¥1,500"})
        self.assertEqual(result["scores"]["profitability"], 5)

    def test_price_extraction_with_comma(self):
        result = _rule_based_evaluate("予算は10,000円です")
        self.assertEqual(result["scores"]["profitability"], 25)

    def test_price_extraction_with_yen_mark(self):
        result = _rule_based_evaluate("報酬：¥5,000")
        self.assertEqual(result["scores"]["profitability"], 20)

    # ─────────────────────────────────────
    # 要件明確性（clarity）
    # ─────────────────────────────────────

    def test_clear_requirements_scores_high_clarity(self):
        result = _rule_based_evaluate(
            "100件のデータをexcel形式で入力してください。納期は3日以内です"
        )
        self.assertGreaterEqual(result["scores"]["clarity"], 20)

    def test_vague_requirements_scores_low_clarity(self):
        result = _rule_based_evaluate("なんかいい感じにデータまとめてほしい")
        self.assertLessEqual(result["scores"]["clarity"], 15)

    # ─────────────────────────────────────
    # verdict 判定境界値
    # ─────────────────────────────────────

    def test_verdict_go_at_70(self):
        """total >= 70 → GO"""
        result = _rule_based_evaluate(
            "公開情報のエクセルデータ入力。100件。納期5日以内。excel形式。",
            meta={"budget_text": "¥15,000"}
        )
        if result["total"] >= 70:
            self.assertEqual(result["verdict"], "GO")

    def test_verdict_nogo_below_50(self):
        """total < 50 → NO-GO"""
        result = _rule_based_evaluate("よく分からない作業")
        if result["total"] < 50:
            self.assertEqual(result["verdict"], "NO-GO")

    def test_verdict_caution_between_50_and_69(self):
        """50 <= total < 70 → CAUTION"""
        result = _rule_based_evaluate(
            "データ収集の作業です",
            meta={"budget_text": "¥3,000"}
        )
        if 50 <= result["total"] < 70:
            self.assertEqual(result["verdict"], "CAUTION")

    # ─────────────────────────────────────
    # 詐欺フラグ
    # ─────────────────────────────────────

    def test_fraud_flag_transfer(self):
        """受け取り・転送系は total=0"""
        result = _rule_based_evaluate("海外在住の方の荷物を受け取り転送する仕事です")
        self.assertEqual(result["total"], 0)
        self.assertTrue(len(result["red_flags"]) > 0)

    def test_fraud_flag_line_registration(self):
        """LINE登録系は total=0"""
        result = _rule_based_evaluate("まずLINE登録してから作業を開始してください")
        self.assertEqual(result["total"], 0)

    def test_suspicious_side_job(self):
        """副業・簡単に稼げる系は大幅減点"""
        result = _rule_based_evaluate("副業 初心者歓迎 誰でも簡単に稼げるデータ入力")
        self.assertLessEqual(result["total"], 30)

    # ─────────────────────────────────────
    # カテゴリ分類
    # ─────────────────────────────────────

    def test_category_excel_input(self):
        result = _rule_based_evaluate("エクセルにデータを入力する作業です")
        self.assertEqual(result["category"], "excel_input")

    def test_category_scraping(self):
        result = _rule_based_evaluate("Webサイトからデータを取得する作業です")
        self.assertEqual(result["category"], "scraping")

    # ─────────────────────────────────────
    # 出力構造
    # ─────────────────────────────────────

    def test_output_has_required_fields(self):
        result = _rule_based_evaluate("テスト用テキスト")
        required_keys = [
            "category", "scores", "total", "verdict",
            "estimated_price_jpy", "estimated_work_hours",
            "hourly_rate_jpy", "red_flags", "green_flags",
            "questions_to_ask", "reason", "evaluated_at",
            "job_text_preview"
        ]
        for key in required_keys:
            self.assertIn(key, result, f"Missing key: {key}")

    def test_scores_has_four_axes(self):
        result = _rule_based_evaluate("テスト用テキスト")
        self.assertIn("technical", result["scores"])
        self.assertIn("legal", result["scores"])
        self.assertIn("profitability", result["scores"])
        self.assertIn("clarity", result["scores"])

    def test_total_equals_sum_of_scores(self):
        result = _rule_based_evaluate("公開情報のエクセル入力。100件。¥10,000")
        scores = result["scores"]
        expected = scores["technical"] + scores["legal"] + scores["profitability"] + scores["clarity"]
        # 詐欺フラグで total が上書きされる場合があるので、フラグなしケースで確認
        if not result["red_flags"]:
            self.assertEqual(result["total"], expected)

    def test_job_text_preview_truncated(self):
        long_text = "あ" * 200
        result = _rule_based_evaluate(long_text)
        self.assertTrue(result["job_text_preview"].endswith("..."))
        self.assertLessEqual(len(result["job_text_preview"]), 103 + 3)

    # ─────────────────────────────────────
    # meta 情報の引き継ぎ
    # ─────────────────────────────────────

    def test_meta_merged_into_result(self):
        meta = {"title": "テスト案件", "url": "https://example.com", "platform": "crowdworks"}
        result = _rule_based_evaluate("エクセル入力", meta=meta)
        self.assertEqual(result["title"], "テスト案件")
        self.assertEqual(result["url"], "https://example.com")
        self.assertEqual(result["platform"], "crowdworks")

    def test_client_reviews_zero_flag(self):
        meta = {"platform": "crowdworks", "client_reviews": "0"}
        result = _rule_based_evaluate("エクセル入力", meta=meta)
        self.assertTrue(any("レビュー0件" in f for f in result["red_flags"]))

    # ─────────────────────────────────────
    # run() 関数（バグ修正後）
    # ─────────────────────────────────────

    def test_run_with_job_list(self):
        jobs = [
            {"title": "エクセル入力", "description": "100件のデータ入力 ¥10,000"},
            {"title": "怪しい仕事", "description": "LINE登録して受け取り転送"},
        ]
        results = run(jobs)
        # 詐欺案件はフィルタされるはず（GO/CAUTION のみ返す）
        for r in results:
            self.assertIn(r["verdict"], ("GO", "CAUTION"))

    def test_run_filters_nogo(self):
        jobs = [
            {"title": "詐欺案件", "description": "海外在住 受け取り 転送 LINE登録"},
        ]
        results = run(jobs)
        self.assertEqual(len(results), 0)

    # ─────────────────────────────────────
    # evaluate() フォールバック
    # ─────────────────────────────────────

    def test_evaluate_without_api_key_uses_rule_based(self):
        """ANTHROPIC_API_KEY が空なら rule_based にフォールバック"""
        import os
        original = os.environ.get("ANTHROPIC_API_KEY", "")
        os.environ["ANTHROPIC_API_KEY"] = ""
        try:
            # モジュールレベルの ANTHROPIC_API_KEY を再設定
            evaluate_mod.ANTHROPIC_API_KEY = ""
            result = evaluate("エクセルにデータ入力する仕事です")
            self.assertIn("evaluated_by", result)
            self.assertEqual(result["evaluated_by"], "rule_based")
        finally:
            os.environ["ANTHROPIC_API_KEY"] = original
            evaluate_mod.ANTHROPIC_API_KEY = original


if __name__ == "__main__":
    unittest.main()
