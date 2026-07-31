import csv
import tempfile
import unittest
import zipfile
from pathlib import Path

from src.io_tools import export_csv, export_xlsx, import_csv


class IoToolsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_import_chinese_headers(self):
        path = self.root / "in.csv"
        path.write_text("平台,用户名称,评论内容,评论时间\n抖音,小明,想去南极多少钱,2026-07-31\n", encoding="utf-8-sig")
        rows = import_csv(path)
        self.assertEqual(rows[0]["platform"], "抖音")
        self.assertEqual(rows[0]["content"], "想去南极多少钱")

    def test_export_csv_prevents_formula_execution(self):
        path = self.root / "out.csv"
        export_csv(path, [{"platform": "抖音", "user_name": "=HYPERLINK(1)", "content": "测试"}])
        content = path.read_text(encoding="utf-8-sig")
        self.assertIn("'=HYPERLINK(1)", content)

    def test_export_xlsx_is_valid_zip(self):
        path = self.root / "out.xlsx"
        export_xlsx(path, [{"platform": "抖音", "user_name": "小明", "content": "南极同行"}])
        self.assertTrue(zipfile.is_zipfile(path))
        with zipfile.ZipFile(path) as archive:
            self.assertIn("xl/worksheets/sheet1.xml", archive.namelist())
            self.assertIn("南极同行", archive.read("xl/worksheets/sheet1.xml").decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
