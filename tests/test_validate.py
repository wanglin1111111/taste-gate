"""tests/test_validate.py — validate.py 校验器正反向自测（零依赖，unittest）。

运行：
  python -m unittest discover -s tests -v
  python tests/test_validate.py
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import validate  # noqa: E402

GOOD = ROOT / "tests" / "sample_good.json"
BAD = ROOT / "tests" / "sample_bad.json"


class TestValidateSamples(unittest.TestCase):
    def test_good_sample_no_fail(self):
        plan = json.loads(GOOD.read_text(encoding="utf-8"))
        checks = validate.validate(plan)
        fails = [c for c in checks if c[0] == "FAIL"]
        self.assertEqual(fails, [], f"good 样例不应有 FAIL: {fails}")

    def test_bad_sample_expected_fails(self):
        plan = json.loads(BAD.read_text(encoding="utf-8"))
        checks = validate.validate(plan)
        fails = [c for c in checks if c[0] == "FAIL"]
        codes = {c[1] for c in fails}
        self.assertGreaterEqual(len(fails), 3, "bad 样例应触发多项 FAIL")
        self.assertGreaterEqual(len(codes), 3, "bad 样例应覆盖多个维度码")

    def test_cli_exit_codes(self):
        good = subprocess.run([sys.executable, str(ROOT / "scripts" / "validate.py"), str(GOOD)],
                              capture_output=True, text=True)
        bad = subprocess.run([sys.executable, str(ROOT / "scripts" / "validate.py"), str(BAD)],
                             capture_output=True, text=True)
        self.assertEqual(good.returncode, 0, good.stdout + good.stderr)
        self.assertEqual(bad.returncode, 1, bad.stdout + bad.stderr)

    def test_cli_usage_error(self):
        result = subprocess.run([sys.executable, str(ROOT / "scripts" / "validate.py")],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()