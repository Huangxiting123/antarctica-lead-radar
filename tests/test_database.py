import tempfile
import unittest
from pathlib import Path

from src.classifier import classify_rule_based
from src.database import Database


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temp.name) / "test.db")

    def tearDown(self):
        self.temp.cleanup()

    def test_insert_deduplicate_and_classify(self):
        item = {
            "platform": "抖音",
            "user_name": "测试用户",
            "user_id": "open_1",
            "content": "南极同行怎么报名？",
            "comment_time": "2026-07-31 12:00:00",
            "platform_comment_id": "c1",
        }
        row_id, created = self.db.upsert_comment(item)
        self.assertTrue(created)
        second_id, created_again = self.db.upsert_comment(item)
        self.assertEqual(row_id, second_id)
        self.assertFalse(created_again)
        self.db.apply_classification(row_id, classify_rule_based(item["content"]))
        row = self.db.get(row_id)
        self.assertEqual(row["intent_label"], "报名预约")
        self.assertEqual(self.db.dashboard_counts()["total"], 1)

    def test_filters(self):
        row_id, _ = self.db.upsert_comment({"platform": "YouTube", "content": "南极预算多少钱", "platform_comment_id": "x"})
        self.db.apply_classification(row_id, classify_rule_based("南极预算多少钱"))
        rows = self.db.list_comments(platform="YouTube", query="预算")
        self.assertEqual(len(rows), 1)


if __name__ == "__main__":
    unittest.main()
