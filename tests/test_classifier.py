import unittest

from src.classifier import classify_rule_based


class ClassifierTests(unittest.TestCase):
    def test_high_intent(self):
        result = classify_rule_based("2027年什么时候出发？大概多少钱，可以一起去吗？")
        self.assertEqual(result.level, "A级")
        self.assertIn(result.label, {"同行意向", "预算价格", "时间船期"})
        self.assertGreaterEqual(result.score, 70)
        self.assertTrue(result.suggested_reply)

    def test_safety_intent(self):
        result = classify_rule_based("德雷克海峡晕船严重吗，需要什么保险？")
        self.assertEqual(result.label, "安全准备")
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
        self.assertEqual(result.label, "预算价格")
        self.assertGreaterEqual(result.score, 40)
        self.assertTrue(result.suggested_reply.startswith("The main costs"))


if __name__ == "__main__":
    unittest.main()
