# engine/matcher.py
# -*- coding: utf-8 -*-
"""
Candidate generation and ranking.

Priority order per query:
  1. Abbreviated pinyin (if input looks like initials — no vowels)
  2. Full pinyin sentence reconstruction (DP beam search over syllables)
  3. Fuzzy pinyin variants of first syllable
User frequency boosts re-rank results within each strategy.
"""

import json
import os
from config import VALID_SYLLABLES, FUZZY_MAP
from engine.dict_loader import DictLoader
from engine.pinyin_parser import segment

_VOWELS = frozenset("aeiouv")
_BEAM_WIDTH = 25     # candidates explored per syllable in DP (was 5 — too narrow, pruned 个 at rank 7)
_MAX_CANDIDATES = 50


class Matcher:

    def __init__(self, loader: DictLoader, user_freq_path: str) -> None:
        self.loader = loader
        self.user_freq_path = user_freq_path
        self.user_freq: dict[str, int] = self._load_user_freq()
        self._dirty = False   # True when user_freq has unsaved changes

    # ── Public API ────────────────────────────────────────────────────────────

    def get_candidates(self, pinyin_str: str) -> list:
        """Return ranked candidate strings for the given pinyin input."""
        s = pinyin_str.lower().strip()
        if not s:
            return []

        # Strategy 1: abbreviation (all consonants — no vowels)
        if not any(c in _VOWELS for c in s):
            abbrev = self._query_abbrev(s)
            if abbrev:
                return self._finalize(abbrev, limit=300)

        # Strategy 2: full segmentation + sentence DP beam search
        syllables = segment(s, self.loader.full_index)
        results = []
        if syllables and all(syl in VALID_SYLLABLES for syl in syllables):
            results = self._sentence_candidates(syllables)
        else:
            valid_syls = self._valid_prefix_syllables(s)
            if valid_syls:
                results = self._sentence_candidates(valid_syls)

        # Strategy 3: add fuzzy variants if we still have room
        if len(results) < _MAX_CANDIDATES:
            fuzzy = self._fuzzy_candidates(syllables)
            seen = {w for w, _ in results}
            results += [(w, sc) for w, sc in fuzzy if w not in seen]

        return self._finalize(results)

    def record_selection(self, pinyin: str, word: str) -> None:
        """Increment user frequency for pinyin:word pair."""
        key = f"{pinyin.lower()}:{word}"
        self.user_freq[key] = self.user_freq.get(key, 0) + 1
        self._dirty = True

    def flush_user_freq(self) -> None:
        """Persist user_freq to disk. Call periodically and on exit."""
        if not self._dirty:
            return
        try:
            os.makedirs(os.path.dirname(self.user_freq_path) or ".", exist_ok=True)
            with open(self.user_freq_path, "w", encoding="utf-8") as f:
                json.dump(self.user_freq, f, ensure_ascii=False, indent=2)
            self._dirty = False
        except Exception:
            pass  # non-fatal

    # ── Private helpers ───────────────────────────────────────────────────────

    def _load_user_freq(self) -> dict:
        if not os.path.exists(self.user_freq_path):
            return {}
        try:
            with open(self.user_freq_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {k: int(v) for k, v in data.items()}
        except Exception:
            return {}  # corruption → start fresh

    def _user_boost(self, pinyin: str, word: str) -> float:
        """Return additive score boost from user history. Each selection adds 2000."""
        key = f"{pinyin}:{word}"
        count = self.user_freq.get(key, 0)
        return count * 2000.0  # 50 selections = 100k boost, overrides 99k static freq

    def _sentence_candidates(self, syllables: list) -> list:
        """
        DP beam search over syllables to build full-sentence candidates.
        Returns list of (sentence_string, score) sorted by score desc.
        """
        n = len(syllables)
        # dp[i] = list of (score, assembled_text) for the first i syllables
        dp = [[] for _ in range(n + 1)]
        dp[0] = [(0.0, "")]

        for i in range(n):
            for score, text in dp[i]:
                # Try all phrase lengths from position i to end
                for j in range(i + 1, n + 1):
                    joined = "".join(syllables[i:j])
                    entries = self.loader.full_index.get(joined, [])
                    for word, freq in entries[:_BEAM_WIDTH]:
                        boost = self._user_boost(joined, word)
                        span_len = j - i  # number of syllables this phrase covers
                        # Span bonus makes ANY dict phrase beat char-by-char decomposition.
                        # Worst-case char combo for N syllables = N * 99000.
                        # A phrase (even freq=1) gets: 1 + (span_len-1)*200000.
                        # At span_len=2: 200001 > 2*99000=198000. Phrase wins. ✓
                        span_bonus = (span_len - 1) * 200000
                        dp[j].append((score + freq + boost + span_bonus, text + word))

            # Prune beam: keep top _MAX_CANDIDATES states per position to avoid explosion
            dp[i + 1].sort(key=lambda x: -x[0])
            dp[i + 1] = dp[i + 1][:_MAX_CANDIDATES]

        seen = set()
        result = []
        for score, text in sorted(dp[n], key=lambda x: -x[0]):
            if text and text not in seen:
                seen.add(text)
                result.append((text, score))
        return result[:_MAX_CANDIDATES]

    def _query_abbrev(self, initials: str) -> list:
        """Look up abbreviated pinyin in abbrev_index."""
        entries = self.loader.abbrev_index.get(initials, [])
        return [(w, f + self._user_boost(initials, w)) for w, f in entries]

    def _fuzzy_candidates(self, syllables: list) -> list:
        """
        Apply FUZZY_MAP to the first syllable and collect alternative candidates.
        Only processes the first syllable to keep combinatorics manageable.
        """
        if not syllables:
            return []
        first = syllables[0]
        if first not in FUZZY_MAP:
            return []
        alt = FUZZY_MAP[first]
        fuzzy_syls = [alt] + syllables[1:]
        result = []
        # Try the full fuzzy phrase
        joined = "".join(fuzzy_syls)
        for word, freq in self.loader.full_index.get(joined, [])[:_BEAM_WIDTH]:
            result.append((word, freq * 0.6))
        # Also try just the first fuzzy syllable
        for word, freq in self.loader.full_index.get(alt, [])[:_BEAM_WIDTH]:
            result.append((word, freq * 0.6))
        return result

    def _valid_prefix_syllables(self, s: str) -> list:
        """
        Return the longest valid prefix segmentation of s.
        Used when the full string has no complete valid parse.
        """
        syls = []
        pos = 0
        while pos < len(s):
            matched = False
            for length in range(min(6, len(s) - pos), 0, -1):
                syl = s[pos: pos + length]
                if syl in VALID_SYLLABLES:
                    syls.append(syl)
                    pos += length
                    matched = True
                    break
            if not matched:
                break
        return syls

    def _finalize(self, results: list, limit: int = _MAX_CANDIDATES) -> list:
        """Sort by score desc, deduplicate, return word strings only."""
        results.sort(key=lambda x: -x[1])
        seen = set()
        out = []
        for word, _ in results:
            if word not in seen:
                seen.add(word)
                out.append(word)
        return out[:limit]
