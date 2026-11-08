import math
import threading
import tkinter as tk
from tkinter import simpledialog, messagebox
import chess
import chess.engine

ENGINE_PATH = r"C:\Users\Tausip\Downloads\stockfish-windows-x86-64-universal\stockfish\stockfish-windows-x86-64-universal.exe"
SQ = 72
LIGHT, DARK = "#f0d9b5", "#b58863"
SEL, LAST, ARROW = "#f6f669", "#cdd26a", "#3a9d4a"
GLYPH = {"p": "♟", "n": "♞", "b": "♝", "r": "♜", "q": "♛", "k": "♚"}


class App:
    def __init__(self, root):
        self.root = root
        root.title("Chess Analyzer")
        self.engine = chess.engine.SimpleEngine.popen_uci(ENGINE_PATH)
        self.lock = threading.Lock()
        self.board = chess.Board()
        self.flipped = False  # False = I play White, True = I play Black
        self.selected = None
        self.best_move = None
        self.job = 0

        self.white_share = 0.5
        self.bar_label = "0.0"
        self.bar = tk.Canvas(root, width=40, height=SQ * 8, highlightthickness=0)
        self.bar.grid(row=0, column=0, padx=(10, 0), pady=10)
        self.canvas = tk.Canvas(root, width=SQ * 8, height=SQ * 8, highlightthickness=0)
        self.canvas.grid(row=0, column=1, pady=10)
        self.canvas.bind("<Button-1>", self.click)

        panel = tk.Frame(root)
        panel.grid(row=0, column=2, sticky="n", padx=10, pady=10)
        self.info = tk.StringVar()
        tk.Label(panel, textvariable=self.info, justify="left", anchor="w",
                 font=("Consolas", 11), width=40, height=8).pack(anchor="w")
        self.side_btn = tk.Button(panel, text="Switch to Black", width=20, command=self.toggle_side)
        self.side_btn.pack(pady=3, anchor="w")
        tk.Button(panel, text="Undo", width=20, command=self.undo).pack(pady=3, anchor="w")
        tk.Button(panel, text="New game", width=20, command=self.new_game).pack(pady=3, anchor="w")
        tk.Button(panel, text="Set position (FEN)", width=20, command=self.set_fen).pack(pady=3, anchor="w")
        tk.Button(panel, text="Copy FEN", width=20, command=self.copy_fen).pack(pady=3, anchor="w")

        root.protocol("WM_DELETE_WINDOW", self.close)
        self.draw()
        self.analyse_async()

    # ---------- coordinates ----------
    def sq_xy(self, sq):
        f, r = chess.square_file(sq), chess.square_rank(sq)
        col, row = (7 - f, r) if self.flipped else (f, 7 - r)
        return col * SQ, row * SQ

    def xy_sq(self, x, y):
        col, row = x // SQ, y // SQ
        f, r = (7 - col, row) if self.flipped else (col, 7 - row)
        return chess.square(int(f), int(r))

    # ---------- drawing ----------
    def draw_bar(self):
        b = self.bar
        b.delete("all")
        W, H = 40, SQ * 8
        wh = H * self.white_share
        b.create_rectangle(0, 0, W, H, fill="#333333", outline="")
        if self.flipped:
            b.create_rectangle(0, 0, W, wh, fill="#f0f0f0", outline="")
        else:
            b.create_rectangle(0, H - wh, W, H, fill="#f0f0f0", outline="")
        b.create_line(0, H / 2, W, H / 2, fill="#888888")
        bottom_is_white = not self.flipped
        bottom_share = self.white_share if bottom_is_white else 1 - self.white_share
        leading_bottom = bottom_share >= 0.5
        leading_white = bottom_is_white if leading_bottom else not bottom_is_white
        b.create_text(W / 2, H - 14 if leading_bottom else 14, text=self.bar_label,
                      fill="black" if leading_white else "white",
                      font=("Segoe UI", 9, "bold"))

    def draw(self):
        c = self.canvas
        c.delete("all")
        self.draw_bar()
        last = self.board.peek() if self.board.move_stack else None
        for sq in chess.SQUARES:
            x, y = self.sq_xy(sq)
            light = (chess.square_file(sq) + chess.square_rank(sq)) % 2 == 1
            color = LIGHT if light else DARK
            if last and sq in (last.from_square, last.to_square):
                color = LAST
            if sq == self.selected:
                color = SEL
            c.create_rectangle(x, y, x + SQ, y + SQ, fill=color, outline=color)
            label_color = DARK if light else LIGHT
            if y == SQ * 7:
                c.create_text(x + SQ - 8, y + SQ - 8, text=chess.FILE_NAMES[chess.square_file(sq)],
                              fill=label_color, font=("Segoe UI", 8, "bold"))
            if x == 0:
                c.create_text(x + 8, y + 8, text=str(chess.square_rank(sq) + 1),
                              fill=label_color, font=("Segoe UI", 8, "bold"))

        if self.best_move:
            x1, y1 = self.sq_xy(self.best_move.from_square)
            x2, y2 = self.sq_xy(self.best_move.to_square)
            c.create_line(x1 + SQ / 2, y1 + SQ / 2, x2 + SQ / 2, y2 + SQ / 2,
                          fill=ARROW, width=10, arrow=tk.LAST, arrowshape=(22, 26, 10))

        font = ("Segoe UI Symbol", 40)
        for sq, p in self.board.piece_map().items():
            x, y = self.sq_xy(sq)
            cx, cy = x + SQ / 2, y + SQ / 2
            g = GLYPH[p.symbol().lower()]
            if p.color == chess.WHITE:
                for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
                    c.create_text(cx + dx, cy + dy, text=g, font=font, fill="black")
                c.create_text(cx, cy, text=g, font=font, fill="white")
            else:
                c.create_text(cx, cy, text=g, font=font, fill="#222222")

        if self.selected is not None:
            for m in self.board.legal_moves:
                if m.from_square == self.selected:
                    x, y = self.sq_xy(m.to_square)
                    c.create_oval(x + SQ / 2 - 8, y + SQ / 2 - 8, x + SQ / 2 + 8, y + SQ / 2 + 8,
                                  fill="#555555", outline="")

    # ---------- interaction ----------
    def click(self, e):
        if self.board.is_game_over() or not (0 <= e.x < SQ * 8 and 0 <= e.y < SQ * 8):
            return
        sq = self.xy_sq(e.x, e.y)
        if self.selected is None:
            p = self.board.piece_at(sq)
            if p and p.color == self.board.turn:
                self.selected = sq
        else:
            move = chess.Move(self.selected, sq)
            piece = self.board.piece_at(self.selected)
            if piece.piece_type == chess.PAWN and chess.square_rank(sq) in (0, 7):
                move.promotion = chess.QUEEN  # auto-queen
            if move in self.board.legal_moves:
                self.board.push(move)
                self.selected = None
                self.best_move = None
                self.analyse_async()
            else:
                p = self.board.piece_at(sq)
                self.selected = sq if p and p.color == self.board.turn else None
        self.draw()

    def toggle_side(self):
        self.flipped = not self.flipped
        self.side_btn.config(text="Switch to White" if self.flipped else "Switch to Black")
        self.draw()
        self.analyse_async()

    def undo(self):
        if self.board.move_stack:
            self.board.pop()
        self.selected = None
        self.best_move = None
        self.draw()
        self.analyse_async()

    def new_game(self):
        self.board = chess.Board()
        self.selected = None
        self.best_move = None
        self.draw()
        self.analyse_async()

    def set_fen(self):
        fen = simpledialog.askstring("Set position", "Paste a FEN:")
        if not fen:
            return
        try:
            self.board = chess.Board(fen.strip())
        except ValueError:
            messagebox.showerror("Error", "Invalid FEN")
            return
        self.selected = None
        self.best_move = None
        self.draw()
        self.analyse_async()

    def copy_fen(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.board.fen())

    # ---------- engine ----------
    def analyse_async(self):
        self.job += 1
        job = self.job
        self.info.set("Analysing...")
        threading.Thread(target=self.work, args=(job, self.board.copy()), daemon=True).start()

    def work(self, job, board):
        with self.lock:
            if job != self.job:
                return
            result = None
            if not board.is_game_over():
                result = self.engine.analyse(board, chess.engine.Limit(time=1.5), multipv=3)
        self.root.after(0, self.show, job, board, result)

    def show(self, job, board, result):
        if job != self.job:
            return
        if result is None:
            self.best_move = None
            res = board.result()
            self.white_share = {"1-0": 1.0, "0-1": 0.0}.get(res, 0.5)
            self.bar_label = res
            self.info.set("Game over: " + res)
        else:
            me = chess.BLACK if self.flipped else chess.WHITE
            lines = [f"Eval from {'Black' if self.flipped else 'White'}'s view "
                     f"({'White' if board.turn else 'Black'} to move)"]
            for i, line in enumerate(result, 1):
                s = line["score"].pov(me)
                ev = f"#{s.mate()}" if s.is_mate() else f"{s.score() / 100:+.2f}"
                if i == 1:
                    self.bar_label = ev
                lines.append(f"{i}. {ev:>6}  {board.variation_san(line['pv'][:6])}")
            cp = result[0]["score"].white().score(mate_score=10000)
            self.white_share = 1 / (1 + math.exp(-cp / 400))
            self.best_move = result[0]["pv"][0]
            self.info.set("\n".join(lines))
        self.draw()

    def close(self):
        try:
            self.engine.quit()
        except Exception:
            pass
        self.root.destroy()


root = tk.Tk()
App(root)
root.mainloop()