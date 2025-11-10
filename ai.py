"""
client_vs_ai.py

Pygame client for Cờ Gánh (5x5) with single-player "Play vs AI" mode.
Features added per request:
- Random-move AI (chooses a valid move at random)
- Minimax with Alpha-Beta pruning
- Evaluation function combining: piece count, gánh (captures) potential, center control
- Difficulty levels: depth = 1, 3, 5
- Simple menu to choose: Play vs AI, choose your color (RED/BLUE), choose difficulty

How to use:
- Ensure pygame is installed in your environment (see previous run.sh / venv instructions).
- Run: python3 client_vs_ai.py

This file deliberately runs as a local single-player program (no networking).
"""

import pygame
import sys
import random
import time

# ---- Config ----
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (180, 180, 180)
RED = (220, 50, 50)
BLUE = (50, 80, 220)
GREEN = (0, 200, 0)

WIDTH, HEIGHT = 360, 420
size = 5
cell_size = 60
offset = 30

# Map color names to simple tokens for internal logic
TOKEN_RED = 'R'
TOKEN_BLUE = 'B'

# ---- Board helpers ----

def rc_from_index(i):
    return divmod(i, size)  # (r, c)


def index_from_rc(r, c):
    return r * size + c


# Build positions (screen coordinates) and adjacency (connections) same as earlier client
positions = []
for r in range(size):
    for c in range(size):
        x = offset + c * cell_size
        y = offset + r * cell_size + 60  # shift down for menu space
        positions.append((x, y))

# adjacency mapping
neighbors = {i: [] for i in range(size * size)}
for r in range(size):
    for c in range(size):
        i = index_from_rc(r, c)
        # right
        if c + 1 < size:
            j = index_from_rc(r, c + 1)
            neighbors[i].append(j)
        # down
        if r + 1 < size:
            j = index_from_rc(r + 1, c)
            neighbors[i].append(j)
        # diagonals if parity even
        if (r + c) % 2 == 0:
            if r + 1 < size and c + 1 < size:
                j = index_from_rc(r + 1, c + 1)
                neighbors[i].append(j)
            if r + 1 < size and c - 1 >= 0:
                j = index_from_rc(r + 1, c - 1)
                neighbors[i].append(j)
# Ensure symmetry
for i in list(neighbors.keys()):
    for j in neighbors[i]:
        if i not in neighbors[j]:
            neighbors[j].append(i)


# ---- Initial board state: list of tokens or None ----
# Use same initial layout as your client code: Blue on top, Red on bottom

def initial_board():
    board = [None] * (size * size)
    blues = [0,1,2,3,4,5,9,14]
    reds = [10,15,19,20,21,22,23,24]
    for b in blues:
        board[b] = TOKEN_BLUE
    for r in reds:
        board[r] = TOKEN_RED
    return board


# ---- Move generation and application ----
# Move represented as tuple (from_idx, to_idx)


def legal_moves(board, color_token):
    moves = []
    for i, t in enumerate(board):
        if t == color_token:
            for nb in neighbors[i]:
                if board[nb] is None:
                    moves.append((i, nb))
    return moves


def apply_move(board, move, color_token):
    """Apply move and perform gánh captures. Returns list of captured positions for undo."""
    frm, to = move
    captured = []
    board[to] = board[frm]
    board[frm] = None

    # After the move, check for opponent pieces that are flanked by two friendlies in a straight line.
    opponent = TOKEN_RED if color_token == TOKEN_BLUE else TOKEN_BLUE

    # For each opponent piece, check each neighbor a; compute opposite cell c and see if both friendlies
    for b in range(len(board)):
        if board[b] != opponent:
            continue
        r_b, c_b = rc_from_index(b)
        for a in neighbors[b]:
            # a is neighbor cell; compute opposite cell c = 2*b - a in row/col space
            r_a, c_a = rc_from_index(a)
            r_c = 2 * r_b - r_a
            c_c = 2 * c_b - c_a
            if 0 <= r_c < size and 0 <= c_c < size:
                c = index_from_rc(r_c, c_c)
                # To be a straight-line capture: a and c must both be neighbors of b (they are by construction for grid),
                # but also a and c must be in-line (vector opposite) and both occupied by friendlies
                if board[c] == color_token and board[a] == color_token:
                    # remove b
                    captured.append(b)
    # Remove captured pieces
    for b in captured:
        board[b] = None
    return captured


def undo_move(board, move, color_token, captured, orig_token):
    frm, to = move
    board[frm] = orig_token
    board[to] = None
    # restore captured
    opponent = TOKEN_RED if color_token == TOKEN_BLUE else TOKEN_BLUE
    for b in captured:
        board[b] = opponent


# ---- Evaluation function ----

def evaluate(board, maximizing_token):
    # Higher is better for maximizing_token
    opponent = TOKEN_RED if maximizing_token == TOKEN_BLUE else TOKEN_BLUE

    # 1) Material: difference in piece counts
    my_count = sum(1 for x in board if x == maximizing_token)
    opp_count = sum(1 for x in board if x == opponent)
    material_score = 10 * (my_count - opp_count)

    # 2) Gánh potential: count of opponent pieces currently flanked by two friendlies (good for maximizing_token)
    ganh_score = 0
    for b in range(len(board)):
        if board[b] != opponent:
            continue
        r_b, c_b = rc_from_index(b)
        for a in neighbors[b]:
            r_a, c_a = rc_from_index(a)
            r_c = 2 * r_b - r_a
            c_c = 2 * c_b - c_a
            if 0 <= r_c < size and 0 <= c_c < size:
                c = index_from_rc(r_c, c_c)
                if board[a] == maximizing_token and board[c] == maximizing_token:
                    ganh_score += 1
    # each potential captured opponent piece is valuable
    ganh_score = 5 * ganh_score

    # 3) Center control: prefer pieces near center (index 12 is the exact center)
    center_r, center_c = rc_from_index(size*size//2)
    center_score = 0
    for i, t in enumerate(board):
        if t == maximizing_token:
            r, c = rc_from_index(i)
            dist = abs(r - center_r) + abs(c - center_c)
            center_score += max(0, 3 - dist)  # closer to center yields more
        elif t == opponent:
            r, c = rc_from_index(i)
            dist = abs(r - center_r) + abs(c - center_c)
            center_score -= max(0, 3 - dist)
    center_score = 2 * center_score

    score = material_score + ganh_score + center_score
    return score


# ---- Minimax with Alpha-Beta ----

def minimax(board, depth, alpha, beta, maximizing_token, current_token):
    # current_token is the player to move at this node
    opponent = TOKEN_RED if current_token == TOKEN_BLUE else TOKEN_BLUE

    if depth == 0:
        return evaluate(board, maximizing_token), None

    moves = legal_moves(board, current_token)
    if not moves:
        # no legal moves: evaluate position
        return evaluate(board, maximizing_token), None

    best_move = None
    if current_token == maximizing_token:
        max_eval = -10**9
        for m in moves:
            # apply
            orig_token = board[m[0]]
            captured = apply_move(board, m, current_token)
            val, _ = minimax(board, depth-1, alpha, beta, maximizing_token, opponent)
            # undo
            undo_move(board, m, current_token, captured, orig_token)

            if val > max_eval:
                max_eval = val
                best_move = m
            alpha = max(alpha, val)
            if beta <= alpha:
                break
        return max_eval, best_move
    else:
        min_eval = 10**9
        for m in moves:
            orig_token = board[m[0]]
            captured = apply_move(board, m, current_token)
            val, _ = minimax(board, depth-1, alpha, beta, maximizing_token, opponent)
            undo_move(board, m, current_token, captured, orig_token)

            if val < min_eval:
                min_eval = val
                best_move = m
            beta = min(beta, val)
            if beta <= alpha:
                break
        return min_eval, best_move


# ---- AI wrappers ----

def ai_random(board, color_token):
    moves = legal_moves(board, color_token)
    if not moves:
        return None
    return random.choice(moves)


def ai_minimax(board, color_token, depth):
    # Returns best move for color_token using minimax with alpha-beta
    board_copy = board  # we modify board in-place and undo inside minimax
    score, move = minimax(board_copy, depth, -10**9, 10**9, color_token, color_token)
    return move


# ---- Pygame UI ----
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('Cờ Gánh - Play vs AI')
font = pygame.font.SysFont(None, 24)
bigfont = pygame.font.SysFont(None, 36)
clock = pygame.time.Clock()


def draw_text_center(surface, text, y):
    txt = bigfont.render(text, True, BLACK)
    rect = txt.get_rect(center=(WIDTH//2, y))
    surface.blit(txt, rect)


def draw_button(surface, rect, text, active=False):
    color = GRAY if not active else (150,150,255)
    pygame.draw.rect(surface, color, rect)
    txt = font.render(text, True, BLACK)
    tr = txt.get_rect(center=rect.center)
    surface.blit(txt, tr)


# Menu: choose mode and difficulty and color

def menu_screen():
    mode = 'AI'  # only implementing Play vs AI per request
    player_color = TOKEN_BLUE
    depth = 3

    running = True
    while running:
        screen.fill(WHITE)
        draw_text_center(screen, 'Cờ Gánh - Chọn chế độ', 40)
        draw_text_center(screen, 'Play vs AI (non-network)', 80)

        # Color buttons
        btn_blue = pygame.Rect(40, 110, 120, 40)
        btn_red = pygame.Rect(200, 110, 120, 40)
        draw_button(screen, btn_blue, 'Play as BLUE', player_color == TOKEN_BLUE)
        draw_button(screen, btn_red, 'Play as RED', player_color == TOKEN_RED)

        # Difficulty buttons
        btn_d1 = pygame.Rect(30, 170, 90, 36)
        btn_d3 = pygame.Rect(135, 170, 90, 36)
        btn_d5 = pygame.Rect(240, 170, 90, 36)
        draw_button(screen, btn_d1, 'Depth 1', depth == 1)
        draw_button(screen, btn_d3, 'Depth 3', depth == 3)
        draw_button(screen, btn_d5, 'Depth 5', depth == 5)

        # Start button
        btn_start = pygame.Rect(100, 230, 160, 50)
        draw_button(screen, btn_start, 'Start Game', False)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx,my = pygame.mouse.get_pos()
                if btn_blue.collidepoint(mx,my):
                    player_color = TOKEN_BLUE
                elif btn_red.collidepoint(mx,my):
                    player_color = TOKEN_RED
                elif btn_d1.collidepoint(mx,my):
                    depth = 1
                elif btn_d3.collidepoint(mx,my):
                    depth = 3
                elif btn_d5.collidepoint(mx,my):
                    depth = 5
                elif btn_start.collidepoint(mx,my):
                    running = False
        pygame.display.flip()
        clock.tick(30)
    return player_color, depth


# ---- Game loop ----

def run_game(player_token, ai_depth):
    board = initial_board()
    selected = None
    turn_token = TOKEN_RED  # Red always starts per earlier code
    running = True
    info_msg = ''
    ai_thinking = False

    while running:
        screen.fill(WHITE)

        # Draw UI header
        txt_turn = f"Lượt: {'RED' if turn_token==TOKEN_RED else 'BLUE'}"
        screen.blit(font.render(txt_turn, True, BLACK), (10, 10))
        screen.blit(font.render(f"Bạn: {'BLUE' if player_token==TOKEN_BLUE else 'RED'}", True, BLACK), (200, 10))
        screen.blit(font.render(f"Depth: {ai_depth}", True, BLACK), (10, 34))
        screen.blit(font.render(info_msg, True, BLACK), (120, 34))

        # Draw board lines
        for a in range(size*size):
            for b in neighbors[a]:
                if a < b:  # draw each line once
                    pygame.draw.line(screen, BLACK, positions[a], positions[b], 2)

        # Draw points and pieces
        for i, (x,y) in enumerate(positions):
            pygame.draw.circle(screen, BLACK, (x,y), 6)
            token = board[i]
            if token == TOKEN_RED:
                pygame.draw.circle(screen, RED, (x,y), 22)
            elif token == TOKEN_BLUE:
                pygame.draw.circle(screen, BLUE, (x,y), 22)

        # Highlight selected
        if selected is not None:
            x,y = positions[selected]
            pygame.draw.circle(screen, GREEN, (x,y), 26, 3)

        pygame.display.flip()

        # If it's AI's turn and we're in Play vs AI, let AI move
        if turn_token != player_token and not ai_thinking:
            ai_thinking = True
            pygame.event.pump()  # keep window responsive
            # decide AI move
            moves = legal_moves(board, turn_token)
            if not moves:
                info_msg = 'AI has no moves'
                ai_thinking = False
                # pass turn
                turn_token = player_token
                continue

            # Choose AI algorithm
            if ai_depth == 0:
                chosen = ai_random(board, turn_token)
            else:
                # If depth small, use minimax; but to keep UI responsive, for larger depths show short delay
                start_t = time.time()
                chosen = ai_minimax(board, turn_token, ai_depth)
                elapsed = time.time() - start_t
                # debug
                print(f"[AI] depth={ai_depth} computed move {chosen} in {elapsed:.2f}s")

            if chosen:
                apply_move(board, chosen, turn_token)
            turn_token = player_token
            ai_thinking = False
            continue

        # Event handling for human player
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx,my = pygame.mouse.get_pos()
                # ignore clicks outside board
                for i,(x,y) in enumerate(positions):
                    if (mx-x)**2 + (my-y)**2 < 22**2:
                        # clicked point i
                        if selected is None:
                            # select own piece
                            if board[i] == player_token and turn_token == player_token:
                                selected = i
                        else:
                            # try move selected -> i
                            if board[i] is None and i in neighbors[selected] and turn_token == player_token:
                                move = (selected, i)
                                apply_move(board, move, player_token)
                                # after move, pass turn to AI
                                turn_token = TOKEN_RED if player_token == TOKEN_BLUE else TOKEN_BLUE
                                selected = None
                            else:
                                # if clicking own piece, switch selection
                                if board[i] == player_token:
                                    selected = i
                        break

        clock.tick(30)

    pygame.quit()


if __name__ == '__main__':
    player_token, depth = menu_screen()
    # Map depth 1/3/5 to the AI depth used; allow depth 0 for random
    run_game(player_token, depth)
