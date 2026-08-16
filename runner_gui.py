"""
runner_gui.py

Proste okno do run_many_games: 4 agenty, liczba gier, żywe średnie, pasek postępu.
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import ttk

from game_runner import _fmt_duration, list_agent_names, make_agents, run_many_games
from run_log import RunLog

PIMC_SAMPLE_CHOICES = ("32", "64", "128", "256", "512", "1024")


def _is_pimc_name(name: str) -> bool:
    base = name.strip().replace(":", "-").split("-")[0]
    return base.lower().removesuffix("agent") == "pimc"


def main() -> None:
    agent_names = list_agent_names()
    default = "Random" if "Random" in agent_names else agent_names[0]

    root = tk.Tk()
    root.title("Baśka runner")
    root.minsize(480, 240)
    root.geometry("560x280")

    q: queue.Queue = queue.Queue()
    running = {"on": False, "stop": threading.Event()}
    font_px = [0]
    style = ttk.Style(root)
    btns: dict[str, tk.Button] = {}

    player_vars: list[tk.StringVar] = []
    sample_vars: list[tk.StringVar] = []
    sample_boxes: list[ttk.Combobox] = []
    avg_labels: list[tk.Label] = []
    font_widgets: list[tk.Widget] = []

    def add_font(w: tk.Widget) -> tk.Widget:
        font_widgets.append(w)
        return w

    def sync_sample_states(*_args) -> None:
        for i, box in enumerate(sample_boxes):
            on = _is_pimc_name(player_vars[i].get())
            box.configure(state="normal" if on else "disabled")

    root.columnconfigure(1, weight=1)

    for i in range(4):
        add_font(tk.Label(root, text=f"Gracz {i}")).grid(
            row=i, column=0, sticky="w", padx=(10, 6), pady=3,
        )
        var = tk.StringVar(value=default)
        agent_box = ttk.Combobox(
            root,
            textvariable=var,
            values=agent_names,
            state="readonly",
        )
        agent_box.grid(row=i, column=1, sticky="ew", padx=4, pady=3)
        agent_box.bind("<<ComboboxSelected>>", sync_sample_states)
        add_font(agent_box)

        svar = tk.StringVar(value="128")
        samp = ttk.Combobox(
            root,
            textvariable=svar,
            values=PIMC_SAMPLE_CHOICES,
            width=6,
        )
        samp.grid(row=i, column=2, padx=4, pady=3)
        add_font(samp)

        avg = add_font(tk.Label(root, text="—", width=8, anchor="e"))
        avg.grid(row=i, column=3, sticky="e", padx=(4, 10), pady=3)

        player_vars.append(var)
        sample_vars.append(svar)
        sample_boxes.append(samp)
        avg_labels.append(avg)

    sync_sample_states()

    n_row = tk.Frame(root)
    n_row.grid(row=4, column=0, columnspan=4, sticky="ew", padx=10, pady=(8, 2))
    n_row.columnconfigure(1, weight=1)
    add_font(tk.Label(n_row, text="Liczba gier")).grid(row=0, column=0, sticky="w")
    n_var = tk.StringVar(value="10000")
    add_font(tk.Entry(n_row, textvariable=n_var)).grid(
        row=0, column=1, sticky="ew", padx=8,
    )
    save_var = tk.BooleanVar(value=True)
    add_font(tk.Checkbutton(
        n_row,
        text="Save output",
        variable=save_var,
        onvalue=True,
        offvalue=False,
    )).grid(row=0, column=2, sticky="e")

    status = add_font(tk.Label(root, text="", anchor="w"))
    status.grid(row=5, column=0, columnspan=4, sticky="ew", padx=10)

    bar = ttk.Progressbar(root, mode="determinate")
    bar.grid(row=6, column=0, columnspan=4, sticky="ew", padx=10, pady=4)

    def set_running(on: bool) -> None:
        running["on"] = on
        btns["start"].config(state="disabled" if on else "normal")
        btns["stop"].config(state="normal" if on else "disabled")

    def stop() -> None:
        if not running["on"]:
            return
        running["stop"].set()
        btns["stop"].config(state="disabled")
        status.config(text="Zatrzymywanie po bieżącej partii...")

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

        save = bool(save_var.get())

        for lbl in avg_labels:
            lbl.config(text="—")
        bar.config(maximum=n, value=0)
        status.config(text="")
        running["stop"] = threading.Event()
        set_running(True)

        def worker() -> None:
            log: RunLog | None = None
            try:
                agents = make_agents(names, pimc_samples=samples)
                if save:
                    log = RunLog.create(
                        agent_names=names,
                        pimc_samples=samples,
                        n=n,
                        agent_reprs=[repr(agents[p]) for p in range(4)],
                    )

                def on_progress(done: int, total: int, stats: dict) -> None:
                    q.put(("progress", done, total, stats))

                def on_game(game_index: int, result: dict) -> None:
                    if log is not None:
                        log.write_game(game_index, result)

                stats = run_many_games(
                    agents,
                    n=n,
                    on_progress=on_progress,
                    on_game=on_game if save else None,
                    should_stop=running["stop"].is_set,
                )
                if log is not None:
                    log.write_summary(stats, played=stats["n"])
                q.put(("done", stats))
            except Exception as e:
                if log is not None:
                    try:
                        log.write_error(str(e))
                    except Exception:
                        pass
                q.put(("error", str(e)))
            finally:
                if log is not None:
                    log.close()

        threading.Thread(target=worker, daemon=True).start()

    btn_row = tk.Frame(root)
    btn_row.grid(row=7, column=0, columnspan=4, sticky="ew", padx=10, pady=(4, 10))
    btn_row.columnconfigure(0, weight=1)
    btn_row.columnconfigure(1, weight=1)
    btns["start"] = add_font(tk.Button(btn_row, text="Start", command=start))
    btns["start"].grid(row=0, column=0, sticky="ew", padx=(0, 4))
    btns["stop"] = add_font(tk.Button(btn_row, text="Stop", command=stop, state="disabled"))
    btns["stop"].grid(row=0, column=1, sticky="ew", padx=(4, 0))

    def apply_font(px: int) -> None:
        font = ("Segoe UI", px)
        for w in font_widgets:
            try:
                w.configure(font=font)
            except tk.TclError:
                pass
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
                    _, done, total, stats = item
                    bar.config(maximum=total, value=done)
                    avg = stats["avg_score"]
                    for p in range(4):
                        avg_labels[p].config(text=f"{avg[p]:+.3f}")
                    extra = stats.get("eta_text") or ""
                    status.config(text=f"{done}/{total}  {extra}".rstrip())
                elif kind == "done":
                    stats = item[1] if len(item) > 1 else {}
                    set_running(False)
                    played = stats.get("n", 0)
                    total = stats.get("requested_n", played)
                    extra = stats.get("eta_text") or ""
                    if "elapsed_s" in stats:
                        kind_txt = "zatrzymano" if stats.get("stopped") else "koniec"
                        extra = (
                            f"{kind_txt}  czas {_fmt_duration(stats['elapsed_s'])}"
                        )
                    if played:
                        bar.config(maximum=total, value=played)
                        avg = stats.get("avg_score", {})
                        for p in range(4):
                            if p in avg:
                                avg_labels[p].config(text=f"{avg[p]:+.3f}")
                    status.config(text=f"{played}/{total}  {extra}".rstrip())
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
