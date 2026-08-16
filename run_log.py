"""
Zapis serii gier do JSONL (jedna linia = jeden rekord).

Każda partia jest dopisywana i spłukiwana od razu — przerwany bieg
nadal ma wszystkie skończone rozdania.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence, TextIO

RUNS_DIR = Path(__file__).resolve().parent / "runs"


def _slug(text: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "", text)
    return s[:24] or "agent"


def run_filename(agent_names: Sequence[str], pimc_samples: Sequence[int]) -> str:
    parts = []
    for i, name in enumerate(agent_names):
        base = name.strip().replace(":", "-").split("-")[0]
        if base.lower().removesuffix("agent") == "pimc":
            parts.append(f"PIMC{pimc_samples[i]}")
        else:
            parts.append(_slug(base))
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{stamp}_{'_'.join(parts)}.jsonl"


def game_record(game_index: int, result: dict) -> dict[str, Any]:
    return {
        "type": "game",
        "i": game_index,
        "score": [result["score"][p] for p in range(4)],
        "winners": list(result["winners"]),
        "starzy": list(result["starzy"]),
        "mlodzi": list(result["mlodzi"]),
        "pts_starzy": result["pts_starzy"],
        "pts_mlodzi": result["pts_mlodzi"],
        "category": result["category"],
        "base_value": result["base_value"],
        "table": list(result["table"]) if "table" in result else [0, 1, 2, 3],
    }


class RunLog:
    def __init__(self, path: Path, fh: TextIO):
        self.path = path
        self._fh = fh
        self._started = datetime.now()

    @classmethod
    def create(
        cls,
        agent_names: Sequence[str],
        pimc_samples: Sequence[int],
        n: int,
        agent_reprs: Sequence[str],
    ) -> "RunLog":
        RUNS_DIR.mkdir(parents=True, exist_ok=True)
        path = RUNS_DIR / run_filename(agent_names, pimc_samples)
        fh = path.open("w", encoding="utf-8", newline="\n")
        log = cls(path, fh)
        log._write({
            "type": "meta",
            "started": log._started.isoformat(timespec="seconds"),
            "n": n,
            "agents": list(agent_names),
            "agent_reprs": list(agent_reprs),
            "pimc_samples": list(pimc_samples),
        })
        return log

    def write_game(self, game_index: int, result: dict) -> None:
        self._write(game_record(game_index, result))

    def write_summary(self, stats: dict, played: int) -> None:
        finished = datetime.now()
        elapsed_s = (finished - self._started).total_seconds()
        self._write({
            "type": "summary",
            "finished": finished.isoformat(timespec="seconds"),
            "played": played,
            "avg_score": [stats["avg_score"][p] for p in range(4)],
            "total_score": [stats["total_score"][p] for p in range(4)],
            "wins": [stats["wins"][p] for p in range(4)],
            "elapsed_s": round(elapsed_s, 3),
            "s_per_deal": round(elapsed_s / played, 6) if played else None,
        })

    def write_error(self, message: str) -> None:
        elapsed_s = (datetime.now() - self._started).total_seconds()
        self._write({
            "type": "error",
            "message": message,
            "elapsed_s": round(elapsed_s, 3),
        })

    def close(self) -> None:
        if self._fh.closed:
            return
        self._fh.close()

    def _write(self, obj: dict) -> None:
        self._fh.write(json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n")
        self._fh.flush()
