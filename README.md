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

Stockfish performs the actual search. Candidate moves are now ordered by the engine evaluation before style preferences break ties, and the evaluation is no longer deliberately penalized merely for looking engine-like. Human-style selection still introduces variation, so it is not equivalent to maximum-strength Stockfish play.

No Elo improvement is claimed: this change has not yet been benchmarked with paired games. For competitive or online play, follow the site's rules and use only permitted assistance.
