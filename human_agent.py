"""
human_agent.py
Agent sterowany przez człowieka z poziomu konsoli.
Widzi tylko to co Observation udostępnia - żadnych ukrytych informacji.
"""
from __future__ import annotations
from agent_base import Agent
from observation import Observation
from baska_engine import card_str, card_points


def _print_scores(scores: dict[int, int]) -> None:
    parts = [f"Gracz {p}: {pts} pkt" for p, pts in sorted(scores.items())]
    print(f"  Punkty:  {' | '.join(parts)}")


def _print_played(played: tuple) -> None:
    if played:
        print(f"  Zagrane: {', '.join(card_str(c) for c in played)}")
    else:
        print("  Zagrane: (brak)")


def _print_trick(trick: tuple) -> None:
    if not trick:
        print("  Bitka:   (otwierasz)")
    else:
        parts = [f"Gracz {p}: {card_str(c)}" for p, c in trick]
        pts = sum(card_points(c) for _, c in trick)
        print(f"  Bitka:   {' | '.join(parts)}  [{pts} pkt na stole]")


class HumanAgent(Agent):
    """
    Agent który pyta gracza o ruch przez konsolę.
    Widzi tylko informacje dostępne w Observation.
    Zapamiętuje poprzedni stan żeby pokazać wynik zakończonej bitki.
    """

    def __init__(self, player_id: int):
        super().__init__(player_id)
        self._prev_tricks_played: int = 0

    def choose_action(
        self,
        obs: Observation,
        legal_moves: list[tuple[str, str]],
    ) -> tuple[str, str]:

        # Jeśli zakończyła się bitka od ostatniego naszego ruchu - pokaż ją
        if obs.tricks_played > self._prev_tricks_played:
            end = obs.tricks_played * 4
            trick_cards = obs.played_cards[end-4:end]
            pts = sum(card_points(c) for c in trick_cards)
            played_str = '  '.join(card_str(c) for c in trick_cards)
            print()
            print(f"{'═'*52}")
            print(f"  ✓ Bitka {obs.tricks_played} zakończona:")
            print(f"    {played_str}  [{pts} pkt]")
            print(f"  Bitkę wygrał Gracz {obs.trick_leader}")
            _print_scores(obs.scores_dict)
            print(f"{'═'*52}")

        # Zapamiętaj liczbę ukończonych bitek
        self._prev_tricks_played = obs.tricks_played

        # Normalny prompt
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