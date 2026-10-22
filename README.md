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

## Optional human-like policy (Maia-3, CPU/offline)

The application can optionally consult Maia-3 5M as a human-move policy. Stockfish remains the tactical safety checker and the fallback. The model is launched lazily in a worker thread with CPU inference and `--local-files-only`; if Maia-3 is not installed or its checkpoint is not cached, the game continues with the existing Stockfish selector.

### One-time setup (requires internet)

Use the same Python interpreter/environment that runs this game. Install a CPU-only PyTorch build, then the official Maia-3 inference package:

```powershell
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
python -m pip install git+https://github.com/CSSLab/maia3.git
maia3-cache --model maia3-5m
```

If `maia3-cache` is not found, close and reopen the terminal and check `python -m pip show maia3`. Start the game with `python chessBotWin.py`. Once the model is cached, the Maia inference command is configured to use local files only, so the game itself does not need network access. The first model download and package installation do require internet.

### Current integration settings

- Model: `maia3-5m`
- Device: CPU only; AMP disabled
- Human target: Elo 2000
- Maia move is considered only if Stockfish independently evaluates it within a maximum 100-centipawn loss from the best scored candidate.
- Among accepted safe positions, Maia's proposed move is selected with 65% probability; otherwise the existing candidate selector chooses.
- If the model cannot start or a move cannot be validated, the app falls back to its Stockfish-only path.

These are initial engineering defaults, not benchmark-calibrated values. The 100 cp guard is a practical filter, not a guarantee against all tactical mistakes. The model's WDL/centipawn compatibility output is not a Stockfish search evaluation; this integration uses Stockfish's own evaluation to assess the proposed move.

### Licensing and distribution

Maia-3 inference code is published under AGPL-3.0. The Maia3-5M model card says the paper is CC BY 4.0 but directs users to the code repository for the code/weights license; do not assume the paper's license automatically licenses the checkpoint. This project does not bundle the model weights. Before distributing a combined application, verify the current upstream code and checkpoint terms and comply with any applicable license obligations. See the [official Maia-3 repository](https://github.com/CSSLab/maia3) and [Maia3-5M model card](https://huggingface.co/UofTCSSLab/Maia3-5M).

This feature is for offline practice and analysis only, not for concealing engine use or bypassing online fair-play rules.

## Checks

GitHub Actions compiles `chessBotWin.py` and runs unit tests for the move-selection window. These checks do not replace a runtime test with a real Stockfish executable or paired-game strength benchmarks.
