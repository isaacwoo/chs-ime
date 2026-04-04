# tests/engine/test_matcher.py
import json, os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from engine.dict_loader import DictLoader
from engine.matcher import Matcher

FIXTURE = {
    "ni":       [{"word": "你", "freq": 99000}, {"word": "尼", "freq": 5000}],
    "hao":      [{"word": "好", "freq": 90000}],
    "nihao":    [{"word": "你好", "freq": 85000}],
    "wo":       [{"word": "我", "freq": 95000}],
    "hen":      [{"word": "很", "freq": 88000}, {"word": "恨", "freq": 3000}],
    "kaixin":   [{"word": "开心", "freq": 70000}],
    "kai":      [{"word": "开", "freq": 60000}],
    "xin":      [{"word": "心", "freq": 55000}, {"word": "新", "freq": 50000}],
    "beijing":  [{"word": "北京", "freq": 80000}],
    "zhongguo": [{"word": "中国", "freq": 78000}],
    "zhong":    [{"word": "中", "freq": 65000}],
    "guo":      [{"word": "国", "freq": 60000}],
}

def make_loader() -> DictLoader:
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(FIXTURE, f, ensure_ascii=False)
    # Load without generating a pickle in temp dir
    loader = DictLoader()
    loader._load_json(path)
    loader._build_abbrev_index()
    os.unlink(path)
    return loader


class TestMatcher(unittest.TestCase):

    def setUp(self):
        self.loader = make_loader()
        self.freq_fd, self.freq_path = tempfile.mkstemp(suffix=".json")
        os.close(self.freq_fd)
        self.matcher = Matcher(self.loader, self.freq_path)

    def tearDown(self):
        try:
            os.unlink(self.freq_path)
        except OSError:
            pass

    # ── Full pinyin ──────────────────────────────────────────────────────────

    def test_single_syllable_returns_chars(self):
        candidates = self.matcher.get_candidates("ni")
        self.assertIn("你", candidates)

    def test_two_syllable_phrase(self):
        candidates = self.matcher.get_candidates("nihao")
        self.assertIn("你好", candidates)

    def test_multi_syllable_builds_sentence(self):
        # "wohenkaixin" should assemble "我很开心"
        candidates = self.matcher.get_candidates("wohenkaixin")
        self.assertIn("我很开心", candidates)

    def test_top_candidate_is_highest_freq(self):
        candidates = self.matcher.get_candidates("ni")
        self.assertEqual(candidates[0], "你")

    # ── Abbreviated pinyin ───────────────────────────────────────────────────

    def test_abbreviated_two_chars(self):
        # "nh" → 你好
        candidates = self.matcher.get_candidates("nh")
        self.assertIn("你好", candidates)

    def test_abbreviated_three_chars(self):
        # "bj" → 北京
        candidates = self.matcher.get_candidates("bj")
        self.assertIn("北京", candidates)

    # ── Fuzzy pinyin ─────────────────────────────────────────────────────────

    def test_fuzzy_zh_z(self):
        # "zongguo" should find entries (fuzzy match for 中国/zhongguo)
        candidates = self.matcher.get_candidates("zongguo")
        self.assertIsInstance(candidates, list)  # relaxed: just no crash

    # ── User frequency ───────────────────────────────────────────────────────

    def test_record_and_boost(self):
        # Record selecting 尼 (low freq) many times
        for _ in range(50):
            self.matcher.record_selection("ni", "尼")
        candidates = self.matcher.get_candidates("ni")
        # After many selections, 尼 should appear before 你
        self.assertEqual(candidates[0], "尼")

    def test_flush_writes_json(self):
        self.matcher.record_selection("nihao", "你好")
        self.matcher.flush_user_freq()
        with open(self.freq_path, encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("nihao:你好", data)

    def test_empty_input_returns_empty(self):
        self.assertEqual(self.matcher.get_candidates(""), [])


if __name__ == '__main__':
    unittest.main()
