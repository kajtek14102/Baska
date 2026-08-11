"""
game_events.py

Zdarzenia partii i listenery (np. konsolowy narrator).
Ścieżka treningowa: run_game bez listenerów — zero alokacji eventów.
"""

from __future__ import annotations
from abc import ABC
from dataclasses import dataclass
from typing import Sequence

from baska_engine import card_str


# ---------------------------------------------------------------------------
# Eventy
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DealEvent:
    hands: dict[int, tuple[tuple[str, str], ...]]
    starzy: tuple[int, ...]
    mlodzi: tuple[int, ...]
    first_player: int
    agent_labels: dict[int, str]


@dataclass(frozen=True)
class PlayEvent:
    player_id: int
    card: tuple[str, str]
    trick_num: int
    position: int


@dataclass(frozen=True)
class TrickEndEvent:
    trick_num: int
    winner: int
    scores: dict[int, int]


@dataclass(frozen=True)
class GameEndEvent:
    result: dict


@dataclass(frozen=True)
class SeriesGameStartEvent:
    game_index: int  # 1-based
    n: int


# ---------------------------------------------------------------------------
# Listener
# ---------------------------------------------------------------------------

class GameListener(ABC):
    """Bazowy listener — domyślnie no-op. Nadpisz tylko to, czego potrzebujesz."""

    def on_deal(self, event: DealEvent) -> None:
        pass

    def on_play(self, event: PlayEvent) -> None:
        pass

    def on_trick_end(self, event: TrickEndEvent) -> None:
        pass

    def on_game_end(self, event: GameEndEvent) -> None:
        pass

    def on_series_game_start(self, event: SeriesGameStartEvent) -> None:
        pass


def notify(listeners: Sequence[GameListener], method: str, event) -> None:
    """Wywołaj metodę na wszystkich listenerach. Nie wołaj gdy listeners jest puste."""
    for listener in listeners:
        getattr(listener, method)(event)


# ---------------------------------------------------------------------------
# Narrator konsolowy
# ---------------------------------------------------------------------------

class ConsoleNarrator(GameListener):
    """
    Drukuje przebieg partii na stdout.

    reveal_private=False — bez rąk i drużyn przy rozdaniu (gra z człowiekiem).
    """

    def __init__(self, reveal_private: bool = True):
        self.reveal_private = reveal_private

    def on_series_game_start(self, event: SeriesGameStartEvent) -> None:
        print(f"\n{'=' * 40}")
        print(f"  GRA {event.game_index}/{event.n}")
        print(f"{'=' * 40}")

    def on_deal(self, event: DealEvent) -> None:
        print("=== Rozdanie ===")
        if self.reveal_private:
            for p in range(4):
                hand = [card_str(c) for c in event.hands[p]]
                label = event.agent_labels.get(p, "")
                suffix = f" ({label})" if label else ""
                print(f"  Gracz {p}{suffix}: {hand}")
            print(f"\n  Starzy: {list(event.starzy)}  |  Młodzi: {list(event.mlodzi)}")
        print(f"  Zaczyna: Gracz {event.first_player}\n")

    def on_play(self, event: PlayEvent) -> None:
        print(
            f"  Bitka {event.trick_num}, poz. {event.position}: "
            f"Gracz {event.player_id} gra {card_str(event.card)}"
        )

    def on_trick_end(self, event: TrickEndEvent) -> None:
        print(
            f"  → Bitkę wygrywa Gracz {event.winner} "
            f"| punkty: {dict(event.scores)}\n"
        )

    def on_game_end(self, event: GameEndEvent) -> None:
        r = event.result
        print("=== Wynik ===")
        print(f"  Starzy {r['starzy']}: {r['pts_starzy']} pkt")
        print(f"  Młodzi {r['mlodzi']}: {r['pts_mlodzi']} pkt")
        print(f"  Zwycięzcy: {r['winners']}  |  Kategoria: {r['category']}")
        print(f"  Score: {r['score']}")
