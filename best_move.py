import chess
import chess.engine

path = r"C:\Users\Tausip\Downloads\stockfish-windows-x86-64-universal\stockfish\stockfish-windows-x86-64-universal.exe"
engine = chess.engine.SimpleEngine.popen_uci(path)
board = chess.Board()

def analyse():
    print()
    print(board)
    print("\nFEN:", board.fen())
    if board.is_game_over():
        print("Game over:", board.result())
        return
    info = engine.analyse(board, chess.engine.Limit(time=2.0), multipv=3)
    print("\nTop moves (eval is from White's view):")
    for i, line in enumerate(info, 1):
        score = line["score"].white()
        ev = f"#{score.mate()}" if score.is_mate() else f"{score.score() / 100:+.2f}"
        print(f"{i}. {ev:>7}  {board.variation_san(line['pv'][:6])}")

print("Commands: a move (e4, Nf3, e2e4) | fen <FEN> | u = undo | new | q = quit")
analyse()
while True:
    cmd = input("\n> ").strip()
    if cmd == "q":
        break
    elif cmd == "u":
        if board.move_stack:
            board.pop()
    elif cmd == "new":
        board = chess.Board()
    elif cmd.startswith("fen "):
        try:
            board = chess.Board(cmd[4:])
        except ValueError:
            print("Bad FEN")
            continue
    else:
        try:
            board.push_san(cmd)
        except ValueError:
            try:
                board.push_uci(cmd)
            except ValueError:
                print("Invalid or illegal move")
                continue
    analyse()

engine.quit()