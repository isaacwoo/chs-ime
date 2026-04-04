# tests/engine/test_dict_loader.py
import json, os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from engine.dict_loader import DictLoader

# Minimal fixture dictionary
FIXTURE = {
    "ni":      [{"word": "你", "freq": 99000}, {"word": "尼", "freq": 5000}],
    "hao":     [{"word": "好", "freq": 90000}, {"word": "号", "freq": 8000}],
    "nihao":   [{"word": "你好", "freq": 85000}],
    "beijing": [{"word": "北京", "freq": 70000}],
    "zhongguo":[{"word": "中国", "freq": 65000}],
    "wo":      [{"word": "我", "freq": 95000}],
    "men":     [{"word": "们", "freq": 80000}],
    "women":   [{"word": "我们", "freq": 75000}],
}

def make_tmp_dict() -> str:
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        json.dump(FIXTURE, f, ensure_ascii=False)
    return path


class TestDictLoader(unittest.TestCase):
    def setUp(self):
        self.path = make_tmp_dict()
        self.loader = DictLoader.load(self.path)

    def tearDown(self):
        os.unlink(self.path)

    def test_full_index_lookup(self):
        results = self.loader.full_index.get("nihao", [])
        words = [w for w, _ in results]
        self.assertIn("你好", words)

    def test_full_index_sorted_by_freq(self):
        results = self.loader.full_index.get("ni", [])
        self.assertEqual(results[0][0], "你")   # highest freq first

    def test_char_index_single_chars_only(self):
        # "women" is a 2-char phrase — should NOT be in char_index
        results = self.loader.char_index.get("women", [])
        self.assertEqual(results, [])
        # Single char "ni" → 你 should be in char_index
        results = self.loader.char_index.get("ni", [])
        self.assertTrue(any(w == "你" for w, _ in results))

    def test_abbrev_index_two_char_phrase(self):
        # "nihao" → initials "nh" → 你好
        results = self.loader.abbrev_index.get("nh", [])
        words = [w for w, _ in results]
        self.assertIn("你好", words)

    def test_abbrev_index_three_char_phrase(self):
        # "beijing" → initials "bj" → 北京
        results = self.loader.abbrev_index.get("bj", [])
        words = [w for w, _ in results]
        self.assertIn("北京", words)

    def test_load_uses_utf8(self):
        # Verify Chinese characters survived the load (not garbled)
        results = self.loader.full_index.get("ni", [])
        self.assertTrue(any(w == "你" for w, _ in results))


if __name__ == '__main__':
    unittest.main()
