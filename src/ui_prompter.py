"""
简单的跨平台用户提示界面。

该模块尝试使用 tkinter 弹出一个窗口，让用户通过点击按钮确认或选择操作。
如果当前环境无法创建图形界面（例如在无显示的服务器环境），则自动回退到控制台输入提示。
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple, Union

try:
    import tkinter as tk
    from tkinter import ttk
except Exception:  # pragma: no cover - tkinter 在部分环境中不可用
    tk = None  # type: ignore
    ttk = None  # type: ignore

PromptOption = Union[
    Tuple[str, str],
    Tuple[str, str, Sequence[str]],
]

__all__ = [
    "wait_for_user_confirmation",
    "prompt_user_choice",
    "prompt_text_input",
]


def _create_tk_root(title: str) -> Optional["tk.Tk"]:
    if tk is None:
        return None

    try:
        root = tk.Tk()
    except Exception:
        return None

    root.title(title)
    root.resizable(False, False)

    try:
        root.attributes("-topmost", True)
    except Exception:
        pass

    return root


def _create_container(root: "tk.Tk"):
    if ttk is not None:
        container = ttk.Frame(root, padding=20)
    else:
        container = tk.Frame(root, padx=20, pady=20)
    container.pack(fill="both", expand=True)
    return container


def _center_window(root: "tk.Tk", *, min_width: int = 420, min_height: int = 200) -> None:
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()

    if width <= 1 or height <= 1:
        root.geometry(f"{min_width}x{min_height}")
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


def _destroy_root(root: "tk.Tk") -> None:
    try:
        root.destroy()
    except Exception:
        pass


def wait_for_user_confirmation(
    message: str,
    *,
    title: str = "操作确认",
    button_text: str = "继续",
    fallback_message: Optional[str] = None,
) -> None:
    """显示一个界面提示用户点击按钮继续。"""

    fallback_text = fallback_message or f"{message}\n请按 Enter 键继续..."

    root = _create_tk_root(title)
    if root is None:
        input(fallback_text)
        return

    container = _create_container(root)

    if ttk is not None:
        label = ttk.Label(container, text=message, wraplength=360, justify="left")
        label.pack(fill="x", pady=(0, 12))

        def on_continue() -> None:
            root.quit()

        button = ttk.Button(container, text=button_text, command=on_continue)
        button.pack(pady=(0, 8))
    else:
        label = tk.Label(container, text=message, wraplength=360, justify="left")
        label.pack(fill="x", pady=(0, 12))

        def on_continue() -> None:
            root.quit()

        button = tk.Button(container, text=button_text, command=on_continue)
        button.pack(pady=(0, 8))

    def on_close() -> None:
        root.quit()

    root.protocol("WM_DELETE_WINDOW", on_close)

    _center_window(root)

    try:
        button.focus_set()
    except Exception:
        pass

    root.mainloop()
    _destroy_root(root)


def prompt_user_choice(
    message: str,
    options: Sequence[PromptOption],
    *,
    title: str = "操作选择",
    default: Optional[str] = None,
    fallback_prompt: Optional[str] = None,
    invalid_message: Optional[str] = None,
) -> str:
    """显示带有多个按钮的选择窗口并返回用户选择的值。"""

    if not options:
        raise ValueError("options must not be empty")

    normalized_options: List[Tuple[str, str]] = []
    alias_map: Dict[str, set] = {}

    for option in options:
        if len(option) == 2:
            value, label = option  # type: ignore[misc]
            aliases: Sequence[str] = ()
        elif len(option) == 3:
            value, label, aliases = option  # type: ignore[misc]
        else:
            raise ValueError("Each option must be a 2-tuple or 3-tuple")

        normalized_options.append((value, label))
        alias_set = {value.upper()}
        alias_set.update(alias.upper() for alias in aliases)
        alias_map[value] = alias_set

    default_value = default if default is not None else normalized_options[0][0]
    if default_value not in {value for value, _ in normalized_options}:
        raise ValueError("default must be one of the option values")

    fallback_text = fallback_prompt or f"{message}\n> "
    invalid_text = invalid_message or "无效选择，请重新输入"

    def fallback_input() -> str:
        while True:
            user_input = input(fallback_text).strip()
            if not user_input:
                return default_value

            normalized = user_input.upper()
            for value, aliases in alias_map.items():
                if normalized in aliases:
                    return value
            print(invalid_text)

    root = _create_tk_root(title)
    if root is None:
        return fallback_input()

    container = _create_container(root)

    if ttk is not None:
        label_widget = ttk.Label(container, text=message, wraplength=360, justify="left")
        label_widget.pack(fill="x", pady=(0, 12))
        buttons_frame = ttk.Frame(container)
    else:
        label_widget = tk.Label(container, text=message, wraplength=360, justify="left")
        label_widget.pack(fill="x", pady=(0, 12))
        buttons_frame = tk.Frame(container)

    buttons_frame.pack(fill="x")

    selected = {"value": default_value}
    button_refs: List[Tuple[str, "tk.Widget"]] = []

    for value, label in normalized_options:
        def on_select(v: str = value) -> None:
            selected["value"] = v
            root.quit()

        if ttk is not None:
            button = ttk.Button(buttons_frame, text=label, command=on_select)
        else:
            button = tk.Button(buttons_frame, text=label, command=on_select)
        button.pack(side="left", expand=True, fill="x", padx=4, pady=(0, 8))
        button_refs.append((value, button))

    def on_close() -> None:
        root.quit()

    root.protocol("WM_DELETE_WINDOW", on_close)

    _center_window(root)

    try:
        for value, button in button_refs:
            if value == selected["value"]:
                button.focus_set()
                break
    except Exception:
        pass

    root.mainloop()
    _destroy_root(root)

    return selected["value"]


def prompt_text_input(
    message: str,
    *,
    title: str = "请输入内容",
    default: str = "",
    button_text: str = "确定",
    fallback_prompt: Optional[str] = None,
) -> str:
    """显示带输入框的窗口并返回用户输入的文本。"""

    fallback_text = fallback_prompt or f"{message}\n> "

    def fallback_input() -> str:
        user_input = input(fallback_text)
        return user_input if user_input else default

    root = _create_tk_root(title)
    if root is None:
        return fallback_input()

    container = _create_container(root)

    if ttk is not None:
        label_widget = ttk.Label(container, text=message, wraplength=360, justify="left")
        label_widget.pack(fill="x", pady=(0, 12))
        entry = ttk.Entry(container, width=50)
    else:
        label_widget = tk.Label(container, text=message, wraplength=360, justify="left")
        label_widget.pack(fill="x", pady=(0, 12))
        entry = tk.Entry(container, width=50)

    entry.insert(0, default)
    entry.pack(fill="x", pady=(0, 12))

    result = {"value": default}

    def on_submit() -> None:
        result["value"] = entry.get()
        root.quit()

    if ttk is not None:
        button = ttk.Button(container, text=button_text, command=on_submit)
    else:
        button = tk.Button(container, text=button_text, command=on_submit)
    button.pack(pady=(0, 8))

    entry.bind("<Return>", lambda event: on_submit())
    entry.bind("<KP_Enter>", lambda event: on_submit())

    def on_close() -> None:
        root.quit()

    root.protocol("WM_DELETE_WINDOW", on_close)

    _center_window(root)

    try:
        entry.focus_set()
        entry.select_range(0, "end")
    except Exception:
        pass

    root.mainloop()
    _destroy_root(root)

    return result["value"]
