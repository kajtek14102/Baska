"""
Silnik gry Baśka (uproszczona wersja - 16 kart, 4 bitki)

Karty:
  Trumfy (od najwyższego): As♥, 10♥, Q♣, Q♠, Q♥, Q♦, J♣, J♠, J♥, J♦, A♦, 10♦
  Fele krzyż: A♣, 10♣
  Fele pik:   A♠, 10♠

Punkty: As=11, 10=10, Q=3, J=2
Wygrana: drużyna z >52 pkt. Remis (52:52) → wygrywają "młodzi" (bez dam).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from itertools import combinations

# ---------------------------------------------------------------------------
# Definicja kart
# ---------------------------------------------------------------------------

SUITS = ['h', 'd', 'c', 's']          # heart, diamond, club, spade
RANKS = ['A', '10', 'Q', 'J']

# Wszystkie 16 kart jako krotki (rank, suit)
ALL_CARDS: list[tuple[str, str]] = [(r, s) for r in RANKS for s in SUITS]

# Hierarchia trumfów (indeks 0 = najsilniejszy)
TRUMP_ORDER: list[tuple[str, str]] = [
    ('A', 'h'), ('10', 'h'),
    ('Q', 'c'), ('Q', 's'), ('Q', 'h'), ('Q', 'd'),
    ('J', 'c'), ('J', 's'), ('J', 'h'), ('J', 'd'),
    ('A', 'd'), ('10', 'd'),
]
TRUMP_SET: set[tuple[str, str]] = set(TRUMP_ORDER)
TRUMP_RANK: dict[tuple[str, str], int] = {c: i for i, c in enumerate(TRUMP_ORDER)}

# Fele według koloru
FELE: dict[str, list[tuple[str, str]]] = {
    'c': [('A', 'c'), ('10', 'c')],   # As krzyż silniejszy
    's': [('A', 's'), ('10', 's')],
}
FELE_SET: set[tuple[str, str]] = {c for lst in FELE.values() for c in lst}
FELE_RANK: dict[tuple[str, str], int] = {}
for lst in FELE.values():
    for i, c in enumerate(lst):
        FELE_RANK[c] = i   # 0=As (silniejszy), 1=10

POINT_VALUE: dict[str, int] = {'A': 11, '10': 10, 'Q': 3, 'J': 2}

TOTAL_POINTS = sum(POINT_VALUE[r] for r, s in ALL_CARDS)  # 4*(11+10+3+2) = 104


def is_trump(card: tuple[str, str]) -> bool:
    return card in TRUMP_SET


def is_fel(card: tuple[str, str]) -> bool:
    return card in FELE_SET


def card_points(card: tuple[str, str]) -> int:
    return POINT_VALUE[card[0]]


def card_str(card: tuple[str, str]) -> str:
    suit_sym = {'h': '♥', 'd': '♦', 'c': '♣', 's': '♠'}
    return f"{card[0]}{suit_sym[card[1]]}"


# ---------------------------------------------------------------------------
# Logika bitki
# ---------------------------------------------------------------------------

def trick_winner(trick: list[tuple[int, tuple[str, str]]]) -> int:
    """
    trick: lista (player_id, card) w kolejności zagrania.
    Zwraca player_id zwycięzcy.
    """
    lead_player, lead_card = trick[0]
    lead_suit = lead_card[1]   # kolor karty otwierającej (istotny tylko przy felach)

    best_player = lead_player
    best_card = lead_card

    for player, card in trick[1:]:
        if _card_beats(card, best_card, lead_suit):
            best_card = card
            best_player = player

    return best_player


def _card_beats(challenger: tuple[str, str],
                current_best: tuple[str, str],
                lead_suit: str) -> bool:
    """Czy challenger bije current_best?
    Każda karta to albo trumf albo fel - nie ma innych możliwości.
    """
    ch_trump = is_trump(challenger)
    cb_trump = is_trump(current_best)

    # Trumf vs trumf → porównaj hierarchię (niższy indeks = silniejszy)
    if ch_trump and cb_trump:
        return TRUMP_RANK[challenger] < TRUMP_RANK[current_best]

    # Trumf bije fela, fel nie bije trumfa
    if ch_trump:
        return True
    if cb_trump:
        return False

    # Oba fele - przebicie możliwe tylko w tym samym kolorze (As > 10)
    if challenger[1] != current_best[1]:
        return False
    return FELE_RANK[challenger] < FELE_RANK[current_best]


# ---------------------------------------------------------------------------
# Zasady - które karty można zagrać
# ---------------------------------------------------------------------------

def legal_moves(hand: list[tuple[str, str]],
                trick_so_far: list[tuple[int, tuple[str, str]]]) -> list[tuple[str, str]]:
    """
    Zwraca listę kart które gracz może legalnie zagrać.
    hand: karty w ręce gracza
    trick_so_far: karty zagrane dotychczas w tej bitce (może być pusta)
    - każdy element to krotka (player_id, karta) gdzie karta to (rank, suit)
    """

    # Otwierający bitkę może zagrać dowolną kartę
    if not trick_so_far:
        return hand

    # Karta która otworzyła bitkę - jej kolor jest istotny tylko przy felach
    lead_card = trick_so_far[0][1]
    lead_suit = lead_card[1]
    lead_is_fel = is_fel(lead_card)

    # Znajdź aktualnie najsilniejszą kartę na stole (tę którą trzeba przebić)
    current_best = lead_card
    for _, c in trick_so_far[1:]:
        if _card_beats(c, current_best, lead_suit):
            current_best = c

    # Zasada 1: jeśli otwierający zagrał fela, musisz dołożyć fela w tym samym kolorze
    # (np. na As♠ musisz dać 10♠ jeśli masz - max 1 taka karta w talii)
    if lead_is_fel:
        same_suit_fele = [c for c in hand if is_fel(c) and c[1] == lead_suit]
        if same_suit_fele:
            return same_suit_fele
        # Nie masz fela w tym kolorze - przechodzimy do zasad ogólnych

    # Zasada 2 (ogólna): musisz przebić jeśli możesz (dowolną kartą - trumfem lub felem)
    can_beat = [c for c in hand if _card_beats(c, current_best, lead_suit)]
    if can_beat:
        return can_beat

    # Zasada 3: nie możesz przebić - musisz dać trumfa jeśli masz
    # (trumf nie przebija ale i tak musisz go dać)
    trumps_in_hand = [c for c in hand if is_trump(c)]
    if trumps_in_hand:
        return trumps_in_hand

    # Zasada 4: nie masz nic wymaganego - możesz dać cokolwiek
    return hand


# ---------------------------------------------------------------------------
# Stan gry
# ---------------------------------------------------------------------------

@dataclass
class GameState:
    hands: dict[int, list[tuple[str, str]]]   # player_id -> karty w ręce
    scores: dict[int, int] = field(default_factory=lambda: {i: 0 for i in range(4)})
    current_trick: list[tuple[int, tuple[str, str]]] = field(default_factory=list)
    tricks_played: int = 0
    current_player: int = 0   # kto teraz gra
    trick_leader: int = 0     # kto zaczął bieżącą bitkę

    # Pamięć: karty już zagrane (widoczne dla wszystkich)
    played_cards: list[tuple[str, str]] = field(default_factory=list)

    def copy(self) -> 'GameState':
        return GameState(
            hands={p: list(cards) for p, cards in self.hands.items()},
            scores=dict(self.scores),
            current_trick=list(self.current_trick),
            tricks_played=self.tricks_played,
            current_player=self.current_player,
            trick_leader=self.trick_leader,
            played_cards=list(self.played_cards),
        )

    def is_terminal(self) -> bool:
        return self.tricks_played == 4

    def get_legal_moves(self) -> list[tuple[str, str]]:
        return legal_moves(self.hands[self.current_player], self.current_trick)

    def apply_move(self, card: tuple[str, str]) -> 'GameState':
        """Zwraca nowy stan po zagraniu karty przez current_player."""
        new = self.copy()
        new.hands[new.current_player].remove(card)
        new.current_trick.append((new.current_player, card))
        new.played_cards.append(card)

        if len(new.current_trick) == 4:
            # Bitka skończona
            winner = trick_winner(new.current_trick)
            pts = sum(card_points(c) for _, c in new.current_trick)
            new.scores[winner] += pts
            new.current_trick = []
            new.tricks_played += 1
            new.trick_leader = winner
            new.current_player = winner
        else:
            new.current_player = (new.current_player + 1) % 4

        return new


# ---------------------------------------------------------------------------
# Drużyny i wynik
# ---------------------------------------------------------------------------

# Stare damy - tylko one decydują o przynależności do drużyny
OLD_QUEENS = {('Q', 'c'), ('Q', 's')}


def determine_teams(hands_initial: dict[int, list[tuple[str, str]]]) -> tuple[list[int], list[int]]:
    """
    Zwraca (starzy, mlodzi).
    Starzy = gracze posiadający Q♣ lub Q♠ (stare damy).
    Możliwe układy: 2v2 lub 1v3 (gdy jeden gracz ma obie stare damy).
    """
    starzy = [p for p, hand in hands_initial.items()
              if any(c in OLD_QUEENS for c in hand)]
    mlodzi = [p for p in range(4) if p not in starzy]
    return starzy, mlodzi


def compute_result(state: GameState,
                   hands_initial: dict[int, list[tuple[str, str]]]) -> dict:
    """
    Zwraca słownik z wynikiem gry, w tym 'score' - {player_id: wynik} (suma zerowa).

    Tabela base_value:
      starzy z wyjściem:    1  | młodzi z wyjściem:    2
      starzy bez wyjścia:   2  | młodzi bez wyjścia:   4
      starzy bez bitki:     3  | młodzi bez bitki:     6

    2v2:  wygrani +base, przegrani -base
    1v3:  samotny ±base*3, każdy z trójki ±base
    """
    assert state.is_terminal(), "Gra jeszcze nie skończona"

    starzy, mlodzi = determine_teams(hands_initial)
    pts_starzy = sum(state.scores[p] for p in starzy)
    pts_mlodzi = sum(state.scores[p] for p in mlodzi)

    # Remis 52:52 → wygrywają młodzi
    starzy_win = pts_starzy > 52
    winners = starzy if starzy_win else mlodzi
    losers  = mlodzi if starzy_win else starzy

    # Kategoria: sprawdzamy czy przegrani mają "wyjście"
    # (starzy potrzebują ≥27, młodzi ≥26)
    if starzy_win:
        losers_have_exit = pts_mlodzi >= 26
    else:
        losers_have_exit = pts_starzy >= 27

    if (pts_starzy if not starzy_win else pts_mlodzi) == 0:
        category = 'bez_bitki'
    elif losers_have_exit:
        category = 'z_wyjsciem'
    else:
        category = 'bez_wyjscia'

    base_value_map = {
        ('starzy', 'z_wyjsciem'):  1,
        ('mlodzi', 'z_wyjsciem'):  2,
        ('starzy', 'bez_wyjscia'): 2,
        ('mlodzi', 'bez_wyjscia'): 4,
        ('starzy', 'bez_bitki'):   3,
        ('mlodzi', 'bez_bitki'):   6,
    }
    winner_team = 'starzy' if starzy_win else 'mlodzi'
    base_value = base_value_map[(winner_team, category)]

    # Układ 1v3?
    solo_player = starzy[0] if len(starzy) == 1 else (mlodzi[0] if len(mlodzi) == 1 else None)

    score: dict[int, int] = {}
    for p in range(4):
        sign = +1 if p in winners else -1
        if solo_player is not None and p == solo_player:
            score[p] = sign * base_value * 3
        else:
            score[p] = sign * base_value

    return {
        'pts_starzy': pts_starzy,
        'pts_mlodzi': pts_mlodzi,
        'starzy': starzy,
        'mlodzi': mlodzi,
        'winners': winners,
        'losers': losers,
        'category': category,
        'base_value': base_value,
        'score': score,
    }


# ---------------------------------------------------------------------------
# Rozdanie kart
# ---------------------------------------------------------------------------

def deal_cards(rng=None) -> dict[int, list[tuple[str, str]]]:
    """Losuje i rozdaje 4 karty każdemu z 4 graczy."""
    import random
    deck = list(ALL_CARDS)
    if rng:
        rng.shuffle(deck)
    else:
        random.shuffle(deck)
    return {i: deck[i*4:(i+1)*4] for i in range(4)}


# ---------------------------------------------------------------------------
# Prosty test
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    pass


    


