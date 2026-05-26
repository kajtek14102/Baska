"""
agent_base.py

Bazowa klasa agenta do gry Baśka.
Każdy konkretny agent dziedziczy po Agent i implementuje choose_action().
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from observation import Observation


class Agent(ABC):
    """
    Abstrakcyjna klasa bazowa dla wszystkich agentów.

    Agent widzi TYLKO to co dostaje w Observation - żadnych rąk przeciwników,
    żadnego podziału na drużyny, żadnych hands_initial.
    """

    def __init__(self, player_id: int):
        self.player_id = player_id

    @abstractmethod
    def choose_action(
        self,
        obs: Observation,
        legal_moves: list[tuple[str, str]],
    ) -> tuple[str, str]:
        """
        Wybierz kartę do zagrania.

        Parametry:
            obs:         obserwacja stanu gry (tylko legalne informacje)
            legal_moves: lista kart które można legalnie zagrać

        Zwraca:
            kartę jako krotkę (rank, suit), np. ('A', 'h')
        """
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(player_id={self.player_id})"