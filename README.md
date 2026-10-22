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

## Configure Stockfish

The app searches for Stockfish in this order:

1. The path in `STOCKFISH_EXECUTABLE`
2. An executable named `stockfish` on `PATH`
3. `stockfish/stockfish-windows-x86-64-avx2.exe` beside `chessBotWin.py`
4. `stockfish/stockfish.exe` or `stockfish.exe` beside the script

Windows PowerShell example:

```powershell
$env:STOCKFISH_EXECUTABLE = "C:\\path\\to\\stockfish.exe"
python .\\chessBotWin.py
```

Linux/macOS example:

```bash
export STOCKFISH_EXECUTABLE=/usr/bin/stockfish
python chessBotWin.py
```

If the piece images are stored elsewhere, set `CHESS_PIECES_DIR` to that directory. Expected filenames are `white-pawn.png`, `black-pawn.png`, `white-knight.png`, `black-knight.png`, `white-bishop.png`, `black-bishop.png`, `white-rook.png`, `black-rook.png`, `white-queen.png`, `black-queen.png`, `white-king.png`, and `black-king.png`.

## Run

```bash
python chessBotWin.py
```

## Notes on playing style and strength

Stockfish performs the actual search. The balanced offline selector prefers the engine's top move and only introduces variation among candidates within a small centipawn-loss window. The window is tighter when converting an advantage or playing an endgame. It does not pad the candidate list with unsearched moves, and candidate analysis uses fewer principal variations so more search effort can go to each candidate.

This is intended for local practice and analysis, not to conceal engine use or bypass online fair-play systems. It is not maximum-strength Stockfish play, and no Elo improvement is claimed until paired-game benchmarks have been run.

## Checks

GitHub Actions compiles `chessBotWin.py` and runs unit tests for the move-selection window. These checks do not replace a runtime test with a real Stockfish executable or paired-game strength benchmarks.
