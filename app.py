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
from src.connectors import DouyinConnector, MetaConnector, RedditConnector, TikTokResearchConnector, XConnector, YouTubeConnector
from src.database import Database
from src.io_tools import export_csv, export_xlsx, import_csv
from src.platforms import LANGUAGES, PLATFORMS, PLATFORM_BY_KEY, REGIONS, option_code


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
        self.root.title("OmniMedia Intelligence Radar · 全域媒介情报雷达")
        self.root.geometry("1440x900")
        self.root.minsize(1180, 720)
        self.db = Database()
        self.douyin = DouyinConnector()
        self.youtube = YouTubeConnector()
        self.x_connector = XConnector()
        self.reddit = RedditConnector()
        self.meta = MetaConnector()
        self.tiktok = TikTokResearchConnector()
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
        ttk.Label(title_box, text="OMNIMEDIA INTELLIGENCE RADAR", style="Header.TLabel").pack(anchor="w")
        self.project_header = StringVar(value=self.db.get_setting("project_name", "2027 南极旅行项目"))
        ttk.Label(title_box, textvariable=self.project_header, style="Sub.TLabel").pack(anchor="w", pady=(3, 0))
        actions = ttk.Frame(top)
        actions.pack(side=RIGHT, pady=4)
        ttk.Button(actions, text="导入数据", command=self.import_csv_action).pack(side=LEFT, padx=4)
        ttk.Button(actions, text="平台连接中心", style="Accent.TButton", command=self.open_platform_hub).pack(side=LEFT, padx=4)
        ttk.Button(actions, text="YouTube快捷搜索", command=self.open_youtube_dialog).pack(side=LEFT, padx=4)
        ttk.Button(actions, text="项目与AI设置", command=self.open_settings).pack(side=LEFT, padx=4)

        cards = ttk.Frame(self.root, padding=(22, 4, 22, 12))
        cards.pack(fill=X)
        self.card_vars = {key: StringVar(value="0") for key in ("total", "a_count", "b_count", "pending", "replied")}
        card_defs = [
            ("total", "全部内容"), ("a_count", "A级线索"), ("b_count", "B级线索"),
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

        ttk.Label(detail_panel, text="内容详情", style="Panel.TLabel", font=("Microsoft YaHei UI", 14, "bold")).pack(anchor="w")
        self.detail_meta = StringVar(value="请选择一条评论")
        ttk.Label(detail_panel, textvariable=self.detail_meta, style="Muted.Panel.TLabel", wraplength=410).pack(anchor="w", pady=(4, 10))
        ttk.Label(detail_panel, text="原始公开内容 / 评论", style="Muted.Panel.TLabel").pack(anchor="w")
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
        ttk.Button(reply_actions, text="打开来源", command=self.open_video).pack(side=LEFT, padx=5)
        ttk.Button(reply_actions, text="标记忽略", command=lambda: self.mark_status("已忽略")).pack(side=LEFT, padx=5)
        ttk.Button(reply_actions, text="授权账号接口回复", style="Gold.TButton", command=self.publish_selected).pack(side=RIGHT, padx=(5, 0))

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
        profile = self._project_profile()
        for row_id in ids:
            row = self.db.get(row_id)
            if not row:
                continue
            result = classify_with_ollama(row["content"], ollama_url, ollama_model, profile=profile) if mode == "ollama" else classify_rule_based(row["content"], profile)
            self.db.apply_classification(row_id, result)

    def _project_profile(self) -> dict[str, str]:
        return {
            "project_name": self.db.get_setting("project_name", "2027 南极旅行项目"),
            "project_intro": self.db.get_setting("project_intro", "我们正在公开筹备项目，相关计划、费用和进展会持续发布。"),
            "project_keywords": self.db.get_setting("project_keywords", "南极,Antarctica,乌斯怀亚,德雷克"),
            "high_intent_keywords": self.db.get_setting("high_intent_keywords", "怎么报名,如何参加,多少钱,价格,费用,一起去,同行,合作,赞助,how much,how to join,interested,price,cost"),
            "exclude_keywords": self.db.get_setting("exclude_keywords", "兼职,刷单,博彩,贷款,私聊赚钱"),
            "reply_signature": self.db.get_setting("reply_signature", "详情可进入主页查看项目介绍。"),
        }

    def import_csv_action(self, platform_override: str = "") -> None:
        path = filedialog.askopenfilename(title="选择评论CSV", filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")])
        if not path:
            return
        def worker():
            items = import_csv(path, platform_override=platform_override)
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
        path = filedialog.asksaveasfilename(title="导出线索清单", defaultextension=".csv", initialfile="全域媒介线索清单.csv", filetypes=[("CSV文件", "*.csv")])
        if path:
            export_csv(path, self._visible_rows())
            messagebox.showinfo("导出完成", path)

    def export_xlsx_action(self) -> None:
        path = filedialog.asksaveasfilename(title="导出Excel清单", defaultextension=".xlsx", initialfile="全域媒介线索清单.xlsx", filetypes=[("Excel文件", "*.xlsx")])
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

    def _collect_result(self, label: str, worker) -> None:
        def wrapped():
            items = worker()
            inserted, updated, ids = self.db.bulk_upsert(items)
            self._classify_ids(ids)
            return len(items), inserted, updated
        self.run_background(label, wrapped, lambda result: messagebox.showinfo("采集完成", f"获取 {result[0]} 条，新增 {result[1]} 条，更新 {result[2]} 条。"))

    def open_platform_hub(self) -> None:
        dialog = Toplevel(self.root)
        dialog.title("平台连接中心")
        dialog.geometry("1050x680")
        dialog.configure(bg=BG)
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill=BOTH, expand=True)
        ttk.Label(frame, text="平台连接中心", font=("Microsoft YaHei UI", 17, "bold")).pack(anchor="w")
        ttk.Label(frame, text="官方直连、授权账号与合规文件导入统一管理。未获平台权限时，连接入口仍会显示，但不会绕过登录、验证码或风控。", style="Sub.TLabel", wraplength=960).pack(anchor="w", pady=(4, 12))
        columns = ("platform", "connection", "capabilities", "region", "status")
        tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="browse", height=18)
        widths = {"platform": 125, "connection": 175, "capabilities": 330, "region": 145, "status": 120}
        labels = {"platform": "平台", "connection": "接入方式", "capabilities": "允许能力", "region": "地区方式", "status": "当前入口"}
        for key in columns:
            tree.heading(key, text=labels[key])
            tree.column(key, width=widths[key], stretch=key == "capabilities")
        for spec in PLATFORMS:
            tree.insert("", END, iid=spec.key, values=(spec.name, spec.connection, spec.capabilities, spec.region_mode, spec.status))
        tree.pack(fill=BOTH, expand=True)

        buttons = ttk.Frame(frame)
        buttons.pack(fill=X, pady=(12, 0))

        def selected_spec():
            selected = tree.selection()
            return PLATFORM_BY_KEY.get(selected[0]) if selected else None

        def configure():
            spec = selected_spec()
            if not spec:
                messagebox.showinfo("请选择平台", "请先选择一个平台。", parent=dialog)
                return
            actions = {
                "youtube": self.open_youtube_dialog, "douyin": self.open_douyin_dialog,
                "x": self.open_x_dialog, "reddit": self.open_reddit_dialog,
                "facebook": self.open_facebook_dialog, "instagram": self.open_instagram_dialog,
                "tiktok": self.open_tiktok_dialog,
            }
            dialog.destroy()
            if spec.key in actions:
                actions[spec.key]()
            else:
                messagebox.showinfo(f"{spec.name} 接入说明", f"{spec.note}\n\n当前版本请使用该平台账号后台或正式数据服务导出的 CSV，再从平台连接中心导入。")

        def show_docs():
            spec = selected_spec()
            if spec:
                if messagebox.askyesno(f"{spec.name} 接入要求", f"{spec.note}\n\n是否打开官方说明页面？", parent=dialog):
                    webbrowser.open(spec.docs_url)

        def import_selected():
            spec = selected_spec()
            if spec:
                dialog.destroy()
                self.import_csv_action(spec.name)

        ttk.Button(buttons, text="配置 / 开始采集", style="Accent.TButton", command=configure).pack(side=LEFT, padx=(0, 7))
        ttk.Button(buttons, text="查看官方接入要求", command=show_docs).pack(side=LEFT, padx=7)
        ttk.Button(buttons, text="导入所选平台CSV", command=import_selected).pack(side=LEFT, padx=7)
        ttk.Button(buttons, text="关闭", command=dialog.destroy).pack(side=RIGHT)
        tree.bind("<Double-1>", lambda _event: configure())

    def open_x_dialog(self) -> None:
        dialog = Toplevel(self.root); dialog.title("X / Twitter 官方搜索"); dialog.geometry("640x610"); dialog.configure(bg=BG)
        frame = ttk.Frame(dialog, padding=20); frame.pack(fill=BOTH, expand=True)
        ttk.Label(frame, text="X API 近期公开帖文与回复搜索", font=("Microsoft YaHei UI", 15, "bold")).pack(anchor="w")
        ttk.Label(frame, text="地区限制只匹配带地理标签的帖文，可能显著减少结果；历史范围和调用量取决于 X 开发者套餐。", style="Sub.TLabel", wraplength=580).pack(anchor="w", pady=(4, 12))
        token = StringVar(); keyword = StringVar(value=self.db.get_setting("project_keywords", "").replace("，", " OR ").replace(",", " OR ")); maximum = StringVar(value="100")
        language = StringVar(value="自动/不限"); region = StringVar(value="不限地区"); replies_only = BooleanVar(value=False)
        for label, var, secret in [("Bearer Token", token, True), ("搜索表达式（使用 OR，不使用竖线）", keyword, False), ("最多帖文/回复数（10–1000）", maximum, False)]:
            ttk.Label(frame, text=label).pack(anchor="w", pady=(7, 3)); ttk.Entry(frame, textvariable=var, show="•" if secret else "").pack(fill=X)
        ttk.Label(frame, text="相关语言").pack(anchor="w", pady=(8, 3)); ttk.Combobox(frame, state="readonly", textvariable=language, values=[x[0] for x in LANGUAGES]).pack(fill=X)
        ttk.Label(frame, text="精确地理标签地区").pack(anchor="w", pady=(8, 3)); ttk.Combobox(frame, state="readonly", textvariable=region, values=[x[0] for x in REGIONS]).pack(fill=X)
        ttk.Checkbutton(frame, text="只搜索回复（is:reply）", variable=replies_only).pack(anchor="w", pady=(10, 0))
        def submit():
            try: limit = max(10, min(1000, int(maximum.get())))
            except ValueError: messagebox.showerror("格式错误", "最大数量必须是整数。", parent=dialog); return
            if not token.get().strip() or not keyword.get().strip(): messagebox.showerror("缺少信息", "Bearer Token 和关键词不能为空。", parent=dialog); return
            values = (token.get().strip(), keyword.get().strip(), limit, option_code(language.get(), LANGUAGES), option_code(region.get(), REGIONS), replies_only.get())
            dialog.destroy(); self._collect_result("正在调用 X 官方搜索…", lambda: self.x_connector.search_posts(*values))
        ttk.Button(frame, text="开始官方搜索", style="Accent.TButton", command=submit).pack(anchor="e", pady=(16, 0))

    def open_reddit_dialog(self) -> None:
        dialog = Toplevel(self.root); dialog.title("Reddit 官方搜索"); dialog.geometry("640x600"); dialog.configure(bg=BG)
        frame = ttk.Frame(dialog, padding=20); frame.pack(fill=BOTH, expand=True)
        ttk.Label(frame, text="Reddit 社区帖子与公开评论", font=("Microsoft YaHei UI", 15, "bold")).pack(anchor="w")
        ttk.Label(frame, text="使用 Reddit script/web app 的 Client ID 与 Secret。没有精确国家过滤，可通过 subreddit、语言词和地区词缩小范围。", style="Sub.TLabel", wraplength=580).pack(anchor="w", pady=(4, 12))
        client_id = StringVar(); secret = StringVar(); user_agent = StringVar(value="windows:omnimedia-radar:v0.2 (by /u/your_username)")
        keyword = StringVar(value=self.db.get_setting("project_keywords", "")); subreddit = StringVar(); max_posts = StringVar(value="20"); max_comments = StringVar(value="200")
        fields = [("Client ID", client_id, False), ("Client Secret", secret, True), ("User-Agent（需包含你的 Reddit 用户名）", user_agent, False), ("关键词", keyword, False), ("Subreddit（可选，不带 r/）", subreddit, False), ("最多帖子数", max_posts, False), ("每帖最多评论数", max_comments, False)]
        for label, var, hidden in fields:
            ttk.Label(frame, text=label).pack(anchor="w", pady=(5, 2)); ttk.Entry(frame, textvariable=var, show="•" if hidden else "").pack(fill=X)
        def submit():
            if not all(v.get().strip() for v in (client_id, secret, user_agent, keyword)): messagebox.showerror("缺少信息", "Client ID、Secret、User-Agent 和关键词不能为空。", parent=dialog); return
            try: p = max(1, min(100, int(max_posts.get()))); c = max(1, min(500, int(max_comments.get())))
            except ValueError: messagebox.showerror("格式错误", "数量必须是整数。", parent=dialog); return
            values = (client_id.get().strip(), secret.get().strip(), user_agent.get().strip(), keyword.get().strip(), subreddit.get().strip(), p, c)
            dialog.destroy(); self._collect_result("正在调用 Reddit 官方 API…", lambda: self.reddit.search_comments(*values))
        ttk.Button(frame, text="开始官方采集", style="Accent.TButton", command=submit).pack(anchor="e", pady=(14, 0))

    def open_facebook_dialog(self) -> None:
        self._open_meta_dialog("Facebook")

    def open_instagram_dialog(self) -> None:
        self._open_meta_dialog("Instagram")

    def _open_meta_dialog(self, platform: str) -> None:
        dialog = Toplevel(self.root); dialog.title(f"{platform} 授权账号评论"); dialog.geometry("620x480"); dialog.configure(bg=BG)
        frame = ttk.Frame(dialog, padding=20); frame.pack(fill=BOTH, expand=True)
        is_fb = platform == "Facebook"
        ttk.Label(frame, text=f"{platform} 已授权账号内容评论", font=("Microsoft YaHei UI", 15, "bold")).pack(anchor="w")
        ttk.Label(frame, text="只读取你管理或已授权的主页/专业账号内容，不能作为全站任意用户评论搜索器。Token 仅保存在当前运行内存。", style="Sub.TLabel", wraplength=560).pack(anchor="w", pady=(4, 12))
        token = StringVar(); account_id = StringVar(); max_posts = StringVar(value="20"); max_comments = StringVar(value="100")
        for label, var, hidden in [("Page Access Token" if is_fb else "Instagram Access Token", token, True), ("Page ID" if is_fb else "Instagram Professional Account ID", account_id, False), ("最多帖子/媒体数", max_posts, False), ("每条内容最多评论数", max_comments, False)]:
            ttk.Label(frame, text=label).pack(anchor="w", pady=(8, 3)); ttk.Entry(frame, textvariable=var, show="•" if hidden else "").pack(fill=X)
        def submit():
            if not token.get().strip() or not account_id.get().strip(): messagebox.showerror("缺少信息", "Token 和账号 ID 不能为空。", parent=dialog); return
            try: p = max(1, min(100, int(max_posts.get()))); c = max(1, min(100, int(max_comments.get())))
            except ValueError: messagebox.showerror("格式错误", "数量必须是整数。", parent=dialog); return
            values = (token.get().strip(), account_id.get().strip(), p, c); dialog.destroy()
            worker = (lambda: self.meta.facebook_page_comments(*values)) if is_fb else (lambda: self.meta.instagram_comments(*values))
            self._collect_result(f"正在调用 {platform} 官方 API…", worker)
        ttk.Button(frame, text="开始读取授权评论", style="Accent.TButton", command=submit).pack(anchor="e", pady=(18, 0))

    def open_tiktok_dialog(self) -> None:
        dialog = Toplevel(self.root); dialog.title("TikTok Research API"); dialog.geometry("650x650"); dialog.configure(bg=BG)
        frame = ttk.Frame(dialog, padding=20); frame.pack(fill=BOTH, expand=True)
        ttk.Label(frame, text="TikTok Research API 视频与评论", font=("Microsoft YaHei UI", 15, "bold")).pack(anchor="w")
        ttk.Label(frame, text="仅供已通过 TikTok Research Tools 资格审核的非营利研究使用。普通创作者或商业获客账号通常不具备此权限。日期范围最长 30 天。", style="Sub.TLabel", wraplength=590).pack(anchor="w", pady=(4, 12))
        token = StringVar(); keyword = StringVar(value=self.db.get_setting("project_keywords", "").split(",")[0]); region = StringVar(value="美国")
        start_date = StringVar(value="20260701"); end_date = StringVar(value="20260730"); max_videos = StringVar(value="20"); max_comments = StringVar(value="100")
        for label, var, hidden in [("Research API Client Access Token", token, True), ("单个关键词", keyword, False), ("开始日期 YYYYMMDD", start_date, False), ("结束日期 YYYYMMDD", end_date, False), ("最多视频数", max_videos, False), ("每视频最多评论数", max_comments, False)]:
            ttk.Label(frame, text=label).pack(anchor="w", pady=(6, 2)); ttk.Entry(frame, textvariable=var, show="•" if hidden else "").pack(fill=X)
        ttk.Label(frame, text="创作者注册地区").pack(anchor="w", pady=(7, 3)); ttk.Combobox(frame, state="readonly", textvariable=region, values=[x[0] for x in REGIONS]).pack(fill=X)
        def submit():
            if not token.get().strip() or not keyword.get().strip(): messagebox.showerror("缺少信息", "Token 和关键词不能为空。", parent=dialog); return
            try: v = max(1, min(100, int(max_videos.get()))); c = max(1, min(1000, int(max_comments.get())))
            except ValueError: messagebox.showerror("格式错误", "数量必须是整数。", parent=dialog); return
            code = option_code(region.get(), REGIONS); regions = [code] if code else []
            values = (token.get().strip(), keyword.get().strip(), regions, start_date.get().strip(), end_date.get().strip(), v, c)
            dialog.destroy(); self._collect_result("正在调用 TikTok Research API…", lambda: self.tiktok.collect(*values))
        ttk.Button(frame, text="开始研究数据采集", style="Accent.TButton", command=submit).pack(anchor="e", pady=(14, 0))

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
        dialog.geometry("640x640")
        dialog.configure(bg=BG)
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill=BOTH, expand=True)
        ttk.Label(frame, text="YouTube官方API关键词采集", font=("Microsoft YaHei UI", 15, "bold")).pack(anchor="w")
        ttk.Label(frame, text="API Key只保存在本次运行内存中。评论回复仍需人工确认并在平台完成。", style="Sub.TLabel", wraplength=560).pack(anchor="w", pady=(4, 14))
        api_key = StringVar(value=self.youtube_api_key)
        keyword = StringVar(value=self.db.get_setting("project_keywords", "南极旅行,南极同行,Antarctica expedition").replace("，", "|").replace(",", "|"))
        max_videos = StringVar(value="10")
        max_comments = StringVar(value="200")
        language = StringVar(value=self.db.get_setting("target_language_label", "简体中文"))
        region = StringVar(value=self.db.get_setting("target_region_label", "不限地区"))
        for label, var, secret in [
            ("YouTube Data API Key", api_key, True), ("搜索关键词", keyword, False),
            ("最多视频数（1–100）", max_videos, False), ("每个视频最多评论数（1–5000）", max_comments, False),
        ]:
            ttk.Label(frame, text=label).pack(anchor="w", pady=(8, 3))
            ttk.Entry(frame, textvariable=var, show="•" if secret else "").pack(fill=X)
        ttk.Label(frame, text="相关语言").pack(anchor="w", pady=(8, 3))
        ttk.Combobox(frame, state="readonly", textvariable=language, values=[item[0] for item in LANGUAGES]).pack(fill=X)
        ttk.Label(frame, text="可观看国家/地区").pack(anchor="w", pady=(8, 3))
        ttk.Combobox(frame, state="readonly", textvariable=region, values=[item[0] for item in REGIONS]).pack(fill=X)
        ttk.Label(frame, text="提示：YouTube 的地区参数影响可观看区域和相关性，不等于评论者真实所在地。", style="Sub.TLabel", wraplength=580).pack(anchor="w", pady=(7, 0))

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
            language_code = option_code(language.get(), LANGUAGES)
            region_code = option_code(region.get(), REGIONS)
            self.db.set_setting("target_language_label", language.get())
            self.db.set_setting("target_region_label", region.get())
            dialog.destroy()
            def worker():
                videos = self.youtube.search_videos(key, term, video_limit, language_code, region_code)
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
        dialog.title("项目与 AI 设置")
        dialog.geometry("780x760")
        dialog.configure(bg=BG)
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill=BOTH, expand=True)
        ttk.Label(frame, text="项目与 AI 设置", font=("Microsoft YaHei UI", 16, "bold")).pack(anchor="w")
        ttk.Label(frame, text="更换项目名称和关键词后，软件可用于旅行、产品、课程、品牌、活动、服务等不同主题。", style="Sub.TLabel", wraplength=720).pack(anchor="w", pady=(5, 12))
        notebook = ttk.Notebook(frame)
        notebook.pack(fill=BOTH, expand=True)
        project_tab = ttk.Frame(notebook, padding=16)
        ai_tab = ttk.Frame(notebook, padding=16)
        notebook.add(project_tab, text="项目与关键词")
        notebook.add(ai_tab, text="本地 AI")

        project_name = StringVar(value=self.db.get_setting("project_name", "2027 南极旅行项目"))
        ttk.Label(project_tab, text="项目/品牌名称").pack(anchor="w", pady=(0, 3))
        ttk.Entry(project_tab, textvariable=project_name).pack(fill=X)

        text_fields: dict[str, ScrolledText] = {}
        definitions = [
            ("project_intro", "项目简介（用于生成回复）", "我们正在公开筹备项目，相关计划、费用和进展会持续发布。", 3),
            ("project_keywords", "主题关键词（逗号或换行分隔）", "南极,Antarctica,乌斯怀亚,德雷克", 4),
            ("high_intent_keywords", "高意向词（报名、价格、购买、合作等）", "怎么报名,如何参加,多少钱,价格,费用,一起去,同行,合作,赞助,how much,how to join,interested,price,cost", 4),
            ("exclude_keywords", "排除词（广告、诈骗或无关主题）", "兼职,刷单,博彩,贷款,私聊赚钱", 3),
            ("reply_signature", "回复结尾/主页引导", "详情可进入主页查看项目介绍。", 3),
        ]
        for key, label, default, height in definitions:
            ttk.Label(project_tab, text=label).pack(anchor="w", pady=(10, 3))
            widget = ScrolledText(project_tab, height=height, wrap="word", bg=PANEL_ALT, fg=TEXT, insertbackground=TEXT, relief="flat", font=("Microsoft YaHei UI", 10))
            widget.pack(fill=X)
            widget.insert("1.0", self.db.get_setting(key, default))
            text_fields[key] = widget

        ttk.Label(ai_tab, text="默认规则引擎完全离线。Ollama 模式只把文本发送到本机模型，不上传云端。", style="Sub.TLabel", wraplength=660).pack(anchor="w", pady=(0, 14))
        mode = StringVar(value=self.db.get_setting("ai_mode", "rules"))
        ollama_url = StringVar(value=self.db.get_setting("ollama_url", "http://127.0.0.1:11434"))
        ollama_model = StringVar(value=self.db.get_setting("ollama_model", "qwen2.5:3b"))
        ttk.Radiobutton(ai_tab, text="离线规则引擎（推荐，开箱即用）", variable=mode, value="rules").pack(anchor="w", pady=4)
        ttk.Radiobutton(ai_tab, text="本机 Ollama 模型", variable=mode, value="ollama").pack(anchor="w", pady=4)
        ttk.Label(ai_tab, text="Ollama 地址").pack(anchor="w", pady=(12, 3))
        ttk.Entry(ai_tab, textvariable=ollama_url).pack(fill=X)
        ttk.Label(ai_tab, text="模型名称").pack(anchor="w", pady=(10, 3))
        ttk.Entry(ai_tab, textvariable=ollama_model).pack(fill=X)
        def save():
            name = project_name.get().strip()
            if not name:
                messagebox.showerror("缺少名称", "项目/品牌名称不能为空。", parent=dialog)
                return
            self.db.set_setting("project_name", name)
            for key, widget in text_fields.items():
                self.db.set_setting(key, widget.get("1.0", END).strip())
            self.db.set_setting("ai_mode", mode.get())
            self.db.set_setting("ollama_url", ollama_url.get().strip())
            self.db.set_setting("ollama_model", ollama_model.get().strip())
            self.project_header.set(f"{name} · 跨平台公开信息 · 本地AI线索分级 · 人工审核")
            dialog.destroy()
            messagebox.showinfo("保存成功", "项目与 AI 设置已保存在本机。可点击“重新AI分析”应用到现有数据。")
        ttk.Button(frame, text="保存设置", style="Accent.TButton", command=save).pack(anchor="e", pady=(14, 0))


def main() -> None:
    root = Tk()
    app = LeadRadarApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
