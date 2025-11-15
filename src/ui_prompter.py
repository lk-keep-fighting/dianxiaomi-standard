"""
跨平台的用户交互工具集合。

默认使用 tkinter 提供可视化界面，并在不可用时自动回退到控制台输入模式。
同时提供一个长驻的流程控制面板，用于启动、暂停、停止自动化流程并展示实时进度。
"""
from __future__ import annotations

import threading
from typing import Callable, Dict, List, Optional, Sequence, Tuple, Union

try:  # pragma: no cover - tkinter 在部分环境中不可用
    import tkinter as tk
    from tkinter import ttk
except Exception:  # pragma: no cover
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
    "ProcessUIController",
]

_ACTIVE_CONTROLLER: Optional["ProcessUIController"] = None


def _set_active_controller(controller: Optional["ProcessUIController"]) -> None:
    global _ACTIVE_CONTROLLER
    _ACTIVE_CONTROLLER = controller


def _get_active_controller() -> Optional["ProcessUIController"]:
    return _ACTIVE_CONTROLLER


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


def _create_container(root: "tk.Misc") -> "tk.Misc":
    if ttk is not None:
        container = ttk.Frame(root, padding=20)
    else:
        container = tk.Frame(root, padx=20, pady=20)
    container.pack(fill="both", expand=True)
    return container


def _center_window(window: "tk.Misc", *, min_width: int = 420, min_height: int = 200) -> None:
    try:
        window.update_idletasks()
    except Exception:
        return

    try:
        width = window.winfo_width()
        height = window.winfo_height()
    except Exception:
        width = min_width
        height = min_height

    if width <= 1 or height <= 1:
        try:
            window.geometry(f"{min_width}x{min_height}")
            window.update_idletasks()
            width = window.winfo_width()
            height = window.winfo_height()
        except Exception:
            width = min_width
            height = min_height

    try:
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = max((screen_width // 2) - (width // 2), 0)
        y = max((screen_height // 2) - (height // 2), 0)
        window.geometry(f"+{x}+{y}")
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

    controller = _get_active_controller()
    if controller and controller.is_gui_available:
        controller.show_confirmation_dialog(message, title=title, button_text=button_text)
        return

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

    root.protocol("WM_DELETE_WINDOW", lambda: root.quit())

    _center_window(root)

    try:
        button.focus_set()
    except Exception:
        pass

    root.mainloop()
    try:
        root.destroy()
    except Exception:
        pass


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

    controller = _get_active_controller()
    if controller and controller.is_gui_available:
        return controller.show_choice_dialog(message, normalized_options, title=title, default_value=default_value)

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

    root.protocol("WM_DELETE_WINDOW", lambda: root.quit())

    _center_window(root)

    try:
        for value, button in button_refs:
            if value == selected["value"]:
                button.focus_set()
                break
    except Exception:
        pass

    root.mainloop()
    try:
        root.destroy()
    except Exception:
        pass

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

    controller = _get_active_controller()
    if controller and controller.is_gui_available:
        return controller.show_text_input_dialog(
            message,
            title=title,
            default=default,
            button_text=button_text,
        )

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

    root.protocol("WM_DELETE_WINDOW", lambda: root.quit())

    _center_window(root)

    try:
        entry.focus_set()
        entry.select_range(0, "end")
    except Exception:
        pass

    root.mainloop()
    try:
        root.destroy()
    except Exception:
        pass

    return result["value"]


class ProcessUIController:
    """流程控制面板，提供启动、暂停、停止和进度展示功能。"""

    def __init__(self, *, title: str = "自动化流程控制面板") -> None:
        self._title = title
        self._gui_enabled = tk is not None
        self._start_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()
        self._stop_event = threading.Event()
        self._ui_ready_event = threading.Event()
        self._modal_events: List[threading.Event] = []
        self._modal_lock = threading.Lock()
        self._paused = False
        self._status_text = "🟡 等待开始"
        self._progress_text = "进度：尚未开始"
        self._root: Optional["tk.Tk"] = None
        self._status_var: Optional["tk.StringVar"] = None
        self._progress_var: Optional["tk.StringVar"] = None
        self._start_button: Optional["tk.Widget"] = None
        self._pause_button: Optional["tk.Widget"] = None
        self._stop_button: Optional["tk.Widget"] = None
        self._ui_thread: Optional[threading.Thread] = None

        if self._gui_enabled:
            self._ui_thread = threading.Thread(target=self._run_ui, name="ProcessUIController", daemon=True)
            self._ui_thread.start()
            self._ui_ready_event.wait(timeout=5)
            if not self._ui_ready_event.is_set():
                self._gui_enabled = False
                print("⚠️ 控制面板初始化失败，将使用命令行模式。")
        else:
            print("⚠️ 当前环境不支持图形界面，将使用命令行控制流程。")

        if self._gui_enabled:
            _set_active_controller(self)

    # ------------------------------------------------------------------
    # 公共属性 & 基本操作
    # ------------------------------------------------------------------
    @property
    def is_gui_available(self) -> bool:
        return self._gui_enabled and self._root is not None

    def wait_for_start(self, message: Optional[str] = None) -> bool:
        if message:
            self.set_status(message)

        if not self._gui_enabled:
            input(message or "按 Enter 键开始流程...")
            return True

        if self._stop_event.is_set():
            return False

        while not self._stop_event.is_set():
            if self._start_event.wait(timeout=0.1):
                return True
        return False

    def wait_if_paused(self) -> bool:
        if not self._gui_enabled:
            return not self._stop_event.is_set()

        while not self._stop_event.is_set():
            if self._pause_event.wait(timeout=0.1):
                return True
        return False

    def should_stop(self) -> bool:
        return self._stop_event.is_set()

    def set_status(self, text: str) -> None:
        self._status_text = text
        if self.is_gui_available and self._status_var is not None:
            self._run_in_ui_thread(lambda: self._status_var.set(text))
        else:
            print(f"[状态] {text}")

    def update_progress(self, current: int, total: Optional[int]) -> None:
        if total and total > 0:
            progress_text = f"进度：处理产品 {current}/{total}"
        else:
            progress_text = f"进度：已处理 {current} 个产品"
        self._progress_text = progress_text

        if self.is_gui_available and self._progress_var is not None:
            self._run_in_ui_thread(lambda: self._progress_var.set(progress_text))
        else:
            print(f"[进度] {progress_text}")

    def close(self) -> None:
        if self._gui_enabled and self._root is not None:
            self._stop_event.set()
            self._pause_event.set()
            self._start_event.set()
            self._run_in_ui_thread(self._root.quit)
            if self._ui_thread and self._ui_thread.is_alive():
                self._ui_thread.join(timeout=2)
        if _get_active_controller() is self:
            _set_active_controller(None)

    # ------------------------------------------------------------------
    # UI 交互模块
    # ------------------------------------------------------------------
    def show_confirmation_dialog(self, message: str, *, title: str, button_text: str) -> None:
        if not self.is_gui_available:
            input(f"{message}\n请按 Enter 键继续...")
            return

        done = threading.Event()
        self._register_modal(done)
        dialog_ref: Dict[str, "tk.Toplevel"] = {}

        def create_dialog() -> None:
            if self._root is None:
                done.set()
                return

            window = tk.Toplevel(self._root)
            dialog_ref["window"] = window
            window.title(title)
            window.transient(self._root)
            window.resizable(False, False)

            container = _create_container(window)

            if ttk is not None:
                label = ttk.Label(container, text=message, wraplength=360, justify="left")
                label.pack(fill="x", pady=(0, 12))
            else:
                label = tk.Label(container, text=message, wraplength=360, justify="left")
                label.pack(fill="x", pady=(0, 12))

            def on_continue() -> None:
                if window.winfo_exists():
                    window.grab_release()
                    window.destroy()
                done.set()

            if ttk is not None:
                button = ttk.Button(container, text=button_text, command=on_continue)
            else:
                button = tk.Button(container, text=button_text, command=on_continue)
            button.pack(pady=(0, 8))

            window.protocol("WM_DELETE_WINDOW", on_continue)
            window.bind("<Destroy>", lambda _: done.set())
            window.grab_set()
            window.focus_force()

            try:
                button.focus_set()
            except Exception:
                pass

            _center_window(window)

        self._run_in_ui_thread(create_dialog)

        while not done.wait(timeout=0.1):
            if self._stop_event.is_set():
                self._destroy_dialog(dialog_ref)
                break

        self._unregister_modal(done)

    def show_choice_dialog(
        self,
        message: str,
        options: Sequence[Tuple[str, str]],
        *,
        title: str,
        default_value: str,
    ) -> str:
        if not self.is_gui_available:
            print("⚠️ 控制面板不可用，回退到命令行模式。")
            print(message)
            return default_value

        result = {"value": default_value}
        done = threading.Event()
        self._register_modal(done)
        dialog_ref: Dict[str, "tk.Toplevel"] = {}

        def create_dialog() -> None:
            if self._root is None:
                done.set()
                return

            window = tk.Toplevel(self._root)
            dialog_ref["window"] = window
            window.title(title)
            window.transient(self._root)
            window.resizable(False, False)

            container = _create_container(window)

            if ttk is not None:
                label_widget = ttk.Label(container, text=message, wraplength=360, justify="left")
            else:
                label_widget = tk.Label(container, text=message, wraplength=360, justify="left")
            label_widget.pack(fill="x", pady=(0, 12))

            if ttk is not None:
                buttons_frame = ttk.Frame(container)
            else:
                buttons_frame = tk.Frame(container)
            buttons_frame.pack(fill="x")

            buttons: List[Tuple[str, "tk.Widget"]] = []

            def on_select(value: str) -> None:
                result["value"] = value
                if window.winfo_exists():
                    window.grab_release()
                    window.destroy()
                done.set()

            for value, label in options:
                button = (
                    ttk.Button(buttons_frame, text=label, command=lambda v=value: on_select(v))
                    if ttk is not None
                    else tk.Button(buttons_frame, text=label, command=lambda v=value: on_select(v))
                )
                button.pack(side="left", expand=True, fill="x", padx=4, pady=(0, 8))
                buttons.append((value, button))

            window.protocol("WM_DELETE_WINDOW", lambda: on_select(default_value))
            window.bind("<Destroy>", lambda _: done.set())
            window.grab_set()
            window.focus_force()

            try:
                for value, button in buttons:
                    if value == default_value:
                        button.focus_set()
                        break
            except Exception:
                pass

            _center_window(window)

        self._run_in_ui_thread(create_dialog)

        while not done.wait(timeout=0.1):
            if self._stop_event.is_set():
                self._destroy_dialog(dialog_ref)
                break

        self._unregister_modal(done)
        return result["value"]

    def show_text_input_dialog(
        self,
        message: str,
        *,
        title: str,
        default: str,
        button_text: str,
    ) -> str:
        if not self.is_gui_available:
            print("⚠️ 控制面板不可用，回退到命令行模式。")
            print(message)
            return default

        result = {"value": default}
        done = threading.Event()
        self._register_modal(done)
        dialog_ref: Dict[str, "tk.Toplevel"] = {}

        def create_dialog() -> None:
            if self._root is None:
                done.set()
                return

            window = tk.Toplevel(self._root)
            dialog_ref["window"] = window
            window.title(title)
            window.transient(self._root)
            window.resizable(False, False)

            container = _create_container(window)

            if ttk is not None:
                label_widget = ttk.Label(container, text=message, wraplength=360, justify="left")
                entry = ttk.Entry(container, width=50)
                button = ttk.Button(container, text=button_text)
            else:
                label_widget = tk.Label(container, text=message, wraplength=360, justify="left")
                entry = tk.Entry(container, width=50)
                button = tk.Button(container, text=button_text)

            label_widget.pack(fill="x", pady=(0, 12))
            entry.insert(0, default)
            entry.pack(fill="x", pady=(0, 12))

            def on_submit() -> None:
                result["value"] = entry.get()
                if window.winfo_exists():
                    window.grab_release()
                    window.destroy()
                done.set()

            button.configure(command=on_submit)
            button.pack(pady=(0, 8))

            entry.bind("<Return>", lambda _: on_submit())
            entry.bind("<KP_Enter>", lambda _: on_submit())

            window.protocol("WM_DELETE_WINDOW", on_submit)
            window.bind("<Destroy>", lambda _: done.set())
            window.grab_set()
            window.focus_force()

            try:
                entry.focus_set()
                entry.select_range(0, "end")
            except Exception:
                pass

            _center_window(window)

        self._run_in_ui_thread(create_dialog)

        while not done.wait(timeout=0.1):
            if self._stop_event.is_set():
                self._destroy_dialog(dialog_ref)
                break

        self._unregister_modal(done)
        return result["value"]

    # ------------------------------------------------------------------
    # 内部实现
    # ------------------------------------------------------------------
    def _run_ui(self) -> None:
        root = _create_tk_root(self._title)
        if root is None:
            self._gui_enabled = False
            self._ui_ready_event.set()
            return

        self._root = root

        if ttk is not None:
            container = ttk.Frame(root, padding=20)
            container.pack(fill="both", expand=True)
            status_label = ttk.Label(container, text=self._status_text, justify="left")
            progress_label = ttk.Label(container, text=self._progress_text, justify="left")
        else:
            container = tk.Frame(root, padx=20, pady=20)
            container.pack(fill="both", expand=True)
            status_label = tk.Label(container, text=self._status_text, justify="left")
            progress_label = tk.Label(container, text=self._progress_text, justify="left")

        self._status_var = tk.StringVar(value=self._status_text)
        self._progress_var = tk.StringVar(value=self._progress_text)

        status_label.config(textvariable=self._status_var, anchor="w")
        progress_label.config(textvariable=self._progress_var, anchor="w")

        status_label.pack(fill="x")
        progress_label.pack(fill="x", pady=(6, 12))

        if ttk is not None:
            buttons_frame = ttk.Frame(container)
            start_button = ttk.Button(buttons_frame, text="开始", command=self._on_start)
            pause_button = ttk.Button(buttons_frame, text="暂停", command=self._on_toggle_pause, state="disabled")
            stop_button = ttk.Button(buttons_frame, text="停止", command=self._on_stop)
        else:
            buttons_frame = tk.Frame(container)
            start_button = tk.Button(buttons_frame, text="开始", command=self._on_start)
            pause_button = tk.Button(buttons_frame, text="暂停", command=self._on_toggle_pause, state="disabled")
            stop_button = tk.Button(buttons_frame, text="停止", command=self._on_stop)

        buttons_frame.pack(fill="x")
        start_button.pack(side="left", expand=True, fill="x", padx=4)
        pause_button.pack(side="left", expand=True, fill="x", padx=4)
        stop_button.pack(side="left", expand=True, fill="x", padx=4)

        self._start_button = start_button
        self._pause_button = pause_button
        self._stop_button = stop_button

        root.protocol("WM_DELETE_WINDOW", self._on_stop)
        _center_window(root, min_width=480, min_height=240)

        self._ui_ready_event.set()
        root.mainloop()

        self._root = None
        self._stop_event.set()
        self._pause_event.set()
        self._start_event.set()
        with self._modal_lock:
            for event in self._modal_events:
                event.set()
            self._modal_events.clear()

    def _run_in_ui_thread(self, func: Callable[[], None]) -> None:
        root = self._root
        if root is None:
            return
        try:
            root.after(0, func)
        except Exception:
            pass

    def _on_start(self) -> None:
        if self._start_event.is_set():
            return
        self._start_event.set()
        self._pause_event.set()
        self._paused = False
        self.set_status("🚀 流程已启动")
        if self._pause_button is not None:
            self._pause_button.configure(state="normal", text="暂停")
        if self._start_button is not None:
            self._start_button.configure(state="disabled")

    def _on_toggle_pause(self) -> None:
        if self._paused:
            self._pause_event.set()
            self._paused = False
            self.set_status("▶️ 流程已继续")
            if self._pause_button is not None:
                self._pause_button.configure(text="暂停")
        else:
            self._pause_event.clear()
            self._paused = True
            self.set_status("⏸️ 流程已暂停")
            if self._pause_button is not None:
                self._pause_button.configure(text="继续")

    def _on_stop(self) -> None:
        if self._stop_event.is_set():
            return
        self._stop_event.set()
        self._pause_event.set()
        self._start_event.set()
        self.set_status("🛑 流程已停止")
        root = self._root
        if root is not None:
            try:
                root.quit()
            except Exception:
                pass

    def _destroy_dialog(self, dialog_ref: Dict[str, "tk.Toplevel"]) -> None:
        window = dialog_ref.get("window")
        if window is not None and window.winfo_exists():
            try:
                window.destroy()
            except Exception:
                pass

    def _register_modal(self, event: threading.Event) -> None:
        with self._modal_lock:
            self._modal_events.append(event)

    def _unregister_modal(self, event: threading.Event) -> None:
        with self._modal_lock:
            if event in self._modal_events:
                self._modal_events.remove(event)

    def __del__(self) -> None:  # pragma: no cover - 清理保障
        try:
            self.close()
        except Exception:
            pass
