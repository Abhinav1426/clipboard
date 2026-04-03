"""Modern CustomTkinter UI for Clipboard Manager.

Works on Windows, macOS, and Linux.
Keyboard bindings are platform-aware (Cmd vs Ctrl).
"""

import logging
import sys

try:
    import customtkinter as ctk
    HAS_CTK = True
except ImportError:
    HAS_CTK = False

import config
from ui.base_ui import BaseUI
from utils.text_utils import get_preview

logger = logging.getLogger(__name__)

_F = config.UI_FONT        # sans-serif UI font (platform-aware)
_M = config.UI_FONT_MONO   # monospace font (platform-aware)


class ModernUI(BaseUI):
    def __init__(self, history_manager, archive_manager, search_engine, auto_paste):
        if not HAS_CTK:
            raise ImportError("customtkinter is not installed. Install with: pip install customtkinter")
        super().__init__(history_manager, archive_manager, search_engine, auto_paste)
        self._app: ctk.CTk | None = None
        self._visible = False
        self._list_frame: ctk.CTkScrollableFrame | None = None
        self._detail_text: ctk.CTkTextbox | None = None
        self._search_var = None
        self._search_entry = None
        self._archive_var = None
        self._status_label: ctk.CTkLabel | None = None
        self._detail_info: ctk.CTkLabel | None = None
        self._item_widgets: list = []
        self._item_map: dict = {}  # entry_id -> {"row": ..., "label": ...}

    def setup_window(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self._app = ctk.CTk()
        self._app.title("Clipboard Manager — Modern")
        self._app.geometry("720x480")
        self._app.minsize(550, 380)
        self._app.protocol("WM_DELETE_WINDOW", self.hide)

    def create_widgets(self):
        app = self._app

        # ── Top bar: search ──────────────────────────────────────
        top_frame = ctk.CTkFrame(app, fg_color="transparent")
        top_frame.pack(fill="x", padx=12, pady=(10, 4))

        ctk.CTkLabel(top_frame, text="Search:", font=(_F, 13)).pack(side="left")

        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._on_search())
        self._search_entry = ctk.CTkEntry(top_frame, textvariable=self._search_var,
                                           width=300, font=(_F, 12))
        self._search_entry.pack(side="left", padx=(8, 12), fill="x", expand=True)

        self._archive_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(top_frame, text="Search archives", variable=self._archive_var,
                        command=self._on_search, font=(_F, 11)).pack(side="left")

        # ── Main area ────────────────────────────────────────────
        main_frame = ctk.CTkFrame(app, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=12, pady=4)

        self._list_frame = ctk.CTkScrollableFrame(main_frame, fg_color="#1e1e2e",
                                                   corner_radius=8)
        self._list_frame.pack(side="left", fill="both", expand=True)

        right_frame = ctk.CTkFrame(main_frame, width=240, fg_color="#252538",
                                    corner_radius=8)
        right_frame.pack(side="right", fill="both", padx=(8, 0))
        right_frame.pack_propagate(False)

        ctk.CTkLabel(right_frame, text="Details", font=(_F, 14, "bold"),
                     text_color="#aaa").pack(anchor="w", padx=12, pady=(10, 2))

        self._detail_info = ctk.CTkLabel(right_frame, text="", font=(_F, 11),
                                          text_color="#999", justify="left", anchor="w")
        self._detail_info.pack(anchor="w", padx=12, fill="x")

        ctk.CTkLabel(right_frame, text="Preview", font=(_F, 13, "bold"),
                     text_color="#aaa").pack(anchor="w", padx=12, pady=(12, 2))

        self._detail_text = ctk.CTkTextbox(right_frame, fg_color="#1e1e2e",
                                            text_color="#ddd", font=(_M, 11),
                                            corner_radius=6, state="disabled")
        self._detail_text.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        # ── Button bar ───────────────────────────────────────────
        btn_frame = ctk.CTkFrame(app, fg_color="transparent")
        btn_frame.pack(fill="x", padx=12, pady=(2, 4))

        btn_font = (_F, 12, "bold")
        ctk.CTkButton(btn_frame, text="📌 Pin/Unpin", fg_color="#e8a838",
                      hover_color="#c98a20", command=self.pin_selected,
                      font=btn_font, width=110).pack(side="left", padx=3)
        ctk.CTkButton(btn_frame, text="📋 Copy", fg_color="#4caf50",
                      hover_color="#388e3c", command=self.copy_to_clipboard,
                      font=btn_font, width=90).pack(side="left", padx=3)
        ctk.CTkButton(btn_frame, text="🗑 Delete", fg_color="#e53935",
                      hover_color="#c62828", command=self.delete_selected,
                      font=btn_font, width=90).pack(side="left", padx=3)
        ctk.CTkButton(btn_frame, text="Clear All", fg_color="#7e57c2",
                      hover_color="#5e35b1", command=self.clear_all,
                      font=btn_font, width=90).pack(side="left", padx=3)

        # ── Status bar ───────────────────────────────────────────
        self._status_label = ctk.CTkLabel(app, text="", font=(_F, 10),
                                           text_color="#888")
        self._status_label.pack(fill="x", padx=12, pady=(0, 6))

    def bind_events(self):
        app = self._app
        app.bind("<Return>", lambda e: self.copy_selected())
        app.bind("<Delete>", lambda e: self.delete_selected())
        app.bind("<Escape>", lambda e: self.hide())
        if sys.platform == "darwin":
            app.bind("<Command-p>", lambda e: self.pin_selected())
            app.bind("<Command-f>", lambda e: self._focus_search())
        else:
            app.bind("<Control-p>", lambda e: self.pin_selected())
            app.bind("<Control-f>", lambda e: self._focus_search())

    def _focus_search(self):
        if self._search_entry:
            self._search_entry.focus_set()
            self._search_entry.select_range(0, "end")

    # ── List rendering ───────────────────────────────────────────

    def refresh_list(self):
        query = self._search_var.get() if self._search_var else ""
        include_archives = self._archive_var.get() if self._archive_var else False

        items = self.do_search(query, include_archives) if query.strip() else self.history.get_all_items()

        for widget in self._list_frame.winfo_children():
            widget.destroy()
        self._item_widgets.clear()
        self._item_map.clear()

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

        self._status_label.configure(text=self.build_status_text())
        self._update_detail()

    def _render_section_header(self, title: str):
        ctk.CTkLabel(self._list_frame, text=title, font=(_F, 11, "bold"),
                     text_color="#7e9cd8").pack(fill="x", padx=6, pady=(8, 2))

    def _render_item(self, item: dict):
        entry_id = item["id"]
        text = item.get("text", "")
        preview = get_preview(text, config.PREVIEW_MAX_CHARS)
        is_selected = (entry_id == self._selected_id)
        bg = "#3c3c54" if is_selected else "#1e1e2e"

        row = ctk.CTkFrame(self._list_frame, fg_color=bg, corner_radius=6,
                           cursor="hand2")
        row.pack(fill="x", pady=2, padx=4)

        label = ctk.CTkLabel(row, text=preview, font=(_F, 11),
                             text_color="#ddd" if is_selected else "#bbb",
                             anchor="w", wraplength=340)
        label.pack(fill="x", padx=8, pady=(4, 1), anchor="w")

        ts = item.get("timestamp", "")[:19].replace("T", " ")
        meta = f"{ts} | {len(text)} chars"
        if item.get("pinned"):
            meta += " | 📌"
        meta_label = ctk.CTkLabel(row, text=meta, font=(_F, 9),
                                   text_color="#888", anchor="w")
        meta_label.pack(fill="x", padx=8, pady=(0, 4), anchor="w")

        def on_click(e, eid=entry_id):
            self._select_item(eid)

        def on_double(e, eid=entry_id):
            self.set_selected_id(eid)
            self.copy_selected()

        for w in (row, label, meta_label):
            w.bind("<Button-1>", on_click)
            w.bind("<Double-Button-1>", on_double)

        self._item_widgets.append(row)
        self._item_map[entry_id] = {"row": row, "label": label}

    def _select_item(self, entry_id: str):
        """Update selection visually without rebuilding the list.

        This avoids destroying widgets on single-click, which would prevent
        the <Double-Button-1> event from ever firing (the widget that received
        the first click would no longer exist).
        """
        self.set_selected_id(entry_id)
        for eid, widgets in self._item_map.items():
            is_sel = (eid == entry_id)
            widgets["row"].configure(fg_color="#3c3c54" if is_sel else "#1e1e2e")
            widgets["label"].configure(text_color="#ddd" if is_sel else "#bbb")
        self._update_detail()

    def _update_detail(self):
        if not self._selected_id:
            self._detail_info.configure(text="")
            self._detail_text.configure(state="normal")
            self._detail_text.delete("1.0", "end")
            self._detail_text.configure(state="disabled")
            return

        item = self.history.get_by_id(self._selected_id)
        if not item:
            return

        ts = item.get("timestamp", "")[:19].replace("T", " ")
        text = item.get("text", "")
        self._detail_info.configure(
            text=f"Copied:  {ts}\nLength:  {len(text)} characters"
        )
        self._detail_text.configure(state="normal")
        self._detail_text.delete("1.0", "end")
        self._detail_text.insert("1.0", text[:config.PREVIEW_DETAIL_MAX_CHARS])
        self._detail_text.configure(state="disabled")

    def _on_search(self):
        self.refresh_list()

    # ── Thread-safe scheduling ───────────────────────────────────

    def _schedule_on_main(self, callback):
        if self._app:
            self._app.after(0, callback)

    # ── Show / Hide / Toggle ─────────────────────────────────────

    def show(self):
        self.refresh_list()
        self._app.deiconify()
        self._app.lift()
        self._app.focus_force()
        self._visible = True

    def hide(self):
        self._app.withdraw()
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
        self._app.after(config.AUTO_REFRESH_INTERVAL, self._schedule_refresh)

    # ── Run ──────────────────────────────────────────────────────

    def run(self):
        self.setup_window()
        self.create_widgets()
        self.bind_events()
        self.refresh_list()
        self.hide()
        self._schedule_refresh()
        self._app.mainloop()
