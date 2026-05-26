"""
human_agent.py
Agent sterowany przez człowieka z poziomu konsoli.
Widzi tylko to co Observation udostępnia - żadnych ukrytych informacji.
"""
from __future__ import annotations
import os

from agent_base import Agent
from observation import Observation
from baska_engine import card_str, card_points

W = 46  # szerokość ramki


def _clear():
    os.system('cls' if os.name == 'nt' else 'clear')


def _line(char='─'):
    print(char * W)


def _trick_row(trick_dict: dict[int, tuple[str, str]]) -> None:
    """Wyświetla sloty graczy 0-3."""
    slots = []
    for p in range(4):
        if p in trick_dict:
            cell = f"{p}:{card_str(trick_dict[p]):<4}"
        else:
            cell = f"{p}:--  "
        slots.append(cell)
    print(f"  {'  '.join(slots)}")


def _build_trick_dict(trick: tuple) -> dict[int, tuple[str, str]]:
    return {p: c for p, c in trick}


class HumanAgent(Agent):
    def __init__(self, player_id: int):
        super().__init__(player_id)
        # Zapamiętujemy całą poprzednią bitkę z player_id -> card
        self._prev_trick_dict: dict[int, tuple[str, str]] = {}
        self._prev_trick_winner: int | None = None
        self._prev_tricks_played: int = 0
        self._prev_trick_leader: int | None = None  # lider poprzedniej bitki

    def _draw_screen(
        self,
        obs: Observation,
        legal_moves: list[tuple[str, str]],
        legal_indices: list[int],
        hand: list,
        extra_lines: list[str] | None = None,
    ) -> None:
        print('\n' * 4)  # przesuń w dół zamiast czyścić
        _line('═')
        print(f"  BAŚKA  |  Bitka {obs.tricks_played + 1}/4  |  Gracz {obs.player_id}")
        _line('═')

        # Poprzednia bitka
        if self._prev_trick_dict:
            print(f"  Poprzednia bitka (wygrał Gracz {self._prev_trick_winner}):")
            _trick_row(self._prev_trick_dict)
        else:
            print(f"  Poprzednia bitka: (to pierwsza bitka)")

        _line()

        # Bieżąca bitka
        current_dict = _build_trick_dict(obs.current_trick)
        print(f"  Bieżąca bitka:")
        _trick_row(current_dict)

        _line()

        # Ręka i legalne ruchy
        legal_set = set(legal_moves)
        hand_str = '  '.join(f"[{i}]{card_str(c)}" for i, c in enumerate(hand))
        print(f"  Twoja ręka:  {hand_str}")
        legal_str = '  '.join(f"[{i}]{card_str(hand[i])}" for i in legal_indices)
        print(f"  Legalne:     {legal_str}")

        # Opcjonalne linie (historia, punkty)
        if extra_lines:
            _line()
            for line in extra_lines:
                print(line)

        _line('═')
        print(f"  Wybierz {legal_indices} lub [h]istoria [p]unkty: ", end='', flush=True)

    def choose_action(
        self,
        obs: Observation,
        legal_moves: list[tuple[str, str]],
    ) -> tuple[str, str]:

        # Jeśli ukończyła się nowa bitka od ostatniego naszego ruchu,
        # odtwórz ją z played_cards - wiemy kto zaczął (trick_leader poprzedniej bitki)
        # trick_leader bieżącej bitki = zwycięzca poprzedniej = kto zaczął poprzednią
        if obs.tricks_played > self._prev_tricks_played:
            end = obs.tricks_played * 4
            prev_cards = obs.played_cards[end-4:end]
            leader = self._prev_trick_leader  # lider który zaczął poprzednią bitkę
            d = {}
            for i, card in enumerate(prev_cards):
                player = (leader + i) % 4
                d[player] = card
            self._prev_trick_dict = d
            self._prev_trick_winner = obs.trick_leader  # zwycięzca = lider bieżącej
            self._prev_tricks_played = obs.tricks_played

        # Zapamiętaj lidera bieżącej bitki - przyda się gdy bitka się skończy
        self._prev_trick_leader = obs.trick_leader

        hand = list(obs.my_hand)
        legal_set = set(legal_moves)
        legal_indices = [i for i, c in enumerate(hand) if c in legal_set]
        extra: list[str] | None = None

        while True:
            self._draw_screen(obs, legal_moves, legal_indices, hand, extra_lines=extra)
            extra = None
            raw = input().strip().lower()

            if raw == 'h':
                if obs.played_cards:
                    lines = ['  Historia:']
                    for i in range(obs.tricks_played):
                        chunk = obs.played_cards[i*4:(i+1)*4]
                        cards_str = '  '.join(card_str(c) for c in chunk)
                        lines.append(f"  Bitka {i+1}: {cards_str}")
                    # bieżąca bitka (niekompletna)
                    if obs.current_trick:
                        chunk = [c for _, c in obs.current_trick]
                        cards_str = '  '.join(card_str(c) for c in chunk)
                        lines.append(f"  Bitka {obs.tricks_played+1}: {cards_str} ...")
                else:
                    lines = ['  Historia: brak zagranych kart.']
                extra = lines

            elif raw == 'p':
                lines = ['  Punkty:']
                for p, pts in sorted(obs.scores_dict.items()):
                    marker = " ◄ TY" if p == obs.player_id else ""
                    lines.append(f"    Gracz {p}: {pts} pkt{marker}")
                extra = lines

            else:
                try:
                    idx = int(raw)
                    if idx in legal_indices:
                        chosen = hand[idx]
                        # zapamiętaj bitkę - zostanie nadpisana przy następnym wywołaniu
                        # jeśli bitka się skończyła po naszym ruchu
                        d = _build_trick_dict(obs.current_trick)
                        d[obs.player_id] = chosen
                        self._prev_trick_dict = d
                        return chosen
                    else:
                        extra = [f"  ✗ Nielegalny ruch. Możesz zagrać: {legal_indices}"]
                except ValueError:
                    extra = [f"  ✗ Wpisz numer karty lub h / p."]

    def show_game_end(self, result: dict) -> None:
        """Wywołaj z game_runner po zakończeniu gry."""
        _clear()
        _line('═')
        print(f"  BAŚKA  |  KONIEC GRY")
        _line('═')
        if self._prev_trick_dict:
            print(f"  Ostatnia bitka (wygrał Gracz {self._prev_trick_winner}):")
            _trick_row(self._prev_trick_dict)
            _line()
        score = result['score']
        print(f"  Wynik końcowy:")
        for p in range(4):
            marker = " ◄ TY" if p == self.player_id else ""
            print(f"    Gracz {p}: {score[p]:+d}{marker}")
        print(f"  Zwycięzcy: Gracze {result['winners']}")
        print(f"  Kategoria: {result['category']}")
        _line('═')