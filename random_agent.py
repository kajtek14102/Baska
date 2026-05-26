"""
random_agent.py

Agent losowy - wybiera kartę losowo spośród legalnych ruchów.
"""

from __future__ import annotations
import random
from typing import TYPE_CHECKING

from agent_base import Agent

if TYPE_CHECKING:
    from baska_engine import GameState


class RandomAgent(Agent):
    """
    Najprostszy możliwy agent - wybiera kartę całkowicie losowo.
    Przydatny jako baseline i do testów.

    Parametry:
        player_id: identyfikator gracza (0-3)
        seed:      opcjonalne ziarno losowości (dla powtarzalnych eksperymentów)
    """

    def __init__(self, player_id: int, seed: int | None = None):
        super().__init__(player_id)
        self.rng = random.Random(seed)

    def choose_action(
        self,
        state: "GameState",
        legal_moves: list[tuple[str, str]],
        hands_initial: dict[int, list[tuple[str, str]]],
    ) -> tuple[str, str]:
        return self.rng.choice(legal_moves)