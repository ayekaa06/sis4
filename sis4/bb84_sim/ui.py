"""Tkinter desktop interface for the BB84 simulator."""

from __future__ import annotations

import math
import tkinter as tk
from tkinter import messagebox, ttk
from typing import List, Optional

from .protocol import BB84Protocol, PhotonTrace, ProtocolConfig, RunResult


def _format_percent(value: float) -> str:
    return f"{value * 100:.2f}%"


def _format_basis(basis: Optional[str]) -> str:
    return basis if basis is not None else "-"


def _trace_window(current_index: int, total: int, window_size: int = 18) -> range:
    if total <= window_size:
        return range(total)
    start = max(0, current_index - (window_size // 2))
    end = min(total, start + window_size)
    start = max(0, end - window_size)
    return range(start, end)


def run_app() -> None:
    app = BB84App()
    app.mainloop()


class BB84App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("BB84 Quantum Key Distribution Simulator")
        self.geometry("1480x920")
        self.minsize(1320, 820)

        self.current_result: Optional[RunResult] = None
        self.current_step = 0
        self.play_job: Optional[str] = None

        self.photon_count_var = tk.IntVar(value=512)
        self.error_check_var = tk.DoubleVar(value=12.0)
        self.error_threshold_var = tk.DoubleVar(value=11.0)
        self.channel_noise_var = tk.DoubleVar(value=0.0)
        self.eve_enabled_var = tk.BooleanVar(value=False)
        self.seed_var = tk.StringVar(value="42")
        self.play_delay_var = tk.IntVar(value=120)

        self.status_var = tk.StringVar(
            value="Ready. Run a simulation to see BB84 transmission, reconciliation, and key generation."
        )
        self.current_photon_var = tk.StringVar(value="No simulation loaded.")
        self.current_decision_var = tk.StringVar(value="Photon decisions will appear here.")
        self.current_measurement_var = tk.StringVar(value="Measurement details will appear here.")
        self.result_var = tk.StringVar(value="Final protocol result will appear here.")

        self._build_style()
        self._build_layout()
        self._set_phase_state(None)
        self._refresh_empty_views()

    def _build_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TLabelframe", background="#f5f7fb")
        style.configure("TLabelframe.Label", background="#f5f7fb", font=("Segoe UI", 11, "bold"))
        style.configure("TFrame", background="#f5f7fb")
        style.configure("TLabel", background="#f5f7fb", font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 11, "bold"))
        style.configure("Stat.Treeview", rowheight=26, font=("Consolas", 10))
        style.configure("Stat.Treeview.Heading", font=("Segoe UI", 10, "bold"))
        self.configure(bg="#f5f7fb")

    def _build_layout(self) -> None:
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0)
        self.grid_rowconfigure(0, weight=1)

        config_frame = ttk.LabelFrame(self, text="Configuration", padding=14)
        config_frame.grid(row=0, column=0, sticky="nsw", padx=(14, 8), pady=14)

        center_frame = ttk.Frame(self, padding=0)
        center_frame.grid(row=0, column=1, sticky="nsew", pady=14)
        center_frame.grid_rowconfigure(2, weight=1)
        center_frame.grid_columnconfigure(0, weight=1)

        summary_frame = ttk.LabelFrame(self, text="Statistics and Results", padding=14)
        summary_frame.grid(row=0, column=2, sticky="nse", padx=(8, 14), pady=14)
        summary_frame.grid_rowconfigure(2, weight=1)

        self._build_config_panel(config_frame)
        self._build_visual_panel(center_frame)
        self._build_summary_panel(summary_frame)

        status_label = ttk.Label(self, textvariable=self.status_var, anchor="w", padding=(16, 8))
        status_label.grid(row=1, column=0, columnspan=3, sticky="ew")

    def _build_config_panel(self, parent: ttk.LabelFrame) -> None:
        fields = [
            ("Photons", ttk.Spinbox(parent, from_=10, to=10000, increment=10, textvariable=self.photon_count_var, width=12)),
            ("Error check %", ttk.Spinbox(parent, from_=0, to=50, increment=1, textvariable=self.error_check_var, width=12)),
            ("Abort threshold %", ttk.Spinbox(parent, from_=1, to=50, increment=1, textvariable=self.error_threshold_var, width=12)),
            ("Channel noise %", ttk.Spinbox(parent, from_=0, to=5, increment=0.5, textvariable=self.channel_noise_var, width=12)),
            ("Seed", ttk.Entry(parent, textvariable=self.seed_var, width=14)),
            ("Playback ms", ttk.Spinbox(parent, from_=20, to=1000, increment=20, textvariable=self.play_delay_var, width=12)),
        ]

        for row, (label_text, widget) in enumerate(fields):
            ttk.Label(parent, text=label_text, style="Header.TLabel").grid(row=row, column=0, sticky="w", pady=(0, 6))
            widget.grid(row=row, column=1, sticky="ew", pady=(0, 10))

        parent.grid_columnconfigure(1, weight=1)

        ttk.Checkbutton(parent, text="Enable Eve intercept-resend attack", variable=self.eve_enabled_var).grid(
            row=len(fields), column=0, columnspan=2, sticky="w", pady=(6, 12)
        )

        button_frame = ttk.Frame(parent)
        button_frame.grid(row=len(fields) + 1, column=0, columnspan=2, sticky="ew", pady=(6, 12))
        button_frame.grid_columnconfigure(0, weight=1)

        ttk.Button(button_frame, text="Run Full Simulation", command=self.run_simulation).grid(
            row=0, column=0, sticky="ew", pady=(0, 8)
        )
        ttk.Button(button_frame, text="Prepare Step Mode", command=self.prepare_step_mode).grid(
            row=1, column=0, sticky="ew", pady=(0, 8)
        )
        ttk.Button(button_frame, text="Play", command=self.play).grid(row=2, column=0, sticky="ew", pady=(0, 8))
        ttk.Button(button_frame, text="Pause", command=self.pause).grid(row=3, column=0, sticky="ew", pady=(0, 8))
        ttk.Button(button_frame, text="Next Photon", command=self.next_step).grid(row=4, column=0, sticky="ew", pady=(0, 8))
        ttk.Button(button_frame, text="Previous Photon", command=self.previous_step).grid(
            row=5, column=0, sticky="ew", pady=(0, 8)
        )
        ttk.Button(button_frame, text="Reset View", command=self.reset_view).grid(row=6, column=0, sticky="ew")

        help_text = (
            "Standard-library only.\n"
            "Quantum states, measurement, Eve, and privacy amplification are all implemented by hand.\n\n"
            "Step mode reveals one photon at a time.\n"
            "Full simulation jumps to the final BB84 outcome."
        )
        ttk.Label(parent, text=help_text, justify="left", wraplength=240).grid(
            row=len(fields) + 2, column=0, columnspan=2, sticky="ew", pady=(8, 0)
        )

    def _build_visual_panel(self, parent: ttk.Frame) -> None:
        visual_frame = ttk.LabelFrame(parent, text="Visualization", padding=12)
        visual_frame.grid(row=0, column=0, sticky="nsew")
        visual_frame.grid_columnconfigure(0, weight=1)
        visual_frame.grid_rowconfigure(0, weight=1)

        self.visual_canvas = tk.Canvas(
            visual_frame,
            width=860,
            height=320,
            background="#ffffff",
            highlightthickness=1,
            highlightbackground="#d6dbe8",
        )
        self.visual_canvas.grid(row=0, column=0, sticky="nsew")
        self.visual_canvas.bind("<Configure>", self._on_visual_canvas_resize)

        phase_frame = ttk.Frame(parent, padding=(0, 10))
        phase_frame.grid(row=1, column=0, sticky="ew")
        for column in range(4):
            phase_frame.grid_columnconfigure(column, weight=1)

        self.phase_labels = {}
        for column, phase_name in enumerate(
            ("Transmission", "Reconciliation", "Error Checking", "Privacy Amplification")
        ):
            label = tk.Label(
                phase_frame,
                text=phase_name,
                font=("Segoe UI", 10, "bold"),
                bd=1,
                relief="solid",
                padx=8,
                pady=8,
            )
            label.grid(row=0, column=column, padx=4, sticky="ew")
            self.phase_labels[phase_name] = label

        detail_frame = ttk.LabelFrame(parent, text="Current Photon Detail", padding=12)
        detail_frame.grid(row=2, column=0, sticky="nsew", pady=(0, 0))
        detail_frame.grid_rowconfigure(3, weight=1)
        detail_frame.grid_columnconfigure(0, weight=1)

        ttk.Label(detail_frame, textvariable=self.current_photon_var, wraplength=860).grid(
            row=0, column=0, sticky="ew", pady=(0, 8)
        )
        ttk.Label(detail_frame, textvariable=self.current_decision_var, wraplength=860).grid(
            row=1, column=0, sticky="ew", pady=(0, 8)
        )
        ttk.Label(detail_frame, textvariable=self.current_measurement_var, wraplength=860).grid(
            row=2, column=0, sticky="ew", pady=(0, 12)
        )

        columns = ("index", "alice", "eve", "bob", "match", "check", "key")
        self.trace_tree = ttk.Treeview(detail_frame, columns=columns, show="headings", height=14, style="Stat.Treeview")
        headings = {
            "index": "#",
            "alice": "Alice",
            "eve": "Eve",
            "bob": "Bob",
            "match": "Basis",
            "check": "Check",
            "key": "Key Flow",
        }
        widths = {
            "index": 54,
            "alice": 170,
            "eve": 170,
            "bob": 170,
            "match": 100,
            "check": 110,
            "key": 130,
        }
        for column in columns:
            self.trace_tree.heading(column, text=headings[column])
            self.trace_tree.column(column, width=widths[column], stretch=column != "index", anchor="center")
        self.trace_tree.grid(row=3, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(detail_frame, orient="vertical", command=self.trace_tree.yview)
        scrollbar.grid(row=3, column=1, sticky="ns")
        self.trace_tree.configure(yscrollcommand=scrollbar.set)

    def _build_summary_panel(self, parent: ttk.LabelFrame) -> None:
        columns = ("metric", "value")
        self.stats_tree = ttk.Treeview(parent, columns=columns, show="headings", height=12, style="Stat.Treeview")
        self.stats_tree.heading("metric", text="Metric")
        self.stats_tree.heading("value", text="Value")
        self.stats_tree.column("metric", width=220, anchor="w")
        self.stats_tree.column("value", width=140, anchor="center")
        self.stats_tree.grid(row=0, column=0, sticky="ew")

        chart_label = ttk.Label(parent, text="Key Evolution and Security Metrics", style="Header.TLabel")
        chart_label.grid(row=1, column=0, sticky="w", pady=(12, 8))

        self.chart_canvas = tk.Canvas(
            parent,
            width=380,
            height=260,
            background="#ffffff",
            highlightthickness=1,
            highlightbackground="#d6dbe8",
        )
        self.chart_canvas.grid(row=2, column=0, sticky="nsew")
        self.chart_canvas.bind("<Configure>", self._on_chart_canvas_resize)

        result_frame = ttk.LabelFrame(parent, text="Result Summary", padding=12)
        result_frame.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        ttk.Label(result_frame, textvariable=self.result_var, justify="left", wraplength=360).grid(
            row=0, column=0, sticky="ew"
        )

    def _read_config(self) -> ProtocolConfig:
        try:
            photon_count = int(self.photon_count_var.get())
            error_check_fraction = float(self.error_check_var.get()) / 100.0
            error_threshold = float(self.error_threshold_var.get()) / 100.0
            channel_noise = float(self.channel_noise_var.get()) / 100.0
            seed_text = self.seed_var.get().strip()
            seed = int(seed_text) if seed_text else None
            return ProtocolConfig(
                photon_count=photon_count,
                error_check_fraction=error_check_fraction,
                error_threshold=error_threshold,
                eve_enabled=bool(self.eve_enabled_var.get()),
                channel_noise=channel_noise,
                seed=seed,
            )
        except ValueError as error:
            raise ValueError(
                "Configuration values must be numeric and within their allowed ranges."
            ) from error

    def run_simulation(self) -> None:
        self.pause()
        try:
            config = self._read_config()
        except ValueError as error:
            messagebox.showerror("Invalid Configuration", str(error))
            return

        result = BB84Protocol(config).run()
        self.current_result = result
        self.current_step = len(result.traces) - 1
        self.status_var.set(
            "Full simulation complete. Review the final key, error rate, and security decision on the right."
        )
        self._refresh_views()

    def prepare_step_mode(self) -> None:
        self.pause()
        try:
            config = self._read_config()
        except ValueError as error:
            messagebox.showerror("Invalid Configuration", str(error))
            return

        result = BB84Protocol(config).run()
        self.current_result = result
        self.current_step = 0
        self.status_var.set(
            "Step mode ready. Use Play or Next Photon to inspect the BB84 exchange one transmission at a time."
        )
        self._refresh_views()

    def play(self) -> None:
        if self.current_result is None:
            self.prepare_step_mode()
            if self.current_result is None:
                return
        if self.play_job is not None:
            return
        self._tick_playback()

    def _tick_playback(self) -> None:
        if self.current_result is None:
            return
        self._refresh_views()
        if self.current_step >= len(self.current_result.traces) - 1:
            self.play_job = None
            self.status_var.set("Reached the end of the photon stream. Final protocol statistics are now visible.")
            return
        self.current_step += 1
        delay = max(20, int(self.play_delay_var.get()))
        self.play_job = self.after(delay, self._tick_playback)

    def pause(self) -> None:
        if self.play_job is not None:
            self.after_cancel(self.play_job)
            self.play_job = None
            self.status_var.set("Playback paused.")

    def next_step(self) -> None:
        self.pause()
        if self.current_result is None:
            self.prepare_step_mode()
            return
        self.current_step = min(self.current_step + 1, len(self.current_result.traces) - 1)
        self.status_var.set("Moved forward by one photon.")
        self._refresh_views()

    def previous_step(self) -> None:
        self.pause()
        if self.current_result is None:
            return
        self.current_step = max(self.current_step - 1, 0)
        self.status_var.set("Moved backward by one photon.")
        self._refresh_views()

    def reset_view(self) -> None:
        self.pause()
        self.current_result = None
        self.current_step = 0
        self.status_var.set("View reset. Configure a new simulation when you are ready.")
        self._refresh_empty_views()

    def _refresh_empty_views(self) -> None:
        self.current_photon_var.set("No simulation loaded.")
        self.current_decision_var.set("Photon decisions will appear here.")
        self.current_measurement_var.set("Measurement details will appear here.")
        self.result_var.set("Final protocol result will appear here.")
        self._set_phase_state(None)
        self._draw_placeholder_canvas()
        self._clear_tree(self.trace_tree)
        self._clear_tree(self.stats_tree)
        self._draw_placeholder_chart()

    def _on_visual_canvas_resize(self, _event: tk.Event) -> None:
        self.after_idle(self._redraw_visual_canvas)

    def _on_chart_canvas_resize(self, _event: tk.Event) -> None:
        self.after_idle(self._redraw_chart_canvas)

    def _redraw_visual_canvas(self) -> None:
        if self.current_result is None:
            self._draw_placeholder_canvas()
            return
        self._draw_visual_canvas(self.current_result.traces[self.current_step])

    def _redraw_chart_canvas(self) -> None:
        if self.current_result is None:
            self._draw_placeholder_chart()
            return
        final_view = self.current_step >= len(self.current_result.traces) - 1
        self._draw_chart(final_view)

    def _canvas_dimensions(self, canvas: tk.Canvas) -> tuple[int, int]:
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        if width <= 1:
            width = int(canvas.cget("width"))
        if height <= 1:
            height = int(canvas.cget("height"))
        return width, height

    def _refresh_views(self) -> None:
        if self.current_result is None:
            self._refresh_empty_views()
            return

        trace = self.current_result.traces[self.current_step]
        final_view = self.current_step >= len(self.current_result.traces) - 1

        self._update_detail_labels(trace, final_view)
        self._set_phase_state(final_view)
        self._draw_visual_canvas(trace)
        self._update_trace_table()
        self._update_stats(final_view)
        self._draw_chart(final_view)
        self._update_result_text(final_view)

    def _update_detail_labels(self, trace: PhotonTrace, final_view: bool) -> None:
        self.current_photon_var.set(
            f"Photon {trace.index + 1}/{len(self.current_result.traces)}: "
            f"Alice encoded bit {trace.alice_bit} in basis {trace.alice_basis} at "
            f"{trace.alice_polarization} deg, and Bob measured bit {trace.bob_bit} in basis {trace.bob_basis}."
        )

        eve_text = "Eve inactive."
        if trace.eve_basis is not None:
            eve_text = (
                f"Eve used basis {trace.eve_basis}, obtained bit {trace.eve_bit}, "
                f"and resent polarization {trace.eve_polarization} deg."
            )
        key_flow = "kept for the sifted key" if trace.basis_match else "discarded during basis reconciliation"
        self.current_decision_var.set(
            f"{eve_text} The bases {'matched' if trace.basis_match else 'did not match'}, so this photon was {key_flow}."
        )

        if trace.basis_match:
            correctness = "correct" if trace.bob_matches_alice else "an error"
            noise_text = " Channel noise flipped the photon." if trace.noise_applied else ""
            self.current_measurement_var.set(
                f"Bob's measurement was {correctness}. "
                f"P(bit=0)={trace.bob_probability_zero:.2f}, P(bit=1)={trace.bob_probability_one:.2f}.{noise_text}"
            )
        else:
            self.current_measurement_var.set(
                f"Because Bob used the other basis, the result is probabilistic. "
                f"P(bit=0)={trace.bob_probability_zero:.2f}, P(bit=1)={trace.bob_probability_one:.2f}."
            )

        if final_view:
            if self.current_result.aborted:
                self.status_var.set("Simulation complete. The protocol aborted because the observed error rate was too high.")
            else:
                self.status_var.set("Simulation complete. Alice and Bob ended with a shared key.")

    def _set_phase_state(self, final_view: Optional[bool]) -> None:
        colors = {
            "pending": "#e7ebf4",
            "active": "#d9e8ff",
            "complete": "#d9f3e5",
        }
        for phase_name, label in self.phase_labels.items():
            if final_view is None:
                state = "pending"
            elif final_view:
                state = "complete"
            else:
                state = "active" if phase_name == "Transmission" else "pending"
            label.configure(background=colors[state])

    def _draw_placeholder_canvas(self) -> None:
        canvas = self.visual_canvas
        canvas.delete("all")
        width, height = self._canvas_dimensions(canvas)
        canvas.create_text(
            width / 2,
            height / 2,
            text="Run a simulation to visualize Alice, Eve, and Bob.",
            fill="#5c6475",
            width=max(180, width - 60),
            justify="center",
            font=("Segoe UI", 14 if width >= 700 else 12, "bold"),
        )

    def _draw_visual_canvas(self, trace: PhotonTrace) -> None:
        canvas = self.visual_canvas
        canvas.delete("all")
        total_width, total_height = self._canvas_dimensions(canvas)
        eve_active = trace.eve_basis is not None
        actor_count = 3 if eve_active else 2
        horizontal_margin = max(24, total_width // 18)
        station_half_width = max(48, min(72, (total_width - (horizontal_margin * 2)) // max(actor_count * 3, 1)))
        station_half_height = max(40, min(48, total_height // 6))
        station_y = max(station_half_height + 14, int(total_height * 0.22))

        left_x = horizontal_margin + station_half_width
        right_x = total_width - horizontal_margin - station_half_width
        positions = {
            "Alice": left_x,
            "Bob": right_x,
        }
        if eve_active:
            positions["Eve"] = total_width // 2

        self._draw_station(
            canvas,
            positions["Alice"],
            station_y,
            station_half_width,
            station_half_height,
            "Alice",
            trace.alice_basis,
            trace.alice_bit,
            trace.alice_polarization,
            "#dbe9ff",
        )
        if eve_active:
            self._draw_station(
                canvas,
                positions["Eve"],
                station_y,
                station_half_width,
                station_half_height,
                "Eve",
                trace.eve_basis,
                trace.eve_bit,
                trace.eve_polarization,
                "#ffe7cc",
            )
        self._draw_station(
            canvas,
            positions["Bob"],
            station_y,
            station_half_width,
            station_half_height,
            "Bob",
            trace.bob_basis,
            trace.bob_bit,
            trace.delivered_polarization,
            "#ddf5e6",
        )

        route_y = min(max(station_y + station_half_height + 28, int(total_height * 0.58)), total_height - 110)
        if eve_active:
            self._draw_link(
                canvas,
                positions["Alice"] + station_half_width,
                route_y,
                positions["Eve"] - station_half_width,
                route_y,
                "#5b7fd5",
            )
            self._draw_link(
                canvas,
                positions["Eve"] + station_half_width,
                route_y,
                positions["Bob"] - station_half_width,
                route_y,
                "#5b7fd5",
            )
            photon_x = int((positions["Eve"] + positions["Bob"]) / 2)
        else:
            self._draw_link(
                canvas,
                positions["Alice"] + station_half_width,
                route_y,
                positions["Bob"] - station_half_width,
                route_y,
                "#5b7fd5",
            )
            photon_x = total_width // 2

        photon_radius = 10 if total_height >= 300 else 8
        canvas.create_oval(
            photon_x - photon_radius,
            route_y - photon_radius,
            photon_x + photon_radius,
            route_y + photon_radius,
            fill="#6b50c7",
            outline="",
        )
        delivered_y = min(route_y + 28, total_height - 82)
        canvas.create_text(
            total_width / 2,
            delivered_y,
            text=f"Delivered polarization: {trace.delivered_polarization} deg",
            font=("Segoe UI", 10 if total_width >= 700 else 9),
            fill="#364056",
        )

        if trace.basis_match:
            match_fill = "#d8f1df" if trace.bob_matches_alice else "#ffe0dd"
            match_text = "Bases match: kept" if trace.bob_matches_alice else "Bases match: sifted error observed"
        else:
            match_fill = "#eceff6"
            match_text = "Bases differ: photon discarded"
        match_box_width = max(180, min(total_width - 48, int(total_width * 0.56)))
        match_y1 = min(delivered_y + 18, total_height - 52)
        match_y2 = min(match_y1 + 30, total_height - 18)
        match_x1 = (total_width - match_box_width) / 2
        match_x2 = match_x1 + match_box_width
        canvas.create_rectangle(match_x1, match_y1, match_x2, match_y2, fill=match_fill, outline="")
        canvas.create_text(
            total_width / 2,
            (match_y1 + match_y2) / 2,
            text=match_text,
            font=("Segoe UI", 10 if total_width >= 700 else 9, "bold"),
            fill="#243145",
            width=max(140, match_box_width - 20),
        )

        if trace.noise_applied:
            noise_y = min(match_y2 + 18, total_height - 30)
            canvas.create_text(
                total_width / 2,
                noise_y,
                text="Channel noise was applied to this photon.",
                font=("Segoe UI", 10 if total_width >= 700 else 9),
                fill="#a34f31",
            )

        window = list(_trace_window(trace.index, len(self.current_result.traces), window_size=24))
        gap = 4
        available_width = max(120, total_width - 40)
        box_width = max(10, min(28, (available_width - (gap * (max(len(window), 1) - 1))) // max(len(window), 1)))
        box_height = 16 if total_height >= 300 else 14
        strip_width = (len(window) * box_width) + ((len(window) - 1) * gap)
        start_x = max(20, int((total_width - strip_width) / 2))
        base_y = total_height - box_height - 12
        for offset, trace_index in enumerate(window):
            item = self.current_result.traces[trace_index]
            x1 = start_x + (offset * (box_width + gap))
            x2 = x1 + box_width
            fill = "#eceff6"
            if item.basis_match and item.bob_matches_alice:
                fill = "#bde6c7"
            elif item.basis_match and not item.bob_matches_alice:
                fill = "#f4b5ae"
            if trace_index == trace.index:
                canvas.create_rectangle(
                    x1 - 2,
                    base_y - 2,
                    x2 + 2,
                    base_y + box_height + 2,
                    outline="#243145",
                    width=2,
                )
            canvas.create_rectangle(x1, base_y, x2, base_y + box_height, fill=fill, outline="")

    def _draw_station(
        self,
        canvas: tk.Canvas,
        x: int,
        y: int,
        half_width: int,
        half_height: int,
        title: str,
        basis: Optional[str],
        bit: Optional[int],
        polarization: Optional[int],
        fill: str,
    ) -> None:
        title_font = ("Segoe UI", 11 if half_width >= 64 else 10, "bold")
        body_font = ("Segoe UI", 10 if half_width >= 64 else 9)
        canvas.create_rectangle(x - half_width, y - half_height, x + half_width, y + half_height, fill=fill, outline="#bcc7da", width=1)
        canvas.create_text(x, y - int(half_height * 0.5), text=title, font=title_font, fill="#243145")
        canvas.create_text(x, y - 4, text=f"Basis: {_format_basis(basis)}", font=body_font, fill="#243145")
        bit_text = "-" if bit is None else str(bit)
        pol_text = "-" if polarization is None else f"{polarization} deg"
        canvas.create_text(x, y + int(half_height * 0.1), text=f"Bit: {bit_text}", font=body_font, fill="#243145")
        canvas.create_text(x, y + int(half_height * 0.5), text=pol_text, font=body_font, fill="#243145")
        if polarization is not None:
            glyph_center_x = x + half_width - 26
            glyph_center_y = y - int(half_height * 0.32)
            self._draw_polarization_glyph(canvas, glyph_center_x, glyph_center_y, polarization)

    def _draw_polarization_glyph(self, canvas: tk.Canvas, center_x: int, center_y: int, angle: int) -> None:
        radius = 14
        radians = math.radians(angle)
        dx = math.cos(radians) * radius
        dy = math.sin(radians) * radius
        canvas.create_oval(center_x - 16, center_y - 16, center_x + 16, center_y + 16, outline="#bbc6d8")
        canvas.create_line(center_x - dx, center_y + dy, center_x + dx, center_y - dy, fill="#243145", width=2)

    def _draw_link(self, canvas: tk.Canvas, x1: int, y1: int, x2: int, y2: int, color: str) -> None:
        canvas.create_line(x1, y1, x2, y2, fill=color, width=3, arrow=tk.LAST)

    def _update_trace_table(self) -> None:
        if self.current_result is None:
            self._clear_tree(self.trace_tree)
            return
        self._clear_tree(self.trace_tree)
        for trace_index in _trace_window(self.current_step, len(self.current_result.traces)):
            trace = self.current_result.traces[trace_index]
            eve_value = "-"
            if trace.eve_basis is not None:
                eve_value = f"{trace.eve_bit} @ {trace.eve_basis} / {trace.eve_polarization} deg"
            match_value = "Keep" if trace.basis_match else "Discard"
            check_value = "-"
            if trace.sampled_for_error_check:
                check_value = "Error" if trace.sample_mismatch else "Clean"
            key_value = "-"
            if trace.retained_after_error_check:
                key_value = "Post-check"
            if self.current_step >= len(self.current_result.traces) - 1 and trace.retained_after_error_check:
                key_value = "Feeds privacy"

            values = (
                trace.index + 1,
                f"{trace.alice_bit} @ {trace.alice_basis} / {trace.alice_polarization} deg",
                eve_value,
                f"{trace.bob_bit} @ {trace.bob_basis}",
                match_value,
                check_value,
                key_value,
            )
            self.trace_tree.insert("", "end", values=values)

    def _update_stats(self, final_view: bool) -> None:
        if self.current_result is None:
            self._clear_tree(self.stats_tree)
            return

        self._clear_tree(self.stats_tree)
        if final_view:
            metrics = [
                ("Photons transmitted", str(self.current_result.stats.total_photons)),
                ("Basis match rate", _format_percent(self.current_result.stats.basis_match_rate)),
                ("Sifted key length", str(self.current_result.stats.sifted_key_length)),
                ("Error-check sample", str(self.current_result.stats.error_check_sample_size)),
                ("Observed error rate", _format_percent(self.current_result.stats.error_rate)),
                ("Corrected residual errors", str(self.current_result.stats.corrected_remaining_errors)),
                ("Final key length", str(self.current_result.stats.final_key_length)),
                ("Efficiency", _format_percent(self.current_result.stats.efficiency)),
                ("Channel noise events", str(self.current_result.stats.channel_noise_events)),
            ]
            if self.current_result.config.eve_enabled:
                metrics.extend(
                    [
                        ("Eve basis match rate", _format_percent(self.current_result.stats.eve_basis_match_rate)),
                        ("Eve exact sifted bits", str(self.current_result.stats.eve_exact_sifted_bits)),
                        ("Eve exact final bits", str(self.current_result.stats.eve_exact_final_bits)),
                    ]
                )
            metrics.append(("Security status", self.current_result.stats.security_status))
        else:
            processed = self.current_step + 1
            subset: List[PhotonTrace] = self.current_result.traces[:processed]
            provisional_matches = sum(1 for trace in subset if trace.basis_match)
            provisional_errors = sum(1 for trace in subset if trace.basis_match and not trace.bob_matches_alice)
            noise_events = sum(1 for trace in subset if trace.noise_applied)
            metrics = [
                ("Processed photons", f"{processed}/{len(self.current_result.traces)}"),
                ("Current basis matches", str(provisional_matches)),
                ("Match rate so far", _format_percent(provisional_matches / processed)),
                ("Errors on kept photons", str(provisional_errors)),
                ("Noise events so far", str(noise_events)),
                ("Error-check sample", "Pending"),
                ("Final key", "Pending"),
                ("Security status", "In progress"),
            ]
        for metric, value in metrics:
            self.stats_tree.insert("", "end", values=(metric, value))

    def _draw_placeholder_chart(self) -> None:
        canvas = self.chart_canvas
        canvas.delete("all")
        width, height = self._canvas_dimensions(canvas)
        canvas.create_text(
            width / 2,
            height / 2,
            text="Charts appear after a simulation run.",
            fill="#5c6475",
            width=max(160, width - 40),
            justify="center",
            font=("Segoe UI", 12 if width >= 320 else 11, "bold"),
        )

    def _draw_chart(self, final_view: bool) -> None:
        canvas = self.chart_canvas
        canvas.delete("all")
        if self.current_result is None:
            self._draw_placeholder_chart()
            return

        if final_view:
            entries = [
                ("Initial", self.current_result.config.photon_count, self.current_result.config.photon_count, "#8bb8ff"),
                ("Sifted", self.current_result.stats.sifted_key_length, self.current_result.config.photon_count, "#7cd3b2"),
                ("Checked", self.current_result.stats.error_check_sample_size, self.current_result.config.photon_count, "#f4c47a"),
                ("Final", self.current_result.stats.final_key_length, self.current_result.config.photon_count, "#9b80e3"),
            ]
            y = 26
            for label, value, maximum, color in entries:
                self._draw_bar(canvas, 18, y, 230, label, value, maximum, color, str(value))
                y += 42

            rate_entries = [
                ("Basis match", self.current_result.stats.basis_match_rate, "#4b88ff"),
                ("Error rate", self.current_result.stats.error_rate, "#e56b5d"),
                ("Efficiency", self.current_result.stats.efficiency, "#5cbf91"),
            ]
            if self.current_result.config.eve_enabled:
                rate_entries.append(
                    ("Eve basis match", self.current_result.stats.eve_basis_match_rate, "#c6803a")
                )
            y = 198
            for label, value, color in rate_entries:
                self._draw_bar(canvas, 18, y, 230, label, value, 1.0, color, _format_percent(value))
                y += 42
        else:
            processed = self.current_step + 1
            subset: List[PhotonTrace] = self.current_result.traces[:processed]
            basis_matches = sum(1 for trace in subset if trace.basis_match)
            kept_errors = sum(1 for trace in subset if trace.basis_match and not trace.bob_matches_alice)
            noise_events = sum(1 for trace in subset if trace.noise_applied)
            entries = [
                ("Processed", processed, self.current_result.config.photon_count, "#8bb8ff"),
                ("Matches", basis_matches, self.current_result.config.photon_count, "#7cd3b2"),
                ("Kept errors", kept_errors, max(1, processed), "#e56b5d"),
                ("Noise", noise_events, self.current_result.config.photon_count, "#f4c47a"),
            ]
            y = 40
            for label, value, maximum, color in entries:
                self._draw_bar(canvas, 18, y, 230, label, value, maximum, color, str(value))
                y += 52
            canvas.create_text(
                190,
                234,
                text="Final key and protocol decision unlock after the last photon.",
                fill="#44506a",
                font=("Segoe UI", 10),
            )

    def _draw_bar(
        self,
        canvas: tk.Canvas,
        x: int,
        y: int,
        width: int,
        label: str,
        value: float,
        maximum: float,
        color: str,
        text_value: str,
    ) -> None:
        canvas_width, _canvas_height = self._canvas_dimensions(canvas)
        width = min(width, max(90, canvas_width - x - 90))
        canvas.create_text(x, y - 6, text=label, anchor="w", font=("Segoe UI", 10, "bold"), fill="#243145")
        canvas.create_rectangle(x, y + 6, x + width, y + 24, fill="#edf1f8", outline="")
        fill_width = 0 if maximum <= 0 else int((value / maximum) * width)
        fill_width = max(0, min(width, fill_width))
        canvas.create_rectangle(x, y + 6, x + fill_width, y + 24, fill=color, outline="")
        canvas.create_text(x + width + 12, y + 15, text=text_value, anchor="w", font=("Consolas", 10), fill="#243145")

    def _update_result_text(self, final_view: bool) -> None:
        if self.current_result is None:
            self.result_var.set("Final protocol result will appear here.")
            return
        if not final_view:
            self.result_var.set(
                "Transmission is still in progress.\n\n"
                "Step through the photons to see how basis choices, Eve, and channel noise shape the sifted key."
            )
            return

        status = "SUCCESS" if self.current_result.success else "ABORT"
        final_key = self.current_result.final_key_preview or "(empty)"
        summary = [
            f"Status: {status}",
            f"Security decision: {self.current_result.stats.security_status}",
            f"Displayed shared key (first 64 bits): {final_key}",
        ]
        if self.current_result.abort_reason:
            summary.append(f"Note: {self.current_result.abort_reason}")
        if self.current_result.config.eve_enabled:
            summary.append(
                "Eve exact knowledge before/after privacy amplification: "
                f"{self.current_result.stats.eve_exact_sifted_bits} -> {self.current_result.stats.eve_exact_final_bits}"
            )
        self.result_var.set("\n\n".join(summary))

    def _clear_tree(self, tree: ttk.Treeview) -> None:
        tree.delete(*tree.get_children())


__all__ = ["BB84App", "run_app"]
