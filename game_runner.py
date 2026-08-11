"""
game_runner.py

Uruchamia pojedynczą grę lub serię gier z dowolnymi agentami.
"""

from __future__ import annotations
import random
from typing import Sequence

from baska_engine import (
    deal_cards,
    GameState,
    compute_result,
    card_str,
    determine_teams,
)
from agent_base import Agent
from observation import Observation
from game_events import (
    GameListener,
    ConsoleNarrator,
    DealEvent,
    PlayEvent,
    TrickEndEvent,
    GameEndEvent,
    SeriesGameStartEvent,
    notify,
)


def _resolve_listeners(
    listeners: Sequence[GameListener] | None,
    verbose: bool,
) -> tuple[GameListener, ...]:
    """Pusta krotka = cicha ścieżka (trening). verbose dokłada ConsoleNarrator."""
    resolved: list[GameListener] = list(listeners) if listeners else []
    if verbose:
        resolved.append(ConsoleNarrator(reveal_private=True))
    return tuple(resolved)


def run_game(
    agents: dict[int, Agent],
    verbose: bool = False,
    listeners: Sequence[GameListener] | None = None,
) -> dict:
    """
    Rozgrywa jedną partię Baśki z podanymi agentami.

    Parametry:
        agents:    słownik {player_id: Agent} dla graczy 0-3
        verbose:   True → dodaje ConsoleNarrator (reveal_private=True)
        listeners: opcjonalne listenery zdarzeń; None / [] = zero narzutu

    Zwraca:
        słownik wynikowy z compute_result()
    """
    assert set(agents.keys()) == {0, 1, 2, 3}, "Wymagani agenci dla graczy 0-3"

    ls = _resolve_listeners(listeners, verbose)

    hands = deal_cards()
    hands_initial = {p: list(h) for p, h in hands.items()}
    first_player = random.randint(0, 3)
    state = GameState(hands=hands, current_player=first_player, trick_leader=first_player)

    if ls:
        starzy, mlodzi = determine_teams(hands_initial)
        notify(ls, "on_deal", DealEvent(
            hands={p: tuple(h) for p, h in hands_initial.items()},
            starzy=tuple(starzy),
            mlodzi=tuple(mlodzi),
            first_player=first_player,
            agent_labels={p: str(agents[p]) for p in range(4)},
        ))

    while not state.is_terminal():
        legal = state.get_legal_moves()
        obs = Observation.from_state(state, state.current_player)
        player = state.current_player
        card = agents[player].choose_action(obs, legal)

        assert card in legal, (
            f"Agent {agents[player]} zwrócił nielegalny ruch: {card_str(card)}"
        )

        if ls:
            notify(ls, "on_play", PlayEvent(
                player_id=player,
                card=card,
                trick_num=state.tricks_played + 1,
                position=len(state.current_trick) + 1,
            ))

        state = state.apply_move(card)

        if ls and state.tricks_played > 0 and not state.current_trick:
            notify(ls, "on_trick_end", TrickEndEvent(
                trick_num=state.tricks_played,
                winner=state.trick_leader,
                scores=dict(state.scores),
            ))

    result = compute_result(state, hands_initial)

    if ls:
        notify(ls, "on_game_end", GameEndEvent(result=result))

    return result


def run_many_games(
    agents: dict[int, Agent],
    n: int,
    verbose: bool = False,
    listeners: Sequence[GameListener] | None = None,
) -> dict:
    """
    Rozgrywa n partii i zbiera statystyki.

    Zwraca słownik:
        'results'       - lista wyników z każdej gry
        'total_score'   - {player_id: suma score'ów}
        'wins'          - {player_id: liczba wygranych gier}
        'n'             - liczba rozegranych gier
    """
    ls = _resolve_listeners(listeners, verbose)
    results = []
    total_score = {p: 0 for p in range(4)}
    wins = {p: 0 for p in range(4)}

    for i in range(n):
        if ls:
            notify(ls, "on_series_game_start", SeriesGameStartEvent(
                game_index=i + 1,
                n=n,
            ))
        # verbose już wciągnięte do ls — nie przekazuj ponownie
        r = run_game(agents, verbose=False, listeners=ls if ls else None)
        results.append(r)
        for p in range(4):
            total_score[p] += r["score"][p]
        for p in r["winners"]:
            wins[p] += 1

    return {
        "results": results,
        "total_score": total_score,
        "wins": wins,
        "n": n,
    }


# ---------------------------------------------------------------------------
# Gotowe scenariusze - wywołuj z konsoli
# ---------------------------------------------------------------------------

def demo_random(n: int = 10000) -> None:
    """4 losowych agentów, statystyki z n gier."""
    from random_agent import RandomAgent
    agents = {i: RandomAgent(i) for i in range(4)}
    print(f"\n=== Statystyki z {n} gier (4x RandomAgent) ===")
    stats = run_many_games(agents, n=n)
    for p in range(4):
        avg = stats["total_score"][p] / stats["n"]
        print(f"  Gracz {p}: średni wynik {avg:+.3f} / partię")


def play_vs_random(human_id: int = 0) -> dict:
    """Człowiek (gracz human_id) kontra 3 losowych agentów."""
    from random_agent import RandomAgent
    from human_agent import HumanAgent
    human = HumanAgent(human_id)
    agents = {i: (human if i == human_id else RandomAgent(i)) for i in range(4)}
    print(f"\n=== Grasz jako Gracz {human_id} przeciwko 3x RandomAgent ===")
    # Narrator bez rąk/drużyn; HumanAgent pokazuje tylko rękę / legalne / h|p
    return run_game(
        agents,
        listeners=[ConsoleNarrator(reveal_private=False)],
    )


if __name__ == "__main__":
    # Odkomentuj co chcesz uruchomić:
    # demo_random(n=10000)
    play_vs_random(human_id=0)
