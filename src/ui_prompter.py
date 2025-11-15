"""
简单的跨平台用户提示界面。

该模块尝试使用 tkinter 弹出一个窗口，让用户通过点击按钮确认继续。
如果当前环境无法创建图形界面（例如在无显示的服务器环境），则自动回退到控制台输入提示。
"""
from __future__ import annotations

from typing import Optional

try:
    import tkinter as tk
    from tkinter import ttk
except Exception:  # pragma: no cover - tkinter 在部分环境中不可用
    tk = None  # type: ignore
    ttk = None  # type: ignore


def wait_for_user_confirmation(
    message: str,
    *,
    title: str = "操作确认",
    button_text: str = "继续",
    fallback_message: Optional[str] = None,
) -> None:
    """显示一个界面提示用户点击按钮继续。

    Args:
        message: 需要展示给用户的提示信息。
        title: 窗口标题。
        button_text: 按钮文字。
        fallback_message: 当无法创建 GUI 窗口时，控制台回退提示信息。
    """

    fallback_text = fallback_message or f"{message}\n请按 Enter 键继续..."

    if tk is None:
        input(fallback_text)
        return

    try:
        root = tk.Tk()
    except Exception:
        input(fallback_text)
        return

    root.title(title)
    root.resizable(False, False)
    try:
        root.attributes("-topmost", True)
    except Exception:
        pass

    if ttk is not None:
        container = ttk.Frame(root, padding=20)
        container.pack(fill="both", expand=True)

        label = ttk.Label(container, text=message, wraplength=360, justify="left")
        label.pack(fill="x", pady=(0, 12))

        def on_continue() -> None:
            root.quit()

        button = ttk.Button(container, text=button_text, command=on_continue)
        button.pack(pady=(0, 8))
    else:
        container = tk.Frame(root, padx=20, pady=20)
        container.pack(fill="both", expand=True)

        label = tk.Label(container, text=message, wraplength=360, justify="left")
        label.pack(fill="x", pady=(0, 12))

        def on_continue() -> None:
            root.quit()

        button = tk.Button(container, text=button_text, command=on_continue)
        button.pack(pady=(0, 8))

    def on_close() -> None:
        root.quit()

    root.protocol("WM_DELETE_WINDOW", on_close)

    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()

    if width <= 1 or height <= 1:
        # 为了在 Windows 上首次展示时能够正确居中
        width = 420
        height = 200
        root.geometry(f"{width}x{height}")
        root.update_idletasks()
        width = root.winfo_width()
        height = root.winfo_height()

    try:
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = max((screen_width // 2) - (width // 2), 0)
        y = max((screen_height // 2) - (height // 2), 0)
        root.geometry(f"+{x}+{y}")
    except Exception:
        pass

    try:
        button.focus_set()
    except Exception:
        pass

    root.mainloop()

    try:
        root.destroy()
    except Exception:
        pass
