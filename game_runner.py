"""
game_runner.py

Uruchamia pojedynczą grę lub serię gier z dowolnymi agentami.
"""

from __future__ import annotations
import random
from collections.abc import Callable
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

    for agent in agents.values():
        agent.reset()

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
        player = state.current_player
        agent = agents[player]
        if getattr(agent, "uses_full_state", False):
            card = agent.choose_from_state(state, hands_initial, legal)
        else:
            obs = Observation.from_state(state, player)
            card = agent.choose_action(obs, legal)

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
    on_progress: Callable[[int, int, dict], None] | None = None,
    on_game: Callable[[int, dict], None] | None = None,
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
    on_progress(done, n, stats) → te same ~100 ticków; stats ma avg_score / wins / total_score
    (średnie liczone z gier do tej pory, nie z pełnego n).
    on_game(game_index, result) → po każdej partii (game_index od 1); do zapisu na dysk.

    Każda partia tasuje obsadę stołu (kto koło kogo). first_player i tak jest losowy.
    Statystyki i log są w kolejności oryginalnych kluczy agents (Gracz 0..3 z GUI).
    """
    ls = _resolve_listeners(listeners, verbose)
    results = [] if keep_results else None
    total_score = {p: 0 for p in range(4)}
    wins = {p: 0 for p in range(4)}
    # co najwyżej ~100 printów / callbacków; przy małych n — co grę
    report_every = max(1, n // 100) if (progress or on_progress) else 0

    for i in range(n):
        if ls:
            notify(ls, "on_series_game_start", SeriesGameStartEvent(
                game_index=i + 1,
                n=n,
            ))
        order = [0, 1, 2, 3]
        random.shuffle(order)
        seated = {seat: agents[order[seat]] for seat in range(4)}
        for seat, ag in seated.items():
            ag.player_id = seat
        try:
            r = run_game(seated, verbose=False, listeners=ls if ls else None)
        finally:
            for gui, ag in agents.items():
                ag.player_id = gui
        # silnik liczy po miejscach; GUI i log chcą Gracza 0..3
        r["score"] = {order[s]: r["score"][s] for s in range(4)}
        r["winners"] = [order[s] for s in r["winners"]]
        r["starzy"] = [order[s] for s in r["starzy"]]
        r["mlodzi"] = [order[s] for s in r["mlodzi"]]
        r["table"] = order
        if results is not None:
            results.append(r)
        if on_game:
            on_game(i + 1, r)
        for p in range(4):
            total_score[p] += r["score"][p]
        for p in r["winners"]:
            wins[p] += 1

        if report_every and ((i + 1) % report_every == 0 or i + 1 == n or i == 0):
            done = i + 1
            if progress:
                pct = 100.0 * done / n
                print(f"\r  postęp: {done}/{n} ({pct:.0f}%)", end="", flush=True)
            if on_progress:
                on_progress(done, n, {
                    "avg_score": {p: total_score[p] / done for p in range(4)},
                    "total_score": dict(total_score),
                    "wins": dict(wins),
                })

    if progress and report_every:
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
# Rejestr agentów (bez Human — interaktywny)
# ---------------------------------------------------------------------------

_AGENT_TYPES: dict[str, type] | None = None


def _agent_registry() -> dict[str, type]:
    global _AGENT_TYPES
    if _AGENT_TYPES is None:
        from random_agent import RandomAgent
        from always_highest_agent import AlwaysHighestAgent
        from always_lowest_agent import AlwaysLowestAgent
        from beat_high_dump_low_agent import BeatHighDumpLowAgent
        from pimc_agent import PIMCAgent
        from oracle_agent import OracleAgent

        classes = (
            RandomAgent,
            AlwaysHighestAgent,
            AlwaysLowestAgent,
            BeatHighDumpLowAgent,
            PIMCAgent,
            OracleAgent,
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


def list_agent_names() -> list[str]:
    """Krótkie nazwy agentów z rejestru (bez Human), posortowane."""
    return sorted({
        cls.__name__.removesuffix("Agent")
        for cls in set(_agent_registry().values())
    })


def _parse_agent_name(name: str) -> tuple[str, int | None]:
    """'PIMC-256' / 'PIMC:64' → ('PIMC', 256). Inaczej (name, None)."""
    raw = name.strip()
    for sep in ("-", ":"):
        if sep not in raw:
            continue
        head, tail = raw.rsplit(sep, 1)
        if head and tail.isdigit() and int(tail) >= 1:
            return head, int(tail)
    return raw, None


def make_agents(
    names: Sequence[str],
    pimc_samples: Sequence[int] | None = None,
) -> dict[int, Agent]:
    """
    Tworzy 4 agentów z listy nazw (kolejność = gracze 0..3).
    Nazwy z list_agent_names(); też z sufiksem Agent, niezależnie od wielkości liter.
    PIMC: n_samples z pimc_samples[i], albo z nazwy 'PIMC-128', domyślnie 128.
    """
    if len(names) != 4:
        raise ValueError(f"Potrzeba dokładnie 4 nazw agentów, dostano {len(names)}")
    if pimc_samples is not None and len(pimc_samples) != 4:
        raise ValueError("pimc_samples musi mieć 4 elementy")
    reg = _agent_registry()
    agents: dict[int, Agent] = {}
    for i, name in enumerate(names):
        key, n_from_name = _parse_agent_name(name)
        cls = reg.get(key) or reg.get(key.lower())
        if cls is None:
            known = ", ".join(sorted({c.__name__ for c in reg.values()}))
            raise ValueError(f"Nieznany agent {name!r}. Znane: {known}")
        extra: dict = {}
        if cls.__name__ == "PIMCAgent":
            n = 128
            if pimc_samples is not None:
                n = int(pimc_samples[i])
            elif n_from_name is not None:
                n = n_from_name
            extra["n_samples"] = n
        agents[i] = cls(i, **extra)
    return agents


def play_vs_random(human_id: int = 0) -> dict:
    """Człowiek (gracz human_id) kontra 3 losowych agentów."""
    from random_agent import RandomAgent
    from human_agent import HumanAgent
    human = HumanAgent(human_id)
    agents = {i: (human if i == human_id else RandomAgent(i)) for i in range(4)}
    print(f"\n=== Grasz jako Gracz {human_id} przeciwko 3x RandomAgent ===")
    return run_game(
        agents,
        listeners=[ConsoleNarrator(reveal_private=False)],
    )

