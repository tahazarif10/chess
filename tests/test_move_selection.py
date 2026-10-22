import unittest
from unittest.mock import patch

import chess

from chessBotWin import ChessGame


class BalancedMoveSelectionTests(unittest.TestCase):
    def setUp(self):
        # The selector is a pure selection routine; no GUI or engine is started.
        self.game = object.__new__(ChessGame)

    def test_white_never_selects_move_outside_quality_window(self):
        best = chess.Move.from_uci("e2e4")
        close = chess.Move.from_uci("d2d4")
        blunder = chess.Move.from_uci("a2a3")
        scored = [
            (best, 30, 70, 90),
            (close, 22, 65, 85),  # 8 cp loss, inside the 20 cp window
            (blunder, -15, 60, 80),  # 45 cp loss, outside the window
        ]
        with patch("chessBotWin.random.choices", side_effect=lambda population, weights, k: [population[-1]]):
            selected = self.game._probabilistic_select_enhanced(
                scored, is_winning=False, is_losing=False, phase="middlegame", turn=chess.WHITE
            )
        self.assertEqual(selected, close)

    def test_black_scores_are_compared_from_black_side_to_move(self):
        best = chess.Move.from_uci("e7e5")
        close = chess.Move.from_uci("d7d5")
        blunder = chess.Move.from_uci("a7a6")
        # Scores are White-relative, with Black's best move having the lowest score.
        scored = [
            (best, -30, 70, 90),
            (close, -22, 65, 85),  # 8 cp loss for Black
            (blunder, 15, 60, 80),  # 45 cp loss for Black
        ]
        with patch("chessBotWin.random.choices", side_effect=lambda population, weights, k: [population[-1]]):
            selected = self.game._probabilistic_select_enhanced(
                scored, is_winning=False, is_losing=False, phase="middlegame", turn=chess.BLACK
            )
        self.assertEqual(selected, close)

    def test_winning_position_uses_tighter_window(self):
        best = chess.Move.from_uci("e2e4")
        slightly_worse = chess.Move.from_uci("d2d4")
        scored = [(best, 100, 70, 90), (slightly_worse, 85, 65, 85)]
        with patch("chessBotWin.random.choices", side_effect=lambda population, weights, k: [population[-1]]):
            selected = self.game._probabilistic_select_enhanced(
                scored, is_winning=True, is_losing=False, phase="middlegame", turn=chess.WHITE
            )
        self.assertEqual(selected, best)

    def test_empty_candidates_return_none(self):
        self.assertIsNone(
            self.game._probabilistic_select_enhanced(
                [], is_winning=False, is_losing=False, phase="middlegame", turn=chess.WHITE
            )
        )


if __name__ == "__main__":
    unittest.main()
