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


def main() -> None:
    agent_names = list_agent_names()
    default = "Random" if "Random" in agent_names else agent_names[0]

    root = tk.Tk()
    root.title("Baśka runner")
    root.minsize(360, 220)
    root.geometry("520x300")

    q: queue.Queue = queue.Queue()
    running = {"on": False}
    font_px = [0]
    style = ttk.Style(root)

    player_vars: list[tk.StringVar] = []
    avg_labels: list[tk.Label] = []
    font_widgets: list[tk.Widget] = []
    menus: list[tk.Menu] = []

    def add_font(w: tk.Widget) -> tk.Widget:
        font_widgets.append(w)
        return w

    for i in range(4):
        row = tk.Frame(root)
        row.pack(fill="x", padx=6, pady=2)
        add_font(tk.Label(row, text=f"Gracz {i}")).pack(side="left")
        var = tk.StringVar(value=default)
        om = add_font(tk.OptionMenu(row, var, *agent_names))
        om.pack(side="left", fill="x", expand=True, padx=6)
        menus.append(om["menu"])
        avg = add_font(tk.Label(row, text="—", width=10, anchor="e"))
        avg.pack(side="right")
        player_vars.append(var)
        avg_labels.append(avg)

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
        for lbl in avg_labels:
            lbl.config(text="—")
        bar.config(maximum=n, value=0)
        status.config(text="")
        set_running(True)

        def worker() -> None:
            try:
                agents = make_agents(names)

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
            w.configure(font=font)
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
