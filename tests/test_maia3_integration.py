import unittest

import chessBotWin


class Maia3ConfigurationTests(unittest.TestCase):
    def test_maia3_command_is_cpu_and_offline_only(self):
        command = chessBotWin._build_maia3_command()
        self.assertIn("--device", command)
        self.assertEqual(command[command.index("--device") + 1], "cpu")
        self.assertIn("--local-files-only", command)
        self.assertIn("--use-uci-history", command)
        self.assertIn("--no-use-amp", command)
        self.assertIn("--elo", command)
        self.assertEqual(
            command[command.index("--elo") + 1],
            str(chessBotWin.MAIA3_TARGET_ELO),
        )

    def test_original_local_paths_are_preserved(self):
        self.assertEqual(
            chessBotWin.ENGINE_PATH,
            r"J:\vs code\python\chessGame\stockfish\stockfish-windows-x86-64-avx2.exe",
        )
        self.assertEqual(
            chessBotWin.PIECE_FOLDER,
            r"J:\vs code\python\chessGame\pieces",
        )

    def test_maia_acceptance_is_bounded(self):
        self.assertGreater(chessBotWin.MAIA3_MAX_STOCKFISH_LOSS_CP, 0)
        self.assertGreaterEqual(chessBotWin.MAIA3_ACCEPTANCE_PROBABILITY, 0.0)
        self.assertLessEqual(chessBotWin.MAIA3_ACCEPTANCE_PROBABILITY, 1.0)


if __name__ == "__main__":
    unittest.main()
