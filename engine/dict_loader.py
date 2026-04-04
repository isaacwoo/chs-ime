# engine/dict_loader.py
# -*- coding: utf-8 -*-
"""
Loads pinyin_dict.json and builds three in-memory indexes.
Uses a pickle cache for faster subsequent starts.
"""

import json
import os
import pickle
from config import CACHE_VERSION


class DictLoader:
    """
    Attributes
    ----------
    full_index   : {pinyin_str: [(word, freq), ...]}  sorted by freq desc
    abbrev_index : {initial_letters: [(word, freq), ...]}  for 2+ char phrases
    char_index   : {pinyin_str: [(single_char, freq), ...]}  single chars only
    """

    def __init__(self) -> None:
        self.full_index:   dict = {}
        self.abbrev_index: dict = {}
        self.char_index:   dict = {}

    # ── Public factory ────────────────────────────────────────────────────────

    @classmethod
    def load(cls, dict_path: str) -> "DictLoader":
        """
        Load dictionary from JSON (or pickle cache).
        dict_path : absolute path to pinyin_dict.json
        """
        cache_path = dict_path.replace(".json", ".pkl")
        loader = cls._load_from_cache(cache_path)
        if loader is not None:
            return loader

        loader = cls()
        loader._load_json(dict_path)
        loader._build_abbrev_index()
        loader._save_cache(cache_path)
        return loader

    # ── Private helpers ───────────────────────────────────────────────────────

    def _load_json(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as f:
            raw: dict = json.load(f)

        for pinyin, entries in raw.items():
            pairs = [
                (e["word"], e["freq"]) for e in entries
            ]
            # Already sorted by build_dict.py, but sort here for safety
            pairs.sort(key=lambda x: -x[1])
            self.full_index[pinyin] = pairs

            # Populate char_index for single-character entries
            for word, freq in pairs:
                if len(word) == 1:
                    if pinyin not in self.char_index:
                        self.char_index[pinyin] = []
                    self.char_index[pinyin].append((word, freq))

    def _build_abbrev_index(self) -> None:
        """
        Build abbreviated pinyin index from phrases in full_index.
        Key = first letter of each syllable concatenated.

        Strategy: we need the per-syllable pinyin of each phrase.
        We derive it from the phrase's key in full_index IF the key
        naturally splits into per-char syllables — which it does because
        build_dict.py joined syllables in order.

        However, splitting a joined pinyin back into per-syllable pieces
        requires the segmenter — which depends on this loader. To break
        the circular dependency we use a lightweight re-split here:
        For multi-char phrases, find entries where word length == number
        of syllables (each char ↔ one syllable). We approximate this by
        only indexing phrases whose joined pinyin key corresponds to a
        known phrase AND whose length equals len(word).
        """
        try:
            from engine.pinyin_parser import segment
        except ImportError:
            return  # pinyin_parser not yet available; abbrev_index will be empty

        for pinyin_key, entries in self.full_index.items():
            for word, freq in entries:
                if len(word) < 2:
                    continue  # skip single chars
                # Re-segment the joined pinyin to get per-syllable list
                syllables = segment(pinyin_key)
                if len(syllables) != len(word):
                    continue  # segmentation didn't match word length — skip
                initials = "".join(s[0] for s in syllables)
                if initials not in self.abbrev_index:
                    self.abbrev_index[initials] = []
                self.abbrev_index[initials].append((word, freq))

        # Sort each abbrev list by freq desc
        for key in self.abbrev_index:
            self.abbrev_index[key].sort(key=lambda x: -x[1])

    @classmethod
    def _load_from_cache(cls, cache_path: str) -> "DictLoader | None":
        if not os.path.exists(cache_path):
            return None
        try:
            with open(cache_path, "rb") as f:
                version, loader = pickle.load(f)
            if version != CACHE_VERSION:
                os.unlink(cache_path)
                return None
            return loader
        except Exception:
            try:
                os.unlink(cache_path)
            except OSError:
                pass
            return None

    def _save_cache(self, cache_path: str) -> None:
        try:
            with open(cache_path, "wb") as f:
                pickle.dump((CACHE_VERSION, self), f, protocol=pickle.HIGHEST_PROTOCOL)
        except Exception:
            pass  # cache write failure is non-fatal
