# main.py
# -*- coding: utf-8 -*-
"""
Entry point for the Green Offline Pinyin IME.
Run: python main.py
"""

import os
import sys
import tkinter as tk
from tkinter import messagebox

# ── Force UTF-8 stdout/stderr (critical on Japanese-locale Windows) ───────────
os.environ.setdefault("PYTHONIOENCODING", "utf-8")


def detect_font(root: tk.Tk) -> str:
    """Return first available font from FONT_CANDIDATES."""
    import tkinter.font as tkfont
    from config import FONT_CANDIDATES
    available = set(tkfont.families())
    for name in FONT_CANDIDATES:
        if name in available:
            return name
    return "TkDefaultFont"


def show_loading(root: tk.Tk, font_name: str) -> tk.Toplevel:
    splash = tk.Toplevel(root)
    splash.title("加载中...")
    splash.geometry("280x80")
    splash.resizable(False, False)
    splash.attributes("-topmost", True)
    # Center on screen
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    splash.geometry(f"280x80+{(sw-280)//2}+{(sh-80)//2}")
    tk.Label(
        splash,
        text="正在加载词库，请稍候...",
        font=(font_name, 12),
        pady=20,
    ).pack()
    splash.update()
    return splash


def main() -> None:
    # ── Locate data directory ─────────────────────────────────────────────────
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dict_path = os.path.join(base_dir, "data", "pinyin_dict.json")
    freq_path = os.path.join(base_dir, "data", "user_freq.json")

    # ── Create root window (hidden during load) ───────────────────────────────
    root = tk.Tk()
    root.withdraw()

    font_name = detect_font(root)

    # ── Show loading splash ───────────────────────────────────────────────────
    splash = show_loading(root, font_name)

    # ── Load dictionary ───────────────────────────────────────────────────────
    if not os.path.exists(dict_path):
        messagebox.showerror(
            "词库缺失",
            f"找不到词库文件：\n{dict_path}\n\n"
            "请确认 data/pinyin_dict.json 存在于程序目录中。",
        )
        root.destroy()
        sys.exit(1)

    try:
        from engine.dict_loader import DictLoader
        loader = DictLoader.load(dict_path)
    except Exception as exc:
        messagebox.showerror(
            "词库加载失败",
            f"加载词库时发生错误：\n{exc}\n\n"
            "词库文件可能已损坏，请重新下载。",
        )
        root.destroy()
        sys.exit(1)

    # ── Create matcher ────────────────────────────────────────────────────────
    from engine.matcher import Matcher
    matcher = Matcher(loader, freq_path)

    # ── Dismiss splash, show main window ─────────────────────────────────────
    splash.destroy()
    root.deiconify()

    from ui.main_window import MainWindow
    MainWindow(root, matcher, font_name)

    root.mainloop()


if __name__ == "__main__":
    main()
