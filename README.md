# Chess Analyzer

An offline chess analysis tool with a graphical board, powered by [Stockfish](https://stockfishchess.org/). Set up any position, play moves, and see the engine's best moves instantly. Built for learning openings and experimenting with positions. No internet connection is needed once everything is installed.

## Features

- Clickable chess board (tkinter GUI) with legal-move hints and last-move highlight
- Top 3 engine lines with evaluations and the moves that follow
- Green arrow showing the best move on the board
- Eval bar showing who is better
- Play as White or Black: the board flips and all evaluations are shown from your side's view
- Undo, new game, load any position from a FEN string, and copy the current FEN
- Runs fully offline on your own machine

## Requirements

- Python 3.9 or newer (tkinter is included with the standard Windows and macOS installers)
- [Stockfish](https://stockfishchess.org/download/) binary
- The `chess` Python library

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/tausip123/chessengine.git
   cd chessengine
   ```

2. Install the Python dependency:

   ```bash
   pip install -r requirements.txt
   ```

3. Download Stockfish from https://stockfishchess.org/download/ and extract it somewhere on your machine.

   On Ubuntu/Debian you can also install it with `sudo apt install stockfish` (the binary is then at `/usr/games/stockfish`).

4. Open `chess_gui.py` and set `ENGINE_PATH` to the location of your Stockfish executable:

   ```python
   # Windows example
   ENGINE_PATH = r"C:\path\to\stockfish\stockfish-windows-x86-64-universal.exe"

   # Linux example
   ENGINE_PATH = "/usr/games/stockfish"
   ```

## Usage

```bash
python chess_gui.py
```

- Click a piece, then click a destination square to move.
- Use **Switch to Black / White** to flip the board and change the evaluation perspective.
- Use **Set position (FEN)** to analyse any position.
- Pawn promotion automatically promotes to a queen.

## How it works

The app talks to Stockfish through the UCI protocol using [python-chess](https://python-chess.readthedocs.io/). Analysis runs in a background thread so the interface stays responsive, and each position is analysed for about 1.5 seconds with 3 lines (MultiPV).

## Roadmap

- Android version (Termux with a local web interface)
- Adjustable analysis time and number of lines
- Opening name detection

## License

This project is released under the GNU General Public License v3.0. Stockfish and python-chess are both GPL-licensed, so derived work should stay GPL-compatible. Do not commit the Stockfish binary to the repository unless you also include its license and source information.

## Credits

- [Stockfish](https://github.com/official-stockfish/Stockfish) by the Stockfish developers
- [python-chess](https://github.com/niklasf/python-chess) by Niklas Fiekas
