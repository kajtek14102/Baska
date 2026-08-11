"""
human_agent.py

Agent sterowany przez człowieka z poziomu konsoli.
Tylko UI własnej tury: ręka, legalne ruchy, bieżąca bitka, h/p.
Przebieg partii i wynik drukuje ConsoleNarrator (game_events), nie ten agent.
"""

from __future__ import annotations

from agent_base import Agent
from observation import Observation
from baska_engine import card_str

W = 46  # szerokość ramki


def _line(char: str = "─") -> None:
    print(char * W)


def _trick_row(trick_dict: dict[int, tuple[str, str]]) -> None:
    """Wyświetla sloty graczy 0-3."""
    slots = []
    for p in range(4):
        if p in trick_dict:
            cell = f"{p}:{card_str(trick_dict[p]):<4}"
        else:
            cell = f"{p}:--  "
        slots.append(cell)
    print(f"  {'  '.join(slots)}")


class HumanAgent(Agent):
    def _draw_screen(
        self,
        obs: Observation,
        legal_indices: list[int],
        hand: list,
        extra_lines: list[str] | None = None,
    ) -> None:
        print()
        _line("═")
        print(f"  BAŚKA  |  Bitka {obs.tricks_played + 1}/4  |  Gracz {obs.player_id}")
        _line("═")

        current_dict = {p: c for p, c in obs.current_trick}
        print("  Bieżąca bitka:")
        _trick_row(current_dict)

        _line()

        hand_str = "  ".join(f"[{i}]{card_str(c)}" for i, c in enumerate(hand))
        print(f"  Twoja ręka:  {hand_str}")
        legal_str = "  ".join(f"[{i}]{card_str(hand[i])}" for i in legal_indices)
        print(f"  Legalne:     {legal_str}")

        if extra_lines:
            _line()
            for line in extra_lines:
                print(line)

        _line("═")
        print(f"  Wybierz {legal_indices} lub [h]istoria [p]unkty: ", end="", flush=True)

    def choose_action(
        self,
        obs: Observation,
        legal_moves: list[tuple[str, str]],
    ) -> tuple[str, str]:
        hand = list(obs.my_hand)
        legal_set = set(legal_moves)
        legal_indices = [i for i, c in enumerate(hand) if c in legal_set]
        extra: list[str] | None = None

        while True:
            self._draw_screen(obs, legal_indices, hand, extra_lines=extra)
            extra = None
            raw = input().strip().lower()

            if raw == "h":
                if obs.played_cards or obs.current_trick:
                    lines = ["  Historia:"]
                    for i in range(obs.tricks_played):
                        chunk = obs.played_cards[i * 4:(i + 1) * 4]
                        cards_str = "  ".join(card_str(c) for c in chunk)
                        lines.append(f"  Bitka {i + 1}: {cards_str}")
                    if obs.current_trick:
                        chunk = [c for _, c in obs.current_trick]
                        cards_str = "  ".join(card_str(c) for c in chunk)
                        lines.append(f"  Bitka {obs.tricks_played + 1}: {cards_str} ...")
                else:
                    lines = ["  Historia: brak zagranych kart."]
                extra = lines

            elif raw == "p":
                lines = ["  Punkty:"]
                for p, pts in sorted(obs.scores_dict.items()):
                    marker = " ◄ TY" if p == obs.player_id else ""
                    lines.append(f"    Gracz {p}: {pts} pkt{marker}")
                extra = lines

            else:
                try:
                    idx = int(raw)
                    if idx in legal_indices:
                        return hand[idx]
                    extra = [f"  ✗ Nielegalny ruch. Możesz zagrać: {legal_indices}"]
                except ValueError:
                    extra = ["  ✗ Wpisz numer karty lub h / p."]
