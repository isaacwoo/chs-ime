# tools/build_dict.py
# -*- coding: utf-8 -*-
"""
Dev-time script: generate data/pinyin_dict.json from open-source pinyin data.

Sources:
  - pinyin-data/pinyin.txt       : unicode codepoint → toned pinyin (for chars)
  - phrase-pinyin-data/large_pinyin.txt : phrase → toned pinyin (for phrases)

Run once on dev machine (needs internet). Output is committed to the repo.
"""

import json
import os
import unicodedata
import urllib.request

# ── URLs ──────────────────────────────────────────────────────────────────────
CHAR_PINYIN_URL = (
    "https://raw.githubusercontent.com/mozillazg/"
    "pinyin-data/master/pinyin.txt"
)
PHRASE_PINYIN_URL = (
    "https://raw.githubusercontent.com/mozillazg/"
    "phrase-pinyin-data/master/large_pinyin.txt"
)

OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "pinyin_dict.json")


def fetch_text(url: str) -> str:
    print(f"Downloading: {url}")
    with urllib.request.urlopen(url, timeout=30) as resp:
        return resp.read().decode("utf-8")


def strip_tones(pinyin: str) -> str:
    """
    Convert toned pinyin to tone-free ASCII.
    'nǐ hǎo' → 'ni hao',  'nǚ' → 'nv'

    Replaces ü (and toned ü variants) with v before NFD decomposition,
    because NFD splits ü into u + combining diaeresis, making a
    post-decomposition replace impossible.
    """
    # Replace all ü-variants with v BEFORE decomposition:
    # U+00FC (plain ü) + U+01D6, U+01D8, U+01DA, U+01DC (toned ü)
    pinyin = pinyin.replace("ü", "v")  # U+00FC
    pinyin = pinyin.replace("ǖ", "v")  # U+01D6
    pinyin = pinyin.replace("ǘ", "v")  # U+01D8
    pinyin = pinyin.replace("ǚ", "v")  # U+01DA
    pinyin = pinyin.replace("ǜ", "v")  # U+01DC
    # NFD decompose → remove combining diacritics (remaining tone marks)
    nfd = unicodedata.normalize("NFD", pinyin)
    stripped = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    return stripped


def parse_char_pinyin(text: str) -> dict[str, str]:
    """
    Parse pinyin.txt → {char: first_pinyin_no_tone}

    File format:
        # U+4E00: 一
        U+4E00: yī
        U+4E01: dīng,dìng
    Lines starting with '#' are comments.
    Multiple pronunciations separated by comma — take first.
    """
    result: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            codepoint_part, pinyin_part = line.split(":", 1)
            codepoint = int(codepoint_part.strip()[2:], 16)  # 'U+4E00' → 0x4E00
            char = chr(codepoint)
            first_pinyin = pinyin_part.strip().split(",")[0].split("#")[0].strip()
            result[char] = strip_tones(first_pinyin)
        except (ValueError, IndexError):
            continue
    return result


def parse_phrase_pinyin(text: str) -> list[tuple[str, str, int]]:
    """
    Parse large_pinyin.txt → list of (phrase, joined_pinyin_no_tone, line_rank)

    File format:
        一: yī
        你好: nǐ hǎo
        中华人民共和国: zhōng huá rén mín gòng hé guó

    Returns triples sorted by line number (ascending = more common first).
    Frequency is derived as: max(1, 100_000 - line_rank * 3)
    """
    entries: list[tuple[str, str, int]] = []
    entry_rank = 0
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        phrase_part, pinyin_part = line.split(":", 1)
        phrase = phrase_part.strip()
        raw_pinyin = pinyin_part.split("#")[0].strip()
        if not phrase or not raw_pinyin:
            continue
        # Join syllables: 'nǐ hǎo' → 'nihao'
        syllables = [strip_tones(s) for s in raw_pinyin.split()]
        joined = "".join(syllables)
        if joined:
            entries.append((phrase, joined, entry_rank))
            entry_rank += 1
    return entries


def build_dict(
    char_map: dict[str, str],
    phrase_entries: list[tuple[str, str, int]],
) -> dict[str, list[dict]]:
    """
    Combine char and phrase data into the output JSON format:
    {
      "ni":    [{"word": "你", "freq": 99000}, ...],
      "nihao": [{"word": "你好", "freq": 85000}],
      ...
    }
    """
    output: dict[str, list[tuple[str, int]]] = {}

    # ── Characters ────────────────────────────────────────────────────────────
    # Base frequency 20000; boosted by up to 79000 based on phrase-head count.
    char_freq_boost: dict[str, int] = {}  # char → count of phrases it leads
    for phrase, pinyin, rank in phrase_entries:
        if phrase:
            char_freq_boost[phrase[0]] = char_freq_boost.get(phrase[0], 0) + 1

    for char, pinyin in char_map.items():
        if not pinyin:
            continue
        boost = char_freq_boost.get(char, 0)
        freq = min(99000, 20000 + boost * 200)
        if pinyin not in output:
            output[pinyin] = []
        output[pinyin].append((char, freq))

    # ── Phrases (2+ chars) ────────────────────────────────────────────────────
    for phrase, pinyin, rank in phrase_entries:
        if len(phrase) < 2:
            continue  # single chars already handled above
        freq = max(1, 100_000 - rank)
        if pinyin not in output:
            output[pinyin] = []
        output[pinyin].append((phrase, freq))

    # ── Sort each entry list by freq desc, deduplicate words ─────────────────
    final: dict[str, list[dict]] = {}
    for pinyin, entries in output.items():
        seen_words: set[str] = set()
        deduped: list[tuple[str, int]] = []
        for word, freq in sorted(entries, key=lambda x: -x[1]):
            if word not in seen_words:
                seen_words.add(word)
                deduped.append((word, freq))
        final[pinyin] = [{"word": w, "freq": f} for w, f in deduped]

    return final


def main() -> None:
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)

    char_text = fetch_text(CHAR_PINYIN_URL)
    phrase_text = fetch_text(PHRASE_PINYIN_URL)

    print("Parsing character pinyin...")
    char_map = parse_char_pinyin(char_text)
    print(f"  {len(char_map)} characters parsed")

    print("Parsing phrase pinyin...")
    phrase_entries = parse_phrase_pinyin(phrase_text)
    print(f"  {len(phrase_entries)} phrases parsed")

    print("Building dictionary...")
    dictionary = build_dict(char_map, phrase_entries)
    total_entries = sum(len(v) for v in dictionary.values())
    print(f"  {len(dictionary)} pinyin keys, {total_entries} total entries")

    print(f"Writing to {OUT_PATH} ...")
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(dictionary, f, ensure_ascii=False, separators=(",", ":"))

    size_mb = os.path.getsize(OUT_PATH) / 1024 / 1024
    print(f"Done. File size: {size_mb:.1f} MB")


if __name__ == "__main__":
    main()
