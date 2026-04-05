# Pinyin IME Diagnostic Report
Date: 2026-04-05

## Summary
Three critical usability issues were identified in the Pinyin IME, all traceable to a single root cause: **insufficient beam width in the DP sentence search algorithm**.

---

## Issue 1: Character 个 Cannot Be Found for Input "ge"

### User Report
User cannot select character 个 when typing "ge".

### Diagnostic Findings
- Dictionary contains 个 with frequency **32200** (7th highest for "ge")
- Top 6 entries for "ge" are: 格(64800), 革(52000), 歌(46800), 隔(43800), 割(40200), 各(38000)
- 个 is **NOT returned in get_candidates() results**
- Character IS present in `loader.full_index['ge']`

### Root Cause
**Beam Width = 5** in `matcher.py` line 20:
```python
_BEAM_WIDTH = 5      # candidates kept per DP position in beam search
```

During `_sentence_candidates()` (lines 100-132), the DP algorithm only keeps the top 5 entries per syllable at each position. Since 个 is ranked 7th, it gets **pruned before ranking**.

**Location:** `engine/matcher.py:116`
```python
for word, freq in entries[:_BEAM_WIDTH]:  # Only top 5!
```

### Impact
- User cannot access the most common classifier particle (个) by frequency ranking
- This is particularly problematic for phrases like "这个" (a very common construction)
- Affects all characters ranked 6+ for any syllable

---

## Issue 2: Common Phrases Like "这个", "问题" Cannot Be Typed

### User Report
Common multi-character phrases don't appear as top candidates.

### Diagnostic Findings

#### Test 1: "zhege" (这个)
- Segmentation works correctly: `['zhe', 'ge']`
- Phrase exists in dictionary with 7 entries (all freq=1)
- Top 5 candidates: `['折格', '折革', '折歌', '遮格', '折隔']` ← All WRONG

#### Test 2: "wenti" (问题)
- Segmentation works correctly: `['wen', 'ti']`
- Phrase exists in dictionary
- Top 5 candidates show single-character decompositions, not the actual phrase

### Root Cause - Two Interrelated Problems

#### Problem 2A: Beam Pruning
Individual syllables are pruned to top 5 (see Issue #1), making it impossible to reconstruct phrases from their syllables.

#### Problem 2B: Dictionary Frequency
Multi-character phrases have very low frequency:
```
"zhege" entries: all have freq=1
"zhe" entries: top entry has freq=68,800
"ge" entries: top entry has freq=64,800
```

The DP algorithm combines high-frequency single characters from each segment rather than considering the phrase as a whole, because:
1. Score for combining [top_zhe] + [top_ge] ≈ 68800 + 64800 = 133600
2. Score for phrase "这个" = 1
3. DP chooses combining route (lines 119 in matcher.py: `span_bonus = (span_len - 1) * 80000`)

**Location:** `engine/matcher.py:100-132` (`_sentence_candidates()`)

### Impact
- Cannot easily type common two-character phrases even when they exist in the dictionary
- Two separate issues compound: low phrase frequency + beam pruning

---

## Issue 3: User Frequency Boost Doesn't Feel Responsive

### User Report
Selecting a character multiple times doesn't sufficiently boost its ranking.

### Diagnostic Findings
- User frequency mechanism exists in `_user_boost()` (line 94-98)
- Each selection adds 2000 points
- **Before any selections:** 个 rank = NOT IN TOP 50
- **After 10 selections:** 个 rank = STILL NOT IN TOP 50
- Boost is recorded in `user_freq.json` correctly

### Root Cause
**User frequency boost only applies to candidates that survive beam pruning.**

The boost is applied in `_sentence_candidates()` at line 117:
```python
boost = self._user_boost(joined, word)
```

However, this code is only reached if the word was:
1. In the original phrase entries (line 115)
2. Within the top 5 by frequency (line 116: `entries[:_BEAM_WIDTH]`)

Since 个 is pruned at step 2, the boost code is never executed.

**Location:** `engine/matcher.py:116-117`

### Impact
- User frequency history is ignored for low-frequency characters
- First-time users cannot quickly train the system to their preferences
- Makes IME feel unresponsive to user behavior

---

## Summary of Root Causes

| Issue | Root Cause | Location |
|-------|-----------|----------|
| 1. 个 not found | `_BEAM_WIDTH = 5` prunes rank 7+ chars | `matcher.py:20,116` |
| 2. Phrases fail | Combination scores > phrase scores + beam pruning | `matcher.py:100-132` |
| 3. Boost ineffective | Pruned candidates never reach boost code | `matcher.py:116-117` |

All three issues trace to **insufficient beam width in the DP algorithm**.

---

## Technical Details

### The DP Algorithm Flow
1. Input: `"ge"`
2. Segmentation: `['ge']` (single syllable)
3. Dictionary lookup: `loader.full_index['ge']` returns 171 entries
4. Beam pruning: **Only top 5 kept** → 个(32200) is pruned
5. Ranking: Top 5 candidates returned
6. User boost: Never applied to 个 (not in top 5)

### Why Beam Width = 5 Is Problematic
- Mandarin has 22 consonant-initial combinations + vowels
- Many syllables have 100+ valid characters
- Fixed beam of 5 is too aggressive
- Common characters get pruned for mid-frequency syllables

### Interaction with Phrase Dictionary
- If phrases were weighted higher, could bypass issue
- But current dictionary has phrases at freq=1-100
- Single characters have freq=20000-99000
- DP naturally chooses character combinations over phrase entries

---

## Files Examined
1. `engine/matcher.py` - DP beam search implementation
2. `engine/dict_loader.py` - Dictionary loading
3. `engine/pinyin_parser.py` - Segmentation algorithm
4. `config.py` - Configuration constants
5. `data/pinyin_dict.json` - Dictionary source (16 MB, 171 entries for "ge")

## Diagnostic Script Results
See `diagnostic.py` for reproducible test cases showing all three issues.
