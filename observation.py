"""
observation.py

Klasa Observation - jedyna informacja jaką agent dostaje o stanie gry.
Zawiera wyłącznie to co gracz legalnie widzi przy stole.
Celowo NIE zawiera: rąk innych graczy, hands_initial, podziału na drużyny.
"""

from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Observation:
    """
    Niezmienny widok stanu gry z perspektywy jednego gracza.

    Pola:
        player_id     - id tego gracza (0-3)
        my_hand       - karty w jego ręce (kopia)
        current_trick - karty zagrane w bieżącej bitce: [(player_id, karta), ...]
        played_cards  - wszystkie karty zagrane w poprzednich bitkach (kopia)
        scores        - punkty zdobyte per gracz: {player_id: punkty}
        tricks_played - liczba ukończonych bitek (0-3)
        trick_leader  - kto zaczął bieżącą bitkę
    """
    player_id:     int
    my_hand:       tuple[tuple[str, str], ...]
    current_trick: tuple[tuple[int, tuple[str, str]], ...]
    played_cards:  tuple[tuple[str, str], ...]
    scores:        tuple[tuple[int, int], ...]   # ((0, pts), (1, pts), ...) - hashowalne
    tricks_played: int
    trick_leader:  int

    # ------------------------------------------------------------------
    # Wygodne właściwości - żeby agent nie musiał rozpakowywać krotek
    # ------------------------------------------------------------------

    @property
    def scores_dict(self) -> dict[int, int]:
        return dict(self.scores)

    @property
    def my_points(self) -> int:
        return dict(self.scores)[self.player_id]

    @classmethod
    def from_state(cls, state, player_id: int) -> "Observation":
        """
        Tworzy Observation ze stanu gry dla danego gracza.
        Wszystkie kolekcje są kopiowane - agent nie ma dostępu do oryginałów.
        """
        return cls(
            player_id=player_id,
            my_hand=tuple(state.hands[player_id]),
            current_trick=tuple(
                (p, tuple(c)) for p, c in state.current_trick
            ),
            played_cards=tuple(state.played_cards),
            scores=tuple(sorted(state.scores.items())),
            tricks_played=state.tricks_played,
            trick_leader=state.trick_leader,
        )