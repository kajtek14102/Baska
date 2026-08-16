"""
runner_gui.py

Proste okno do run_many_games: 4 agenty, liczba gier, żywe średnie, pasek postępu.
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import ttk

from game_runner import list_agent_names, make_agents, run_many_games

PIMC_SAMPLE_CHOICES = ("32", "64", "128", "256", "512", "1024")


def _is_pimc_name(name: str) -> bool:
    base = name.strip().replace(":", "-").split("-")[0]
    return base.lower().removesuffix("agent") == "pimc"


def main() -> None:
    agent_names = list_agent_names()
    default = "Random" if "Random" in agent_names else agent_names[0]

    root = tk.Tk()
    root.title("Baśka runner")
    root.minsize(420, 260)
    root.geometry("620x340")

    q: queue.Queue = queue.Queue()
    running = {"on": False}
    font_px = [0]
    style = ttk.Style(root)

    player_vars: list[tk.StringVar] = []
    sample_vars: list[tk.StringVar] = []
    sample_boxes: list[ttk.Combobox] = []
    avg_labels: list[tk.Label] = []
    font_widgets: list[tk.Widget] = []
    menus: list[tk.Menu] = []

    def add_font(w: tk.Widget) -> tk.Widget:
        font_widgets.append(w)
        return w

    def sync_sample_states(*_args) -> None:
        for i, box in enumerate(sample_boxes):
            on = _is_pimc_name(player_vars[i].get())
            box.configure(state="normal" if on else "disabled")

    for i in range(4):
        row = tk.Frame(root)
        row.pack(fill="x", padx=6, pady=2)
        add_font(tk.Label(row, text=f"Gracz {i}")).pack(side="left")
        var = tk.StringVar(value=default)
        om = add_font(tk.OptionMenu(row, var, *agent_names, command=sync_sample_states))
        om.pack(side="left", fill="x", expand=True, padx=6)
        menus.append(om["menu"])
        avg = add_font(tk.Label(row, text="—", width=10, anchor="e"))
        avg.pack(side="right")
        svar = tk.StringVar(value="128")
        box = ttk.Combobox(
            row,
            textvariable=svar,
            values=PIMC_SAMPLE_CHOICES,
            width=6,
        )
        box.pack(side="right", padx=4)
        add_font(box)
        add_font(tk.Label(row, text="n")).pack(side="right")
        player_vars.append(var)
        sample_vars.append(svar)
        sample_boxes.append(box)
        avg_labels.append(avg)

    sync_sample_states()

    add_font(tk.Label(
        root,
        text="n — próbki PIMC (wpisz albo wybierz). Oracle zna wszystkie ręce.",
        anchor="w",
    )).pack(fill="x", padx=6, pady=(4, 0))

    n_row = tk.Frame(root)
    n_row.pack(fill="x", padx=6, pady=2)
    add_font(tk.Label(n_row, text="Liczba gier")).pack(side="left")
    n_var = tk.StringVar(value="10000")
    add_font(tk.Entry(n_row, textvariable=n_var)).pack(
        side="left", fill="x", expand=True, padx=6
    )

    status = add_font(tk.Label(root, text="", anchor="w"))
    status.pack(fill="x", padx=6)

    bar = ttk.Progressbar(root, mode="determinate")
    bar.pack(fill="x", padx=6, pady=4)

    def set_running(on: bool) -> None:
        running["on"] = on
        start_btn.config(state="disabled" if on else "normal")

    def start() -> None:
        if running["on"]:
            return
        raw = n_var.get().strip().replace("_", "").replace(" ", "")
        try:
            n = int(raw)
        except ValueError:
            status.config(text="Liczba gier musi być liczbą całkowitą")
            return
        if n <= 0:
            status.config(text="Liczba gier musi być > 0")
            return

        names = [v.get() for v in player_vars]
        samples: list[int] = []
        for i, name in enumerate(names):
            if not _is_pimc_name(name):
                samples.append(128)
                continue
            raw_s = sample_vars[i].get().strip().replace("_", "").replace(" ", "")
            try:
                ns = int(raw_s)
            except ValueError:
                status.config(text=f"Gracz {i}: n PIMC musi być liczbą całkowitą")
                return
            if ns < 1:
                status.config(text=f"Gracz {i}: n PIMC musi być ≥ 1")
                return
            samples.append(ns)

        for lbl in avg_labels:
            lbl.config(text="—")
        bar.config(maximum=n, value=0)
        status.config(text="")
        set_running(True)

        def worker() -> None:
            try:
                agents = make_agents(names, pimc_samples=samples)

                def on_progress(done: int, total: int, stats: dict) -> None:
                    q.put(("progress", done, total, stats["avg_score"]))

                run_many_games(agents, n=n, on_progress=on_progress)
                q.put(("done",))
            except Exception as e:
                q.put(("error", str(e)))

        threading.Thread(target=worker, daemon=True).start()

    start_btn = add_font(tk.Button(root, text="Start", command=start))
    start_btn.pack(fill="x", padx=6, pady=6)

    def apply_font(px: int) -> None:
        font = ("Segoe UI", px)
        for w in font_widgets:
            try:
                w.configure(font=font)
            except tk.TclError:
                pass
        for menu in menus:
            menu.configure(font=font)
        style.configure("TProgressbar", thickness=max(10, int(px * 1.8)))

    def on_resize(event: tk.Event) -> None:
        if event.widget is not root:
            return
        px = max(10, min(36, min(event.width // 36, event.height // 18)))
        if px == font_px[0]:
            return
        font_px[0] = px
        apply_font(px)

    root.bind("<Configure>", on_resize)

    def poll() -> None:
        try:
            while True:
                item = q.get_nowait()
                kind = item[0]
                if kind == "progress":
                    _, done, total, avg = item
                    bar.config(maximum=total, value=done)
                    for p in range(4):
                        avg_labels[p].config(text=f"{avg[p]:+.3f}")
                elif kind == "done":
                    set_running(False)
                elif kind == "error":
                    status.config(text=item[1])
                    set_running(False)
        except queue.Empty:
            pass
        root.after(50, poll)

    root.after(50, poll)
    root.mainloop()


if __name__ == "__main__":
    main()
