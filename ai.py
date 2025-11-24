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
from game import CoGanh, TOKEN_RED, TOKEN_BLUE, SIZE, EMPTY

# -------------------- Config --------------------
WHITE = (255, 255, 255)
BLACK = (20, 24, 33)
MUTED = (115, 120, 130)
LINE = (205, 210, 220)
PANEL = (245, 248, 252)
GRAY = (200, 205, 215)
RED = (220, 50, 50)
BLUE = (50, 80, 220)
GREEN = (0, 170, 0)
OVERLAY = (0, 0, 0)

WIDTH, HEIGHT = 420, 540
cell_size = 72
header_h = 88


# -------------------- Fonts --------------------
def load_fonts():
    candidates = ["Segoe UI", "Arial", "Helvetica", "Roboto", None]
    for name in candidates:
        try:
            title_f = pygame.font.SysFont(name, 40, bold=True)
            font_b = pygame.font.SysFont(name, 22, bold=True)
            font = pygame.font.SysFont(name, 20)
            tiny = pygame.font.SysFont(name, 16)
            _ = title_f.render("TEST", True, BLACK)
            return title_f, font_b, font, tiny
        except Exception:
            continue
    return (
        pygame.font.SysFont(None, 40, bold=True),
        pygame.font.SysFont(None, 22, bold=True),
        pygame.font.SysFont(None, 20),
        pygame.font.SysFont(None, 16),
    )


# -------------------- Geometry --------------------
# Helper to map index 0-24 to (x, y) pixels
grid_w = (SIZE - 1) * cell_size
grid_h = (SIZE - 1) * cell_size
x0 = (WIDTH - grid_w) // 2
y0 = header_h + ((HEIGHT - header_h) - grid_h) // 2

positions = []
for r in range(SIZE):
    for c in range(SIZE):
        x = x0 + c * cell_size
        y = y0 + r * cell_size
        positions.append((x, y))


# -------------------- AI Logic --------------------
def evaluate(game, maximizing_token):
    """
    Heuristic evaluation function.
    Positives are good for 'maximizing_token'.
    """
    opponent = TOKEN_RED if maximizing_token == TOKEN_BLUE else TOKEN_BLUE

    # 1. Material Count
    my_cnt = game.board.count(maximizing_token)
    op_cnt = game.board.count(opponent)
    material = 10 * (my_cnt - op_cnt)

    # 2. Center Control (The center pieces are valuable for Gánh)
    center_score = 0
    # Indices of the inner 3x3 grid
    center_indices = [6, 7, 8, 11, 12, 13, 16, 17, 18]
    for i in center_indices:
        if game.board[i] == maximizing_token:
            center_score += 1
        elif game.board[i] == opponent:
            center_score -= 1

    # 3. Mobility (Number of legal moves)
    # Note: Calculating legal moves is expensive, so we skip it for depth > 0 if needed,
    # but for a small board like this, it's usually fine.
    my_moves = len(game.get_legal_moves(maximizing_token))
    op_moves = len(game.get_legal_moves(opponent))
    mobility = 0.5 * (my_moves - op_moves)

    return material + (center_score * 2) + mobility


def minimax(game, depth, alpha, beta, maximizing_token, current_token):
    opponent = TOKEN_RED if current_token == TOKEN_BLUE else TOKEN_BLUE

    # Check terminal state
    winner, _ = game.check_winner()
    if winner:
        if winner == maximizing_token:
            return 10000 + depth, None
        elif winner == opponent:
            return -10000 - depth, None
        else:
            return 0, None  # Draw

    if depth == 0:
        return evaluate(game, maximizing_token), None

    moves = game.get_legal_moves(current_token)
    if not moves:
        # No moves available = Lose
        if current_token == maximizing_token:
            return -10000, None
        else:
            return 10000, None

    # Move ordering (Optimization: try center moves first)
    def score_move(mv):
        # Prefer moving to center (index 12 is absolute center)
        return -abs(mv[1] - 12)

    moves.sort(key=score_move, reverse=True)

    best_move = None

    if current_token == maximizing_token:
        max_eval = -float("inf")
        for start, end in moves:
            # Create a copy of the game to simulate the move
            new_game = game.copy()
            new_game.apply_move(start, end, current_token)

            val, _ = minimax(
                new_game, depth - 1, alpha, beta, maximizing_token, opponent
            )

            if val > max_eval:
                max_eval = val
                best_move = (start, end)
            alpha = max(alpha, val)
            if beta <= alpha:
                break
        return max_eval, best_move
    else:
        min_eval = float("inf")
        for start, end in moves:
            new_game = game.copy()
            new_game.apply_move(start, end, current_token)

            val, _ = minimax(
                new_game, depth - 1, alpha, beta, maximizing_token, opponent
            )

            if val < min_eval:
                min_eval = val
                best_move = (start, end)
            beta = min(beta, val)
            if beta <= alpha:
                break
        return min_eval, best_move


def ai_minimax(game, color_token, depth):
    if depth == 0:
        # Random move
        moves = game.get_legal_moves(color_token)
        return random.choice(moves) if moves else None

    _, move = minimax(
        game, depth, -float("inf"), float("inf"), color_token, color_token
    )
    return move


# -------------------- UI Classes --------------------
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Cờ Gánh - Play vs AI")
title_f, font_b, font, tiny = load_fonts()
clock = pygame.time.Clock()


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
        if hover:
            base = (225, 230, 238) if not self.active else (195, 212, 255)
        pygame.draw.rect(surf, base, self.rect, border_radius=10)
        pygame.draw.rect(surf, LINE, self.rect, 2, border_radius=10)
        txt = font.render(self.text, True, BLACK)
        surf.blit(txt, txt.get_rect(center=self.rect.center))

    def handle(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.on_click()
                return True
        return False

    def set_text(self, text):
        self.text = text


# -------------------- UI Functions --------------------
def draw_grid_and_pieces(game, turn_token, player_token, depth):
    screen.fill(WHITE)
    # Header
    pygame.draw.rect(screen, PANEL, (0, 0, WIDTH, header_h))
    title = title_f.render("CỜ GÁNH", True, BLACK)
    screen.blit(title, title.get_rect(center=(WIDTH // 2, 28)))

    turn_str = "RED" if turn_token == TOKEN_RED else "BLUE"
    p_str = "BLUE" if player_token == TOKEN_BLUE else "RED"
    sub = tiny.render(
        f"Lượt: {turn_str}   |   Bạn: {p_str}   |   Depth: {depth}", True, MUTED
    )
    screen.blit(sub, sub.get_rect(center=(WIDTH // 2, 58)))

    # Lines (Use game.neighbors to draw connections)
    # We iterate all nodes, find their neighbors, and draw lines.
    # To avoid double drawing, we only draw if i < j
    for i in range(SIZE * SIZE):
        for j in game.neighbors[i]:
            if i < j:
                pygame.draw.line(screen, BLACK, positions[i], positions[j], 2)

    # Pieces
    for i, (x, y) in enumerate(positions):
        # Draw intersection dot
        pygame.draw.circle(screen, BLACK, (x, y), 6)

        t = game.board[i]
        if t == TOKEN_RED:
            pygame.draw.circle(screen, RED, (x, y), 24)
        elif t == TOKEN_BLUE:
            pygame.draw.circle(screen, BLUE, (x, y), 24)


def menu_screen():
    player_color = TOKEN_BLUE
    depth = 3
    running = True

    # Layout
    panel = pygame.Rect(WIDTH // 2 - 170, header_h + 20, 340, 300)
    buttons = []

    def set_blue():
        nonlocal player_color
        player_color = TOKEN_BLUE
        refresh()

    def set_red():
        nonlocal player_color
        player_color = TOKEN_RED
        refresh()

    def set_depth(d):
        nonlocal depth
        depth = d
        refresh()

    def start_game():
        nonlocal running
        running = False

    def refresh():
        buttons.clear()
        # Color
        buttons.append(
            Button(
                (panel.x + 22, panel.y + 26, 140, 44),
                "Chơi BLUE",
                set_blue,
                active=(player_color == TOKEN_BLUE),
            )
        )
        buttons.append(
            Button(
                (panel.x + 178, panel.y + 26, 140, 44),
                "Chơi RED",
                set_red,
                active=(player_color == TOKEN_RED),
            )
        )
        # Depth
        buttons.append(
            Button(
                (panel.x + 22, panel.y + 92, 90, 40),
                "Random",
                lambda: set_depth(0),
                active=(depth == 0),
            )
        )
        buttons.append(
            Button(
                (panel.x + 126, panel.y + 92, 90, 40),
                "Depth 1",
                lambda: set_depth(1),
                active=(depth == 1),
            )
        )
        buttons.append(
            Button(
                (panel.x + 230, panel.y + 92, 90, 40),
                "Depth 3",
                lambda: set_depth(3),
                active=(depth == 3),
            )
        )
        buttons.append(
            Button(
                (panel.x + 126, panel.y + 142, 90, 40),
                "Depth 5",
                lambda: set_depth(5),
                active=(depth == 5),
            )
        )
        # Start
        buttons.append(
            Button(
                (panel.x + 70, panel.y + 210, 200, 48),
                "Bắt đầu",
                start_game,
                active=False,
            )
        )

    refresh()

    while running:
        screen.fill(WHITE)
        pygame.draw.rect(screen, PANEL, (0, 0, WIDTH, header_h))
        title = title_f.render("CỜ GÁNH", True, BLACK)
        screen.blit(title, title.get_rect(center=(WIDTH // 2, 36)))

        pygame.draw.rect(screen, PANEL, panel, border_radius=14)
        pygame.draw.rect(screen, LINE, panel, 2, border_radius=14)

        screen.blit(font_b.render("Chọn màu", True, BLACK), (panel.x + 22, panel.y - 2))
        screen.blit(font_b.render("Độ khó", True, BLACK), (panel.x + 22, panel.y + 64))

        for b in buttons:
            b.draw(screen)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            for b in buttons:
                b.handle(event)

        pygame.display.flip()
        clock.tick(60)

    return player_color, depth


def result_screen(winner_token, reason, player_token, depth):
    running = True
    panel = pygame.Rect(WIDTH // 2 - 170, HEIGHT // 2 - 90, 340, 180)

    action = None

    def replay():
        nonlocal action, running
        action = "REPLAY"
        running = False

    def back_menu():
        nonlocal action, running
        action = "MENU"
        running = False

    btn_replay = Button((panel.x + 24, panel.y + 110, 130, 44), "Chơi lại", replay)
    btn_menu = Button(
        (panel.x + 186, panel.y + 110, 130, 44), "Quay về menu", back_menu
    )

    who = (
        "RED"
        if winner_token == TOKEN_RED
        else "BLUE" if winner_token == TOKEN_BLUE else "Hòa"
    )

    while running:
        screen.fill(WHITE)
        pygame.draw.rect(screen, PANEL, (0, 0, WIDTH, header_h))
        title = title_f.render("KẾT THÚC VÁN", True, BLACK)
        screen.blit(title, title.get_rect(center=(WIDTH // 2, 36)))

        pygame.draw.rect(screen, PANEL, panel, border_radius=14)
        pygame.draw.rect(screen, LINE, panel, 2, border_radius=14)

        msg1 = font_b.render(f"Thắng: {who}", True, BLACK)
        msg2 = font.render(f"Lý do: {reason}", True, MUTED)
        p_str = "BLUE" if player_token == TOKEN_BLUE else "RED"
        msg3 = tiny.render(f"Bạn: {p_str} | Depth: {depth}", True, MUTED)

        screen.blit(msg1, msg1.get_rect(center=(WIDTH // 2, panel.y + 36)))
        screen.blit(msg2, msg2.get_rect(center=(WIDTH // 2, panel.y + 66)))
        screen.blit(msg3, msg3.get_rect(center=(WIDTH // 2, panel.y + 88)))

        btn_replay.draw(screen)
        btn_menu.draw(screen)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            btn_replay.handle(event)
            btn_menu.handle(event)

        pygame.display.flip()
        clock.tick(60)

    return action


# -------------------- Main Game Loop --------------------
def run_game(player_token, ai_depth):
    # Initialize the Game Logic Object
    game = CoGanh()

    selected = None
    turn_token = TOKEN_RED  # Red always starts
    ai_thinking = False
    paused = False

    pause_btn = Button((WIDTH - 416, 10, 110, 38), "Pause", lambda: None)

    def toggle_pause():
        nonlocal paused
        paused = not paused
        pause_btn.set_text("Continue" if paused else "Pause")

    pause_btn.on_click = toggle_pause

    while True:
        # 1. Check Winner
        winner, reason = game.check_winner()

        # 2. Check if current player is stuck (No moves)
        if not winner:
            legal = game.get_legal_moves(turn_token)
            if not legal:
                winner = TOKEN_BLUE if turn_token == TOKEN_RED else TOKEN_RED
                reason = "Hết nước đi"

        if winner:
            return result_screen(winner, reason, player_token, ai_depth)

        # 3. Handle Events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "MENU"

            if pause_btn.handle(event):
                continue

            if paused:
                continue

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if turn_token != player_token:
                    continue  # Not your turn

                mx, my = event.pos
                for i, (x, y) in enumerate(positions):
                    if (mx - x) ** 2 + (my - y) ** 2 <= 24**2:
                        if selected is None:
                            if game.board[i] == player_token:
                                selected = i
                        else:
                            valid_moves = game.get_legal_moves(player_token)
                            is_valid = any(
                                start == selected and end == i for start, end in valid_moves
                            )

                            if is_valid:
                                game.apply_move(selected, i, player_token)
                                turn_token = (
                                    TOKEN_RED if player_token == TOKEN_BLUE else TOKEN_BLUE
                                )
                                selected = None
                            else:
                                if game.board[i] == player_token:
                                    selected = i
                                else:
                                    selected = None
                        break

        # 4. AI Turn
        if not paused and turn_token != player_token and not ai_thinking:
            ai_thinking = True
            start_t = time.time()
            chosen_move = ai_minimax(game, turn_token, ai_depth)
            end_t = time.time()
            print(
                f"[AI] Depth={ai_depth} Move={chosen_move} Time={end_t - start_t:.2f}s"
            )

            if chosen_move:
                game.apply_move(chosen_move[0], chosen_move[1], turn_token)

            turn_token = TOKEN_RED if turn_token == TOKEN_BLUE else TOKEN_BLUE
            ai_thinking = False

        # 5. Render
        draw_grid_and_pieces(game, turn_token, player_token, ai_depth)

        if selected is not None:
            x, y = positions[selected]
            pygame.draw.circle(screen, GREEN, (x, y), 28, 3)

        if paused:
            overlay = pygame.Surface((WIDTH, HEIGHT))
            overlay.set_alpha(140)
            overlay.fill(OVERLAY)
            screen.blit(overlay, (0, 0))
            paused_text = font_b.render("TẠM DỪNG", True, WHITE)
            screen.blit(paused_text, paused_text.get_rect(center=(WIDTH // 2, HEIGHT // 2)))

        pause_btn.draw(screen)

        pygame.display.flip()
        clock.tick(60)


# -------------------- Entry Point --------------------
if __name__ == "__main__":
    try:
        while True:
            player_token, depth = menu_screen()
            action = run_game(player_token, depth)
            if action == "MENU":
                continue
            elif action == "REPLAY":
                # Run loop again with same settings
                continue
            else:
                break
    except KeyboardInterrupt:
        pygame.quit()
        sys.exit()
