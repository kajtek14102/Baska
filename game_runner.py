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
    keep_results: bool = False,
    progress: bool = False,
) -> dict:
    """
    Rozgrywa n partii i zbiera statystyki.

    Zwraca słownik:
        'avg_score'     - {player_id: średni score na rozdanie}
        'total_score'   - {player_id: suma score'ów}
        'wins'          - {player_id: liczba wygranych gier}
        'n'             - liczba rozegranych gier
        'results'       - tylko gdy keep_results=True (lista wyników każdej gry)

    progress=True → ~100 aktualizacji na stderr (koszt znikomy nawet przy milionie gier).
    """
    ls = _resolve_listeners(listeners, verbose)
    results = [] if keep_results else None
    total_score = {p: 0 for p in range(4)}
    wins = {p: 0 for p in range(4)}
    # co najwyżej ~100 printów; przy małych n — co grę
    report_every = max(1, n // 100) if progress else 0

    for i in range(n):
        if ls:
            notify(ls, "on_series_game_start", SeriesGameStartEvent(
                game_index=i + 1,
                n=n,
            ))
        # verbose już wciągnięte do ls — nie przekazuj ponownie
        r = run_game(agents, verbose=False, listeners=ls if ls else None)
        if results is not None:
            results.append(r)
        for p in range(4):
            total_score[p] += r["score"][p]
        for p in r["winners"]:
            wins[p] += 1

        if report_every and ((i + 1) % report_every == 0 or i + 1 == n):
            pct = 100.0 * (i + 1) / n
            print(f"\r  postęp: {i + 1}/{n} ({pct:.0f}%)", end="", flush=True)

    if report_every:
        print()

    out = {
        "avg_score": {p: total_score[p] / n for p in range(4)},
        "total_score": total_score,
        "wins": wins,
        "n": n,
    }
    if results is not None:
        out["results"] = results
    return out


# ---------------------------------------------------------------------------
# Gotowe scenariusze - wywołuj z konsoli
# ---------------------------------------------------------------------------

# Nazwy skrócone i pełne → klasa agenta (bez Human — interaktywny)
_AGENT_TYPES: dict[str, type] | None = None


def _agent_registry() -> dict[str, type]:
    global _AGENT_TYPES
    if _AGENT_TYPES is None:
        from random_agent import RandomAgent
        from always_highest_agent import AlwaysHighestAgent
        from always_lowest_agent import AlwaysLowestAgent
        from beat_high_dump_low_agent import BeatHighDumpLowAgent

        classes = (
            RandomAgent,
            AlwaysHighestAgent,
            AlwaysLowestAgent,
            BeatHighDumpLowAgent,
        )
        reg: dict[str, type] = {}
        for cls in classes:
            reg[cls.__name__] = cls
            # skrót: RandomAgent -> Random, AlwaysHighestAgent -> AlwaysHighest
            short = cls.__name__.removesuffix("Agent")
            reg[short] = cls
            reg[short.lower()] = cls
            reg[cls.__name__.lower()] = cls
        _AGENT_TYPES = reg
    return _AGENT_TYPES


def make_agents(names: Sequence[str]) -> dict[int, Agent]:
    """
    Tworzy 4 agentów z listy nazw (kolejność = gracze 0..3).

    Akceptowane nazwy m.in.: Random, AlwaysHighest, AlwaysLowest,
    BeatHighDumpLow (też z sufiksem Agent, niezależnie od wielkości liter).
    """
    if len(names) != 4:
        raise ValueError(f"Potrzeba dokładnie 4 nazw agentów, dostano {len(names)}")
    reg = _agent_registry()
    agents: dict[int, Agent] = {}
    for i, name in enumerate(names):
        key = name.strip()
        cls = reg.get(key) or reg.get(key.lower())
        if cls is None:
            known = ", ".join(sorted({c.__name__ for c in reg.values()}))
            raise ValueError(f"Nieznany agent {name!r}. Znane: {known}")
        agents[i] = cls(i)
    return agents


def _print_matchup_stats(
    stats: dict,
    labels: Sequence[str],
) -> None:
    for p in range(4):
        avg = stats["avg_score"][p]
        print(f"  Gracz {p} ({labels[p]}): {avg:+.3f} / rozdanie")


def demo_agents(
    names: Sequence[str],
    n: int = 10000,
) -> dict:
    """
    Rozgrywa n partii z dowolną czwórką agentów podaną z nazwy.

    Przykład:
        demo_agents(['AlwaysLowest', 'Random', 'Random', 'Random'], n=5000)
        demo_agents(['AlwaysHighest', 'AlwaysLowest', 'Random', 'Random'])

    Zwraca zwięzłe statystyki (avg_score, wins, n) — bez listy wszystkich gier.
    """
    agents = make_agents(names)
    labels = [type(agents[i]).__name__ for i in range(4)]
    print(f"\n=== {n} rozdań ===")
    for p, label in enumerate(labels):
        print(f"  {p}: {label}")
    stats = run_many_games(agents, n=n, progress=True)
    print("--- średni score / rozdanie ---")
    _print_matchup_stats(stats, labels)
    return {
        "avg_score": stats["avg_score"],
        "wins": stats["wins"],
        "n": stats["n"],
    }


def demo_random(n: int = 10000) -> dict:
    """4 losowych agentów, statystyki z n gier."""
    return demo_agents(["Random", "Random", "Random", "Random"], n=n)


def demo_always_highest_vs_random(
    n: int = 10000,
    agent_id: int = 0,
) -> dict:
    """AlwaysHighestAgent vs 3x RandomAgent."""
    names = ["Random"] * 4
    names[agent_id] = "AlwaysHighest"
    return demo_agents(names, n=n)


def demo_always_lowest_vs_random(
    n: int = 10000,
    agent_id: int = 0,
) -> dict:
    """AlwaysLowestAgent vs 3x RandomAgent."""
    names = ["Random"] * 4
    names[agent_id] = "AlwaysLowest"
    return demo_agents(names, n=n)


def demo_beat_high_dump_low_vs_random(
    n: int = 10000,
    agent_id: int = 0,
) -> dict:
    """BeatHighDumpLowAgent vs 3x RandomAgent."""
    names = ["Random"] * 4
    names[agent_id] = "BeatHighDumpLow"
    return demo_agents(names, n=n)


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
    # play_vs_random(human_id=0)
    pass

