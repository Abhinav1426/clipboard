"""Classic Tkinter UI for Clipboard Manager.

Works on Windows, macOS, and Linux.
Fonts fall back gracefully to the system default if the named font is unavailable.
Scroll events are handled for both Windows/macOS (MouseWheel) and Linux (Button-4/5).
"""

import logging
import sys
import tkinter as tk

import config
from ui.base_ui import BaseUI
from utils.text_utils import get_preview

logger = logging.getLogger(__name__)

_F = config.UI_FONT        # sans-serif UI font (platform-aware)
_M = config.UI_FONT_MONO   # monospace font (platform-aware)


class ClassicUI(BaseUI):
    def __init__(self, history_manager, archive_manager, search_engine, auto_paste):
        super().__init__(history_manager, archive_manager, search_engine, auto_paste)
        self._root: tk.Tk | None = None
        self._window: tk.Toplevel | None = None
        self._visible = False
        self._list_frame: tk.Frame | None = None
        self._list_canvas: tk.Canvas | None = None
        self._detail_text: tk.Text | None = None
        self._search_var: tk.StringVar | None = None
        self._search_entry: tk.Entry | None = None
        self._archive_var: tk.BooleanVar | None = None
        self._status_var: tk.StringVar | None = None
        self._item_widgets: list[tk.Frame] = []
        self._detail_info: tk.Label | None = None

    # ── Window setup ─────────────────────────────────────────────

    def setup_window(self):
        self._root = tk.Tk()
        self._root.withdraw()

        self._window = tk.Toplevel(self._root)
        self._window.title("Clipboard Manager")
        self._window.geometry("680x450")
        self._window.minsize(500, 350)
        self._window.protocol("WM_DELETE_WINDOW", self.hide)
        self._window.configure(bg="#2b2b3d")

        try:
            self._window.iconbitmap(default="")
        except Exception:
            pass

    def create_widgets(self):
        w = self._window

        # ── Top bar: search ──────────────────────────────────────
        top_frame = tk.Frame(w, bg="#2b2b3d", pady=6, padx=8)
        top_frame.pack(fill=tk.X)

        tk.Label(top_frame, text="🔍 Search:", bg="#2b2b3d", fg="white",
                 font=(_F, 9)).pack(side=tk.LEFT)

        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._on_search())
        search_entry = tk.Entry(top_frame, textvariable=self._search_var,
                                bg="#3c3c54", fg="white", insertbackground="white",
                                relief=tk.FLAT, font=(_F, 10))
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 8))
        self._search_entry = search_entry

        self._archive_var = tk.BooleanVar(value=False)
        tk.Checkbutton(top_frame, text="Archives", variable=self._archive_var,
                       bg="#2b2b3d", fg="white", selectcolor="#3c3c54",
                       activebackground="#2b2b3d", activeforeground="white",
                       command=self._on_search).pack(side=tk.LEFT)

        # ── Main paned area ──────────────────────────────────────
        main_frame = tk.Frame(w, bg="#2b2b3d")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=8)

        # Left: list with scrollbar
        left_frame = tk.Frame(main_frame, bg="#1e1e2e", relief=tk.FLAT, bd=1)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        list_canvas = tk.Canvas(left_frame, bg="#1e1e2e", highlightthickness=0)
        scrollbar = tk.Scrollbar(left_frame, orient=tk.VERTICAL, command=list_canvas.yview)
        self._list_frame = tk.Frame(list_canvas, bg="#1e1e2e")

        self._list_frame.bind(
            "<Configure>",
            lambda e: list_canvas.configure(scrollregion=list_canvas.bbox("all"))
        )
        list_canvas.create_window((0, 0), window=self._list_frame, anchor="nw",
                                  tags="list_window")
        list_canvas.configure(yscrollcommand=scrollbar.set)
        list_canvas.bind("<Configure>",
                         lambda e: list_canvas.itemconfig("list_window", width=e.width))

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        list_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._list_canvas = list_canvas

        self._bind_scroll(list_canvas)
        self._bind_scroll(self._list_frame)

        # Right: detail panel
        right_frame = tk.Frame(main_frame, bg="#252538", width=230, relief=tk.FLAT, bd=1)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(6, 0))
        right_frame.pack_propagate(False)

        tk.Label(right_frame, text="Details", bg="#252538", fg="#aaa",
                 font=(_F, 11, "bold")).pack(anchor="w", padx=8, pady=(8, 4))

        self._detail_info = tk.Label(right_frame, text="", bg="#252538", fg="#999",
                                     font=(_F, 8), justify=tk.LEFT, anchor="w")
        self._detail_info.pack(anchor="w", padx=8, fill=tk.X)

        tk.Label(right_frame, text="Preview", bg="#252538", fg="#aaa",
                 font=(_F, 10, "bold")).pack(anchor="w", padx=8, pady=(10, 2))

        self._detail_text = tk.Text(right_frame, bg="#1e1e2e", fg="#ddd", wrap=tk.WORD,
                                    relief=tk.FLAT, font=(_M, 9),
                                    state=tk.DISABLED, padx=6, pady=6)
        self._detail_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        # ── Button bar ───────────────────────────────────────────
        btn_frame = tk.Frame(w, bg="#2b2b3d", pady=6, padx=8)
        btn_frame.pack(fill=tk.X)

        btn_style = dict(relief=tk.FLAT, font=(_F, 9, "bold"),
                         cursor="hand2", padx=12, pady=4)

        tk.Button(btn_frame, text="📌 Pin/Unpin", bg="#e8a838", fg="white",
                  command=self.pin_selected, **btn_style).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="📋 Copy", bg="#4caf50", fg="white",
                  command=self.copy_to_clipboard, **btn_style).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="🗑 Delete", bg="#e53935", fg="white",
                  command=self.delete_selected, **btn_style).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Clear All", bg="#7e57c2", fg="white",
                  command=self.clear_all, **btn_style).pack(side=tk.LEFT, padx=2)

        # ── Status bar ───────────────────────────────────────────
        self._status_var = tk.StringVar()
        status_bar = tk.Label(w, textvariable=self._status_var, bg="#1e1e2e", fg="#888",
                              font=(_F, 8), anchor="center", pady=2)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    def bind_events(self):
        w = self._window
        w.bind("<Return>", lambda e: self.copy_selected())
        w.bind("<Delete>", lambda e: self.delete_selected())
        # macOS uses Command+P; Windows/Linux use Ctrl+P
        if sys.platform == "darwin":
            w.bind("<Command-p>", lambda e: self.pin_selected())
            w.bind("<Command-f>", lambda e: self._focus_search())
        else:
            w.bind("<Control-p>", lambda e: self.pin_selected())
            w.bind("<Control-f>", lambda e: self._focus_search())
        w.bind("<Escape>", lambda e: self.hide())

    def _bind_scroll(self, widget):
        """Bind mouse-wheel scroll: Windows/macOS use MouseWheel, Linux uses Button-4/5."""
        def _on_wheel(event):
            if event.delta:
                self._list_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            elif event.num == 4:
                self._list_canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                self._list_canvas.yview_scroll(1, "units")

        widget.bind("<MouseWheel>", _on_wheel)   # Windows / macOS
        widget.bind("<Button-4>", _on_wheel)      # Linux scroll up
        widget.bind("<Button-5>", _on_wheel)      # Linux scroll down

    def _focus_search(self):
        if self._search_entry:
            self._search_entry.focus_set()
            self._search_entry.select_range(0, tk.END)

    # ── List rendering ───────────────────────────────────────────

    def refresh_list(self):
        query = self._search_var.get() if self._search_var else ""
        include_archives = self._archive_var.get() if self._archive_var else False

        items = self.do_search(query, include_archives) if query.strip() else self.history.get_all_items()

        for widget in self._list_frame.winfo_children():
            widget.destroy()
        self._item_widgets.clear()

        pinned = [i for i in items if i.get("pinned")]
        current = [i for i in items if not i.get("pinned")]

        if pinned:
            self._render_section_header("📌 PINNED ITEMS")
            for item in pinned:
                self._render_item(item)

        if current:
            self._render_section_header("📋 RECENT ITEMS")
            for item in current:
                self._render_item(item)

        self._status_var.set(self.build_status_text())
        self._update_detail()

    def _render_section_header(self, title: str):
        header = tk.Label(self._list_frame, text=title, bg="#1e1e2e", fg="#7e9cd8",
                          font=(_F, 9, "bold"), anchor="w", padx=8)
        header.pack(fill=tk.X, pady=(6, 2))

    def _render_item(self, item: dict):
        entry_id = item["id"]
        text = item.get("text", "")
        preview = get_preview(text, config.PREVIEW_MAX_CHARS)
        ts = item.get("timestamp", "")[:19].replace("T", " ")
        meta = f"  — {ts} | {len(text)} chars"
        if item.get("pinned"):
            meta += " | 📌"

        is_selected = (entry_id == self._selected_id)
        bg = "#3c3c54" if is_selected else "#1e1e2e"
        fg = "#fff" if is_selected else "#ccc"

        row = tk.Frame(self._list_frame, bg=bg, cursor="hand2", padx=8, pady=3)
        row.pack(fill=tk.X, pady=1)

        preview_label = tk.Label(row, text=preview, bg=bg, fg=fg,
                                 font=(_F, 9), anchor="w", wraplength=350)
        preview_label.pack(fill=tk.X, anchor="w")

        meta_label = tk.Label(row, text=meta, bg=bg, fg="#888",
                              font=(_F, 7), anchor="w")
        meta_label.pack(fill=tk.X, anchor="w")

        def on_click(e, eid=entry_id):
            self.set_selected_id(eid)
            self.refresh_list()

        def on_double(e, eid=entry_id):
            self.set_selected_id(eid)
            self.copy_selected()

        def on_right_click(e, eid=entry_id):
            self.set_selected_id(eid)
            self.refresh_list()
            self._show_context_menu(e)

        for widget in (row, preview_label, meta_label):
            widget.bind("<Button-1>", on_click)
            widget.bind("<Double-Button-1>", on_double)
            widget.bind("<Button-3>", on_right_click)
            # Right-click on macOS can also come as Button-2 or Control-Button-1
            if sys.platform == "darwin":
                widget.bind("<Button-2>", on_right_click)
                widget.bind("<Control-Button-1>", on_right_click)
            self._bind_scroll(widget)

        self._item_widgets.append(row)

    def _show_context_menu(self, event):
        menu = tk.Menu(self._window, tearoff=0, bg="#2b2b3d", fg="white",
                       activebackground="#3c3c54")
        menu.add_command(label="Copy & Paste", command=self.copy_selected)
        menu.add_command(label="Copy Only", command=self.copy_to_clipboard)
        menu.add_command(label="Pin/Unpin", command=self.pin_selected)
        menu.add_command(label="Delete", command=self.delete_selected)
        menu.tk_popup(event.x_root, event.y_root)

    def _update_detail(self):
        if not self._selected_id:
            self._detail_info.config(text="")
            self._detail_text.config(state=tk.NORMAL)
            self._detail_text.delete("1.0", tk.END)
            self._detail_text.config(state=tk.DISABLED)
            return

        item = self.history.get_by_id(self._selected_id)
        if not item:
            return

        ts = item.get("timestamp", "")[:19].replace("T", " ")
        text = item.get("text", "")
        self._detail_info.config(text=f"Copied:  {ts}\nLength:  {len(text)} characters")

        self._detail_text.config(state=tk.NORMAL)
        self._detail_text.delete("1.0", tk.END)
        self._detail_text.insert("1.0", text[:config.PREVIEW_DETAIL_MAX_CHARS])
        self._detail_text.config(state=tk.DISABLED)

    def _on_search(self):
        self.refresh_list()

    # ── Thread-safe scheduling ───────────────────────────────────

    def _schedule_on_main(self, callback):
        if self._root:
            self._root.after(0, callback)

    # ── Show / Hide / Toggle ─────────────────────────────────────

    def show(self):
        self.refresh_list()
        self._window.deiconify()
        self._window.lift()
        self._window.focus_force()
        self._visible = True

    def hide(self):
        self._window.withdraw()
        self._visible = False

    def toggle(self):
        if self._visible:
            self.hide()
        else:
            self.show()

    # ── Auto-refresh ─────────────────────────────────────────────

    def _schedule_refresh(self):
        if self._visible:
            self.refresh_list()
        self._root.after(config.AUTO_REFRESH_INTERVAL, self._schedule_refresh)

    # ── Run ──────────────────────────────────────────────────────

    def run(self):
        self.setup_window()
        self.create_widgets()
        self.bind_events()
        self.refresh_list()
        self.hide()
        self._schedule_refresh()
        self._root.mainloop()
