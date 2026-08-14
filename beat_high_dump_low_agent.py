"""
beat_high_dump_low_agent.py

Agent: przebija najmocniejszą legalną kartą, nie przebija najsłabszą.
Otwarcie bitki = nie przebija → najsłabsza.
"""

from __future__ import annotations

from agent_base import Agent
from observation import Observation
from always_highest_agent import card_strength_key
from baska_engine import _card_beats


def _current_best(
    trick: tuple[tuple[int, tuple[str, str]], ...],
) -> tuple[tuple[str, str], str]:
    lead_card = trick[0][1]
    lead_suit = lead_card[1]
    best = lead_card
    for _, card in trick[1:]:
        if _card_beats(card, best, lead_suit):
            best = card
    return best, lead_suit


class BeatHighDumpLowAgent(Agent):
    """Przebija max siłą, zrzuca min siłą. Lead = zrzut."""

    def choose_action(
        self,
        obs: Observation,
        legal_moves: list[tuple[str, str]],
    ) -> tuple[str, str]:
        if obs.current_trick:
            best, lead_suit = _current_best(obs.current_trick)
            if any(_card_beats(c, best, lead_suit) for c in legal_moves):
                return min(legal_moves, key=card_strength_key)
        return max(legal_moves, key=card_strength_key)
