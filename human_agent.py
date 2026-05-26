"""
human_agent.py

Agent sterowany przez człowieka z poziomu konsoli.
Widzi tylko to co Observation udostępnia - żadnych ukrytych informacji.
"""

from __future__ import annotations

from agent_base import Agent
from observation import Observation
from baska_engine import card_str, card_points


def _print_trick(trick: tuple) -> None:
    if not trick:
        print("  Bitka:   (otwierasz)")
    else:
        parts = [f"Gracz {p}: {card_str(c)}" for p, c in trick]
        pts = sum(card_points(c) for _, c in trick)
        print(f"  Bitka:   {' | '.join(parts)}  [{pts} pkt na stole]")


def _print_scores(scores: dict[int, int]) -> None:
    parts = [f"Gracz {p}: {pts} pkt" for p, pts in sorted(scores.items())]
    print(f"  Punkty:  {' | '.join(parts)}")


def _print_played(played: tuple) -> None:
    if played:
        print(f"  Zagrane: {', '.join(card_str(c) for c in played)}")
    else:
        print("  Zagrane: (brak)")


class HumanAgent(Agent):
    """
    Agent który pyta gracza o ruch przez konsolę.
    Wyświetla tylko informacje dostępne w Observation.
    """

    def choose_action(
        self,
        obs: Observation,
        legal_moves: list[tuple[str, str]],
    ) -> tuple[str, str]:

        print()
        print(f"{'─'*52}")
        print(f"  Bitka {obs.tricks_played + 1}/4  |  Twój ruch, Gracz {obs.player_id}")
        print(f"{'─'*52}")

        _print_trick(obs.current_trick)
        _print_scores(obs.scores_dict)
        _print_played(obs.played_cards)

        hand = list(obs.my_hand)
        legal_set = set(legal_moves)

        print(f"\n  Twoja ręka:    {', '.join(f'[{i}] {card_str(c)}' for i, c in enumerate(hand))}")
        print(f"  Legalne ruchy: {', '.join(f'[{i}] {card_str(c)}' for i, c in enumerate(hand) if c in legal_set)}")

        legal_indices = [i for i, c in enumerate(hand) if c in legal_set]

        while True:
            try:
                raw = input(f"\n  Wybierz kartę {legal_indices}: ").strip()
                idx = int(raw)
                if idx in legal_indices:
                    chosen = hand[idx]
                    print(f"  ➜ Grasz: {card_str(chosen)}")
                    return chosen
                else:
                    print(f"  ✗ Nielegalny ruch. Możesz zagrać: {legal_indices}")
            except ValueError:
                print("  ✗ Podaj numer karty.")