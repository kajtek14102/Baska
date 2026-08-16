"""
pimc_agent.py

Perfect Information Monte Carlo: losuje (albo wylicza) rozdania spójne
z historią, w każdym rozwiązuje grę minimaxem przy pełnej informacji,
wybiera ruch o najwyższym średnim score.

Agent pamięta kto wychodził w pierwszej bitce, żeby z played_cards
odzyskać kto co zagrał (Observation nie trzyma tego dla starych bitek).
"""

from __future__ import annotations

import random
from itertools import combinations
from math import comb

from agent_base import Agent
from observation import Observation
from always_highest_agent import card_strength_key
from baska_engine import ALL_CARDS, legal_moves as engine_legal, trick_winner
from perfect_info import root_move_values


def _n_assignments(n_cards: int, counts: list[int]) -> int:
    x = 1
    left = n_cards
    for c in counts:
        x *= comb(left, c)
        left -= c
    return x


def _iter_assignments(
    cards: list[tuple[str, str]],
    players: list[int],
    counts: list[int],
):
    if len(players) == 1:
        yield {players[0]: list(cards)}
        return
    p, k = players[0], counts[0]
    for combo in combinations(cards, k):
        chosen = set(combo)
        rest = [c for c in cards if c not in chosen]
        for deal in _iter_assignments(rest, players[1:], counts[1:]):
            deal[p] = list(combo)
            yield deal


def _played_by_player(
    completed_tricks: list[list[tuple[int, tuple[str, str]]]],
    current_trick: tuple[tuple[int, tuple[str, str]], ...],
) -> dict[int, list[tuple[str, str]]]:
    out: dict[int, list[tuple[str, str]]] = {p: [] for p in range(4)}
    for trick in completed_tricks:
        for p, c in trick:
            out[p].append(tuple(c))
    for p, c in current_trick:
        out[p].append(tuple(c))
    return out


def _reconstruct_completed(
    obs: Observation,
) -> list[list[tuple[int, tuple[str, str]]]]:
    """
    Odtwórz kto zagrał co w skończonych bitkach.

    Observation.played_cards jest w kolejności zagrania, ale bez player_id.
    Lider bieżącej bitki = zwycięzca poprzedniej — idziemy od końca.
    """
    n = obs.tricks_played
    if n == 0:
        return []
    winner = obs.trick_leader
    reconstructed: list[list[tuple[int, tuple[str, str]]] | None] = [None] * n
    for t in range(n - 1, -1, -1):
        cards = [tuple(obs.played_cards[t * 4 + i]) for i in range(4)]
        dummy = [(i, cards[i]) for i in range(4)]
        win_pos = trick_winner(dummy)
        leader = (winner - win_pos) % 4
        reconstructed[t] = [((leader + i) % 4, cards[i]) for i in range(4)]
        winner = leader
    return reconstructed  # type: ignore[return-value]


def _is_consistent(
    original_hands: dict[int, list[tuple[str, str]]],
    completed_tricks: list[list[tuple[int, tuple[str, str]]]],
    current_trick: tuple[tuple[int, tuple[str, str]], ...],
) -> bool:
    hands = {p: list(cs) for p, cs in original_hands.items()}
    for trick in completed_tricks:
        so_far: list[tuple[int, tuple[str, str]]] = []
        for p, c in trick:
            if c not in engine_legal(hands[p], so_far):
                return False
            hands[p].remove(c)
            so_far.append((p, c))
    so_far = []
    for p, c in current_trick:
        card = tuple(c)
        if card not in engine_legal(hands[p], so_far):
            return False
        hands[p].remove(card)
        so_far.append((p, card))
    return True


class PIMCAgent(Agent):
    """
    Determinizacja + exact minimax.

    n_samples: ile światów liczyć, gdy wszystkich rozdań jest więcej.
    Gdy możliwych rozdań pozostałych kart jest ≤ n_samples, liczymy wszystkie.
    """

    def __init__(
        self,
        player_id: int,
        n_samples: int = 128,
        seed: int | None = None,
    ):
        super().__init__(player_id)
        if n_samples < 1:
            raise ValueError("n_samples musi być ≥ 1")
        self.n_samples = n_samples
        self.rng = random.Random(seed)

    def choose_action(
        self,
        obs: Observation,
        legal_moves: list[tuple[str, str]],
    ) -> tuple[str, str]:
        if len(legal_moves) == 1:
            return legal_moves[0]

        worlds = self._worlds(obs)
        if not worlds:
            return min(legal_moves, key=card_strength_key)

        totals: dict[tuple[str, str], float] = {m: 0.0 for m in legal_moves}
        seen: dict[tuple[str, str], int] = {m: 0 for m in legal_moves}
        for remaining, original in worlds:
            values = root_move_values(
                hands=remaining,
                scores=obs.scores_dict,
                current_trick=obs.current_trick,
                tricks_played=obs.tricks_played,
                current_player=obs.player_id,
                trick_leader=obs.trick_leader,
                hands_initial=original,
            )
            for m, v in values.items():
                if m in totals:
                    totals[m] += v
                    seen[m] += 1

        for m in legal_moves:
            if seen[m] == 0:
                totals[m] = float("-inf")

        best_val = max(totals.values())
        candidates = [m for m in legal_moves if totals[m] == best_val]
        return min(candidates, key=card_strength_key)

    def _worlds(
        self,
        obs: Observation,
    ) -> list[tuple[dict[int, list], dict[int, list]]]:
        """Lista par (ręce teraz, ręce początkowe) spójnych z historią."""
        me = obs.player_id
        completed = _reconstruct_completed(obs)
        played_by = _played_by_player(completed, obs.current_trick)

        seen = set(obs.my_hand) | {tuple(c) for c in obs.played_cards}
        unknown = [c for c in ALL_CARDS if c not in seen]
        others = [p for p in range(4) if p != me]
        counts = [4 - len(played_by[p]) for p in others]
        if sum(counts) != len(unknown):
            return []

        def to_world(assignment: dict[int, list]) -> tuple[dict, dict]:
            remaining = {me: list(obs.my_hand)}
            remaining.update(assignment)
            original = {
                p: list(played_by[p]) + list(remaining[p])
                for p in range(4)
            }
            return remaining, original

        n_all = _n_assignments(len(unknown), counts)
        worlds: list[tuple[dict, dict]] = []

        if n_all <= self.n_samples:
            for asg in _iter_assignments(unknown, others, counts):
                remaining, original = to_world(asg)
                if _is_consistent(original, completed, obs.current_trick):
                    worlds.append((remaining, original))
            if worlds:
                return worlds
            # Historia nie zgadza się z żadnym rozdaniem — bierz bez filtra.
            return [to_world(asg) for asg in _iter_assignments(unknown, others, counts)]

        max_tries = max(self.n_samples * 40, 200)
        tries = 0
        while len(worlds) < self.n_samples and tries < max_tries:
            tries += 1
            pool = unknown[:]
            self.rng.shuffle(pool)
            asg: dict[int, list] = {}
            i = 0
            for p, k in zip(others, counts):
                asg[p] = pool[i:i + k]
                i += k
            remaining, original = to_world(asg)
            if _is_consistent(original, completed, obs.current_trick):
                worlds.append((remaining, original))

        if worlds:
            return worlds

        # Nic nie przeszło filtra — bierz niespójne niż padnij.
        pool = unknown[:]
        self.rng.shuffle(pool)
        asg = {}
        i = 0
        for p, k in zip(others, counts):
            asg[p] = pool[i:i + k]
            i += k
        return [to_world(asg)]

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(player_id={self.player_id}, "
            f"n_samples={self.n_samples})"
        )
