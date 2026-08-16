"""
oracle_agent.py

Wyrocznia: widzi wszystkie ręce (i przez to drużyny) i gra minimaxem.
To NIE jest uczciwy agent — górne ograniczenie, ile da się wycisnąć
z pełnej informacji. Runner woła choose_from_state, nie Observation.
"""

from __future__ import annotations

from agent_base import Agent
from observation import Observation
from always_highest_agent import card_strength_key
from perfect_info import best_move


class OracleAgent(Agent):
    uses_full_state = True

    def choose_action(
        self,
        obs: Observation,
        legal_moves: list[tuple[str, str]],
    ) -> tuple[str, str]:
        raise RuntimeError(
            "OracleAgent wymaga pełnego stanu (uses_full_state). "
            "Uruchom przez game_runner — nie wołaj choose_action."
        )

    def choose_from_state(
        self,
        state,
        hands_initial: dict[int, list[tuple[str, str]]],
        legal_moves: list[tuple[str, str]],
    ) -> tuple[str, str]:
        if len(legal_moves) == 1:
            return legal_moves[0]
        move, _val = best_move(
            state.hands,
            state.scores,
            state.current_trick,
            state.tricks_played,
            state.current_player,
            state.trick_leader,
            hands_initial,
        )
        if move not in legal_moves:
            return min(legal_moves, key=card_strength_key)
        return move
