"""
agent_base.py

Bazowa klasa agenta do gry Baśka.
Każdy konkretny agent dziedziczy po Agent i implementuje choose_action().
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from baska_engine import GameState


class Agent(ABC):
    """
    Abstrakcyjna klasa bazowa dla wszystkich agentów.

    Parametry:
        player_id: identyfikator gracza (0-3)
    """

    def __init__(self, player_id: int):
        self.player_id = player_id

    @abstractmethod
    def choose_action(
        self,
        state: "GameState",
        legal_moves: list[tuple[str, str]],
        hands_initial: dict[int, list[tuple[str, str]]],
    ) -> tuple[str, str]:
        """
        Wybierz kartę do zagrania.

        Parametry:
            state:         aktualny stan gry (tylko do odczytu - nie modyfikuj!)
            legal_moves:   lista kart które można legalnie zagrać
            hands_initial: początkowy rozkład kart (widoczny dla wszystkich agentów)
                           przydatny np. do ustalenia drużyn

        Zwraca:
            kartę jako krotkę (rank, suit), np. ('A', 'h')
        """
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(player_id={self.player_id})"