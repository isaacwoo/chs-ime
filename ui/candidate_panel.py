# ui/candidate_panel.py
# -*- coding: utf-8 -*-
"""
Candidate display widget with 5-per-page pagination.
"""

import tkinter as tk
from typing import Callable

PAGE_SIZE = 5


class CandidatePanel(tk.Frame):
    """
    Displays up to PAGE_SIZE candidates per page.
    Callback on_select(word: str) is called when user clicks or presses 1-5.
    """

    def __init__(
        self,
        parent: tk.Widget,
        on_select: Callable[[str], None],
        font: tuple = ("Microsoft YaHei", 11),
        **kwargs,
    ) -> None:
        super().__init__(parent, **kwargs)
        self._on_select = on_select
        self._font = font
        self._candidates: list[str] = []
        self._page: int = 0          # 0-based page index

        self._build_ui()

    # ── Public API ────────────────────────────────────────────────────────────

    def update_candidates(self, candidates: list[str]) -> None:
        """Replace the full candidate list and reset to page 0."""
        self._candidates = candidates
        self._page = 0
        self._refresh()

    def prev_page(self) -> None:
        if self._page > 0:
            self._page -= 1
            self._refresh()

    def next_page(self) -> None:
        max_page = max(0, (len(self._candidates) - 1) // PAGE_SIZE)
        if self._page < max_page:
            self._page += 1
            self._refresh()

    def select_by_number(self, n: int) -> None:
        """Select candidate at 1-based position n on the current page. No-op if out of range."""
        idx = self._page * PAGE_SIZE + (n - 1)
        if 0 <= idx < len(self._candidates):
            self._on_select(self._candidates[idx])

    def current_page_count(self) -> int:
        """Number of candidates on the current page."""
        start = self._page * PAGE_SIZE
        return min(PAGE_SIZE, len(self._candidates) - start)

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # Row 0: candidate buttons
        self._btn_frame = tk.Frame(self)
        self._btn_frame.pack(fill=tk.X)

        self._btns: list[tk.Label] = []
        for i in range(PAGE_SIZE):
            lbl = tk.Label(
                self._btn_frame,
                text="",
                font=self._font,
                cursor="hand2",
                padx=6,
                pady=2,
                relief=tk.FLAT,
                anchor="w",
            )
            lbl.pack(side=tk.LEFT, padx=2)
            lbl.bind("<Button-1>", self._make_click_handler(i))
            lbl.bind("<Enter>", lambda e, l=lbl: l.config(bg="#ddeeff"))
            lbl.bind("<Leave>", lambda e, l=lbl: l.config(bg=self.cget("bg")))
            self._btns.append(lbl)

        # Row 1: pagination
        nav_frame = tk.Frame(self)
        nav_frame.pack(fill=tk.X, pady=(2, 0))

        tk.Button(
            nav_frame, text="◀", font=("TkDefaultFont", 9),
            command=self.prev_page, relief=tk.FLAT, padx=4,
        ).pack(side=tk.LEFT)

        self._page_label = tk.Label(nav_frame, text="", font=("TkDefaultFont", 9))
        self._page_label.pack(side=tk.LEFT, padx=4)

        tk.Button(
            nav_frame, text="▶", font=("TkDefaultFont", 9),
            command=self.next_page, relief=tk.FLAT, padx=4,
        ).pack(side=tk.LEFT)

    def _refresh(self) -> None:
        start = self._page * PAGE_SIZE
        page_items = self._candidates[start : start + PAGE_SIZE]

        for i, btn in enumerate(self._btns):
            if i < len(page_items):
                btn.config(text=f"{i+1}.{page_items[i]}", fg="#222222")
            else:
                btn.config(text="", fg="gray")

        total_pages = max(1, -(-len(self._candidates) // PAGE_SIZE))  # ceiling division
        self._page_label.config(text=f"{self._page + 1}/{total_pages}")

    def _make_click_handler(self, slot_index: int) -> Callable:
        def handler(event):
            idx = self._page * PAGE_SIZE + slot_index
            if idx < len(self._candidates):
                self._on_select(self._candidates[idx])
        return handler
