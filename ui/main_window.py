# ui/main_window.py
# -*- coding: utf-8 -*-
"""
Main application window.

Layout (top → bottom):
  ┌─────────────────────────────────────┐
  │  Edit area (Text widget)             │
  │  [复制全部]  [清空]  [撤销]           │
  ├─────────────────────────────────────┤
  │  拼音: ___________________           │
  │  切分: wo | hen | kai | xin         │
  │  CandidatePanel                      │
  └─────────────────────────────────────┘

Key bindings on pinyin Entry:
  a-z       → normal typing (handled by Entry widget)
  1-5       → select candidate by number
  Space     → select candidate 1 (highest ranked)
  Enter     → select candidate 1 (highest ranked)
  Backspace → delete last pinyin char; if empty, delete last edit char
  Escape    → clear pinyin
  - / =     → prev/next candidate page
  Ctrl+C    → copy all edit area text to clipboard
  Ctrl+Z    → undo last word selection
  Ctrl+Backspace → clear edit area
  punctuation (when pinyin empty) → insert Chinese punct
"""

import tkinter as tk
from tkinter import messagebox
from typing import Callable, Optional

from config import PUNCT_MAP
from engine.matcher import Matcher
from engine.pinyin_parser import segment
from ui.candidate_panel import CandidatePanel

_FLUSH_INTERVAL_MS = 30_000   # flush user_freq every 30 seconds


class MainWindow:

    def __init__(self, root: tk.Tk, matcher: Matcher, font_name: str) -> None:
        self.root = root
        self.matcher = matcher
        self.font_name = font_name

        self._edit_font   = (font_name, 13)
        self._label_font  = (font_name, 11)
        self._button_font = (font_name, 10)

        # State
        self._undo_stack: list[tuple[str, int]] = []  # (word, edit_len_before)
        self._quote_single_open = True   # alternates with each ' press
        self._quote_double_open = True   # alternates with each " press

        self._build_ui()
        self._bind_keys()
        self._schedule_flush()

    # ── Public API ────────────────────────────────────────────────────────────

    def insert_to_edit(self, word: str) -> None:
        """Append word to edit area and update undo stack."""
        before_len = len(self.edit_area.get("1.0", tk.END)) - 1  # exclude trailing \n
        self._undo_stack.append((word, before_len))
        self.edit_area.config(state=tk.NORMAL)
        self.edit_area.insert(tk.END, word)
        self.edit_area.see(tk.END)

    def clear_pinyin(self) -> None:
        self.pinyin_var.set("")
        self.split_label.config(text="")
        self.candidate_panel.update_candidates([])

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.root.title("简体中文输入助手")
        self.root.geometry("520x420")
        self.root.attributes("-topmost", True)
        self.root.resizable(True, True)

        # Position: bottom-right of screen
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"520x420+{sw - 540}+{sh - 460}")

        # ── Edit area ────────────────────────────────────────────────────────
        edit_frame = tk.LabelFrame(self.root, text="已输入文本", font=self._button_font)
        edit_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(8, 2))

        self.edit_area = tk.Text(
            edit_frame,
            font=self._edit_font,
            wrap=tk.WORD,
            height=5,
            relief=tk.FLAT,
            bg="#fafafa",
        )
        self.edit_area.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # ── Action buttons ───────────────────────────────────────────────────
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(fill=tk.X, padx=8, pady=2)

        for text, cmd in [
            ("复制全部", self._copy_all),
            ("清空",   self._clear_edit),
            ("撤销",   self._undo),
        ]:
            tk.Button(
                btn_frame, text=text, font=self._button_font,
                command=cmd, relief=tk.GROOVE, padx=8,
            ).pack(side=tk.LEFT, padx=3)

        # Status label (right side)
        self._status_var = tk.StringVar(value="就绪")
        tk.Label(btn_frame, textvariable=self._status_var,
                 font=("TkDefaultFont", 9), fg="gray").pack(side=tk.RIGHT, padx=6)

        # ── Separator ────────────────────────────────────────────────────────
        tk.Frame(self.root, height=1, bg="#cccccc").pack(fill=tk.X, padx=8, pady=4)

        # ── Pinyin input row ─────────────────────────────────────────────────
        input_frame = tk.Frame(self.root)
        input_frame.pack(fill=tk.X, padx=8)

        tk.Label(input_frame, text="拼音:", font=self._label_font).pack(side=tk.LEFT)

        self.pinyin_var = tk.StringVar()
        self.pinyin_entry = tk.Entry(
            input_frame,
            textvariable=self.pinyin_var,
            font=self._label_font,
            relief=tk.GROOVE,
            bg="#eef6ff",
        )
        self.pinyin_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))
        self.pinyin_entry.focus_set()

        # ── Split display ─────────────────────────────────────────────────────
        self.split_label = tk.Label(
            self.root, text="", font=("TkDefaultFont", 9), fg="#666666", anchor="w"
        )
        self.split_label.pack(fill=tk.X, padx=8, pady=(2, 0))

        # ── Candidate panel ───────────────────────────────────────────────────
        self.candidate_panel = CandidatePanel(
            self.root,
            on_select=self._on_candidate_selected,
            font=self._label_font,
            bg=self.root.cget("bg"),
        )
        self.candidate_panel.pack(fill=tk.X, padx=8, pady=4)

        # Register trace on pinyin_var for real-time candidate update
        self.pinyin_var.trace_add("write", self._on_pinyin_changed)

        # Close handler
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── Key bindings ──────────────────────────────────────────────────────────

    def _bind_keys(self) -> None:
        e = self.pinyin_entry
        e.bind("<KeyPress>", self._on_key_press)

    def _on_key_press(self, event: tk.Event) -> Optional[str]:
        keysym = event.keysym
        char   = event.char
        ctrl   = (event.state & 0x4) != 0

        # ── Ctrl combos ───────────────────────────────────────────────────────
        if ctrl:
            if keysym.lower() == "c":
                self._copy_all(); return "break"
            if keysym.lower() == "z":
                self._undo(); return "break"
            if keysym == "BackSpace":
                self._clear_edit(); return "break"
            if keysym.lower() == "a":
                self.edit_area.tag_add(tk.SEL, "1.0", tk.END)
                return "break"
            return None  # let other Ctrl combos pass

        # ── Navigation ────────────────────────────────────────────────────────
        if keysym == "Escape":
            self.clear_pinyin(); return "break"
        if keysym == "minus":
            self.candidate_panel.prev_page(); return "break"
        if keysym == "equal":
            self.candidate_panel.next_page(); return "break"

        # ── Candidate selection ───────────────────────────────────────────────
        if keysym in ("1", "2", "3", "4", "5"):
            self.candidate_panel.select_by_number(int(keysym))
            self.clear_pinyin()
            return "break"
        if keysym in ("space", "Return"):
            self.candidate_panel.select_by_number(1)
            self.clear_pinyin()
            return "break"

        # ── Backspace ─────────────────────────────────────────────────────────
        if keysym == "BackSpace":
            if self.pinyin_var.get() == "":
                self._delete_last_from_edit()
                return "break"
            return None  # let Entry delete its own char

        # ── Punctuation (only when pinyin box is empty) ───────────────────────
        if self.pinyin_var.get() == "" and char in PUNCT_MAP:
            punct = PUNCT_MAP[char]
            # Smart quotes: toggle open/close
            if char == "'":
                punct = "\u2018" if self._quote_single_open else "\u2019"
                self._quote_single_open = not self._quote_single_open
            elif char == '"':
                punct = "\u201c" if self._quote_double_open else "\u201d"
                self._quote_double_open = not self._quote_double_open
            self.insert_to_edit(punct)
            return "break"

        return None  # default: let Entry handle it

    # ── Callbacks ─────────────────────────────────────────────────────────────

    def _on_pinyin_changed(self, *_) -> None:
        pinyin = self.pinyin_var.get()
        if not pinyin:
            self.split_label.config(text="")
            self.candidate_panel.update_candidates([])
            return

        # Update split display
        syls = segment(pinyin, self.matcher.loader.full_index)
        self.split_label.config(text=" | ".join(syls))

        # Get and display candidates
        candidates = self.matcher.get_candidates(pinyin)
        self.candidate_panel.update_candidates(candidates)

    def _on_candidate_selected(self, word: str) -> None:
        pinyin = self.pinyin_var.get()
        self.matcher.record_selection(pinyin, word)
        self.insert_to_edit(word)
        self.clear_pinyin()
        self._status_var.set(f"已选: {word}")

    # ── Edit area operations ──────────────────────────────────────────────────

    def _copy_all(self) -> None:
        text = self.edit_area.get("1.0", tk.END).rstrip("\n")
        if not text:
            self._status_var.set("编辑区为空")
            return
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self._status_var.set(f"已复制 {len(text)} 字")
        except Exception:
            self._status_var.set("复制失败")

    def _clear_edit(self) -> None:
        self.edit_area.delete("1.0", tk.END)
        self._undo_stack.clear()
        self._status_var.set("已清空")

    def _undo(self) -> None:
        if not self._undo_stack:
            self._status_var.set("无可撤销")
            return
        word, before_len = self._undo_stack.pop()
        current = self.edit_area.get("1.0", tk.END)
        # Remove the word: keep only the text before the insertion point
        new_text = current[:before_len]
        self.edit_area.delete("1.0", tk.END)
        self.edit_area.insert("1.0", new_text)
        self._status_var.set(f"撤销: {word}")

    def _delete_last_from_edit(self) -> None:
        content = self.edit_area.get("1.0", tk.END)
        if len(content) > 1:   # content always ends with \n
            self.edit_area.delete("end - 2 chars")

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def _schedule_flush(self) -> None:
        self.matcher.flush_user_freq()
        self.root.after(_FLUSH_INTERVAL_MS, self._schedule_flush)

    def _on_close(self) -> None:
        self.matcher.flush_user_freq()
        self.root.destroy()
