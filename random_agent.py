"""
random_agent.py

Agent losowy - wybiera kartę losowo spośród legalnych ruchów.
"""

from __future__ import annotations
import random

from agent_base import Agent
from observation import Observation


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
        obs: Observation,
        legal_moves: list[tuple[str, str]],
    ) -> tuple[str, str]:
        return self.rng.choice(legal_moves)