# tests/engine/test_pinyin_parser.py
import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from engine.pinyin_parser import segment

class TestSegment(unittest.TestCase):

    def test_simple_two_syllables(self):
        self.assertEqual(segment("nihao"), ["ni", "hao"])

    def test_three_syllables(self):
        self.assertEqual(segment("women"), ["wo", "men"])

    def test_four_syllables(self):
        result = segment("wohenkaixin")
        self.assertEqual(result, ["wo", "hen", "kai", "xin"])

    def test_single_syllable(self):
        self.assertEqual(segment("wo"), ["wo"])

    def test_empty_string(self):
        self.assertEqual(segment(""), [])

    def test_compound_initials(self):
        # zh, ch, sh are single initials
        result = segment("zhongguo")
        self.assertEqual(result, ["zhong", "guo"])

    def test_xian_ambiguity_resolved(self):
        # "xian" should be parsed — either as one syllable ["xian"] or ["xi","an"]
        # both are valid; just ensure it doesn't crash and returns a list
        result = segment("xian")
        self.assertIn(result, [["xian"], ["xi", "an"]])

    def test_long_phrase(self):
        result = segment("zhonghuarenmingongheguo")
        self.assertEqual(result, ["zhong", "hua", "ren", "min", "gong", "he", "guo"])

    def test_fallback_on_garbage(self):
        # Non-pinyin input shouldn't crash; returns some list
        result = segment("xyz123")
        self.assertIsInstance(result, list)

    def test_uppercase_normalized(self):
        # Input should be lowercased internally
        self.assertEqual(segment("NIHAO"), ["ni", "hao"])

if __name__ == '__main__':
    unittest.main()
