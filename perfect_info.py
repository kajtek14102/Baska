"""
Solver z pełną informacją: minimax / alpha-beta.

Zakłada, że wszyscy widzą wszystkie ręce — więc znają też drużyny.
Każdy gracz maksymalizuje swój score z compute_result (w 2v2 i 1v3
to to samo co gra zespołowa).

Używane przez PIMC (determinizacje) i ewentualnie wyrocznię.
"""

from __future__ import annotations

from baska_engine import (
    ALL_CARDS,
    FELE_RANK,
    POINT_VALUE,
    TRUMP_RANK,
    compute_result,
    determine_teams,
    is_fel,
    is_trump,
)

# ---------------------------------------------------------------------------
# Karty jako indeksy 0..15 (ten sam porządek co ALL_CARDS)
# ---------------------------------------------------------------------------

N_CARDS = 16
CARD_ID: dict[tuple[str, str], int] = {c: i for i, c in enumerate(ALL_CARDS)}
ID_CARD: list[tuple[str, str]] = list(ALL_CARDS)

_POINTS = [POINT_VALUE[c[0]] for c in ALL_CARDS]
_SUIT = [c[1] for c in ALL_CARDS]
_IS_TRUMP = [is_trump(c) for c in ALL_CARDS]
_IS_FEL = [is_fel(c) for c in ALL_CARDS]
_TRUMP_RANK = [TRUMP_RANK.get(c, 99) for c in ALL_CARDS]
_FELE_RANK = [FELE_RANK.get(c, 99) for c in ALL_CARDS]

# Kolejność ruchów: najpierw silniejsze trumfy, potem fele (As przed 10).
_MOVE_ORDER = sorted(
    range(N_CARDS),
    key=lambda i: (0, _TRUMP_RANK[i]) if _IS_TRUMP[i] else (1, _FELE_RANK[i], _SUIT[i]),
)


def _beats(ch: int, cur: int) -> bool:
    ch_t = _IS_TRUMP[ch]
    cu_t = _IS_TRUMP[cur]
    if ch_t and cu_t:
        return _TRUMP_RANK[ch] < _TRUMP_RANK[cur]
    if ch_t:
        return True
    if cu_t:
        return False
    if _SUIT[ch] != _SUIT[cur]:
        return False
    return _FELE_RANK[ch] < _FELE_RANK[cur]


def _trick_winner_ids(players: list[int], cards: list[int]) -> int:
    best_i = 0
    for i in range(1, len(cards)):
        if _beats(cards[i], cards[best_i]):
            best_i = i
    return players[best_i]


def _legal_ids(hand_mask: int, trick_cards: list[int], n_trick: int) -> list[int]:
    """Legalne karty z maski ręki — ta sama logika co baska_engine.legal_moves."""
    if n_trick == 0:
        return [i for i in _MOVE_ORDER if hand_mask & (1 << i)]

    lead = trick_cards[0]
    best = lead
    for i in range(1, n_trick):
        c = trick_cards[i]
        if _beats(c, best):
            best = c

    if _IS_FEL[lead]:
        lead_suit = _SUIT[lead]
        same = [
            i for i in _MOVE_ORDER
            if hand_mask & (1 << i) and _IS_FEL[i] and _SUIT[i] == lead_suit
        ]
        if same:
            return same

    can_beat = [i for i in _MOVE_ORDER if hand_mask & (1 << i) and _beats(i, best)]
    if can_beat:
        return can_beat

    trumps = [i for i in _MOVE_ORDER if hand_mask & (1 << i) and _IS_TRUMP[i]]
    if trumps:
        return trumps

    return [i for i in _MOVE_ORDER if hand_mask & (1 << i)]


# ---------------------------------------------------------------------------
# Wynik końcowy z perspektywy jednego gracza (kopia logiki compute_result)
# ---------------------------------------------------------------------------

_BASE = {
    (True,  "z_wyjsciem"):  1,
    (False, "z_wyjsciem"):  2,
    (True,  "bez_wyjscia"): 2,
    (False, "bez_wyjscia"): 4,
    (True,  "bez_bitki"):   3,
    (False, "bez_bitki"):   6,
}


def score_for_player(
    scores: list[int],
    starzy: tuple[int, ...],
    mlodzi: tuple[int, ...],
    player_id: int,
) -> int:
    pts_s = sum(scores[p] for p in starzy)
    pts_m = 104 - pts_s

    starzy_win = pts_s > 52
    if starzy_win:
        loser_pts = pts_m
        losers_have_exit = pts_m >= 26
    else:
        loser_pts = pts_s
        losers_have_exit = pts_s >= 27

    if loser_pts == 0:
        cat = "bez_bitki"
    elif losers_have_exit:
        cat = "z_wyjsciem"
    else:
        cat = "bez_wyjscia"

    base = _BASE[(starzy_win, cat)]
    winners = starzy if starzy_win else mlodzi
    solo = (
        starzy[0] if len(starzy) == 1
        else (mlodzi[0] if len(mlodzi) == 1 else None)
    )
    sign = 1 if player_id in winners else -1
    if solo is not None and player_id == solo:
        return sign * base * 3
    return sign * base


def _score_from_masks(starzy_mask: int, scores: list[int], player_id: int) -> int:
    starzy = tuple(p for p in range(4) if starzy_mask & (1 << p))
    mlodzi = tuple(p for p in range(4) if not starzy_mask & (1 << p))
    return score_for_player(scores, starzy, mlodzi, player_id)


# ---------------------------------------------------------------------------
# Alpha-beta
# ---------------------------------------------------------------------------

class _Search:
    __slots__ = (
        "hands", "scores", "tp", "tc", "n_trick", "current", "leader",
        "tricks_played", "root", "root_starzy", "starzy_mask", "nodes",
        "_stack",
    )

    def __init__(
        self,
        hands: list[int],
        scores: list[int],
        trick_players: list[int],
        trick_cards: list[int],
        n_trick: int,
        current: int,
        leader: int,
        tricks_played: int,
        root: int,
        starzy_mask: int,
    ):
        self.hands = hands
        self.scores = scores
        self.tp = trick_players
        self.tc = trick_cards
        self.n_trick = n_trick
        self.current = current
        self.leader = leader
        self.tricks_played = tricks_played
        self.root = root
        self.root_starzy = bool(starzy_mask & (1 << root))
        self.starzy_mask = starzy_mask
        self.nodes = 0
        self._stack: list[tuple | None] = []

    def value(self, alpha: int, beta: int) -> int:
        self.nodes += 1
        if self.tricks_played == 4:
            return _score_from_masks(self.starzy_mask, self.scores, self.root)

        p = self.current
        moves = _legal_ids(self.hands[p], self.tc, self.n_trick)
        maximizing = bool(self.starzy_mask & (1 << p)) == self.root_starzy

        if maximizing:
            best = -999
            for card in moves:
                self._do(p, card)
                v = self.value(alpha, beta)
                self._undo_move(p, card)
                if v > best:
                    best = v
                if best > alpha:
                    alpha = best
                if alpha >= beta:
                    break
            return best

        best = 999
        for card in moves:
            self._do(p, card)
            v = self.value(alpha, beta)
            self._undo_move(p, card)
            if v < best:
                best = v
            if best < beta:
                beta = best
            if beta <= alpha:
                break
        return best

    def _do(self, p: int, card: int) -> None:
        self.hands[p] ^= 1 << card
        n = self.n_trick
        self.tp[n] = p
        self.tc[n] = card
        if n < 3:
            self._stack.append(None)
            self.n_trick = n + 1
            self.current = (p + 1) & 3
            return
        w = _trick_winner_ids(self.tp, self.tc)
        pts = (
            _POINTS[self.tc[0]] + _POINTS[self.tc[1]]
            + _POINTS[self.tc[2]] + _POINTS[self.tc[3]]
        )
        rec = (
            w, pts, self.leader,
            self.tp[0], self.tp[1], self.tp[2], self.tp[3],
            self.tc[0], self.tc[1], self.tc[2], self.tc[3],
        )
        self._stack.append(rec)
        self.scores[w] += pts
        self.tricks_played += 1
        self.leader = w
        self.current = w
        self.n_trick = 0

    def _undo_move(self, p: int, card: int) -> None:
        rec = self._stack.pop()
        if rec is None:
            self.n_trick -= 1
            self.current = p
        else:
            w, pts, old_leader, p0, p1, p2, p3, c0, c1, c2, c3 = rec
            self.scores[w] -= pts
            self.tricks_played -= 1
            self.leader = old_leader
            self.tp[0], self.tp[1], self.tp[2], self.tp[3] = p0, p1, p2, p3
            self.tc[0], self.tc[1], self.tc[2], self.tc[3] = c0, c1, c2, c3
            self.n_trick = 3
            self.current = p
        self.hands[p] ^= 1 << card


def _hands_to_masks(hands: dict[int, list[tuple[str, str]]]) -> list[int]:
    masks = [0, 0, 0, 0]
    for p, cards in hands.items():
        m = 0
        for c in cards:
            m |= 1 << CARD_ID[c]
        masks[p] = m
    return masks


def _trick_to_ids(
    trick: list[tuple[int, tuple[str, str]]] | tuple[tuple[int, tuple[str, str]], ...],
) -> tuple[list[int], list[int]]:
    tp = [0, 0, 0, 0]
    tc = [0, 0, 0, 0]
    for i, (p, c) in enumerate(trick):
        tp[i] = p
        tc[i] = CARD_ID[tuple(c)]
    return tp, tc


def root_move_values(
    hands: dict[int, list[tuple[str, str]]],
    scores: dict[int, int],
    current_trick: list[tuple[int, tuple[str, str]]] | tuple,
    tricks_played: int,
    current_player: int,
    trick_leader: int,
    hands_initial: dict[int, list[tuple[str, str]]],
) -> dict[tuple[str, str], int]:
    """
    Wartość każdego legalnego ruchu z korzenia (score z perspektywy current_player).
    """
    starzy, _mlodzi = determine_teams(hands_initial)
    starzy_mask = 0
    for p in starzy:
        starzy_mask |= 1 << p

    hand_masks = _hands_to_masks(hands)
    tp, tc = _trick_to_ids(current_trick)
    n_trick = len(current_trick)
    score_list = [scores[0], scores[1], scores[2], scores[3]]

    moves = _legal_ids(hand_masks[current_player], tc, n_trick)
    out: dict[tuple[str, str], int] = {}
    for card in moves:
        s = _Search(
            hands=hand_masks[:],
            scores=score_list[:],
            trick_players=tp[:],
            trick_cards=tc[:],
            n_trick=n_trick,
            current=current_player,
            leader=trick_leader,
            tricks_played=tricks_played,
            root=current_player,
            starzy_mask=starzy_mask,
        )
        s._do(current_player, card)
        out[ID_CARD[card]] = s.value(-999, 999)
    return out


def best_move(
    hands: dict[int, list[tuple[str, str]]],
    scores: dict[int, int],
    current_trick: list | tuple,
    tricks_played: int,
    current_player: int,
    trick_leader: int,
    hands_initial: dict[int, list[tuple[str, str]]],
) -> tuple[tuple[str, str], int]:
    values = root_move_values(
        hands, scores, current_trick, tricks_played,
        current_player, trick_leader, hands_initial,
    )
    move = max(values.items(), key=lambda kv: kv[1])
    return move[0], move[1]


def verify_terminal_vs_engine(n: int = 200, rng=None) -> None:
    """Sprawdź, że score_for_player == compute_result dla losowych końcówek."""
    import random
    rng = rng or random.Random(0)
    for _ in range(n):
        # Losowy podział 104 pkt na 4 graczy (niekoniecznie legalny układ bitek)
        parts = [0, 0, 0, 0]
        left = 104
        for i in range(3):
            parts[i] = rng.randint(0, left)
            left -= parts[i]
        parts[3] = left
        hands = {p: list(ALL_CARDS[p * 4:(p + 1) * 4]) for p in range(4)}
        # Wymieszaj, żeby damy wylądowały różnie
        deck = list(ALL_CARDS)
        rng.shuffle(deck)
        hands = {i: deck[i * 4:(i + 1) * 4] for i in range(4)}
        starzy, mlodzi = determine_teams(hands)
        from baska_engine import GameState
        st = GameState(hands={p: [] for p in range(4)})
        st.scores = {p: parts[p] for p in range(4)}
        st.tricks_played = 4
        engine = compute_result(st, hands)
        for p in range(4):
            got = score_for_player(parts, tuple(starzy), tuple(mlodzi), p)
            if got != engine["score"][p]:
                raise AssertionError(
                    f"score mismatch p={p}: {got} vs {engine['score'][p]} "
                    f"parts={parts} starzy={starzy}"
                )


def verify_legal_vs_engine(n: int = 500, rng=None) -> None:
    """Losowe pozycje: zbiór legalnych ruchów = baska_engine.legal_moves."""
    import random
    from baska_engine import legal_moves

    rng = rng or random.Random(1)
    for _ in range(n):
        deck = list(ALL_CARDS)
        rng.shuffle(deck)
        n_hand = rng.randint(1, 4)
        n_trick = rng.randint(0, min(3, 16 - n_hand))
        hand = deck[:n_hand]
        trick = [(i, deck[n_hand + i]) for i in range(n_trick)]
        engine = set(legal_moves(hand, trick))
        mask = 0
        for c in hand:
            mask |= 1 << CARD_ID[c]
        tc = [0, 0, 0, 0]
        for i, (_, c) in enumerate(trick):
            tc[i] = CARD_ID[c]
        ours = {ID_CARD[i] for i in _legal_ids(mask, tc, n_trick)}
        if ours != engine:
            raise AssertionError(f"legal mismatch hand={hand} trick={trick}\n{ours} vs {engine}")


if __name__ == "__main__":
    verify_terminal_vs_engine()
    verify_legal_vs_engine()
    print("verify_terminal_vs_engine + verify_legal_vs_engine OK")

    import random
    import time
    from baska_engine import GameState, deal_cards, legal_moves as engine_legal

    rng = random.Random(42)
    t0 = time.perf_counter()
    n_games = 5
    for g in range(n_games):
        hands = deal_cards(rng)
        initial = {p: list(h) for p, h in hands.items()}
        first = rng.randint(0, 3)
        state = GameState(hands=hands, current_player=first, trick_leader=first)
        while not state.is_terminal():
            move, val = best_move(
                state.hands, state.scores, state.current_trick,
                state.tricks_played, state.current_player, state.trick_leader,
                initial,
            )
            legal = engine_legal(state.hands[state.current_player], state.current_trick)
            assert move in legal, (move, legal, val)
            state = state.apply_move(move)
        compute_result(state, initial)
    dt = time.perf_counter() - t0
    print(f"oracle self-play {n_games} gier: {dt:.3f}s ({dt / n_games:.3f}s/gra)")
