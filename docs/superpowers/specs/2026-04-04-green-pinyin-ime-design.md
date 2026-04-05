# Green Offline Pinyin IME - Design Spec

## Context

User works onsite in Japan on Windows 10/11 machines with Japanese system locale (CP932/Shift-JIS). These machines have no admin rights, no internet access, and no way to install software including Chinese input methods. Python 3.13 is available. The goal is a portable, zero-install Simplified Chinese pinyin input tool built entirely with Python's standard library (tkinter).

Primary use case: typing medium-to-long Chinese text for AI chat conversations.

---

## 1. Architecture Overview

### File Structure

```
chs-ime/
├── start.bat              # Quick launcher (chcp 65001 + python main.py)
├── main.py                # Entry point
├── config.py              # Constants: punctuation map, fuzzy pinyin map, font list, valid syllables
├── engine/
│   ├── __init__.py
│   ├── pinyin_parser.py   # Pinyin segmentation (DP-based)
│   ├── matcher.py         # Candidate matching + ranking (full/abbrev/fuzzy)
│   └── dict_loader.py     # Dictionary loading (JSON + pickle cache)
├── ui/
│   ├── __init__.py
│   ├── main_window.py     # Main window (topmost, layout, key bindings)
│   └── candidate_panel.py # Candidate display + pagination
└── data/
    ├── pinyin_dict.json   # Pinyin dictionary (~5-8MB, open-source derived)
    └── user_freq.json     # User frequency data (auto-generated at runtime)
```

### Tech Stack

- **Language**: Python 3.13 (standard library only)
- **GUI**: tkinter
- **Data**: JSON for dictionary and user frequency
- **Clipboard**: tkinter's built-in clipboard API (`clipboard_append`)

---

## 2. Pinyin Engine

### 2.1 Valid Syllables Table

Hardcoded set of ~410 standard pinyin syllables in `config.py` as `VALID_SYLLABLES`. Includes all legal Mandarin syllables without tones (e.g., `a, ai, an, ang, ao, ba, bai, ban, bang, ...zuo`).

### 2.2 Segmentation Algorithm

**Dynamic Programming approach** for globally optimal segmentation of continuous pinyin input.

Given input string of length N:
- Build a DP table where `dp[i]` = best segmentation score for the first `i` characters
- At each position, try all possible syllable lengths (1-6 characters, since the longest pinyin syllable is 6 letters like `zhuang`)
- Score each segmentation path by dictionary match quality (prefer paths that match existing words/phrases)
- Complexity: O(N × 6), fast enough for real-time input

**Example:**
```
Input: "wohenkaixin"
DP segmentation: wo | hen | kai | xin
Score boosted because "开心" exists as a phrase in dictionary
```

**Ambiguity resolution:**
```
Input: "xian"
Candidates: "xian" (先/现/线) vs "xi|an" (西安)
→ Both kept as candidate paths, ranked by dictionary frequency
→ "xian" as whole syllable preferred (more common), "西安" also shown in candidates
```

### 2.3 Fuzzy Pinyin

Defined in `config.py` as `FUZZY_MAP`:

```python
FUZZY_MAP = {
    # Initials
    'zh': 'z', 'z': 'zh',
    'ch': 'c', 'c': 'ch',
    'sh': 's', 's': 'sh',
    'l': 'n', 'n': 'l',
    'r': 'l', 'f': 'h', 'h': 'f',
    # Finals
    'an': 'ang', 'ang': 'an',
    'en': 'eng', 'eng': 'en',
    'in': 'ing', 'ing': 'in',
}
```

When querying, the engine also queries all fuzzy variants of each syllable. Results are merged with exact matches ranked higher than fuzzy matches.

### 2.4 Abbreviated Pinyin (简拼)

Two modes:
- **Pure initials**: `bj` → matches all phrases where first char starts with `b` and second char starts with `j` → "北京", "背景"
- **Mixed initials + full pinyin**: `bji` → matches `b` + `ji` → narrower results

Implementation: a pre-built `abbrev_index` mapping initial-letter combinations to candidate phrases, constructed at dictionary load time.

---

## 3. Dictionary System

### 3.1 Dictionary Format

`data/pinyin_dict.json`:
```json
{
  "ni": [
    {"word": "你", "freq": 99000},
    {"word": "尼", "freq": 12000}
  ],
  "nihao": [
    {"word": "你好", "freq": 85000}
  ]
}
```

- Key: full pinyin (no tones), value: array of {word, freq} sorted by freq descending
- Contains both single characters (~6700) and phrases (tens of thousands)
- Source: open-source pinyin data (pypinyin project, CC-CEDICT, wiki frequency lists)
- Estimated size: 5-8MB JSON

### 3.2 Loading Strategy

1. On first launch: load `pinyin_dict.json` (UTF-8), generate `pinyin_dict.pkl` cache
2. On subsequent launches: load pickle cache (3-5x faster)
3. If pickle version mismatch or corruption: delete and regenerate from JSON
4. Show a "Loading..." splash window during load

### 3.3 In-Memory Index Structures

| Index | Purpose | Key Example | Value Example |
|---|---|---|---|
| `full_index` | Full pinyin lookup | `"nihao"` | `[("你好", 85000)]` |
| `abbrev_index` | Abbreviated pinyin | `"nh"` | `[("你好", 85000), ("南海", 42000)]` |
| `char_index` | Single character lookup | `"ni"` | `[("你", 99000), ("尼", 12000)]` |

### 3.4 User Frequency

`data/user_freq.json`:
```json
{
  "nihao:你好": 37,
  "beijing:北京": 12
}
```

- Key format: `pinyin:word` to avoid collisions
- Ranking score: `static_freq × 0.4 + user_freq_normalized × 0.6`
- Write strategy: flush to disk every 30 seconds or on application exit (not on every selection)
- On corruption: silently discard and start fresh

---

## 4. UI Design

### 4.1 Window Layout

```
┌──────────────────────────────────────────────┐
│  简体中文输入助手                    ─  □  ×  │
├──────────────────────────────────────────────┤
│  ┌──────────────────────────────────────┐    │
│  │ Edit Area (tkinter.Text)             │    │
│  │ Accumulated Chinese text shown here  │    │
│  └──────────────────────────────────────┘    │
│  [复制全部]  [清空]  [撤销]                    │
├──────────────────────────────────────────────┤
│  Pinyin: wohenkaixin                         │
│  Split:  wo | hen | kai | xin                │
│  ┌──────────────────────────────────────┐    │
│  │ 1.我很开心  2.我很开新  3.我恨开心    │    │
│  │ 4.窝很开心  5.我很凯信               │    │
│  └──────────────────────────────────────┘    │
│  ◀ Prev  [1/3]  Next ▶                      │
└──────────────────────────────────────────────┘
```

### 4.2 Components

| Component | Widget | Role |
|---|---|---|
| Edit Area | `tkinter.Text` | Displays accumulated text, supports cursor editing, select, delete |
| Action Buttons | `tkinter.Button` | Copy All → clipboard, Clear, Undo last selection |
| Pinyin Input | `tkinter.Entry` | User types pinyin here, triggers real-time matching |
| Split Display | `tkinter.Label` | Shows engine's segmentation result for user confirmation |
| Candidate Panel | `tkinter.Frame` with dynamic labels | Shows up to 5 candidates per page |
| Pagination | `tkinter.Button` + `tkinter.Label` | Prev/Next page + page indicator |

### 4.3 Keyboard Shortcuts

| Key | Action |
|---|---|
| `a-z` | Input pinyin letters |
| `1-5` | Select candidate by number, append to edit area |
| `Space` | Select first candidate (highest ranked) |
| `Enter` | Commit entire candidate phrase to edit area |
| `Backspace` | Delete last pinyin char; if pinyin empty, delete last char in edit area |
| `Escape` | Clear current pinyin input |
| `-` / `=` | Previous / Next candidate page |
| `Ctrl+C` | Copy all edit area text to clipboard |
| `Ctrl+A` | Select all in edit area |
| `Ctrl+Z` | Undo last word selection |
| `Ctrl+Backspace` | Clear entire edit area |

### 4.4 Chinese Punctuation Mapping

When pinyin input box is empty, these keys produce Chinese punctuation directly into the edit area:

| Key | Output |
|---|---|
| `,` | ， |
| `.` | 。 |
| `!` (Shift+1) | ！ |
| `?` (Shift+/) | ？ |
| `:` (Shift+;) | ： |
| `;` | ； |
| `'` | ' ' (smart quotes, alternating open/close) |
| `"` (Shift+') | " " (smart quotes, alternating open/close) |
| `(` | （ |
| `)` | ） |
| `<` | 《 |
| `>` | 》 |

This mapping table is configurable in `config.py` so the user can adjust for JIS keyboard layout differences if needed.

When pinyin input box has content, these keys are ignored (normal pinyin typing continues).

### 4.5 Window Properties

- **Always on top**: `root.attributes('-topmost', True)`
- **Default size**: 500×400, resizable
- **Position**: Bottom-right corner of screen on startup
- **Font fallback chain**: `Microsoft YaHei` → `SimSun` → `MS Gothic` → `Arial Unicode MS` → tkinter default
- Font detection at startup: iterate candidates, use first available

---

## 5. Encoding & Japanese Locale Handling

### 5.1 All-UTF-8 Strategy

| Location | Measure |
|---|---|
| Every `open()` call | Explicit `encoding='utf-8'` |
| `main.py` top | `os.environ['PYTHONIOENCODING'] = 'utf-8'` |
| `json.dump()` for user_freq | `ensure_ascii=False` to keep Chinese readable |
| `start.bat` | `chcp 65001` to switch console codepage |
| `start.bat` file itself | Save as UTF-8 with BOM |
| tkinter Text/Label | Unicode-safe internally, no extra handling needed |
| Clipboard | `root.clipboard_append()` is Unicode-safe |

### 5.2 start.bat

```bat
@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"
python main.py
pause
```

---

## 6. Error Handling

| Scenario | Handling |
|---|---|
| Dictionary file missing | `tkinter.messagebox.showerror()`, exit |
| Dictionary JSON corrupted | Catch exception, show error detail in messagebox, exit |
| `user_freq.json` corrupted | Silently discard, create fresh empty file |
| Pickle cache version mismatch | Delete cache, reload from JSON |
| All fonts unavailable | Fall back to tkinter default font |
| Clipboard operation fails | Catch exception, show warning in status area |

---

## 7. Deployment

- **All files (including dictionary) committed to GitHub repository** (`D:\code\chs-ime`)
- Total estimated size: code ~50KB + dictionary ~5-8MB = well under GitHub's 100MB single-file limit
- User downloads repository contents to target machine and runs `python main.py` or double-clicks `start.bat`
- No installation, no admin rights, no internet required at runtime
- `user_freq.json` and `pinyin_dict.pkl` are auto-generated at runtime (both should be in `.gitignore`)

---

## 8. Dictionary Generation (Development Phase)

A separate build script (not shipped to target machine) will:
1. Download/parse open-source pinyin data sources
2. Merge and deduplicate
3. Assign frequency scores from word frequency corpora
4. Output `data/pinyin_dict.json` in the specified format
5. This script runs on the development machine (has internet access)
