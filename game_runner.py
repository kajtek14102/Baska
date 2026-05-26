"""
game_runner.py

Uruchamia pojedynczą grę lub serię gier z dowolnymi agentami.
"""

from __future__ import annotations
import random
from baska_engine import deal_cards, GameState, compute_result, card_str
from agent_base import Agent
from observation import Observation


def run_game(
    agents: dict[int, Agent],
    verbose: bool = False,
) -> dict:
    """
    Rozgrywa jedną partię Baśki z podanymi agentami.

    Parametry:
        agents:  słownik {player_id: Agent} dla graczy 0-3
        verbose: czy drukować przebieg gry

    Zwraca:
        słownik wynikowy z compute_result() zawierający m.in.:
          'score'      - {player_id: wynik} (suma zerowa)
          'winners'    - lista zwycięskich player_id
          'pts_starzy' / 'pts_mlodzi'
          'category'   - 'z_wyjsciem' / 'bez_wyjscia' / 'bez_bitki'
    """
    assert set(agents.keys()) == {0, 1, 2, 3}, "Wymagani agenci dla graczy 0-3"

    hands = deal_cards()
    hands_initial = {p: list(h) for p, h in hands.items()}
    first_player = random.randint(0, 3)
    state = GameState(hands=hands, current_player=first_player, trick_leader=first_player)

    if verbose:
        print("=== Rozdanie ===")
        for p, h in hands.items():
            print(f"  Gracz {p} ({agents[p]}): {[card_str(c) for c in h]}")
        starzy = [p for p, h in hands_initial.items()
                  if any(c in {('Q','c'),('Q','s')} for c in h)]
        mlodzi = [p for p in range(4) if p not in starzy]
        print(f"\n  Starzy: {starzy}  |  Młodzi: {mlodzi}\n")

    while not state.is_terminal():
        legal = state.get_legal_moves()
        obs = Observation.from_state(state, state.current_player)
        card = agents[state.current_player].choose_action(obs, legal)

        assert card in legal, (
            f"Agent {agents[state.current_player]} zwrócił nielegalny ruch: {card_str(card)}"
        )

        if verbose:
            trick_num = state.tricks_played + 1
            pos = len(state.current_trick) + 1
            print(f"  Bitka {trick_num}, poz. {pos}: "
                  f"Gracz {state.current_player} gra {card_str(card)}")

        state = state.apply_move(card)

        if verbose and state.tricks_played > 0 and not state.current_trick:
            print(f"  → Bitkę wygrywa Gracz {state.trick_leader} "
                  f"| punkty: {dict(state.scores)}\n")

    result = compute_result(state, hands_initial)

    if verbose:
        print("=== Wynik ===")
        print(f"  Starzy {result['starzy']}: {result['pts_starzy']} pkt")
        print(f"  Młodzi {result['mlodzi']}: {result['pts_mlodzi']} pkt")
        print(f"  Zwycięzcy: {result['winners']}  |  Kategoria: {result['category']}")
        print(f"  Score: {result['score']}")

    return result


def run_many_games(
    agents: dict[int, Agent],
    n: int,
    verbose: bool = False,
) -> dict:
    """
    Rozgrywa n partii i zbiera statystyki.

    Zwraca słownik:
        'results'       - lista wyników z każdej gry
        'total_score'   - {player_id: suma score'ów}
        'wins'          - {player_id: liczba wygranych gier}
        'n'             - liczba rozegranych gier
    """
    results = []
    total_score = {p: 0 for p in range(4)}
    wins = {p: 0 for p in range(4)}

    for i in range(n):
        if verbose:
            print(f"\n{'='*40}")
            print(f"  GRA {i+1}/{n}")
            print(f"{'='*40}")
        r = run_game(agents, verbose=verbose)
        results.append(r)
        for p in range(4):
            total_score[p] += r['score'][p]
        for p in r['winners']:
            wins[p] += 1

    return {
        'results': results,
        'total_score': total_score,
        'wins': wins,
        'n': n,
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
        avg = stats['total_score'][p] / stats['n']
        print(f"  Gracz {p}: średni wynik {avg:+.3f} / partię")


def play_vs_random(human_id: int = 0) -> dict:
    """Człowiek (gracz human_id) kontra 3 losowych agentów."""
    from random_agent import RandomAgent
    from human_agent import HumanAgent
    agents = {i: (HumanAgent(i) if i == human_id else RandomAgent(i)) for i in range(4)}
    print(f"\n=== Grasz jako Gracz {human_id} przeciwko 3x RandomAgent ===")
    return run_game(agents, verbose=False)


if __name__ == '__main__':
    # Odkomentuj co chcesz uruchomić:
    #demo_random(n=10000)
    play_vs_random(human_id=0)