from baska_engine import *
import random


def test_legal_moves():
    def show(hand, trick, opis=''):
        if opis:
            print(f'--- {opis} ---')
        if trick:
            print(f'  Bitka: {[card_str(c) for _, c in trick]}')
        else:
            print(f'  Bitka: (otwierasz)')
        print(f'  Ręka:    {[card_str(c) for c in hand]}')
        print(f'  Legalne: {[card_str(c) for c in legal_moves(hand, trick)]}')
        print()

    # Otwierasz - cokolwiek
    show([('A', 'h'), ('10', 's'), ('Q', 'c'), ('J', 'd')], [],
         'otwierasz, cokolwiek')

    # Fel otwiera, masz fela w tym kolorze - musisz go dać
    show([('10', 's'), ('Q', 'h'), ('J', 'c')],
         [(0, ('A', 's'))],
         'As♠ otwiera, masz 10♠ - musisz dać')

    # Fel otwiera, nie masz fela w tym kolorze - trumfy
    show([('Q', 'h'), ('J', 'c'), ('A', 'c')],
         [(0, ('A', 's'))],
         'As♠ otwiera, nie masz pika - dajesz trumfa')

    # Fel otwiera, nie masz nic - cokolwiek
    show([('A', 'c'), ('10', 'c')],
         [(0, ('A', 's'))],
         'As♠ otwiera, masz tylko fele krzyż - cokolwiek')

    # Trumf na stole, masz słabszy i mocniejszy - musisz przebić mocniejszym
    show([('J', 'h'), ('Q', 'd'), ('A', 'c')],
         [(0, ('J', 'c')), (1, ('J', 's'))],
         'J♣ J♠ na stole, masz J♥ Q♦ A♣ - musisz dać Q♦ bo przebija')

    # Trumf na stole, masz tylko słabsze trumfy - dajesz jeden z nich
    show([('J', 'h'), ('J', 'd'), ('A', 'c')],
         [(0, ('Q', 'c')), (1, ('10', 'h'))],
         'Q♣ 10♥ na stole, masz J♥ J♦ A♣ - nie możesz przebić, dajesz trumfa')

    # Trumf na stole, nie masz żadnego trumfa - cokolwiek
    show([('A', 'c'), ('10', 's')],
         [(0, ('Q', 'c')), (1, ('10', 'h'))],
         'Q♣ 10♥ na stole, masz A♣ 10♠ (fele) - cokolwiek')

    # Długa bitka: 3 karty już zagrane, jesteś 4ty
    show([('A', 'h'), ('Q', 's'), ('10', 'c')],
         [(0, ('J', 'd')), (1, ('Q', 'h')), (2, ('10', 'h'))],
         '3 karty na stole (J♦ Q♥ 10♥), masz A♥ Q♠ 10♣ - musisz dać A♥')


def test_determine_teams():
    def show(hands, opis=''):
        if opis:
            print(f'--- {opis} ---')
        for p, h in hands.items():
            print(f'  Gracz {p}: {[card_str(c) for c in h]}')
        starzy, mlodzi = determine_teams(hands)
        print(f'  Starzy: {starzy}')
        print(f'  Młodzi: {mlodzi}')
        print(f'  Układ:  {"1v3" if len(starzy)==1 or len(mlodzi)==1 else "2v2"}')
        print()

    # Typowy 2v2: gracze 0 i 2 mają stare damy
    show({
        0: [('Q', 'c'), ('A', 'h'), ('J', 'd'), ('10', 'd')],
        1: [('Q', 'h'), ('Q', 'd'), ('J', 'h'), ('A', 'd')],
        2: [('Q', 's'), ('10', 'h'), ('J', 's'), ('10', 's')],
        3: [('A', 'c'), ('10', 'c'), ('A', 's'), ('J', 'c')],
    }, 'typowy 2v2: gracz 0 ma Q♣, gracz 2 ma Q♠')

    # 1v3: gracz 1 ma obie stare damy
    show({
        0: [('Q', 'h'), ('Q', 'd'), ('A', 'h'), ('10', 'h')],
        1: [('Q', 'c'), ('Q', 's'), ('J', 'c'), ('J', 's')],
        2: [('J', 'h'), ('J', 'd'), ('A', 'd'), ('10', 'd')],
        3: [('A', 'c'), ('10', 'c'), ('A', 's'), ('10', 's')],
    }, '1v3: gracz 1 ma obie stare damy (Q♣ i Q♠)')

    # 2v2: gracze 1 i 3 mają stare damy (siedzą naprzeciwko)
    show({
        0: [('Q', 'h'), ('Q', 'd'), ('A', 'h'), ('10', 'h')],
        1: [('Q', 'c'), ('J', 'c'), ('J', 's'), ('A', 'd')],
        2: [('J', 'h'), ('J', 'd'), ('10', 'd'), ('A', 'c')],
        3: [('Q', 's'), ('10', 'c'), ('A', 's'), ('10', 's')],
    }, '2v2: gracz 1 ma Q♣, gracz 3 ma Q♠')


def test_compute_result():
    def show(scores, hands_initial, opis=''):
        if opis:
            print(f'--- {opis} ---')
        starzy, mlodzi = determine_teams(hands_initial)
        pts_starzy = sum(scores[p] for p in starzy)
        pts_mlodzi = sum(scores[p] for p in mlodzi)
        print(f'  Starzy {starzy}: {pts_starzy} pkt')
        print(f'  Młodzi {mlodzi}: {pts_mlodzi} pkt')
        # Symuluj terminal state
        state = GameState(hands={p: [] for p in range(4)})
        state.scores = scores
        state.tricks_played = 4
        r = compute_result(state, hands_initial)
        print(f'  Wygrani: {r["winners"]} | Kategoria: {r["category"]} | base_value: {r["base_value"]}')
        print(f'  Score:   {r["score"]} | Suma: {sum(r["score"].values())}')
        print()

    # Rozdanie bazowe: gracz 0 ma Q♣, gracz 2 ma Q♠ (2v2)
    hands_2v2 = {
        0: [('Q', 'c'), ('A', 'h'), ('J', 'd'), ('10', 'd')],
        1: [('Q', 'h'), ('Q', 'd'), ('J', 'h'), ('A', 'd')],
        2: [('Q', 's'), ('10', 'h'), ('J', 's'), ('10', 's')],
        3: [('A', 'c'), ('10', 'c'), ('A', 's'), ('J', 'c')],
    }

    # Rozdanie 1v3: gracz 0 ma obie stare damy
    hands_1v3 = {
        0: [('Q', 'c'), ('Q', 's'), ('A', 'h'), ('10', 'h')],
        1: [('Q', 'h'), ('Q', 'd'), ('J', 'c'), ('J', 's')],
        2: [('J', 'h'), ('J', 'd'), ('A', 'd'), ('10', 'd')],
        3: [('A', 'c'), ('10', 'c'), ('A', 's'), ('10', 's')],
    }

    show({0: 70, 1: 10, 2: 14, 3: 10}, hands_2v2,
         '2v2: starzy 84 pkt, młodzi 20 - starzy wygrywają, młodzi bez wyjścia (oczekiwane: +2/-2)')

    show({0: 10, 1: 50, 2: 14, 3: 30}, hands_2v2,
         '2v2: starzy 24 pkt, młodzi 80 - młodzi wygrywają, starzy bez wyjścia (oczekiwane: -4/+4)')

    show({0: 52, 1: 26, 2: 0, 3: 26}, hands_2v2,
         '2v2: remis 52:52 - wygrywają młodzi z wyjściem (oczekiwane: -2/+2)')

    show({0: 104, 1: 0, 2: 0, 3: 0}, hands_2v2,
         '2v2: starzy bez bitki (oczekiwane: +3/-3)')

    show({0: 0, 1: 50, 2: 0, 3: 54}, hands_2v2,
         '2v2: młodzi bez bitki (oczekiwane: -6/+6)')

    show({0: 80, 1: 8, 2: 8, 3: 8}, hands_1v3,
         '1v3: stary wygrywa, młodzi bez wyjścia (oczekiwane: stary +6, każdy młody -2)')

    show({0: 0, 1: 40, 2: 32, 3: 32}, hands_1v3,
         '1v3: młodzi wygrywają, stary bez wyjścia - bez bitki (oczekiwane: stary -18, każdy młody +6)')

    show({0: 104, 1: 0, 2: 0, 3: 0}, hands_1v3,
         '1v3: stary bez bitki (oczekiwane: stary +9, każdy młody -3)')

    show({0: 20, 1: 40, 2: 32, 3: 12}, hands_1v3,
         '1v3: młodzi wygrywają, stary bez wyjścia (oczekiwane: stary -12, każdy młody +4)')
    
    
def random_game():
    #random.seed(24)
    hands = deal_cards()
    hands_initial = {p: list(h) for p, h in hands.items()}

    print("=== Rozdanie ===")
    for p, h in hands.items():
        print(f"  Gracz {p}: {[card_str(c) for c in h]}")

    starzy, mlodzi = determine_teams(hands_initial)
    print(f"\nStarzy (mają damy): {starzy}")
    print(f"Młodzi: {mlodzi}")

    state = GameState(hands=hands)

    print("\n=== Gra losowa ===")
    while not state.is_terminal():
        moves = state.get_legal_moves()
        card = random.choice(moves)
        trick_num = state.tricks_played + 1
        pos_in_trick = len(state.current_trick) + 1
        print(f"  Bitka {trick_num}, pozycja {pos_in_trick}: "
              f"Gracz {state.current_player} gra {card_str(card)}")
        state = state.apply_move(card)

        if state.tricks_played > 0 and not state.current_trick:
            print(f"  → Bitkę wygrywa Gracz {state.trick_leader} "
                  f"(punkty: {state.scores})")

    result = compute_result(state, hands_initial)
    print(f"\n=== Wynik ===")
    print(f"  Starzy ({result['starzy']}): {result['pts_starzy']} pkt")
    print(f"  Młodzi ({result['mlodzi']}): {result['pts_mlodzi']} pkt")
    print(f"  Zwycięzcy: gracze {result['winners']}")
    
random_game()