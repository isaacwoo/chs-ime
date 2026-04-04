import unittest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import config

class TestConfig(unittest.TestCase):
    def test_valid_syllables_is_set(self):
        self.assertIsInstance(config.VALID_SYLLABLES, frozenset)

    def test_common_syllables_present(self):
        for syl in ['ni', 'hao', 'wo', 'men', 'zhong', 'guo', 'zhuang']:
            self.assertIn(syl, config.VALID_SYLLABLES, f"Missing syllable: {syl}")

    def test_invalid_syllables_absent(self):
        for syl in ['bj', 'xyz', 'zzz', 'aaa']:
            self.assertNotIn(syl, config.VALID_SYLLABLES, f"Invalid syllable present: {syl}")

    def test_fuzzy_map_is_dict(self):
        self.assertIsInstance(config.FUZZY_MAP, dict)
        self.assertIn('zh', config.FUZZY_MAP)
        self.assertIn('an', config.FUZZY_MAP)

    def test_punct_map_has_required_keys(self):
        for key in [',', '.', ';']:
            self.assertIn(key, config.PUNCT_MAP)
        self.assertEqual(config.PUNCT_MAP[','], '，')
        self.assertEqual(config.PUNCT_MAP['.'], '。')

    def test_font_candidates_is_list(self):
        self.assertIsInstance(config.FONT_CANDIDATES, list)
        self.assertGreater(len(config.FONT_CANDIDATES), 0)

    def test_cache_version_is_int(self):
        self.assertIsInstance(config.CACHE_VERSION, int)

if __name__ == '__main__':
    unittest.main()
