import socket
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog, font
import json
import random
import time
from datetime import datetime
from algorithms import flip_bit


COLORS = {
    'bg_dark': '#0d1117',
    'bg_card': '#161b22',
    'bg_hover': '#21262d',
    'accent': '#58a6ff',
    'accent_green': '#3fb950',
    'accent_red': '#f85149',
    'accent_yellow': '#d29922',
    'accent_purple': '#a371f7',
    'text_primary': '#f0f6fc',
    'text_secondary': '#8b949e',
    'border': '#30363d',
    'x_color': '#ff7b72',
    'o_color': '#79c0ff',
}


class MITMServer:
    def __init__(self):
        self.host = 'localhost'
        self.port = 5000
        self.server_socket = None
        self.clients = {}
        self.running = False
        self.pending_move = None
        self.pending_chat = None
        self.game_board = ['' for _ in range(9)]
        self.current_player = 'X'
        self.gui = None
        self.game_active = False
        self.restart_votes = set()
        
    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(2)
        self.running = True
        threading.Thread(target=self.accept_clients, daemon=True).start()
        
    def accept_clients(self):
        symbols = ['X', 'O']
        count = 0
        while self.running and count < 2:
            try:
                sock, addr = self.server_socket.accept()
                symbol = symbols[count]
                pid = f"player_{count+1}"
                self.clients[pid] = {'socket': sock, 'address': addr, 'symbol': symbol}
                
                self.send_to(sock, {'type': 'assign', 'symbol': symbol})
                if self.gui:
                    self.gui.log(f"Player {symbol} connected from {addr[0]}", 'success')
                    self.gui.update_player_status(symbol, True)
                
                threading.Thread(target=self.handle_client, args=(pid,), daemon=True).start()
                count += 1
                
                if count == 2:
                    self.start_game()
            except Exception as e:
                if self.running:
                    print(f"Accept error: {e}")
    
    def start_game(self):
        self.game_board = ['' for _ in range(9)]
        self.current_player = 'X'
        self.game_active = True
        self.restart_votes = set()
        self.pending_move = None
        
        self.broadcast({'type': 'game_start', 'current': 'X', 'board': self.game_board})
        
        if self.gui:
            self.gui.reset_board()
            self.gui.log("Game started!", 'success')
            self.gui.update_status("Game in progress")
    
    def handle_client(self, pid):
        client = self.clients[pid]
        while self.running:
            try:
                data = client['socket'].recv(4096)
                if not data:
                    break
                msg = json.loads(data.decode())
                self.process_message(pid, msg)
            except:
                break
        
        if self.gui:
            self.gui.update_player_status(client['symbol'], False)
    
    def process_message(self, pid, msg):
        client = self.clients[pid]
        symbol = client['symbol']
        msg_type = msg.get('type')
        
        if msg_type == 'move':
            if self.game_active:
                self.pending_move = {
                    'player_id': pid,
                    'symbol': symbol,
                    'position': msg['position'],
                    'encoded': msg.get('encoded', {})
                }
                if self.gui:
                    self.gui.show_pending_move(self.pending_move)
                    
        elif msg_type == 'chat':
            self.pending_chat = {
                'player_id': pid,
                'symbol': symbol,
                'text': msg['text'],
                'method': msg['method'],
                'encoded': msg['encoded']
            }
            if self.gui:
                self.gui.show_pending_chat(self.pending_chat)
                
        elif msg_type == 'surrender':
            winner = 'O' if symbol == 'X' else 'X'
            self.end_round(winner, f"Player {symbol} surrendered")
            
        elif msg_type == 'vote_restart':
            if self.game_active:
                return
            
            self.restart_votes.add(symbol)
            other = 'O' if symbol == 'X' else 'X'
            
            if self.gui:
                self.gui.log(f"Player {symbol} voted for restart ({len(self.restart_votes)}/2)", 'info')
            
            if other not in self.restart_votes:
                self.send_to_symbol(other, {
                    'type': 'restart_vote',
                    'from': symbol,
                    'message': f'Player {symbol} wants to play again!'
                })
            
            if len(self.restart_votes) >= 2:
                if self.gui:
                    self.gui.log("Both players voted! Starting new game...", 'success')
                self.start_game()
    
    def send_to(self, sock, msg):
        try:
            sock.send(json.dumps(msg).encode())
        except:
            pass
    
    def send_to_symbol(self, symbol, msg):
        for c in self.clients.values():
            if c['symbol'] == symbol:
                self.send_to(c['socket'], msg)
                break
    
    def broadcast(self, msg):
        for c in self.clients.values():
            self.send_to(c['socket'], msg)
    
    def forward_move(self, move, modified=False, mod_type=None):
        if not move or not self.game_active:
            return
        
        pos = move['position']
        symbol = move['symbol']
        
        if 0 <= pos <= 8 and self.game_board[pos] == '':
            self.game_board[pos] = symbol
            
            self.broadcast({
                'type': 'move_made',
                'position': pos,
                'symbol': symbol,
                'modified': modified,
                'mod_type': mod_type
            })
            
            if self.gui:
                self.gui.update_board(pos, symbol)
            
            winner = self.check_winner()
            if winner:
                if winner == 'Draw':
                    self.end_round('Draw', "It's a draw!")
                else:
                    self.end_round(winner, f"Player {winner} wins!")
            else:
                self.current_player = 'O' if self.current_player == 'X' else 'X'
                self.broadcast({'type': 'turn', 'current': self.current_player})
        
        self.pending_move = None
        if self.gui:
            self.gui.clear_pending_move()
    
    def forward_chat(self, chat, inject_error=False, error_type=None):
        if not chat:
            return
        
        encoded = chat['encoded']
        if inject_error and error_type:
            if error_type == 'flip_bit' and len(encoded) > 0:
                pos = random.randint(0, len(encoded)-1)
                encoded = flip_bit(encoded, pos)
                if self.gui:
                    self.gui.log(f"Flipped bit at position {pos}", 'warning')
            elif error_type == 'flip_multi' and len(encoded) > 0:
                for _ in range(min(3, len(encoded))):
                    pos = random.randint(0, len(encoded)-1)
                    encoded = flip_bit(encoded, pos)
                if self.gui:
                    self.gui.log("Flipped multiple bits", 'warning')
        
        other_symbol = 'O' if chat['symbol'] == 'X' else 'X'
        self.send_to_symbol(other_symbol, {
            'type': 'chat_msg',
            'from': chat['symbol'],
            'encoded': encoded,
            'method': chat['method'],
            'original': chat['text'],
            'modified': inject_error
        })
        
        self.pending_chat = None
        if self.gui:
            self.gui.clear_pending_chat()
    
    def end_round(self, winner, reason):
        self.game_active = False
        self.restart_votes = set()
        
        self.broadcast({
            'type': 'round_over',
            'winner': winner,
            'reason': reason
        })
        
        if self.gui:
            self.gui.log(f"Round over: {reason}", 'info')
            self.gui.update_status("Round ended")
    
    def server_restart(self, note=""):
        self.broadcast({'type': 'server_restart', 'note': note})
        time.sleep(0.1)
        self.start_game()
    
    def server_end(self, note=""):
        self.game_active = False
        self.broadcast({'type': 'server_end', 'note': note})
        if self.gui:
            self.gui.log(f"Game ended: {note}", 'error')
    
    def check_winner(self):
        b = self.game_board
        lines = [
            [0,1,2], [3,4,5], [6,7,8],
            [0,3,6], [1,4,7], [2,5,8],
            [0,4,8], [2,4,6]
        ]
        for line in lines:
            if b[line[0]] == b[line[1]] == b[line[2]] != '':
                return b[line[0]]
        if '' not in b:
            return 'Draw'
        return None
    
    def stop(self):
        self.running = False
        for c in self.clients.values():
            try:
                c['socket'].close()
            except:
                pass
        if self.server_socket:
            self.server_socket.close()


class ModernButton(tk.Canvas):
    def __init__(self, parent, text, command, bg=COLORS['accent'], fg='white', 
                 width=120, height=36, icon=None):
        super().__init__(parent, width=width, height=height, bg=COLORS['bg_dark'], 
                        highlightthickness=0, cursor='hand2')
        self.command = command
        self.bg = bg
        self.fg = fg
        self.text = text
        self.w = width
        self.h = height
        
        self.draw_button(bg)
        self.bind('<Enter>', lambda e: self.draw_button(self.lighten(bg)))
        self.bind('<Leave>', lambda e: self.draw_button(bg))
        self.bind('<Button-1>', lambda e: self.on_click())
    
    def draw_button(self, color):
        self.delete('all')
        self.create_rectangle(0, 0, self.w, self.h, fill=color, outline='')
        self.create_text(self.w//2, self.h//2, text=self.text, fill=self.fg, 
                        font=('Segoe UI', 9, 'bold'))
    
    def lighten(self, color):
        r = min(255, int(color[1:3], 16) + 25)
        g = min(255, int(color[3:5], 16) + 25)
        b = min(255, int(color[5:7], 16) + 25)
        return f'#{r:02x}{g:02x}{b:02x}'
    
    def on_click(self):
        if self.command:
            self.command()


class ServerGUI:
    def __init__(self, server):
        self.server = server
        self.server.gui = self
        
        self.root = tk.Tk()
        self.root.title("MITM Control Panel")
        self.root.geometry("950x700")
        self.root.configure(bg=COLORS['bg_dark'])
        self.root.minsize(750, 550)
        self.root.resizable(True, True)  # Enable resizing
        # Configure root grid weights for resizing
        self.root.grid_rowconfigure(0, weight=0)  # Header
        self.root.grid_rowconfigure(1, weight=1)  # Main content
        self.root.grid_columnconfigure(0, weight=1)
        
        self.title_font = font.Font(family='Segoe UI', size=18, weight='bold')
        self.subtitle_font = font.Font(family='Segoe UI', size=10)
        self.cell_font = font.Font(family='Segoe UI', size=20, weight='bold')
        self.small_font = font.Font(family='Consolas', size=9)
        
        self.setup_ui()
        
    def setup_ui(self):
        # Header section
        header = tk.Frame(self.root, bg=COLORS['bg_dark'])
        header.grid(row=0, column=0, sticky='ew', padx=20, pady=15)
        
        title_frame = tk.Frame(header, bg=COLORS['bg_dark'])
        title_frame.pack(side='left')
        
        tk.Label(title_frame, text="MITM", font=self.title_font,
                bg=COLORS['bg_dark'], fg=COLORS['accent_purple']).pack(side='left')
        tk.Label(title_frame, text=" Control Panel", font=self.title_font,
                bg=COLORS['bg_dark'], fg=COLORS['text_primary']).pack(side='left')
        
        status_frame = tk.Frame(header, bg=COLORS['bg_dark'])
        status_frame.pack(side='right')
        
        self.status_lbl = tk.Label(status_frame, text="● Waiting for players...",
                                   font=self.subtitle_font, bg=COLORS['bg_dark'],
                                   fg=COLORS['text_secondary'])
        self.status_lbl.pack(side='right')
        
        self.player_x = tk.Label(status_frame, text="X ○", font=self.subtitle_font,
                                bg=COLORS['bg_dark'], fg=COLORS['text_secondary'])
        self.player_x.pack(side='right', padx=15)
        
        self.player_o = tk.Label(status_frame, text="O ○", font=self.subtitle_font,
                                bg=COLORS['bg_dark'], fg=COLORS['text_secondary'])
        self.player_o.pack(side='right', padx=5)
        
        # Main content area with grid for resizing
        main = tk.Frame(self.root, bg=COLORS['bg_dark'])
        main.grid(row=1, column=0, sticky='nsew', padx=20)
        main.grid_columnconfigure(0, weight=0, minsize=280)  # Left side fixed width
        main.grid_columnconfigure(1, weight=1)  # Right side expands
        main.grid_rowconfigure(0, weight=1)
        
        left = tk.Frame(main, bg=COLORS['bg_dark'])
        left.grid(row=0, column=0, sticky='ns', padx=(0, 10))
        
        board_card = tk.Frame(left, bg=COLORS['bg_card'])
        board_card.pack(fill='x', pady=(0, 15))
        
        tk.Label(board_card, text="GAME BOARD", font=('Segoe UI', 9, 'bold'),
                bg=COLORS['bg_card'], fg=COLORS['text_secondary']).pack(anchor='w', padx=15, pady=10)
        
        board_frame = tk.Frame(board_card, bg=COLORS['border'], padx=2, pady=2)
        board_frame.pack(padx=15, pady=(0, 15))
        
        grid = tk.Frame(board_frame, bg=COLORS['bg_card'])
        grid.pack()
        
        self.board_btns = []
        for i in range(9):
            cell = tk.Frame(grid, bg=COLORS['bg_dark'], width=65, height=65)
            cell.grid(row=i//3, column=i%3, padx=1, pady=1)
            cell.grid_propagate(False)
            
            lbl = tk.Label(cell, text='', font=self.cell_font, bg=COLORS['bg_dark'],
                          fg=COLORS['text_primary'])
            lbl.place(relx=0.5, rely=0.5, anchor='center')
            self.board_btns.append(lbl)
        
        game_ctrl = tk.Frame(left, bg=COLORS['bg_card'])
        game_ctrl.pack(fill='x')
        
        tk.Label(game_ctrl, text="GAME CONTROLS", font=('Segoe UI', 9, 'bold'),
                bg=COLORS['bg_card'], fg=COLORS['text_secondary']).pack(anchor='w', padx=15, pady=10)
        
        btn_frame = tk.Frame(game_ctrl, bg=COLORS['bg_card'])
        btn_frame.pack(padx=15, pady=(0, 15))
        
        ModernButton(btn_frame, "Restart Game", self.restart_game,
                    bg=COLORS['accent'], width=140).pack(side='left', padx=3)
        ModernButton(btn_frame, "End Game", self.end_game,
                    bg=COLORS['accent_red'], width=120).pack(side='left', padx=3)
        
        # Right panel - controls and log (resizable)
        right = tk.Frame(main, bg=COLORS['bg_dark'])
        right.grid(row=0, column=1, sticky='nsew', padx=(10, 0))
        right.grid_rowconfigure(3, weight=1)  # Log section expands
        right.grid_columnconfigure(0, weight=1)
        
        pending_card = tk.Frame(right, bg=COLORS['bg_card'])
        pending_card.grid(row=0, column=0, sticky='ew', pady=(0, 10))
        
        pending_header = tk.Frame(pending_card, bg=COLORS['bg_card'])
        pending_header.pack(fill='x', padx=15, pady=10)
        
        tk.Label(pending_header, text="📩 PENDING MOVE", font=('Segoe UI', 9, 'bold'),
                bg=COLORS['bg_card'], fg=COLORS['text_secondary']).pack(side='left')
        
        self.pending_txt = tk.Text(pending_card, height=3, bg=COLORS['bg_dark'],
                                  fg=COLORS['accent_green'], font=self.small_font,
                                  bd=0, highlightthickness=0)
        self.pending_txt.pack(fill='x', padx=15, pady=(0, 10))
        self.pending_txt.insert('1.0', 'No pending move')
        
        move_btns = tk.Frame(pending_card, bg=COLORS['bg_card'])
        move_btns.pack(padx=15, pady=(0, 15))
        
        for txt, cmd, clr in [("✓ Pass", self.pass_move, COLORS['accent_green']),
                              ("⟲ Flip", self.flip_move, COLORS['accent_yellow']),
                              ("⊕ Random", self.random_move, COLORS['accent_purple'])]:
            ModernButton(move_btns, txt, cmd, bg=clr, width=100).pack(side='left', padx=3)
        
        chat_card = tk.Frame(right, bg=COLORS['bg_card'])
        chat_card.grid(row=1, column=0, sticky='ew', pady=(0, 10))
        
        tk.Label(chat_card, text="💬 PENDING CHAT", font=('Segoe UI', 9, 'bold'),
                bg=COLORS['bg_card'], fg=COLORS['text_secondary']).pack(anchor='w', padx=15, pady=10)
        
        self.chat_pending = tk.Text(chat_card, height=2, bg=COLORS['bg_dark'],
                                   fg=COLORS['accent_green'], font=self.small_font,
                                   bd=0, highlightthickness=0)
        self.chat_pending.pack(fill='x', padx=15, pady=(0, 10))
        self.chat_pending.insert('1.0', 'No pending chat')
        
        chat_btns = tk.Frame(chat_card, bg=COLORS['bg_card'])
        chat_btns.pack(padx=15, pady=(0, 15))
        
        for txt, inj, err, clr in [("✓ Pass", False, None, COLORS['accent_green']),
                                    ("⟲ Flip 1 Bit", True, 'flip_bit', COLORS['accent_yellow']),
                                    ("⟲ Multi Flip", True, 'flip_multi', COLORS['accent_red'])]:
            ModernButton(chat_btns, txt, lambda i=inj, e=err: self.forward_chat(i, e),
                        bg=clr, width=110).pack(side='left', padx=3)
        
        log_card = tk.Frame(right, bg=COLORS['bg_card'])
        log_card.grid(row=3, column=0, sticky='nsew', pady=(0, 10))
        log_card.grid_rowconfigure(1, weight=1)
        log_card.grid_columnconfigure(0, weight=1)
        
        tk.Label(log_card, text="📋 ACTIVITY LOG", font=('Segoe UI', 9, 'bold'),
                bg=COLORS['bg_card'], fg=COLORS['text_secondary']).grid(row=0, column=0, sticky='w', padx=15, pady=10)
        
        self.log_text = tk.Text(log_card, bg=COLORS['bg_dark'], fg=COLORS['text_secondary'],
                               font=self.small_font, bd=0, highlightthickness=0)
        self.log_text.grid(row=1, column=0, sticky='nsew', padx=15, pady=(0, 15))
        
    def log(self, msg, level='info'):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert('end', f"[{timestamp}] {msg}\n")
        self.log_text.see('end')
    
    def update_status(self, s):
        self.status_lbl.config(text=f"● {s}")
    
    def update_player_status(self, symbol, connected):
        color = COLORS['accent_green'] if connected else COLORS['text_secondary']
        icon = "●" if connected else "○"
        if symbol == 'X':
            self.player_x.config(text=f"X {icon}", fg=color)
        else:
            self.player_o.config(text=f"O {icon}", fg=color)
    
    def show_pending_move(self, m):
        self.pending_txt.delete('1.0', 'end')
        info = f"Player: {m['symbol']}  |  Position: {m['position']}"
        self.pending_txt.insert('1.0', info)
        self.log(f"Move received: {m['symbol']} → Position {m['position']}", 'info')
    
    def clear_pending_move(self):
        self.pending_txt.delete('1.0', 'end')
        self.pending_txt.insert('1.0', 'No pending move')
    
    def show_pending_chat(self, c):
        self.chat_pending.delete('1.0', 'end')
        info = f"From: {c['symbol']}  |  Method: {c['method']}  |  Text: {c['text'][:30]}..."
        self.chat_pending.insert('1.0', info)
        self.log(f"Chat from {c['symbol']}: {c['text'][:20]}...", 'info')
    
    def clear_pending_chat(self):
        self.chat_pending.delete('1.0', 'end')
        self.chat_pending.insert('1.0', 'No pending chat')
    
    def update_board(self, pos, sym):
        colors = {'X': COLORS['x_color'], 'O': COLORS['o_color']}
        self.board_btns[pos].config(text=sym, fg=colors.get(sym, COLORS['text_primary']))
    
    def reset_board(self):
        for b in self.board_btns:
            b.config(text='', fg=COLORS['text_primary'])
        self.clear_pending_move()
        self.clear_pending_chat()
    
    def pass_move(self):
        if self.server.pending_move:
            self.log("Move passed through", 'success')
            self.server.forward_move(self.server.pending_move)
        else:
            messagebox.showinfo("Info", "No pending move")
    
    def flip_move(self):
        if self.server.pending_move:
            m = self.server.pending_move
            orig = m['position']
            new = (orig + random.randint(1, 8)) % 9
            for _ in range(9):
                if self.server.game_board[new] == '':
                    break
                new = (new + 1) % 9
            m['position'] = new
            self.log(f"Position flipped: {orig} → {new}", 'warning')
            self.server.forward_move(m, True, 'flip')
        else:
            messagebox.showinfo("Info", "No pending move")
    
    def random_move(self):
        if self.server.pending_move:
            m = self.server.pending_move
            orig = m['position']
            empty = [i for i, x in enumerate(self.server.game_board) if x == '']
            if empty:
                m['position'] = random.choice(empty)
                self.log(f"Random position: {orig} → {m['position']}", 'warning')
                self.server.forward_move(m, True, 'random')
        else:
            messagebox.showinfo("Info", "No pending move")
    
    def forward_chat(self, inject, err_type):
        if self.server.pending_chat:
            if inject:
                self.log(f"Injecting error: {err_type}", 'warning')
            else:
                self.log("Chat passed through", 'success')
            self.server.forward_chat(self.server.pending_chat, inject, err_type)
        else:
            messagebox.showinfo("Info", "No pending chat")
    
    def restart_game(self):
        note = simpledialog.askstring("Restart", "Note (optional):", parent=self.root) or ""
        self.server.server_restart(note)
    
    def end_game(self):
        note = simpledialog.askstring("End Game", "Note (optional):", parent=self.root) or ""
        self.server.server_end(note)
    
    def run(self):
        self.log("Server starting...", 'info')
        self.server.start()
        self.log(f"Listening on {self.server.host}:{self.server.port}", 'success')
        self.root.protocol("WM_DELETE_WINDOW", lambda: [self.server.stop(), self.root.destroy()])
        self.root.mainloop()


if __name__ == "__main__":
    ServerGUI(MITMServer()).run()
