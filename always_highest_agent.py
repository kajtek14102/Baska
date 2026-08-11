"""
always_highest_agent.py

Agent, który zawsze gra najmocniejszą legalną kartę
według hierarchii z baska_engine (trumfy, potem fele).
"""

from __future__ import annotations

from agent_base import Agent
from observation import Observation
from baska_engine import is_trump, TRUMP_RANK, FELE_RANK


def card_strength_key(card: tuple[str, str]) -> tuple:
    """
    Klucz sortowania: mniejszy = silniejsza karta.
    Trumfy według TRUMP_RANK, fele słabsze od wszystkich trumfów
    (As przed 10 według FELE_RANK).
    """
    if is_trump(card):
        return (0, TRUMP_RANK[card])
    return (1, FELE_RANK[card], card[1])


class AlwaysHighestAgent(Agent):
    """Zawsze wybiera najmocniejszą kartę spośród legal_moves."""

    def choose_action(
        self,
        obs: Observation,
        legal_moves: list[tuple[str, str]],
    ) -> tuple[str, str]:
        return min(legal_moves, key=card_strength_key)
