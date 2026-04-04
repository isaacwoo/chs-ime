# engine/pinyin_parser.py  — STUB, full implementation in Task 5
def segment(pinyin_str: str, full_index=None) -> list:
    """Minimal stub: split by known pinyin boundaries. Task 5 replaces this."""
    from config import VALID_SYLLABLES
    s = pinyin_str.lower()
    result = []
    i = 0
    while i < len(s):
        matched = False
        for length in range(min(6, len(s) - i), 0, -1):
            syl = s[i:i+length]
            if syl in VALID_SYLLABLES:
                result.append(syl)
                i += length
                matched = True
                break
        if not matched:
            result.append(s[i])
            i += 1
    return result
