"""
ai.py

Cờ Gánh 5x5 (local Play vs AI, không networking).
- Font: dùng system font qua pygame.font.SysFont (không cần .ttf)
- Luật: Gánh + Chẹt
- AI: Random (depth=0) hoặc Minimax + Alpha-Beta (depth 1/3/5)
- Phát hiện thắng/thua:
    + Một bên HẾT QUÂN
    + Bên tới lượt KHÔNG CÒN NƯỚC ĐI
- Màn hình kết quả có: "Chơi lại" & "Quay về menu"
"""

import pygame
import sys
import random
import time
from collections import deque

# -------------------- Config --------------------
WHITE = (255, 255, 255)
BLACK = (20, 24, 33)
MUTED = (115, 120, 130)
LINE  = (205, 210, 220)
PANEL = (245, 248, 252)
GRAY  = (200, 205, 215)
RED   = (220, 50, 50)
BLUE  = (50, 80, 220)
GREEN = (0, 170, 0)

WIDTH, HEIGHT = 420, 540       # tăng size cho dễ bấm
size = 5
cell_size = 72                 # ô lớn hơn
header_h = 88                  # chừa vùng header cho text

# Tokens
TOKEN_RED  = 'R'
TOKEN_BLUE = 'B'

# -------------------- Fonts (no .ttf) --------------------
def load_fonts():
    # Thử vài system font phổ biến; nếu không có, SysFont(None, ...) sẽ fallback an toàn
    candidates = ["Segoe UI", "Arial", "Helvetica", "Roboto", None]
    for name in candidates:
        try:
            title_f = pygame.font.SysFont(name, 40, bold=True)
            font_b  = pygame.font.SysFont(name, 22, bold=True)
            font    = pygame.font.SysFont(name, 20)
            tiny    = pygame.font.SysFont(name, 16)
            # render test để chắc chắn không lỗi
            _ = title_f.render("CỜ GÁNH", True, BLACK)
            return title_f, font_b, font, tiny
        except Exception:
            continue
    # fallback cuối
    return (pygame.font.SysFont(None, 40, bold=True),
            pygame.font.SysFont(None, 22, bold=True),
            pygame.font.SysFont(None, 20),
            pygame.font.SysFont(None, 16))

# -------------------- Geometry --------------------
def rc_from_index(i):
    return divmod(i, size)  # (r,c)

def index_from_rc(r, c):
    return r * size + c

# Tính toạ độ lưới, canh GIỮA chiều ngang & phần dưới header
grid_w = (size - 1) * cell_size
grid_h = (size - 1) * cell_size
x0 = (WIDTH  - grid_w) // 2
y0 = header_h + ((HEIGHT - header_h) - grid_h) // 2

positions = []
for r in range(size):
    for c in range(size):
        x = x0 + c * cell_size
        y = y0 + r * cell_size
        positions.append((x, y))

# Đồ thị kề theo luật: ngang, dọc, chéo khi (r+c) chẵn (đối xứng)
neighbors = {i: [] for i in range(size * size)}
for r in range(size):
    for c in range(size):
        i = index_from_rc(r, c)
        if c + 1 < size:
            j = index_from_rc(r, c + 1)
            neighbors[i].append(j); neighbors[j].append(i)
        if r + 1 < size:
            j = index_from_rc(r + 1, c)
            neighbors[i].append(j); neighbors[j].append(i)
        if (r + c) % 2 == 0:
            if r + 1 < size and c + 1 < size:
                j = index_from_rc(r + 1, c + 1)
                neighbors[i].append(j); neighbors[j].append(i)
            if r + 1 < size and c - 1 >= 0:
                j = index_from_rc(r + 1, c - 1)
                neighbors[i].append(j); neighbors[j].append(i)

def are_neighbors(i, j):
    return j in neighbors[i]

# 4 hướng trục kiểm tra Gánh
AXES = [(0,1), (1,0), (1,1), (1,-1)]

# -------------------- Board --------------------
def initial_board():
    board = [None] * (size * size)
    blues = [0,1,2,3,4,5,9,14]
    reds  = [10,15,19,20,21,22,23,24]
    for b in blues: board[b] = TOKEN_BLUE
    for r in reds:  board[r] = TOKEN_RED
    return board

def legal_moves(board, color_token):
    moves = []
    for i, t in enumerate(board):
        if t == color_token:
            for nb in neighbors[i]:
                if board[nb] is None:
                    moves.append((i, nb))
    return moves

# -------------------- Rules: Gánh + Chẹt --------------------
def try_ganh(board, dst, me):
    flips = []
    opp = TOKEN_RED if me == TOKEN_BLUE else TOKEN_BLUE
    r, c = rc_from_index(dst)
    for dr, dc in AXES:
        ar, ac = r - dr, c - dc
        cr, cc = r + dr, c + dc
        if 0 <= ar < size and 0 <= ac < size and 0 <= cr < size and 0 <= cc < size:
            a  = index_from_rc(ar, ac)
            c2 = index_from_rc(cr, cc)
            if are_neighbors(a, dst) and are_neighbors(dst, c2):
                if board[a] == opp and board[c2] == opp:
                    board[a], board[c2] = me, me
                    flips.append((a, opp))
                    flips.append((c2, opp))
    return flips

def group_and_liberty(board, start):
    color = board[start]
    q = deque([start])
    seen = {start}
    has_lib = False
    while q:
        u = q.popleft()
        for v in neighbors[u]:
            if board[v] is None:
                has_lib = True
            elif board[v] == color and v not in seen:
                seen.add(v)
                q.append(v)
    return seen, has_lib

def try_chet(board, me):
    flips = []
    opp = TOKEN_RED if me == TOKEN_BLUE else TOKEN_BLUE
    visited = set()
    for i, t in enumerate(board):
        if t == opp and i not in visited:
            grp, has_lib = group_and_liberty(board, i)
            visited |= grp
            if not has_lib:
                for u in grp:
                    board[u] = me
                    flips.append((u, opp))
    return flips

def apply_move(board, move, color_token):
    frm, to = move
    changes = {"move": (frm, to, board[frm]), "flips": []}
    board[to] = board[frm]
    board[frm] = None
    flips_g = try_ganh(board, to, color_token)
    flips_c = try_chet(board, color_token)
    changes["flips"].extend(flips_g)
    changes["flips"].extend(flips_c)
    return changes

def undo_move(board, changes):
    for idx, old_tok in reversed(changes["flips"]):
        board[idx] = old_tok
    frm, to, orig_token = changes["move"]
    board[frm] = orig_token
    board[to]  = None

# -------------------- Evaluation --------------------
def ganh_potential(board, me):
    opp = TOKEN_RED if me == TOKEN_BLUE else TOKEN_BLUE
    cnt = 0
    for b in range(len(board)):
        if board[b] != opp: continue
        rb, cb = rc_from_index(b)
        for dr, dc in AXES:
            ra, ca = rb - dr, cb - dc
            rc2, cc2 = rb + dr, cb + dc
            if 0 <= ra < size and 0 <= ca < size and 0 <= rc2 < size and 0 <= cc2 < size:
                a  = index_from_rc(ra, ca)
                c2 = index_from_rc(rc2, cc2)
                if are_neighbors(a, b) and are_neighbors(b, c2):
                    if board[a] == me and board[c2] == me:
                        cnt += 1
    return cnt

def evaluate(board, maximizing_token):
    opponent = TOKEN_RED if maximizing_token == TOKEN_BLUE else TOKEN_BLUE
    my_cnt  = sum(1 for x in board if x == maximizing_token)
    op_cnt  = sum(1 for x in board if x == opponent)
    material = 10 * (my_cnt - op_cnt)
    gp_me = ganh_potential(board, maximizing_token)
    gp_op = ganh_potential(board, opponent)
    ganh_score = 5 * (gp_me - gp_op)
    center_r, center_c = 2, 2
    center_score = 0
    for i, t in enumerate(board):
        if t is None: continue
        r, c = rc_from_index(i)
        dist = abs(r - center_r) + abs(c - center_c)
        val = max(0, 3 - dist)
        if t == maximizing_token: center_score += val
        elif t == opponent:       center_score -= val
    center_score *= 2
    mob = 0.3 * (len(legal_moves(board, maximizing_token)) - len(legal_moves(board, opponent)))
    return material + ganh_score + center_score + mob

# -------------------- Minimax + Alpha-Beta --------------------
def minimax(board, depth, alpha, beta, maximizing_token, current_token):
    opponent = TOKEN_RED if current_token == TOKEN_BLUE else TOKEN_BLUE

    if depth == 0:
        return evaluate(board, maximizing_token), None

    moves = legal_moves(board, current_token)
    if not moves:
        return evaluate(board, maximizing_token), None

    def center_bias(mv):
        _, to = mv
        r, c = rc_from_index(to)
        return abs(r - 2) + abs(c - 2)

    if current_token == maximizing_token:
        moves.sort(key=lambda m: center_bias(m))
        best_move, max_eval = None, -10**9
        for m in moves:
            changes = apply_move(board, m, current_token)
            val, _ = minimax(board, depth - 1, alpha, beta, maximizing_token, opponent)
            undo_move(board, changes)
            if val > max_eval:
                max_eval, best_move = val, m
            alpha = max(alpha, val)
            if beta <= alpha: break
        return max_eval, best_move
    else:
        moves.sort(key=lambda m: -center_bias(m))
        best_move, min_eval = None, 10**9
        for m in moves:
            changes = apply_move(board, m, current_token)
            val, _ = minimax(board, depth - 1, alpha, beta, maximizing_token, opponent)
            undo_move(board, changes)
            if val < min_eval:
                min_eval, best_move = val, m
            beta = min(beta, val)
            if beta <= alpha: break
        return min_eval, best_move

def ai_random(board, color_token):
    ms = legal_moves(board, color_token)
    return random.choice(ms) if ms else None

def ai_minimax(board, color_token, depth):
    if depth <= 0:
        return ai_random(board, color_token)
    score, mv = minimax(board, depth, -10**9, 10**9, color_token, color_token)
    return mv

# -------------------- Win detection --------------------
def count_pieces(board, token):
    return sum(1 for x in board if x == token)

def check_winner(board, turn_token):
    """
    Trả về (winner_token|None, reason:str|None)
    - Nếu R hoặc B hết quân -> bên kia thắng
    - Nếu bên TỚI LƯỢT không có nước đi -> bên CÒN LẠI thắng
    """
    r_cnt = count_pieces(board, TOKEN_RED)
    b_cnt = count_pieces(board, TOKEN_BLUE)
    if r_cnt == 0 and b_cnt == 0:
        return None, "Hòa?! (cả hai hết quân)"
    if r_cnt == 0:
        return TOKEN_BLUE, "RED hết quân"
    if b_cnt == 0:
        return TOKEN_RED, "BLUE hết quân"

    no_moves = len(legal_moves(board, turn_token)) == 0
    if no_moves:
        winner = TOKEN_BLUE if turn_token == TOKEN_RED else TOKEN_RED
        return winner, "Bên tới lượt không còn nước đi"
    return None, None

# -------------------- UI --------------------
pygame.init()
screen  = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('Cờ Gánh - Play vs AI')
title_f, font_b, font, tiny = load_fonts()
clock   = pygame.time.Clock()

class Button:
    def __init__(self, rect, text, on_click, active=False):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.on_click = on_click
        self.active = active
    def draw(self, surf):
        mx, my = pygame.mouse.get_pos()
        hover = self.rect.collidepoint(mx, my)
        base = (234, 238, 245) if not self.active else (210, 224, 255)
        if hover: base = (225, 230, 238) if not self.active else (195, 212, 255)
        pygame.draw.rect(surf, base, self.rect, border_radius=10)
        pygame.draw.rect(surf, LINE, self.rect, 2, border_radius=10)
        txt = font.render(self.text, True, BLACK)
        surf.blit(txt, txt.get_rect(center=self.rect.center))
    def handle(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.on_click()

def draw_grid_and_pieces(board, turn_token, player_token, depth, info_msg=''):
    screen.fill(WHITE)
    # Header
    pygame.draw.rect(screen, PANEL, (0, 0, WIDTH, header_h))
    title = title_f.render("CỜ GÁNH", True, BLACK)
    screen.blit(title, title.get_rect(center=(WIDTH//2, 28)))
    sub = tiny.render(f"Lượt: {'RED' if turn_token==TOKEN_RED else 'BLUE'}   |   Bạn: {'BLUE' if player_token==TOKEN_BLUE else 'RED'}   |   Depth: {depth}", True, MUTED)
    screen.blit(sub, sub.get_rect(center=(WIDTH//2, 58)))

    # Lines
    for a in range(size*size):
        for b in neighbors[a]:
            if a < b:
                pygame.draw.line(screen, BLACK, positions[a], positions[b], 2)

    # Nodes + pieces
    for i, (x,y) in enumerate(positions):
        pygame.draw.circle(screen, BLACK, (x,y), 6)
        t = board[i]
        if t == TOKEN_RED:
            pygame.draw.circle(screen, RED, (x,y), 24)
        elif t == TOKEN_BLUE:
            pygame.draw.circle(screen, BLUE, (x,y), 24)

def menu_screen():
    player_color = TOKEN_BLUE
    depth = 3
    running = True

    # Layout
    panel = pygame.Rect(WIDTH//2-170, header_h+20, 340, 300)

    buttons = []
    def set_blue():
        nonlocal player_color; player_color = TOKEN_BLUE; refresh()
    def set_red():
        nonlocal player_color; player_color = TOKEN_RED;  refresh()
    def set_depth(d):
        nonlocal depth; depth = d; refresh()
    def start_game():
        nonlocal running; running = False

    def refresh():
        buttons.clear()
        # Color
        buttons.append(Button((panel.x+22, panel.y+26, 140, 44), "Chơi BLUE", set_blue, active=(player_color==TOKEN_BLUE)))
        buttons.append(Button((panel.x+178, panel.y+26,140, 44), "Chơi RED",  set_red,  active=(player_color==TOKEN_RED)))
        # Depth
        buttons.append(Button((panel.x+22,  panel.y+92, 90, 40), "Random", lambda: set_depth(0), active=(depth==0)))
        buttons.append(Button((panel.x+126, panel.y+92, 90, 40), "Depth 1", lambda: set_depth(1), active=(depth==1)))
        buttons.append(Button((panel.x+230, panel.y+92, 90, 40), "Depth 3", lambda: set_depth(3), active=(depth==3)))
        buttons.append(Button((panel.x+126, panel.y+142,90, 40), "Depth 5", lambda: set_depth(5), active=(depth==5)))
        # Start
        buttons.append(Button((panel.x+70,  panel.y+210,200, 48), "Bắt đầu", start_game, active=False))

    refresh()

    while running:
        screen.fill(WHITE)
        pygame.draw.rect(screen, PANEL, (0,0,WIDTH, header_h))
        title = title_f.render("CỜ GÁNH", True, BLACK)
        screen.blit(title, title.get_rect(center=(WIDTH//2, 36)))
        pygame.draw.rect(screen, PANEL, panel, border_radius=14)
        pygame.draw.rect(screen, LINE,  panel, 2, border_radius=14)

        screen.blit(font_b.render("Chọn màu", True, BLACK), (panel.x+22, panel.y-2))
        screen.blit(font_b.render("Độ khó",  True, BLACK), (panel.x+22, panel.y+64))

        for b in buttons: b.draw(screen)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            for b in buttons: b.handle(event)

        pygame.display.flip()
        clock.tick(60)

    return player_color, depth

def result_screen(winner_token, reason, player_token, depth):
    """
    Hiển thị kết quả. Trả về:
      - "REPLAY" để chơi lại với cùng cấu hình
      - "MENU"   để quay về menu
    """
    running = True
    panel = pygame.Rect(WIDTH//2-170, HEIGHT//2-90, 340, 180)

    action = None
    def replay():
        nonlocal action, running; action = "REPLAY"; running = False
    def back_menu():
        nonlocal action, running; action = "MENU"; running = False

    btn_replay = Button((panel.x+24, panel.y+110, 130, 44), "Chơi lại", replay)
    btn_menu   = Button((panel.x+186, panel.y+110,130, 44), "Quay về menu", back_menu)

    who = "RED" if winner_token == TOKEN_RED else "BLUE" if winner_token == TOKEN_BLUE else "Hòa"
    while running:
        screen.fill(WHITE)
        pygame.draw.rect(screen, PANEL, (0,0,WIDTH, header_h))
        title = title_f.render("KẾT THÚC VÁN", True, BLACK)
        screen.blit(title, title.get_rect(center=(WIDTH//2, 36)))

        pygame.draw.rect(screen, PANEL, panel, border_radius=14)
        pygame.draw.rect(screen, LINE,  panel, 2, border_radius=14)

        msg1 = font_b.render(f"Thắng: {who}", True, BLACK)
        msg2 = font.render(f"Lý do: {reason}", True, MUTED)
        msg3 = tiny.render(f"Bạn: {'BLUE' if player_token==TOKEN_BLUE else 'RED'} | Depth: {depth}", True, MUTED)

        screen.blit(msg1, msg1.get_rect(center=(WIDTH//2, panel.y+36)))
        screen.blit(msg2, msg2.get_rect(center=(WIDTH//2, panel.y+66)))
        screen.blit(msg3, msg3.get_rect(center=(WIDTH//2, panel.y+88)))

        btn_replay.draw(screen)
        btn_menu.draw(screen)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            btn_replay.handle(event)
            btn_menu.handle(event)

        pygame.display.flip()
        clock.tick(60)

    return action

# -------------------- Game loop --------------------
def run_game(player_token, ai_depth):
    board = initial_board()
    selected = None
    turn_token = TOKEN_RED  # RED đi trước
    ai_thinking = False
    last_ai_time = 0.0

    while True:
        # Kiểm tra thắng thua trước khi xử lý lượt
        winner, reason = check_winner(board, turn_token)
        if winner or reason:
            return result_screen(winner, reason, player_token, ai_depth)

        draw_grid_and_pieces(board, turn_token, player_token, ai_depth)

        # AI di chuyển
        if turn_token != player_token and not ai_thinking:
            ai_thinking = True
            pygame.event.pump()
            if time.time() - last_ai_time < 0.05:
                pass
            moves = legal_moves(board, turn_token)
            if not moves:
                # Không còn nước đi → check_winner sẽ xử lý ở đầu vòng lặp
                ai_thinking = False
            else:
                t0 = time.time()
                chosen = ai_minimax(board, turn_token, ai_depth)
                elapsed = time.time() - t0
                print(f"[AI] depth={ai_depth} move={chosen} in {elapsed:.2f}s")
                if chosen:
                    apply_move(board, chosen, turn_token)
                turn_token = TOKEN_RED if turn_token == TOKEN_BLUE else TOKEN_BLUE
                ai_thinking = False
                last_ai_time = time.time()

        # Tương tác người chơi
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "MENU"
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if turn_token != player_token:
                    continue
                for i, (x,y) in enumerate(positions):
                    if (mx-x)**2 + (my-y)**2 <= 24**2:
                        if selected is None:
                            if board[i] == player_token:
                                selected = i
                        else:
                            if board[i] is None and are_neighbors(selected, i):
                                move = (selected, i)
                                apply_move(board, move, player_token)
                                turn_token = TOKEN_RED if player_token == TOKEN_BLUE else TOKEN_BLUE
                                selected = None
                            else:
                                if board[i] == player_token:
                                    selected = i
                        break

        # Vẽ highlight quân đang chọn
        if selected is not None:
            x,y = positions[selected]
            pygame.draw.circle(screen, GREEN, (x,y), 28, 3)
        pygame.display.flip()
        clock.tick(60)

# -------------------- Main --------------------
if __name__ == '__main__':
    try:
        while True:
            player_token, depth = menu_screen()
            action = run_game(player_token, depth)
            if action == "MENU":
                # quay về menu chính
                continue
            elif action == "REPLAY":
                # chơi lại cùng cấu hình
                action2 = run_game(player_token, depth)
                if action2 != "MENU":
                    break
            else:
                break
    except KeyboardInterrupt:
        pygame.quit(); sys.exit()
