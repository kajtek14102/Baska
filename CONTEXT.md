# Baśka — kontekst dla kolejnego czatu

Uproszczona Baśka (16 kart, 4 gracze, 4 bitki). Cel długoterminowy: uczenie modeli / miliony rozdań. Human agent tylko do testów.

## Pliki

| plik | rola |
|------|------|
| `baska_engine.py` | reguły: karty, trumfy/fele, legal_moves, GameState, drużyny (starzy=Q♣/Q♠), compute_result, deal |
| `observation.py` | Observation — jedyny widok dla agenta (bez cudzych rąk / drużyn) |
| `agent_base.py` | ABC Agent.choose_action(obs, legal_moves) |
| `random_agent.py` | RandomAgent |
| `always_highest_agent.py` | AlwaysHighestAgent + `card_strength_key` (min = silniejsza) |
| `always_lowest_agent.py` | AlwaysLowestAgent (max po tym samym kluczu) |
| `beat_high_dump_low_agent.py` | BeatHighDumpLowAgent — przebija najmocniejszą, zrzuca/lead najsłabszą |
| `human_agent.py` | konsolowe UI tury: ręka, legalne, bieżąca bitka, h/p — bez narracji partii |
| `game_events.py` | Deal/Play/TrickEnd/GameEnd + GameListener + ConsoleNarrator |
| `game_runner.py` | run_game, run_many_games, demo_*, make_agents |
| `test_engine.py` | ręczne testy reguł (nie pytest) |

## Architektura printów

- Przebieg partii → listenery (`ConsoleNarrator`), nie agent.
- Hot path treningu: `run_game(agents)` / `run_many_games(..., progress=False)` — bez listenerów, bez zbędnych alokacji.
- `verbose=True` dokłada ConsoleNarrator(reveal_private=True).
- `play_vs_random`: narrator z `reveal_private=False` + HumanAgent.

## Uruchamianie matchupów

```python
from game_runner import demo_agents, demo_always_lowest_vs_random, make_agents

demo_agents(["AlwaysLowest", "Random", "Random", "Random"], n=10_000)
demo_always_lowest_vs_random(n=10_000)   # też AlwaysHighest analogicznie
# nazwy: Random, AlwaysHighest, AlwaysLowest, BeatHighDumpLow (+ sufiks Agent, case-insensitive)
```

`run_many_games`: `progress=True` ≈ 100 update'ów; `keep_results=False` domyślnie (nie zwracaj listy 1e6 wyników — puchnie REPL). Demo zwraca `{avg_score, wins, n}`.

## Python na tej maszynie

`python` w PATH = stub Windows Store. Działa m.in.:
`C:\Users\kajte\AppData\Local\spyder-6\python.exe`
Konsola cp1250 — unikaj znaków typu ◄ w printach demo.

## Świadomie jeszcze nie ma

Sieci / RL, silniejszej heurystyki, GUI, pytest. Hierarchia siły kart = TRUMP_RANK, potem FELE_RANK (fele słabsze od wszystkich trumfów).
