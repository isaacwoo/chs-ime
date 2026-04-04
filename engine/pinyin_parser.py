# engine/pinyin_parser.py
# -*- coding: utf-8 -*-
"""
DP-based pinyin segmentation.

segment("wohenkaixin") -> ["wo", "hen", "kai", "xin"]

Algorithm: forward DP, at each position try all lengths 1-6.
Optional full_index scores for dictionary-aware disambiguation.
"""

from config import VALID_SYLLABLES

_MAX_SYLLABLE_LEN = 6   # longest Mandarin syllable: "zhuang"


def segment(pinyin_str: str, full_index: dict = None) -> list:
    """
    Segment a continuous lower-case pinyin string into valid syllables.

    Parameters
    ----------
    pinyin_str : continuous pinyin, e.g. "wohenkaixin"
    full_index : optional dict from DictLoader; improves disambiguation
                 when multiple valid segmentations exist

    Returns
    -------
    list of syllable strings; falls back to list(chars) if no valid parse.
    """
    s = pinyin_str.lower()
    n = len(s)

    if n == 0:
        return []

    NEG_INF = float("-inf")
    # dp[i] = (best_score, path)  covering s[0:i]
    dp = [(NEG_INF, [])] * (n + 1)
    dp[0] = (0.0, [])

    for i in range(n):
        score_i, path_i = dp[i]
        if score_i == NEG_INF:
            continue

        for length in range(1, min(_MAX_SYLLABLE_LEN + 1, n - i + 1)):
            syl = s[i : i + length]
            if syl not in VALID_SYLLABLES:
                continue

            # Base score: +length per match (prefer longer syllables = fewer splits)
            bonus = float(length)
            # Dict-aware bonus: prefer syllables that match known words/phrases
            if full_index is not None and syl in full_index:
                top_freq = full_index[syl][0][1] if full_index[syl] else 0
                bonus += min(top_freq / 100_000.0, 2.0)

            new_score = score_i + bonus
            j = i + length
            if new_score > dp[j][0]:
                dp[j] = (new_score, path_i + [syl])

    if dp[n][0] == NEG_INF:
        # No valid complete segmentation — return chars as fallback
        return list(s)

    return dp[n][1]
