# Chess Game with Stockfish

A local Pygame chess GUI that uses Stockfish through `python-chess`.

## Requirements

- Python 3.10 or newer
- Stockfish installed separately (the executable is not bundled)
- Piece PNG assets in a `pieces/` directory, unless configured with `CHESS_PIECES_DIR`

Install Python dependencies:

```bash
python -m pip install -r requirements.txt
```

## Original local paths

To preserve the user's existing setup, `chessBotWin.py` uses these original Windows paths:

- Stockfish: `J:\\vs code\\python\\chessGame\\stockfish\\stockfish-windows-x86-64-avx2.exe`
- Piece images: `J:\\vs code\\python\\chessGame\\pieces`

The application logic and move-selection changes are all in the single `chessBotWin.py` file. Stockfish, the Python packages, and the piece image assets remain external dependencies and are not embedded in the Python source.

## Run

```bash
python chessBotWin.py
```

## Notes on playing style and strength

Stockfish performs the actual search. The balanced offline selector prefers the engine's top move and only introduces variation among candidates within a small centipawn-loss window. The window is tighter when converting an advantage or playing an endgame. It does not pad the candidate list with unsearched moves, and candidate analysis uses fewer principal variations so more search effort can go to each candidate.

This is intended for local practice and analysis, not to conceal engine use or bypass online fair-play systems. It is not maximum-strength Stockfish play, and no Elo improvement is claimed until paired-game benchmarks have been run.

## Checks

GitHub Actions compiles `chessBotWin.py` and runs unit tests for the move-selection window. These checks do not replace a runtime test with a real Stockfish executable or paired-game strength benchmarks.
