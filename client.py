import socket
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox, font
import json
from algorithms import encode_move, encode_message, decode_message

COLORS = {
    'bg_dark': '#0d1117',
    'bg_card': '#161b22',
    'bg_hover': '#21262d',
    'accent': '#58a6ff',
    'accent_green': '#3fb950',
    'accent_red': '#f85149',
    'accent_yellow': '#d29922',
    'text_primary': '#f0f6fc',
    'text_secondary': '#8b949e',
    'border': '#30363d',
    'x_color': '#ff7b72',
    'o_color': '#79c0ff',
}

class GameClient:
    def __init__(self, host='localhost', port=5000):
        self.host = host
        self.port = port
        self.socket = None
        self.symbol = None
        self.my_turn = False
        self.gui = None
        self.connected = False
        self.game_active = False
        
    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            threading.Thread(target=self.receive_loop, daemon=True).start()
            return True
        except:
            return False
    
    def receive_loop(self):
        while self.connected:
            try:
                data = self.socket.recv(4096)
                if not data:
                    break
                msg = json.loads(data.decode())
                self.handle_msg(msg)
            except:
                break
    
    def handle_msg(self, msg):
        t = msg.get('type')
        if t == 'assign':
            self.symbol = msg['symbol']
            self.safe_gui(lambda: self.gui.set_symbol(self.symbol))
            self.safe_gui(lambda: self.gui.notify(f"You are Player {self.symbol}", 'success'))
        elif t == 'game_start':
            self.game_active = True
            self.my_turn = (msg['current'] == self.symbol)
            self.safe_gui(lambda: self.gui.reset_board())
            self.safe_gui(lambda: self.gui.notify("Game started!", 'success'))
            self.safe_gui(lambda: self.gui.set_turn(self.my_turn))
        elif t == 'move_made':
            pos = msg['position']
            sym = msg['symbol']
            self.safe_gui(lambda: self.gui.set_cell(pos, sym))
            if msg.get('modified'):
                self.safe_gui(lambda: self.gui.notify("Move was MODIFIED!", 'warning'))
        elif t == 'turn':
            self.my_turn = (msg['current'] == self.symbol)
            self.safe_gui(lambda: self.gui.set_turn(self.my_turn))
        elif t == 'round_over':
            self.game_active = False
            self.my_turn = False
            self.safe_gui(lambda: self.gui.show_result(msg['winner'], msg['reason']))
        elif t == 'restart_vote':
            from_p = msg['from']
            self.safe_gui(lambda: self.gui.notify(f"Player {from_p} wants rematch!", 'info'))
            self.safe_gui(lambda: self.gui.show_restart_prompt(from_p))
        elif t == 'server_restart':
            self.safe_gui(lambda: self.gui.notify(f"Server restarted", 'info'))
        elif t == 'server_end':
            self.game_active = False
            self.safe_gui(lambda: self.gui.notify("Server ended game", 'error'))
        elif t == 'chat_msg':
            self.safe_gui(lambda: self.gui.receive_chat(msg))
    
    def safe_gui(self, func):
        if self.gui:
            self.gui.root.after(0, func)
    
    def send(self, msg):
        try:
            self.socket.send(json.dumps(msg).encode())
            return True
        except:
            return False
    
    def send_move(self, pos):
        if not self.my_turn or not self.game_active:
            return False
        encoded = encode_move(pos, self.symbol)
        self.send({'type': 'move', 'position': pos, 'symbol': self.symbol, 'encoded': encoded})
        self.my_turn = False
        self.safe_gui(lambda: self.gui.set_turn(False))
        return True
    
    def send_chat(self, text, method):
        enc = encode_message(text, method)
        self.send({'type': 'chat', 'text': text, 'method': method, 'encoded': enc['encoded_data']})
    
    def vote_restart(self):
        self.send({'type': 'vote_restart'})
    
    def surrender(self):
        self.send({'type': 'surrender'})
    
    def disconnect(self):
        self.connected = False
        if self.socket:
            self.socket.close()

class ModernButton(tk.Canvas):
    def __init__(self, parent, text, command, bg=COLORS['accent'], fg='white', width=120, height=36):
        super().__init__(parent, width=width, height=height, bg=COLORS['bg_dark'], highlightthickness=0, cursor='hand2')
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
        self.create_rectangle(2, 2, self.w-2, self.h-2, fill=color, outline='')
        self.create_text(self.w//2, self.h//2, text=self.text, fill=self.fg, font=('Segoe UI', 10, 'bold'))
    
    def lighten(self, color):
        r = min(255, int(color[1:3], 16) + 20)
        g = min(255, int(color[3:5], 16) + 20)
        b = min(255, int(color[5:7], 16) + 20)
        return f'#{r:02x}{g:02x}{b:02x}'
    
    def on_click(self):
        if self.command:
            self.command()

class ClientGUI:
    def __init__(self, client):
        self.client = client
        self.client.gui = self
        self.board = ['' for _ in range(9)]
        self.root = tk.Tk()
        self.root.title("XO Game")
        self.root.geometry("800x600")
        self.root.configure(bg=COLORS['bg_dark'])
        self.root.minsize(600, 500)
        self.root.resizable(True, True)  # Enable resizing
        # Configure root grid weights for resizing
        self.root.grid_rowconfigure(0, weight=0)  # Header
        self.root.grid_rowconfigure(1, weight=1)  # Main content
        self.root.grid_columnconfigure(0, weight=1)
        self.title_font = font.Font(family='Segoe UI', size=24, weight='bold')
        self.subtitle_font = font.Font(family='Segoe UI', size=12)
        self.cell_font = font.Font(family='Segoe UI', size=32, weight='bold')
        self.small_font = font.Font(family='Consolas', size=9)
        self.setup_ui()
        
    def setup_ui(self):
        # Header section
        header = tk.Frame(self.root, bg=COLORS['bg_dark'])
        header.grid(row=0, column=0, sticky='ew', pady=15)
        title_frame = tk.Frame(header, bg=COLORS['bg_dark'])
        title_frame.pack()
        tk.Label(title_frame, text="TIC", font=self.title_font, bg=COLORS['bg_dark'], fg=COLORS['x_color']).pack(side='left')
        tk.Label(title_frame, text="-", font=self.title_font, bg=COLORS['bg_dark'], fg=COLORS['text_secondary']).pack(side='left')
        tk.Label(title_frame, text="TAC", font=self.title_font, bg=COLORS['bg_dark'], fg=COLORS['accent']).pack(side='left')
        tk.Label(title_frame, text="-", font=self.title_font, bg=COLORS['bg_dark'], fg=COLORS['text_secondary']).pack(side='left')
        tk.Label(title_frame, text="TOE", font=self.title_font, bg=COLORS['bg_dark'], fg=COLORS['o_color']).pack(side='left')
        
        status_frame = tk.Frame(header, bg=COLORS['bg_dark'])
        status_frame.pack(pady=5)
        self.sym_lbl = tk.Label(status_frame, text="Connecting...", font=self.subtitle_font, bg=COLORS['bg_dark'], fg=COLORS['text_secondary'])
        self.sym_lbl.pack(side='left', padx=20)
        self.turn_lbl = tk.Label(status_frame, text="", font=('Segoe UI', 14, 'bold'), bg=COLORS['bg_dark'], fg=COLORS['accent_yellow'])
        self.turn_lbl.pack(side='left', padx=20)
        
        # Main content area with grid for resizing
        main = tk.Frame(self.root, bg=COLORS['bg_dark'])
        main.grid(row=1, column=0, sticky='nsew', padx=20, pady=10)
        main.grid_columnconfigure(0, weight=1)  # Left side expands
        main.grid_columnconfigure(1, weight=1)  # Right side expands
        main.grid_rowconfigure(0, weight=1)
        
        left = tk.Frame(main, bg=COLORS['bg_dark'])
        left.grid(row=0, column=0, sticky='nsew')
        
        board_size = 270
        cell_size = 80
        self.board_canvas = tk.Canvas(left, width=board_size, height=board_size, bg=COLORS['bg_card'], highlightthickness=2, highlightbackground=COLORS['border'])
        self.board_canvas.pack(pady=10)
        
        for i in range(1, 3):
            x = i * (board_size // 3)
            self.board_canvas.create_line(x, 10, x, board_size-10, fill=COLORS['accent'], width=3)
            y = i * (board_size // 3)
            self.board_canvas.create_line(10, y, board_size-10, y, fill=COLORS['accent'], width=3)
        
        self.btns = []
        for i in range(9):
            row, col = i // 3, i % 3
            x1, y1 = col * (board_size // 3) + 8, row * (board_size // 3) + 8
            x2, y2 = x1 + cell_size - 6, y1 + cell_size - 6
            rect = self.board_canvas.create_rectangle(x1, y1, x2, y2, fill=COLORS['bg_card'], outline='', tags=f'cell_{i}')
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            text_id = self.board_canvas.create_text(cx, cy, text='', font=self.cell_font, fill=COLORS['text_primary'], tags=f'text_{i}')
            self.btns.append({'rect': rect, 'text': text_id})
            self.board_canvas.tag_bind(f'cell_{i}', '<Button-1>', lambda e, p=i: self.click_cell(p))
            self.board_canvas.tag_bind(f'text_{i}', '<Button-1>', lambda e, p=i: self.click_cell(p))
            self.board_canvas.tag_bind(f'cell_{i}', '<Enter>', lambda e, r=rect: self.board_canvas.itemconfig(r, fill=COLORS['bg_hover']))
            self.board_canvas.tag_bind(f'cell_{i}', '<Leave>', lambda e, r=rect: self.board_canvas.itemconfig(r, fill=COLORS['bg_card']))
        
        ctrl = tk.Frame(left, bg=COLORS['bg_dark'])
        ctrl.pack(pady=15)
        ModernButton(ctrl, "Surrender", self.surrender, bg=COLORS['accent_red'], width=100, height=34).pack(side='left', padx=5)
        ModernButton(ctrl, "Exit", self.quit, bg=COLORS['bg_hover'], width=80, height=34).pack(side='left', padx=5)
        
        # Right panel - chat and notifications (resizable)
        right = tk.Frame(main, bg=COLORS['bg_dark'])
        right.grid(row=0, column=1, sticky='nsew', padx=(20, 0))
        right.grid_rowconfigure(1, weight=1)  # Chat section expands
        right.grid_columnconfigure(0, weight=1)
        
        notif_card = tk.Frame(right, bg=COLORS['bg_card'])
        notif_card.grid(row=0, column=0, sticky='ew', pady=(0, 10))
        tk.Label(notif_card, text="NOTIFICATIONS", font=('Segoe UI', 9, 'bold'), bg=COLORS['bg_card'], fg=COLORS['text_secondary']).pack(anchor='w', padx=12, pady=8)
        self.notif = tk.Text(notif_card, height=4, bg=COLORS['bg_dark'], fg=COLORS['text_secondary'], font=self.small_font, bd=0, highlightthickness=0, wrap='word')
        self.notif.pack(fill='both', expand=True, padx=12, pady=(0, 12))
        
        chat_card = tk.Frame(right, bg=COLORS['bg_card'])
        chat_card.grid(row=1, column=0, sticky='nsew')
        chat_card.grid_rowconfigure(1, weight=1)  # Chat text area expands
        chat_card.grid_columnconfigure(0, weight=1)
        tk.Label(chat_card, text="CHAT", font=('Segoe UI', 9, 'bold'), bg=COLORS['bg_card'], fg=COLORS['text_secondary']).grid(row=0, column=0, sticky='w', padx=12, pady=8)
        self.chat = tk.Text(chat_card, height=8, bg=COLORS['bg_dark'], fg=COLORS['accent_green'], font=self.small_font, bd=0, highlightthickness=0, wrap='word')
        self.chat.grid(row=1, column=0, sticky='nsew', padx=12)
        
        method_frame = tk.Frame(chat_card, bg=COLORS['bg_card'])
        method_frame.grid(row=2, column=0, sticky='ew', padx=12, pady=5)
        tk.Label(method_frame, text="Method:", font=self.small_font, bg=COLORS['bg_card'], fg=COLORS['text_secondary']).pack(side='left')
        self.method = tk.StringVar(value='crc')
        for txt, val in [('Parity', 'parity'), ('CRC', 'crc'), ('Hamming', 'hamming')]:
            tk.Radiobutton(method_frame, text=txt, variable=self.method, value=val, bg=COLORS['bg_card'], fg=COLORS['text_secondary'], selectcolor=COLORS['bg_dark'], font=self.small_font).pack(side='left', padx=5)
        
        input_frame = tk.Frame(chat_card, bg=COLORS['bg_card'])
        input_frame.grid(row=3, column=0, sticky='ew', padx=12, pady=10)
        input_frame.grid_columnconfigure(0, weight=1)
        self.entry = tk.Entry(input_frame, font=('Segoe UI', 10), bg=COLORS['bg_dark'], fg=COLORS['text_primary'], insertbackground=COLORS['text_primary'], bd=0, highlightthickness=1, highlightcolor=COLORS['accent'], highlightbackground=COLORS['border'])
        self.entry.grid(row=0, column=0, sticky='ew', ipady=6)
        self.entry.bind('<Return>', lambda e: self.send_chat())
        ModernButton(input_frame, "Send", self.send_chat, bg=COLORS['accent_green'], width=60, height=30).grid(row=0, column=1, padx=(8, 0))
        
    def set_symbol(self, s):
        colors = {'X': COLORS['x_color'], 'O': COLORS['o_color']}
        self.sym_lbl.config(text=f"Player {s}", fg=colors.get(s, COLORS['text_primary']))
        self.root.title(f"XO Game - Player {s}")
        
    def set_turn(self, my_turn):
        if my_turn:
            self.turn_lbl.config(text="YOUR TURN", fg=COLORS['accent_green'])
        else:
            self.turn_lbl.config(text="WAITING...", fg=COLORS['text_secondary'])
    
    def set_cell(self, pos, sym):
        if 0 <= pos <= 8:
            colors = {'X': COLORS['x_color'], 'O': COLORS['o_color']}
            self.board[pos] = sym
            cell = self.btns[pos]
            self.board_canvas.itemconfig(cell['text'], text=sym, fill=colors.get(sym, COLORS['text_primary']))
            self.board_canvas.tag_unbind(f'cell_{pos}', '<Enter>')
            self.board_canvas.tag_unbind(f'cell_{pos}', '<Leave>')
    
    def reset_board(self):
        self.board = ['' for _ in range(9)]
        for i, cell in enumerate(self.btns):
            self.board_canvas.itemconfig(cell['text'], text='', fill=COLORS['text_primary'])
            self.board_canvas.itemconfig(cell['rect'], fill=COLORS['bg_card'])
            self.board_canvas.tag_bind(f'cell_{i}', '<Enter>', lambda e, r=cell['rect']: self.board_canvas.itemconfig(r, fill=COLORS['bg_hover']))
            self.board_canvas.tag_bind(f'cell_{i}', '<Leave>', lambda e, r=cell['rect']: self.board_canvas.itemconfig(r, fill=COLORS['bg_card']))
    
    def click_cell(self, pos):
        if not self.client.my_turn:
            self.notify("Not your turn!", 'warning')
            return
        if self.board[pos]:
            self.notify("Cell occupied!", 'warning')
            return
        if not self.client.game_active:
            return
        self.set_cell(pos, self.client.symbol)
        self.client.send_move(pos)
    
    def notify(self, msg, level='info'):
        self.notif.insert('end', f"{msg}\n")
        self.notif.see('end')
    
    def show_result(self, winner, reason):
        if winner == 'Draw':
            title, msg, color = "DRAW", "It's a tie!", COLORS['accent_yellow']
        elif winner == self.client.symbol:
            title, msg, color = "VICTORY!", "You won!", COLORS['accent_green']
        else:
            title, msg, color = "DEFEAT", f"Player {winner} wins", COLORS['accent_red']
        self.notify(f"{title} - {reason}", 'info')
        dlg = tk.Toplevel(self.root)
        dlg.title("Game Over")
        dlg.geometry("300x180")
        dlg.configure(bg=COLORS['bg_card'])
        dlg.transient(self.root)
        dlg.resizable(False, False)
        dlg.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 300) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 180) // 2
        dlg.geometry(f"+{x}+{y}")
        tk.Label(dlg, text=title, font=('Segoe UI', 20, 'bold'), bg=COLORS['bg_card'], fg=color).pack(pady=(25, 5))
        tk.Label(dlg, text=msg, font=('Segoe UI', 11), bg=COLORS['bg_card'], fg=COLORS['text_secondary']).pack()
        btn_frame = tk.Frame(dlg, bg=COLORS['bg_card'])
        btn_frame.pack(pady=25)
        ModernButton(btn_frame, "Rematch", lambda: [dlg.destroy(), self.request_restart()], bg=COLORS['accent_green'], width=100).pack(side='left', padx=5)
        ModernButton(btn_frame, "Exit", lambda: [dlg.destroy(), self.quit()], bg=COLORS['bg_hover'], width=80).pack(side='left', padx=5)
    
    def show_restart_prompt(self, from_p):
        if messagebox.askyesno("Rematch", f"Player {from_p} wants a rematch. Accept?"):
            self.client.vote_restart()
            self.notify("You accepted the rematch", 'success')
    
    def request_restart(self):
        self.client.vote_restart()
        self.notify("Rematch requested...", 'info')
    
    def surrender(self):
        if messagebox.askyesno("Surrender", "Are you sure?"):
            self.client.surrender()
            self.notify("You surrendered!", 'error')
    
    def send_chat(self):
        txt = self.entry.get().strip()
        if not txt:
            return
        self.entry.delete(0, 'end')
        self.chat.insert('end', f"You [{self.method.get()}]: {txt}\n")
        self.chat.see('end')
        self.client.send_chat(txt, self.method.get())
    
    def receive_chat(self, msg):
        result = decode_message(msg['encoded'], msg['method'])
        self.chat.insert('end', f"\nFrom: {msg['from']} [{msg['method']}]\n")
        if msg.get('modified'):
            self.chat.insert('end', "MODIFIED BY SERVER!\n")
        self.chat.insert('end', f"Recv: {result['received_control']}\n")
        self.chat.insert('end', f"Calc: {result['calculated_control']}\n")
        self.chat.insert('end', f"Match: {'YES' if result['control_match'] else 'NO'}\n")
        self.chat.insert('end', f"Text: {result['decoded_text']}\n\n")
        self.chat.see('end')
        self.notify(f"Message from {msg['from']}", 'info')
    
    def quit(self):
        self.client.disconnect()
        self.root.destroy()
    
    def run(self):
        self.notify("Connecting...", 'info')
        if self.client.connect():
            self.notify(f"Connected to {self.client.host}:{self.client.port}", 'success')
        else:
            self.notify("Connection failed!", 'error')
        self.root.protocol("WM_DELETE_WINDOW", self.quit)
        self.root.mainloop()

if __name__ == "__main__":
    ClientGUI(GameClient()).run()
