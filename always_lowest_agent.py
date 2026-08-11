"""
always_lowest_agent.py

Agent, który zawsze gra najsłabszą legalną kartę
według hierarchii z baska_engine (trumfy, potem fele).
"""

from __future__ import annotations

from agent_base import Agent
from observation import Observation
from always_highest_agent import card_strength_key


class AlwaysLowestAgent(Agent):
    """Zawsze wybiera najsłabszą kartę spośród legal_moves."""

    def choose_action(
        self,
        obs: Observation,
        legal_moves: list[tuple[str, str]],
    ) -> tuple[str, str]:
        return max(legal_moves, key=card_strength_key)
