from __future__ import annotations

import os
import sys
import threading
import traceback
import webbrowser
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, VERTICAL, X, Y, BooleanVar, StringVar, Tk, Toplevel, filedialog, messagebox
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.classifier import classify_rule_based, classify_with_ollama
from src.connectors import DouyinConnector, YouTubeConnector
from src.database import Database
from src.io_tools import export_csv, export_xlsx, import_csv


BG = "#07131b"
PANEL = "#0d202b"
PANEL_ALT = "#102a37"
TEXT = "#e8f5f8"
MUTED = "#87a7b4"
ACCENT = "#46d7ef"
GOLD = "#e4b863"
RED = "#ff7d79"


class LeadRadarApp:
    def __init__(self, root: Tk):
        self.root = root
        self.root.title("Antarctica Lead Radar · 南极意向雷达")
        self.root.geometry("1440x900")
        self.root.minsize(1180, 720)
        self.db = Database()
        self.douyin = DouyinConnector()
        self.youtube = YouTubeConnector()
        self.douyin_session: dict[str, str] = {}
        self.youtube_api_key = ""
        self.selected_row_id: int | None = None
        self.busy = False
        self._configure_style()
        self._build_ui()
        self.refresh()

    def _configure_style(self) -> None:
        self.root.configure(bg=BG)
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(".", background=BG, foreground=TEXT, fieldbackground=PANEL, font=("Microsoft YaHei UI", 10))
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("Header.TLabel", background=BG, foreground=TEXT, font=("Microsoft YaHei UI", 22, "bold"))
        style.configure("Sub.TLabel", background=BG, foreground=MUTED, font=("Microsoft YaHei UI", 9))
        style.configure("CardTitle.TLabel", background=PANEL, foreground=MUTED, font=("Microsoft YaHei UI", 9))
        style.configure("CardValue.TLabel", background=PANEL, foreground=ACCENT, font=("Microsoft YaHei UI", 20, "bold"))
        style.configure("TLabel", background=BG, foreground=TEXT)
        style.configure("Panel.TLabel", background=PANEL, foreground=TEXT)
        style.configure("Muted.Panel.TLabel", background=PANEL, foreground=MUTED)
        style.configure("TButton", background=PANEL_ALT, foreground=TEXT, padding=(12, 7), borderwidth=0)
        style.map("TButton", background=[("active", "#174156"), ("pressed", "#1b526a")])
        style.configure("Accent.TButton", background="#0f6678", foreground="white", padding=(14, 8))
        style.map("Accent.TButton", background=[("active", "#14839a")])
        style.configure("Gold.TButton", background="#775c29", foreground="white", padding=(14, 8))
        style.map("Gold.TButton", background=[("active", "#9c7938")])
        style.configure("Danger.TButton", background="#713b42", foreground="white")
        style.configure("TEntry", fieldbackground=PANEL_ALT, foreground=TEXT, insertcolor=TEXT, bordercolor="#254553")
        style.configure("TCombobox", fieldbackground=PANEL_ALT, foreground=TEXT, arrowcolor=TEXT)
        style.map("TCombobox", fieldbackground=[("readonly", PANEL_ALT)], foreground=[("readonly", TEXT)])
        style.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=TEXT, rowheight=31, borderwidth=0)
        style.configure("Treeview.Heading", background="#163646", foreground=TEXT, font=("Microsoft YaHei UI", 9, "bold"), relief="flat")
        style.map("Treeview", background=[("selected", "#17657c")], foreground=[("selected", "white")])
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=PANEL, foreground=MUTED, padding=(16, 8))
        style.map("TNotebook.Tab", background=[("selected", PANEL_ALT)], foreground=[("selected", ACCENT)])
        style.configure("Horizontal.TProgressbar", troughcolor=PANEL, background=ACCENT)

    def _build_ui(self) -> None:
        top = ttk.Frame(self.root, padding=(22, 18, 22, 10))
        top.pack(fill=X)
        title_box = ttk.Frame(top)
        title_box.pack(side=LEFT)
        ttk.Label(title_box, text="ANTARCTICA LEAD RADAR", style="Header.TLabel").pack(anchor="w")
        ttk.Label(title_box, text="南极同行意向识别 · 本地数据 · 人工审核回复", style="Sub.TLabel").pack(anchor="w", pady=(3, 0))
        actions = ttk.Frame(top)
        actions.pack(side=RIGHT, pady=4)
        ttk.Button(actions, text="导入CSV", command=self.import_csv_action).pack(side=LEFT, padx=4)
        ttk.Button(actions, text="抖音官方采集", style="Accent.TButton", command=self.open_douyin_dialog).pack(side=LEFT, padx=4)
        ttk.Button(actions, text="YouTube搜索", style="Accent.TButton", command=self.open_youtube_dialog).pack(side=LEFT, padx=4)
        ttk.Button(actions, text="设置", command=self.open_settings).pack(side=LEFT, padx=4)

        cards = ttk.Frame(self.root, padding=(22, 4, 22, 12))
        cards.pack(fill=X)
        self.card_vars = {key: StringVar(value="0") for key in ("total", "a_count", "b_count", "pending", "replied")}
        card_defs = [
            ("total", "全部评论"), ("a_count", "A级意向"), ("b_count", "B级意向"),
            ("pending", "待审核"), ("replied", "已回复"),
        ]
        for key, title in card_defs:
            card = ttk.Frame(cards, style="Panel.TFrame", padding=(18, 12))
            card.pack(side=LEFT, fill=X, expand=True, padx=(0, 10))
            ttk.Label(card, text=title, style="CardTitle.TLabel").pack(anchor="w")
            ttk.Label(card, textvariable=self.card_vars[key], style="CardValue.TLabel").pack(anchor="w", pady=(3, 0))

        filters = ttk.Frame(self.root, padding=(22, 0, 22, 10))
        filters.pack(fill=X)
        ttk.Label(filters, text="筛选").pack(side=LEFT, padx=(0, 8))
        self.level_var = StringVar(value="全部")
        self.platform_var = StringVar(value="全部")
        self.status_filter_var = StringVar(value="全部")
        self.query_var = StringVar()
        self.level_box = ttk.Combobox(filters, width=10, state="readonly", textvariable=self.level_var, values=["全部", "A级", "B级", "C级", "排除", "未分析"])
        self.level_box.pack(side=LEFT, padx=4)
        self.platform_box = ttk.Combobox(filters, width=12, state="readonly", textvariable=self.platform_var, values=["全部"])
        self.platform_box.pack(side=LEFT, padx=4)
        self.status_box = ttk.Combobox(filters, width=10, state="readonly", textvariable=self.status_filter_var, values=["全部", "待审核", "已回复", "已复制", "已忽略"])
        self.status_box.pack(side=LEFT, padx=4)
        search = ttk.Entry(filters, width=34, textvariable=self.query_var)
        search.pack(side=LEFT, padx=8)
        ttk.Button(filters, text="刷新", command=self.refresh).pack(side=LEFT, padx=4)
        ttk.Button(filters, text="重新AI分析", command=self.reanalyze_visible).pack(side=LEFT, padx=4)
        ttk.Button(filters, text="导出Excel", style="Gold.TButton", command=self.export_xlsx_action).pack(side=RIGHT, padx=4)
        ttk.Button(filters, text="导出CSV", command=self.export_csv_action).pack(side=RIGHT, padx=4)
        for widget in (self.level_box, self.platform_box, self.status_box):
            widget.bind("<<ComboboxSelected>>", lambda _event: self.refresh())
        search.bind("<Return>", lambda _event: self.refresh())

        body = ttk.Panedwindow(self.root, orient="horizontal")
        body.pack(fill=BOTH, expand=True, padx=22, pady=(0, 10))
        table_panel = ttk.Frame(body, style="Panel.TFrame", padding=8)
        detail_panel = ttk.Frame(body, style="Panel.TFrame", padding=14)
        body.add(table_panel, weight=4)
        body.add(detail_panel, weight=2)

        columns = ("level", "score", "platform", "user", "account", "content", "time", "status")
        self.tree = ttk.Treeview(table_panel, columns=columns, show="headings", selectmode="browse")
        headings = {"level": "等级", "score": "分数", "platform": "平台", "user": "用户名称", "account": "平台用户标识", "content": "评论内容", "time": "评论时间", "status": "状态"}
        widths = {"level": 62, "score": 58, "platform": 76, "user": 125, "account": 140, "content": 420, "time": 155, "status": 75}
        for key in columns:
            self.tree.heading(key, text=headings[key])
            self.tree.column(key, width=widths[key], minwidth=50, stretch=key == "content")
        scroll = ttk.Scrollbar(table_panel, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        scroll.pack(side=RIGHT, fill=Y)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.tag_configure("A", background="#103b3e")
        self.tree.tag_configure("B", background="#132f3a")
        self.tree.tag_configure("excluded", foreground="#6f8790")

        ttk.Label(detail_panel, text="评论详情", style="Panel.TLabel", font=("Microsoft YaHei UI", 14, "bold")).pack(anchor="w")
        self.detail_meta = StringVar(value="请选择一条评论")
        ttk.Label(detail_panel, textvariable=self.detail_meta, style="Muted.Panel.TLabel", wraplength=410).pack(anchor="w", pady=(4, 10))
        ttk.Label(detail_panel, text="原始评论", style="Muted.Panel.TLabel").pack(anchor="w")
        self.comment_text = ScrolledText(detail_panel, height=5, wrap="word", bg=PANEL_ALT, fg=TEXT, insertbackground=TEXT, relief="flat", font=("Microsoft YaHei UI", 10))
        self.comment_text.pack(fill=X, pady=(4, 10))
        self.comment_text.configure(state="disabled")
        ttk.Label(detail_panel, text="AI判断", style="Muted.Panel.TLabel").pack(anchor="w")
        self.reason_var = StringVar(value="")
        ttk.Label(detail_panel, textvariable=self.reason_var, style="Panel.TLabel", wraplength=410, justify="left").pack(anchor="w", fill=X, pady=(4, 10))
        ttk.Label(detail_panel, text="建议回复（发布前必须人工确认）", style="Muted.Panel.TLabel").pack(anchor="w")
        self.reply_text = ScrolledText(detail_panel, height=8, wrap="word", bg="#0a2632", fg=TEXT, insertbackground=TEXT, relief="flat", font=("Microsoft YaHei UI", 10))
        self.reply_text.pack(fill=BOTH, expand=True, pady=(4, 10))
        reply_actions = ttk.Frame(detail_panel, style="Panel.TFrame")
        reply_actions.pack(fill=X)
        ttk.Button(reply_actions, text="复制回复", command=self.copy_reply).pack(side=LEFT, padx=(0, 5))
        ttk.Button(reply_actions, text="打开原视频", command=self.open_video).pack(side=LEFT, padx=5)
        ttk.Button(reply_actions, text="标记忽略", command=lambda: self.mark_status("已忽略")).pack(side=LEFT, padx=5)
        ttk.Button(reply_actions, text="官方接口回复", style="Gold.TButton", command=self.publish_selected).pack(side=RIGHT, padx=(5, 0))

        bottom = ttk.Frame(self.root, padding=(22, 0, 22, 14))
        bottom.pack(fill=X)
        self.status_var = StringVar(value=f"本地数据库：{self.db.path}")
        ttk.Label(bottom, textvariable=self.status_var, style="Sub.TLabel").pack(side=LEFT)
        self.progress = ttk.Progressbar(bottom, mode="indeterminate", length=180)
        self.progress.pack(side=RIGHT)

    def _set_text(self, widget: ScrolledText, value: str, readonly: bool = False) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", END)
        widget.insert("1.0", value)
        if readonly:
            widget.configure(state="disabled")

    def refresh(self) -> None:
        rows = self.db.list_comments(
            level=self.level_var.get(), platform=self.platform_var.get(),
            status=self.status_filter_var.get(), query=self.query_var.get(),
        )
        selected = str(self.selected_row_id or "")
        self.tree.delete(*self.tree.get_children())
        for row in rows:
            content_preview = row["content"].replace("\n", " ")
            if len(content_preview) > 62:
                content_preview = content_preview[:62] + "…"
            tag = "A" if row["intent_level"] == "A级" else "B" if row["intent_level"] == "B级" else "excluded" if row["intent_level"] == "排除" else ""
            self.tree.insert(
                "", END, iid=str(row["id"]), tags=(tag,) if tag else (),
                values=(row["intent_level"], row["intent_score"], row["platform"], row["user_name"], row["user_id"], content_preview, row["comment_time"], row["status"]),
            )
        if selected and self.tree.exists(selected):
            self.tree.selection_set(selected)
        counts = self.db.dashboard_counts()
        for key, var in self.card_vars.items():
            var.set(str(counts.get(key, 0)))
        platforms = ["全部", *self.db.platforms()]
        self.platform_box.configure(values=platforms)
        if self.platform_var.get() not in platforms:
            self.platform_var.set("全部")
        self.status_var.set(f"显示 {len(rows)} 条 · 本地数据库：{self.db.path}")

    def on_select(self, _event=None) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        self.selected_row_id = int(selection[0])
        row = self.db.get(self.selected_row_id)
        if not row:
            return
        self.detail_meta.set(f"{row['platform']} · {row['user_name']} · {row['user_id']}\n{row['intent_level']} / {row['intent_label']} / {row['intent_score']}分 · {row['comment_time']}")
        self._set_text(self.comment_text, row["content"], readonly=True)
        self.reason_var.set(row["reason"] or "尚未分析")
        self._set_text(self.reply_text, row["final_reply"] or row["suggested_reply"])

    def run_background(self, label: str, worker, success=None) -> None:
        if self.busy:
            messagebox.showinfo("任务进行中", "请等待当前任务完成。")
            return
        self.busy = True
        self.status_var.set(label)
        self.progress.start(12)

        def target():
            try:
                result = worker()
            except Exception as exc:
                trace = traceback.format_exc(limit=4)
                self.root.after(0, lambda: self._background_error(exc, trace))
            else:
                self.root.after(0, lambda: self._background_success(result, success))

        threading.Thread(target=target, daemon=True).start()

    def _background_error(self, exc: Exception, trace: str) -> None:
        self.busy = False
        self.progress.stop()
        self.status_var.set("任务失败")
        messagebox.showerror("操作失败", f"{exc}\n\n{trace[-900:]}")

    def _background_success(self, result, success) -> None:
        self.busy = False
        self.progress.stop()
        if success:
            success(result)
        self.refresh()

    def _classify_ids(self, ids: list[int]) -> None:
        mode = self.db.get_setting("ai_mode", "rules")
        ollama_url = self.db.get_setting("ollama_url", "http://127.0.0.1:11434")
        ollama_model = self.db.get_setting("ollama_model", "qwen2.5:3b")
        for row_id in ids:
            row = self.db.get(row_id)
            if not row:
                continue
            result = classify_with_ollama(row["content"], ollama_url, ollama_model) if mode == "ollama" else classify_rule_based(row["content"])
            self.db.apply_classification(row_id, result)

    def import_csv_action(self) -> None:
        path = filedialog.askopenfilename(title="选择评论CSV", filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")])
        if not path:
            return
        def worker():
            items = import_csv(path)
            inserted, updated, ids = self.db.bulk_upsert(items)
            self._classify_ids(ids)
            return inserted, updated
        self.run_background("正在导入并分析CSV…", worker, lambda result: messagebox.showinfo("导入完成", f"新增 {result[0]} 条，更新 {result[1]} 条。"))

    def reanalyze_visible(self) -> None:
        ids = [int(item) for item in self.tree.get_children()]
        if not ids:
            messagebox.showinfo("没有数据", "当前筛选条件下没有可分析的评论。")
            return
        self.run_background("正在重新分析评论…", lambda: self._classify_ids(ids), lambda _result: messagebox.showinfo("分析完成", f"已分析 {len(ids)} 条评论。"))

    def _visible_rows(self):
        return [self.db.get(int(item)) for item in self.tree.get_children() if self.db.get(int(item))]

    def export_csv_action(self) -> None:
        path = filedialog.asksaveasfilename(title="导出评论清单", defaultextension=".csv", initialfile="南极意向评论清单.csv", filetypes=[("CSV文件", "*.csv")])
        if path:
            export_csv(path, self._visible_rows())
            messagebox.showinfo("导出完成", path)

    def export_xlsx_action(self) -> None:
        path = filedialog.asksaveasfilename(title="导出Excel清单", defaultextension=".xlsx", initialfile="南极意向评论清单.xlsx", filetypes=[("Excel文件", "*.xlsx")])
        if path:
            export_xlsx(path, self._visible_rows())
            messagebox.showinfo("导出完成", path)

    def copy_reply(self) -> None:
        if not self.selected_row_id:
            return
        content = self.reply_text.get("1.0", END).strip()
        if not content:
            messagebox.showinfo("没有回复", "AI未生成回复，或该评论已被排除。")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        self.db.set_status(self.selected_row_id, "已复制", content)
        self.status_var.set("回复已复制。请在平台人工确认后发布。")
        self.refresh()

    def open_video(self) -> None:
        if not self.selected_row_id:
            return
        row = self.db.get(self.selected_row_id)
        if row and row["video_url"]:
            webbrowser.open(row["video_url"])
        else:
            messagebox.showinfo("没有链接", "该条记录没有原视频链接。")

    def mark_status(self, status: str) -> None:
        if self.selected_row_id:
            self.db.set_status(self.selected_row_id, status, self.reply_text.get("1.0", END).strip())
            self.refresh()

    def publish_selected(self) -> None:
        if not self.selected_row_id:
            messagebox.showinfo("请选择评论", "请先选择一条评论。")
            return
        row = self.db.get(self.selected_row_id)
        if not row or row["platform"] != "抖音":
            messagebox.showinfo("暂不支持", "第一版只支持通过官方接口回复已授权抖音账号的视频评论；其他平台请复制后人工发布。")
            return
        required = ("access_token", "open_id")
        if not all(self.douyin_session.get(key) for key in required):
            messagebox.showinfo("需要授权", "请先打开“抖音官方采集”，输入本次会话的 access_token 与 open_id。密钥不会自动保存。")
            return
        reply = self.reply_text.get("1.0", END).strip()
        if not reply:
            messagebox.showinfo("没有回复", "请先填写回复内容。")
            return
        if not messagebox.askyesno("确认发布", "请确认这是你已授权账号视频下的评论，并已人工检查回复内容。是否通过抖音官方接口发布？"):
            return
        def worker():
            return self.douyin.reply_comment(self.douyin_session["access_token"], self.douyin_session["open_id"], row["video_id"], row["platform_comment_id"], reply)
        def success(_result):
            self.db.set_status(row["id"], "已回复", reply)
            messagebox.showinfo("发布成功", "抖音官方接口已接受回复。")
        self.run_background("正在通过抖音官方接口发布…", worker, success)

    def open_douyin_dialog(self) -> None:
        dialog = Toplevel(self.root)
        dialog.title("抖音官方评论采集")
        dialog.geometry("620x540")
        dialog.configure(bg=BG)
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill=BOTH, expand=True)
        ttk.Label(frame, text="只采集已授权账号的视频评论", font=("Microsoft YaHei UI", 15, "bold")).pack(anchor="w")
        ttk.Label(frame, text="需要抖音开放平台 video.comment 权限。access_token 仅保存在本次运行内存中。", style="Sub.TLabel", wraplength=560).pack(anchor="w", pady=(4, 14))
        fields = {}
        definitions = [
            ("access_token", "Access Token", True), ("open_id", "授权账号 Open ID", False),
            ("item_id", "视频 Item ID", False), ("video_title", "视频标题（可选）", False),
            ("video_url", "视频链接（可选）", False), ("max_pages", "最多采集页数（每页最多50条）", False),
        ]
        for key, label, secret in definitions:
            ttk.Label(frame, text=label).pack(anchor="w", pady=(7, 3))
            var = StringVar(value="10" if key == "max_pages" else self.douyin_session.get(key, ""))
            ttk.Entry(frame, textvariable=var, show="•" if secret else "").pack(fill=X)
            fields[key] = var

        def submit():
            values = {key: var.get().strip() for key, var in fields.items()}
            if not values["access_token"] or not values["open_id"] or not values["item_id"]:
                messagebox.showerror("缺少信息", "Access Token、Open ID和Item ID不能为空。", parent=dialog)
                return
            try:
                max_pages = max(1, min(50, int(values["max_pages"] or "10")))
            except ValueError:
                messagebox.showerror("格式错误", "最多页数必须是整数。", parent=dialog)
                return
            self.douyin_session = {"access_token": values["access_token"], "open_id": values["open_id"]}
            dialog.destroy()
            def worker():
                items = self.douyin.list_comments(values["access_token"], values["open_id"], values["item_id"], values["video_title"], values["video_url"], max_pages)
                inserted, updated, ids = self.db.bulk_upsert(items)
                self._classify_ids(ids)
                return inserted, updated
            self.run_background("正在通过抖音官方接口采集…", worker, lambda result: messagebox.showinfo("采集完成", f"新增 {result[0]} 条，更新 {result[1]} 条。"))
        ttk.Button(frame, text="开始官方采集", style="Accent.TButton", command=submit).pack(anchor="e", pady=(18, 0))

    def open_youtube_dialog(self) -> None:
        dialog = Toplevel(self.root)
        dialog.title("YouTube关键词搜索")
        dialog.geometry("620x500")
        dialog.configure(bg=BG)
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill=BOTH, expand=True)
        ttk.Label(frame, text="YouTube官方API关键词采集", font=("Microsoft YaHei UI", 15, "bold")).pack(anchor="w")
        ttk.Label(frame, text="API Key只保存在本次运行内存中。评论回复仍需人工确认并在平台完成。", style="Sub.TLabel", wraplength=560).pack(anchor="w", pady=(4, 14))
        api_key = StringVar(value=self.youtube_api_key)
        keyword = StringVar(value="南极旅行 OR 南极同行 OR Antarctica expedition")
        max_videos = StringVar(value="10")
        max_comments = StringVar(value="200")
        for label, var, secret in [
            ("YouTube Data API Key", api_key, True), ("搜索关键词", keyword, False),
            ("最多视频数（1–100）", max_videos, False), ("每个视频最多评论数（1–5000）", max_comments, False),
        ]:
            ttk.Label(frame, text=label).pack(anchor="w", pady=(8, 3))
            ttk.Entry(frame, textvariable=var, show="•" if secret else "").pack(fill=X)

        def submit():
            key = api_key.get().strip()
            term = keyword.get().strip()
            if not key or not term:
                messagebox.showerror("缺少信息", "API Key和关键词不能为空。", parent=dialog)
                return
            try:
                video_limit = max(1, min(100, int(max_videos.get())))
                comment_limit = max(1, min(5000, int(max_comments.get())))
            except ValueError:
                messagebox.showerror("格式错误", "数量必须是整数。", parent=dialog)
                return
            self.youtube_api_key = key
            dialog.destroy()
            def worker():
                videos = self.youtube.search_videos(key, term, video_limit)
                all_items = []
                errors = 0
                for video in videos:
                    try:
                        all_items.extend(self.youtube.list_comments(key, video, comment_limit))
                    except Exception:
                        errors += 1
                inserted, updated, ids = self.db.bulk_upsert(all_items)
                self._classify_ids(ids)
                return len(videos), inserted, updated, errors
            self.run_background("正在搜索视频并分析评论…", worker, lambda result: messagebox.showinfo("采集完成", f"处理视频 {result[0]} 个，新增评论 {result[1]} 条，更新 {result[2]} 条，跳过异常视频 {result[3]} 个。"))
        ttk.Button(frame, text="开始搜索与采集", style="Accent.TButton", command=submit).pack(anchor="e", pady=(20, 0))

    def open_settings(self) -> None:
        dialog = Toplevel(self.root)
        dialog.title("AI设置")
        dialog.geometry("570x390")
        dialog.configure(bg=BG)
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill=BOTH, expand=True)
        ttk.Label(frame, text="AI分析方式", font=("Microsoft YaHei UI", 15, "bold")).pack(anchor="w")
        ttk.Label(frame, text="默认规则引擎完全离线。Ollama模式把评论发送到本机模型，不上传云端。", style="Sub.TLabel", wraplength=520).pack(anchor="w", pady=(5, 14))
        mode = StringVar(value=self.db.get_setting("ai_mode", "rules"))
        ollama_url = StringVar(value=self.db.get_setting("ollama_url", "http://127.0.0.1:11434"))
        ollama_model = StringVar(value=self.db.get_setting("ollama_model", "qwen2.5:3b"))
        ttk.Radiobutton(frame, text="离线规则引擎（推荐，开箱即用）", variable=mode, value="rules").pack(anchor="w", pady=4)
        ttk.Radiobutton(frame, text="本机Ollama模型", variable=mode, value="ollama").pack(anchor="w", pady=4)
        ttk.Label(frame, text="Ollama地址").pack(anchor="w", pady=(12, 3))
        ttk.Entry(frame, textvariable=ollama_url).pack(fill=X)
        ttk.Label(frame, text="模型名称").pack(anchor="w", pady=(10, 3))
        ttk.Entry(frame, textvariable=ollama_model).pack(fill=X)
        def save():
            self.db.set_setting("ai_mode", mode.get())
            self.db.set_setting("ollama_url", ollama_url.get().strip())
            self.db.set_setting("ollama_model", ollama_model.get().strip())
            dialog.destroy()
            messagebox.showinfo("保存成功", "AI设置已保存在本机。")
        ttk.Button(frame, text="保存设置", style="Accent.TButton", command=save).pack(anchor="e", pady=(18, 0))


def main() -> None:
    root = Tk()
    app = LeadRadarApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
