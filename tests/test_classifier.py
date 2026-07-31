import unittest

from src.classifier import classify_rule_based


class ClassifierTests(unittest.TestCase):
    def test_high_intent(self):
        result = classify_rule_based("2027年什么时候出发？大概多少钱，可以一起去吗？")
        self.assertEqual(result.level, "A级")
        self.assertIn(result.label, {"报名预约", "价格预算", "时间安排"})
        self.assertGreaterEqual(result.score, 70)
        self.assertTrue(result.suggested_reply)

    def test_safety_intent(self):
        result = classify_rule_based("德雷克海峡晕船严重吗，需要什么保险？")
        self.assertEqual(result.label, "安全与风险")
        self.assertGreaterEqual(result.score, 40)

    def test_spam_is_excluded(self):
        result = classify_rule_based("兼职刷单加微信赚钱")
        self.assertEqual(result.level, "排除")
        self.assertEqual(result.score, 0)

    def test_unrelated_is_excluded(self):
        result = classify_rule_based("今天中午吃什么")
        self.assertEqual(result.label, "无关")
        self.assertEqual(result.level, "排除")

    def test_english_budget_intent(self):
        result = classify_rule_based("How much is the Antarctica expedition in 2027?")
        self.assertEqual(result.label, "价格预算")
        self.assertGreaterEqual(result.score, 40)
        self.assertIn("Pricing and budget", result.suggested_reply)

    def test_custom_project_is_not_antarctica_specific(self):
        profile = {
            "project_name": "AI 视频剪辑课程",
            "project_keywords": "视频剪辑,AI课程",
            "high_intent_keywords": "报名,多少钱",
            "project_intro": "课程大纲和开课时间会在官方页面更新。",
            "reply_signature": "请查看主页置顶内容。",
        }
        result = classify_rule_based("AI课程怎么报名，大概多少钱？", profile)
        self.assertEqual(result.level, "A级")
        self.assertIn("AI 视频剪辑课程", result.suggested_reply)


if __name__ == "__main__":
    unittest.main()
