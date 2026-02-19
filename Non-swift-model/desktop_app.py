"""EcoScan AI native desktop application (Tkinter).

This is a local desktop app alternative to the web interfaces.
Run with: python desktop_app.py
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import math
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Dict, Optional

import requests

from camera import find_first_readable_camera, scan_barcode_from_webcam
from database import (
    get_current_streak,
    get_impact_distribution,
    get_live_environmental_score,
    get_monthly_scans,
    get_scan_history,
    get_total_co2,
    get_total_scans,
    get_trend_line,
    get_weekly_co2_series,
    init_db,
    insert_scan,
)
from disposal import SUPPORTED_CITIES, get_disposal_instruction
from scoring import IMPACT_TO_LABEL, estimate_co2, score_product, suggest_alternative

try:
    from PIL import Image, ImageTk
except ImportError:  # pragma: no cover - optional rendering support
    Image = None
    ImageTk = None


OPEN_FOOD_FACTS_URL = "https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
APP_BG = "#0e1117"
CARD_BG = "#171b24"
CARD_BG_ALT = "#131923"
TEXT_PRIMARY = "#e6edf7"
TEXT_MUTED = "#8f9bb2"
ACCENT = "#43f2a2"
ACCENT_BLUE = "#66b6ff"
IMPACT_COLORS = {"Green": "#3dffb6", "Yellow": "#ffe066", "Red": "#ff5d73"}


def impact_color(score: str) -> str:
    return IMPACT_COLORS.get(score, ACCENT)


class EcoScanDesktopApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("EcoScan AI - Desktop")
        self.geometry("1220x820")
        self.minsize(1100, 760)
        self.configure(bg=APP_BG)

        self.latest_result: Optional[Dict[str, Any]] = None
        self.last_image_ref = None
        self.latest_weekly_data: list[Dict[str, Any]] = []
        self.latest_trend_data: list[Dict[str, Any]] = []
        self.pulse_phase = 0
        self.badge_base_color = "#1f2735"
        self.badge_animation_job: Optional[str] = None

        init_db()
        self._build_styles()
        self._build_ui()
        self._start_badge_pulse()
        self.refresh_dashboard()
        self.refresh_history()
        self.refresh_analytics()

    @staticmethod
    def _hex_to_rgb(value: str) -> tuple[int, int, int]:
        value = value.lstrip("#")
        return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))

    @staticmethod
    def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
        return "#{:02x}{:02x}{:02x}".format(*rgb)

    def _mix(self, c1: str, c2: str, t: float) -> str:
        r1, g1, b1 = self._hex_to_rgb(c1)
        r2, g2, b2 = self._hex_to_rgb(c2)
        rgb = (
            int(r1 + (r2 - r1) * t),
            int(g1 + (g2 - g1) * t),
            int(b1 + (b2 - b1) * t),
        )
        return self._rgb_to_hex(rgb)

    def _build_styles(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure("TFrame", background=APP_BG)
        style.configure("Card.TFrame", background=CARD_BG)
        style.configure("TLabel", background=APP_BG, foreground=TEXT_PRIMARY, font=("Helvetica", 11))
        style.configure("Title.TLabel", background=APP_BG, foreground=TEXT_PRIMARY, font=("Helvetica", 32, "bold"))
        style.configure("Subtitle.TLabel", background=APP_BG, foreground=TEXT_MUTED, font=("Helvetica", 13))
        style.configure("MetricValue.TLabel", background=CARD_BG, foreground=ACCENT, font=("Helvetica", 24, "bold"))
        style.configure("MetricLabel.TLabel", background=CARD_BG, foreground=TEXT_MUTED, font=("Helvetica", 10))
        style.configure("TButton", font=("Helvetica", 11, "bold"), padding=9)
        style.map("TButton", background=[("active", "#2d3444")], foreground=[("active", TEXT_PRIMARY)])
        style.configure(
            "Accent.TButton",
            font=("Helvetica", 11, "bold"),
            padding=10,
            background=ACCENT,
            foreground="#091218",
        )
        style.map("Accent.TButton", background=[("active", "#5dffb8")], foreground=[("active", "#091218")])
        style.configure("TEntry", fieldbackground="#10141d", foreground=TEXT_PRIMARY)
        style.configure("TCombobox", fieldbackground="#10141d", foreground=TEXT_PRIMARY)
        style.configure("TNotebook", background=APP_BG, borderwidth=0)
        style.configure("TNotebook.Tab", background="#10141d", foreground=TEXT_PRIMARY, padding=(16, 10))
        style.map("TNotebook.Tab", background=[("selected", "#1f2735")], foreground=[("selected", ACCENT)])
        style.configure("Treeview", background="#121722", foreground=TEXT_PRIMARY, fieldbackground="#121722")
        style.configure("Treeview.Heading", background="#1d2432", foreground=TEXT_PRIMARY, font=("Helvetica", 10, "bold"))

    def _build_ui(self) -> None:
        root = ttk.Frame(self, style="TFrame", padding=20)
        root.pack(fill=tk.BOTH, expand=True)

        header_card = tk.Frame(root, bg=CARD_BG, highlightthickness=1, highlightbackground="#283244")
        header_card.pack(fill=tk.X, pady=(0, 14))
        header = ttk.Frame(header_card, style="Card.TFrame", padding=14)
        header.pack(fill=tk.X)

        left = ttk.Frame(header, style="Card.TFrame")
        left.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(left, text="EcoScan AI", style="Title.TLabel").pack(anchor="w")
        ttk.Label(left, text="Scan. Understand. Reduce.", style="Subtitle.TLabel").pack(anchor="w")

        self.header_chip = tk.Label(
            header,
            text="SYSTEM READY",
            bg="#112033",
            fg=ACCENT_BLUE,
            font=("Helvetica", 10, "bold"),
            padx=12,
            pady=8,
        )
        self.header_chip.pack(side=tk.RIGHT, padx=(12, 0))

        self.metrics_row = ttk.Frame(root, style="TFrame")
        self.metrics_row.pack(fill=tk.X, pady=(0, 12))
        self.metric_live = self._metric_card(self.metrics_row, "Live Environmental Score (7d)")
        self.metric_streak = self._metric_card(self.metrics_row, "Daily Scan Streak")
        self.metric_co2 = self._metric_card(self.metrics_row, "Total CO2 Footprint")
        self.metric_scans = self._metric_card(self.metrics_row, "Total Scans")

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.scan_tab = ttk.Frame(self.notebook, style="TFrame", padding=12)
        self.analytics_tab = ttk.Frame(self.notebook, style="TFrame", padding=12)
        self.history_tab = ttk.Frame(self.notebook, style="TFrame", padding=12)

        self.notebook.add(self.scan_tab, text="Scanner")
        self.notebook.add(self.analytics_tab, text="Analytics")
        self.notebook.add(self.history_tab, text="History")
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        self._build_scan_tab()
        self._build_analytics_tab()
        self._build_history_tab()

    def _metric_card(self, parent: ttk.Frame, label: str) -> ttk.Label:
        frame = tk.Frame(parent, bg=CARD_BG, highlightthickness=1, highlightbackground="#283244")
        frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        inner = ttk.Frame(frame, style="Card.TFrame", padding=10)
        inner.pack(fill=tk.BOTH, expand=True)
        value = ttk.Label(inner, text="0", style="MetricValue.TLabel")
        value.pack(anchor="w")
        ttk.Label(inner, text=label, style="MetricLabel.TLabel").pack(anchor="w")
        return value

    def _build_scan_tab(self) -> None:
        top = ttk.Frame(self.scan_tab, style="TFrame")
        top.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        top.grid_columnconfigure(0, weight=5)
        top.grid_columnconfigure(1, weight=6)
        top.grid_rowconfigure(0, weight=1)

        controls_outer = tk.Frame(top, bg=CARD_BG, highlightthickness=1, highlightbackground="#283244")
        controls_outer.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        controls = ttk.Frame(controls_outer, style="Card.TFrame", padding=12)
        controls.pack(fill=tk.BOTH, expand=True)

        ttk.Label(controls, text="City", style="TLabel").grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.city_var = tk.StringVar(value=SUPPORTED_CITIES[0])
        self.city_box = ttk.Combobox(
            controls,
            values=list(SUPPORTED_CITIES),
            textvariable=self.city_var,
            state="readonly",
            width=24,
        )
        self.city_box.grid(row=0, column=1, sticky="w", padx=(10, 0), pady=(0, 6))

        ttk.Label(controls, text="Barcode", style="TLabel").grid(row=1, column=0, sticky="w", pady=(0, 6))
        self.barcode_var = tk.StringVar()
        self.barcode_entry = ttk.Entry(controls, textvariable=self.barcode_var, width=42)
        self.barcode_entry.grid(row=1, column=1, sticky="w", padx=(10, 0), pady=(0, 6))

        ttk.Label(controls, text="Camera Index", style="TLabel").grid(row=2, column=0, sticky="w")
        self.camera_idx_var = tk.IntVar(value=1)
        tk.Spinbox(
            controls,
            from_=0,
            to=5,
            width=5,
            textvariable=self.camera_idx_var,
            bg="#10141d",
            fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            relief=tk.FLAT,
        ).grid(row=2, column=1, sticky="w", padx=(10, 0))

        button_row = ttk.Frame(controls, style="Card.TFrame")
        button_row.grid(row=3, column=0, columnspan=2, sticky="w", pady=(12, 0))
        ttk.Button(button_row, text="Scan Camera", command=self.scan_with_camera, style="Accent.TButton").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(button_row, text="Analyze", command=self.analyze_product).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(button_row, text="Save Scan", command=self.save_scan).pack(side=tk.LEFT)

        self.scan_status = ttk.Label(controls, text="Ready.", style="Subtitle.TLabel")
        self.scan_status.grid(row=4, column=0, columnspan=2, sticky="w", pady=(12, 0))

        result_outer = tk.Frame(top, bg=CARD_BG, highlightthickness=1, highlightbackground="#283244")
        result_outer.grid(row=0, column=1, sticky="nsew")
        result_frame = ttk.Frame(result_outer, style="Card.TFrame", padding=12)
        result_frame.pack(fill=tk.BOTH, expand=True)

        self.product_title = tk.Label(
            result_frame,
            text="No product analyzed yet",
            bg=CARD_BG,
            fg=TEXT_PRIMARY,
            font=("Helvetica", 18, "bold"),
        )
        self.product_title.pack(anchor="w", pady=(0, 8))

        self.impact_badge = tk.Label(
            result_frame,
            text="Impact: --",
            bg="#1f2735",
            fg=TEXT_PRIMARY,
            font=("Helvetica", 11, "bold"),
            padx=14,
            pady=6,
        )
        self.impact_badge.pack(anchor="w", pady=(0, 8))

        self.image_label = tk.Label(result_frame, bg=CARD_BG)
        self.image_label.pack(fill=tk.X, pady=(0, 8))

        stat_cards = ttk.Frame(result_frame, style="Card.TFrame")
        stat_cards.pack(fill=tk.X, pady=(0, 8))

        self.disposal_card = tk.Label(
            stat_cards,
            text="Disposal: --",
            bg=CARD_BG_ALT,
            fg=TEXT_PRIMARY,
            font=("Helvetica", 11, "bold"),
            padx=10,
            pady=10,
            justify=tk.LEFT,
            anchor="w",
        )
        self.disposal_card.pack(fill=tk.X, pady=(0, 6))

        self.co2_card = tk.Label(
            stat_cards,
            text="CO2 Estimate: --",
            bg=CARD_BG_ALT,
            fg=TEXT_PRIMARY,
            font=("Helvetica", 11, "bold"),
            padx=10,
            pady=10,
            justify=tk.LEFT,
            anchor="w",
        )
        self.co2_card.pack(fill=tk.X)

        self.result_text = tk.Text(
            result_frame,
            height=18,
            bg="#10141d",
            fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            relief=tk.FLAT,
            wrap=tk.WORD,
            font=("Helvetica", 11),
        )
        self.result_text.pack(fill=tk.BOTH, expand=True)
        self.result_text.insert(tk.END, "Scan or enter a barcode, then click Analyze.")
        self.result_text.configure(state=tk.DISABLED)
        self.barcode_entry.focus_set()

    def _build_analytics_tab(self) -> None:
        header = ttk.Frame(self.analytics_tab, style="TFrame")
        header.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(header, text="Refresh Analytics", command=self.refresh_analytics).pack(side=tk.LEFT)
        ttk.Button(header, text="Export Monthly CSV", command=self.export_monthly_csv).pack(side=tk.LEFT, padx=(10, 0))

        self.analytics_summary = tk.Text(
            self.analytics_tab,
            height=8,
            bg="#10141d",
            fg=TEXT_PRIMARY,
            relief=tk.FLAT,
            wrap=tk.WORD,
            font=("Helvetica", 11),
        )
        self.analytics_summary.pack(fill=tk.X, pady=(0, 8))
        self.analytics_summary.configure(state=tk.DISABLED)

        chart_wrap = ttk.Frame(self.analytics_tab, style="TFrame")
        chart_wrap.pack(fill=tk.BOTH, expand=True)

        self.weekly_canvas = tk.Canvas(chart_wrap, bg="#10141d", highlightthickness=0)
        self.weekly_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        self.trend_canvas = tk.Canvas(chart_wrap, bg="#10141d", highlightthickness=0)
        self.trend_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        self.weekly_canvas.bind("<Configure>", lambda _: self._draw_weekly_bars(self.latest_weekly_data))
        self.trend_canvas.bind("<Configure>", lambda _: self._draw_trend_line(self.latest_trend_data))

    def _build_history_tab(self) -> None:
        wrap = ttk.Frame(self.history_tab, style="Card.TFrame", padding=10)
        wrap.pack(fill=tk.BOTH, expand=True)

        ttk.Button(wrap, text="Refresh History", command=self.refresh_history).pack(anchor="w", pady=(0, 8))

        columns = ("product_name", "city", "impact_score", "disposal_type", "co2_estimate", "timestamp")
        self.history_tree = ttk.Treeview(wrap, columns=columns, show="headings", height=22)
        headings = {
            "product_name": "Product",
            "city": "City",
            "impact_score": "Impact",
            "disposal_type": "Disposal",
            "co2_estimate": "CO2 (kg)",
            "timestamp": "Timestamp",
        }
        widths = {
            "product_name": 300,
            "city": 120,
            "impact_score": 100,
            "disposal_type": 160,
            "co2_estimate": 90,
            "timestamp": 180,
        }
        for column in columns:
            self.history_tree.heading(column, text=headings[column])
            self.history_tree.column(column, width=widths[column], stretch=False)
        self.history_tree.tag_configure("impact_green", foreground="#3dffb6")
        self.history_tree.tag_configure("impact_yellow", foreground="#ffe066")
        self.history_tree.tag_configure("impact_red", foreground="#ff7d8e")

        scroll = ttk.Scrollbar(wrap, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scroll.set)
        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _start_badge_pulse(self) -> None:
        """Continuously pulse the impact badge glow."""
        base = self.badge_base_color
        peak = "#ffffff"
        t = (math.sin(self.pulse_phase) + 1.0) / 2.0
        t = 0.12 + (t * 0.28)
        shade = self._mix(base, peak, t)
        self.impact_badge.configure(bg=shade)
        self.pulse_phase += 0.18
        self.badge_animation_job = self.after(80, self._start_badge_pulse)

    def _window_fade_transition(self) -> None:
        """Subtle fade on tab switch for smoother transitions."""
        try:
            levels = [1.0, 0.985, 0.97, 0.985, 1.0]
            for i, alpha in enumerate(levels):
                self.after(i * 24, lambda a=alpha: self.attributes("-alpha", a))
        except tk.TclError:
            return

    def _on_tab_changed(self, _: tk.Event) -> None:
        tab_text = self.notebook.tab(self.notebook.select(), "text")
        self.header_chip.configure(text=f"{tab_text.upper()} MODE", fg=ACCENT_BLUE)
        self._window_fade_transition()

    def set_result_text(self, text: str) -> None:
        self.result_text.configure(state=tk.NORMAL)
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert(tk.END, text)
        self.result_text.configure(state=tk.DISABLED)

    def fetch_product(self, barcode: str) -> Dict[str, Any]:
        url = OPEN_FOOD_FACTS_URL.format(barcode=barcode)
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") != 1 or not payload.get("product"):
            raise ValueError("Product not found in Open Food Facts.")
        return payload["product"]

    def parse_product_result(self, barcode: str, city: str, product: Dict[str, Any]) -> Dict[str, Any]:
        product_name = product.get("product_name") or product.get("product_name_en") or "Unknown Product"
        image_url = product.get("image_url")
        packaging_tags = product.get("packaging_tags") or []
        packaging_raw = product.get("packaging") or ""
        packaging_text = " ".join(packaging_tags + [packaging_raw]).strip()

        impact_score, reason = score_product(product)
        disposal = get_disposal_instruction(city, packaging_text)
        co2 = estimate_co2(impact_score)
        alternative = suggest_alternative(impact_score, product_name)

        return {
            "barcode": barcode,
            "city": city,
            "product_name": product_name,
            "product_image": image_url,
            "impact_score": impact_score,
            "impact_label": IMPACT_TO_LABEL.get(impact_score, "Medium Impact"),
            "impact_reason": reason,
            "disposal_type": disposal["disposal_type"],
            "disposal_detail": disposal["detail"],
            "disposal_icon": disposal["icon"],
            "co2_estimate": co2,
            "suggested_alternative": alternative,
        }

    def analyze_product(self) -> None:
        barcode = self.barcode_var.get().strip()
        city = self.city_var.get().strip()

        if not barcode:
            messagebox.showwarning("Missing Barcode", "Enter or scan a barcode first.")
            return

        self.scan_status.configure(text="Analyzing product...")

        def worker() -> None:
            try:
                product = self.fetch_product(barcode)
                result = self.parse_product_result(barcode, city, product)
                self.after(0, lambda: self._on_analysis_success(result))
            except Exception as exc:  # noqa: BLE001
                self.after(0, lambda: self._on_analysis_error(str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _on_analysis_success(self, result: Dict[str, Any]) -> None:
        self.latest_result = result
        self.scan_status.configure(text="Analysis complete.")
        self.header_chip.configure(text=f"{result['impact_score'].upper()} SIGNAL", fg=impact_color(result["impact_score"]))
        self.render_result(result)
        self.render_product_image(result.get("product_image"))
        self.badge_base_color = impact_color(result["impact_score"])
        self.product_title.configure(text=result["product_name"])
        self.impact_badge.configure(
            text=f"{result['impact_score']} • {result['impact_label']}",
            fg="#0b111b",
        )
        self.disposal_card.configure(
            text=f"Disposal\n{result['disposal_icon']} {result['disposal_type']}\n{result['disposal_detail']}"
        )
        self.co2_card.configure(text=f"CO2 Estimate\n{result['co2_estimate']:.2f} kg CO2e")

    def _on_analysis_error(self, message: str) -> None:
        self.scan_status.configure(text="Analysis failed.")
        self.header_chip.configure(text="ANALYZE ERROR", fg="#ff7d8e")
        messagebox.showerror("Analyze Failed", message)

    def render_result(self, result: Dict[str, Any]) -> None:
        text = (
            f"Product: {result['product_name']}\n"
            f"Barcode: {result['barcode']}\n"
            f"City: {result['city']}\n\n"
            f"Impact: {result['impact_score']} ({result['impact_label']})\n"
            f"Reason: {result['impact_reason']}\n\n"
            f"Disposal: {result['disposal_icon']} {result['disposal_type']}\n"
            f"Instruction: {result['disposal_detail']}\n\n"
            f"Estimated CO2: {result['co2_estimate']:.2f} kg\n\n"
            f"Suggested Alternative:\n{result['suggested_alternative']}\n"
        )
        self.set_result_text(text)

    def render_product_image(self, image_url: Optional[str]) -> None:
        if not image_url or Image is None or ImageTk is None:
            self.image_label.configure(image="", text="No image preview available.", fg=TEXT_MUTED)
            return

        def worker() -> None:
            try:
                response = requests.get(image_url, timeout=12)
                response.raise_for_status()
                image_data = response.content
                pil_image = Image.open(io.BytesIO(image_data)).convert("RGB")
                pil_image.thumbnail((460, 260))
                tk_image = ImageTk.PhotoImage(pil_image)
                self.after(0, lambda: self._set_product_image(tk_image))
            except Exception:  # noqa: BLE001
                self.after(0, lambda: self.image_label.configure(image="", text="Image unavailable.", fg=TEXT_MUTED))

        threading.Thread(target=worker, daemon=True).start()

    def _set_product_image(self, tk_image: Any) -> None:
        self.last_image_ref = tk_image
        self.image_label.configure(image=tk_image, text="")

    def save_scan(self) -> None:
        if not self.latest_result:
            messagebox.showwarning("No Result", "Analyze a product before saving.")
            return

        scan_id = insert_scan(
            product_name=self.latest_result["product_name"],
            barcode=self.latest_result["barcode"],
            city=self.latest_result["city"],
            impact_score=self.latest_result["impact_score"],
            disposal_type=self.latest_result["disposal_type"],
            co2_estimate=self.latest_result["co2_estimate"],
        )
        self.scan_status.configure(text=f"Saved scan #{scan_id}.")
        messagebox.showinfo(
            "Saved",
            f"Scan saved.\nDisposal: {self.latest_result['disposal_type']}\n"
            f"CO2: {self.latest_result['co2_estimate']:.2f} kg",
        )
        self.refresh_dashboard()
        self.refresh_history()
        self.refresh_analytics()

    def scan_with_camera(self) -> None:
        self.scan_status.configure(text="Scanning camera for barcode...")

        def worker() -> None:
            preferred = [1, 2, 3, 4, 5]
            selected = find_first_readable_camera(preferred) or self.camera_idx_var.get()
            scan_result = scan_barcode_from_webcam(timeout_seconds=15, camera_index=selected)
            self.after(0, lambda: self._on_camera_scan_done(scan_result.barcode, scan_result.error))

        threading.Thread(target=worker, daemon=True).start()

    def _on_camera_scan_done(self, barcode: Optional[str], error: Optional[str]) -> None:
        if barcode:
            self.barcode_var.set(barcode)
            self.scan_status.configure(text=f"Barcode detected: {barcode}")
            self.header_chip.configure(text="BARCODE LOCKED", fg=ACCENT)
        else:
            self.scan_status.configure(text=error or "No barcode detected.")
            messagebox.showwarning("Scan Failed", error or "No barcode detected.")

    def refresh_dashboard(self) -> None:
        live_score = get_live_environmental_score(days=7)
        streak = get_current_streak()
        total_co2 = get_total_co2()
        total_scans = get_total_scans()

        self.metric_live.configure(text=str(live_score))
        self.metric_streak.configure(text=f"{streak} days")
        self.metric_co2.configure(text=f"{total_co2:.2f} kg")
        self.metric_scans.configure(text=str(total_scans))

    def refresh_history(self) -> None:
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)

        for row in get_scan_history(limit=200):
            impact = row["impact_score"]
            tag = "impact_green" if impact == "Green" else "impact_red" if impact == "Red" else "impact_yellow"
            self.history_tree.insert(
                "",
                tk.END,
                values=(
                    row["product_name"],
                    row["city"],
                    row["impact_score"],
                    row["disposal_type"],
                    f"{row['co2_estimate']:.2f}",
                    row["timestamp"],
                ),
                tags=(tag,),
            )

    def refresh_analytics(self) -> None:
        weekly = get_weekly_co2_series()
        dist = get_impact_distribution()
        trend = get_trend_line(days=30)

        summary = [
            f"Total scans: {get_total_scans()}",
            f"Total CO2 footprint: {get_total_co2():.2f} kg",
            f"Current streak: {get_current_streak()} day(s)",
            "",
            "Impact distribution:",
        ]
        for row in dist:
            summary.append(f"- {row['impact_score']}: {row['count']}")

        self.analytics_summary.configure(state=tk.NORMAL)
        self.analytics_summary.delete("1.0", tk.END)
        self.analytics_summary.insert(tk.END, "\n".join(summary))
        self.analytics_summary.configure(state=tk.DISABLED)
        self.latest_weekly_data = weekly
        self.latest_trend_data = trend
        self._draw_weekly_bars(weekly)
        self._draw_trend_line(trend)

    def _draw_weekly_bars(self, data: list[Dict[str, Any]]) -> None:
        self.weekly_canvas.delete("all")
        w = self.weekly_canvas.winfo_width() or 520
        h = self.weekly_canvas.winfo_height() or 300
        self.weekly_canvas.create_text(16, 16, anchor="nw", fill=TEXT_PRIMARY, text="Weekly CO2 (kg)", font=("Helvetica", 12, "bold"))
        self.weekly_canvas.create_line(14, 34, w - 14, 34, fill="#243045")

        if not data:
            self.weekly_canvas.create_text(w / 2, h / 2, fill=TEXT_MUTED, text="No weekly data")
            return

        max_val = max(float(item["co2"]) for item in data) or 1.0
        bar_w = max(24, int((w - 70) / max(len(data), 1)))
        start_x = 40
        base_y = h - 40
        usable_h = h - 90

        for i, item in enumerate(data):
            val = float(item["co2"])
            x1 = start_x + i * bar_w
            x2 = x1 + int(bar_w * 0.72)
            y1 = base_y - int((val / max_val) * usable_h)
            self.weekly_canvas.create_rectangle(x1, y1, x2, base_y, fill=ACCENT, outline="")
            self.weekly_canvas.create_text((x1 + x2) / 2, y1 - 10, fill=TEXT_PRIMARY, text=f"{val:.1f}", font=("Helvetica", 9))
            self.weekly_canvas.create_text((x1 + x2) / 2, base_y + 12, fill=TEXT_MUTED, text=item["day"][5:], font=("Helvetica", 9))

    def _draw_trend_line(self, data: list[Dict[str, Any]]) -> None:
        self.trend_canvas.delete("all")
        w = self.trend_canvas.winfo_width() or 520
        h = self.trend_canvas.winfo_height() or 300
        self.trend_canvas.create_text(16, 16, anchor="nw", fill=TEXT_PRIMARY, text="30-Day CO2 Trend", font=("Helvetica", 12, "bold"))
        self.trend_canvas.create_line(14, 34, w - 14, 34, fill="#243045")

        if len(data) < 2:
            self.trend_canvas.create_text(w / 2, h / 2, fill=TEXT_MUTED, text="Not enough trend data")
            return

        vals = [float(item["co2"]) for item in data]
        max_val = max(vals) or 1.0
        min_val = min(vals)
        spread = max(max_val - min_val, 0.5)

        pad = 40
        points = []
        for i, item in enumerate(data):
            x = pad + i * ((w - (pad * 2)) / (len(data) - 1))
            normalized = (float(item["co2"]) - min_val) / spread
            y = (h - pad) - normalized * (h - (pad * 2))
            points.extend([x, y])

        self.trend_canvas.create_line(*points, fill="#76f7c4", width=3, smooth=True)
        for i in range(0, len(points), 2):
            self.trend_canvas.create_oval(points[i] - 3, points[i + 1] - 3, points[i] + 3, points[i + 1] + 3, fill=ACCENT, outline="")

    def export_monthly_csv(self) -> None:
        today = dt.date.today()
        rows = get_monthly_scans(today.year, today.month)
        if not rows:
            messagebox.showinfo("No Data", "No scans found for the current month.")
            return

        destination = filedialog.asksaveasfilename(
            title="Save Monthly Report",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile=f"ecoscan_report_{today.year}_{today.month:02d}.csv",
        )
        if not destination:
            return

        with Path(destination).open("w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(
                [
                    "id",
                    "product_name",
                    "barcode",
                    "city",
                    "impact_score",
                    "disposal_type",
                    "co2_estimate",
                    "timestamp",
                ]
            )
            for row in rows:
                writer.writerow(
                    [
                        row["id"],
                        row["product_name"],
                        row["barcode"],
                        row["city"],
                        row["impact_score"],
                        row["disposal_type"],
                        row["co2_estimate"],
                        row["timestamp"],
                    ]
                )
        messagebox.showinfo("Export Complete", f"Saved: {destination}")


def main() -> None:
    app = EcoScanDesktopApp()
    app.mainloop()


if __name__ == "__main__":
    main()
