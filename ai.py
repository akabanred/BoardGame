"""
ai.py

Cờ Gánh 5x5 (local Play vs AI, không networking).
- Font: dùng system font qua pygame.font.SysFont (không cần .ttf)
- Luật: Gánh + Chẹt (được xử lý bởi game.py)
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

WIDTH, HEIGHT = 420, 540  # tăng size cho dễ bấm
cell_size = 72  # ô lớn hơn
header_h = 88  # chừa vùng header cho text


# -------------------- Fonts (no .ttf) --------------------
def load_fonts():
    # Thử vài system font phổ biến; nếu không có, SysFont(None, ...) sẽ fallback an toàn
    candidates = ["Segoe UI", "Arial", "Helvetica", "Roboto", None]
    for name in candidates:
        try:
            title_f = pygame.font.SysFont(name, 40, bold=True)
            font_b = pygame.font.SysFont(name, 22, bold=True)
            font = pygame.font.SysFont(name, 20)
            tiny = pygame.font.SysFont(name, 16)
            # render test để chắc chắn không lỗi
            _ = title_f.render("TEST", True, BLACK)
            return title_f, font_b, font, tiny
        except Exception:
            continue
    # fallback cuối
    return (
        pygame.font.SysFont(None, 40, bold=True),
        pygame.font.SysFont(None, 22, bold=True),
        pygame.font.SysFont(None, 20),
        pygame.font.SysFont(None, 16),
    )


# -------------------- Geometry --------------------
# Helper to map index 0-24 to (x, y) pixels
# Tính toạ độ lưới, canh GIỮA chiều ngang & phần dưới header
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
    Hàm đánh giá bàn cờ (Heuristic evaluation).
    Điểm dương tốt cho 'maximizing_token', âm tốt cho đối thủ.
    """
    opponent = TOKEN_RED if maximizing_token == TOKEN_BLUE else TOKEN_BLUE

    # 1. Material Count (Số lượng quân)
    my_cnt = game.board.count(maximizing_token)
    op_cnt = game.board.count(opponent)
    material = 10 * (my_cnt - op_cnt)

    # 2. Center Control (Kiểm soát trung tâm - quan trọng để Gánh)
    center_score = 0
    # Các vị trí 3x3 ở giữa bàn cờ
    center_indices = [6, 7, 8, 11, 12, 13, 16, 17, 18]
    for i in center_indices:
        if game.board[i] == maximizing_token:
            center_score += 1
        elif game.board[i] == opponent:
            center_score -= 1

    # 3. Mobility (Số nước đi hợp lệ chênh lệch)
    # Lưu ý: Tính toán legal moves tốn tài nguyên, nhưng với bàn 5x5 thì vẫn ổn.
    my_moves = len(game.get_legal_moves(maximizing_token))
    op_moves = len(game.get_legal_moves(opponent))
    mobility = 0.5 * (my_moves - op_moves)

    return material + (center_score * 2) + mobility


def minimax(game, depth, alpha, beta, maximizing_token, current_token):
    opponent = TOKEN_RED if current_token == TOKEN_BLUE else TOKEN_BLUE

    # Kiểm tra trạng thái kết thúc (Thắng/Thua/Hòa)
    winner, _ = game.check_winner()
    if winner:
        if winner == maximizing_token:
            return 10000 + depth, None
        elif winner == opponent:
            return -10000 - depth, None
        else:
            return 0, None  # Hòa

    if depth == 0:
        return evaluate(game, maximizing_token), None

    moves = game.get_legal_moves(current_token)
    if not moves:
        # Không còn nước đi = Thua
        if current_token == maximizing_token:
            return -10000, None
        else:
            return 10000, None

    # Move ordering (Tối ưu: ưu tiên đi vào trung tâm trước để cắt tỉa tốt hơn)
    def score_move(mv):
        # Ưu tiên di chuyển đến ô 12 (tâm bàn cờ)
        return -abs(mv[1] - 12)

    moves.sort(key=score_move, reverse=True)

    best_move = None

    if current_token == maximizing_token:
        max_eval = -float("inf")
        for start, end in moves:
            # Tạo bản sao game để mô phỏng nước đi
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
    if depth <= 0:
        # Random move (Depth 0)
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

    # Lines (Sử dụng game.neighbors để vẽ đường nối)
    for i in range(SIZE * SIZE):
        for j in game.neighbors[i]:
            if i < j:  # Tránh vẽ trùng lặp
                pygame.draw.line(screen, BLACK, positions[i], positions[j], 2)

    # Nodes + pieces
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
    """
    Hiển thị kết quả. Trả về:
      - "REPLAY" để chơi lại với cùng cấu hình
      - "MENU"   để quay về menu
    """
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
    # Khởi tạo Game Logic
    game = CoGanh()

    selected = None
    turn_token = TOKEN_RED  # Red luôn đi trước
    ai_thinking = False

    while True:
        # 1. Kiểm tra thắng thua
        winner, reason = game.check_winner()

        # 2. Kiểm tra nếu bên tới lượt bị kẹt (không còn nước đi)
        if not winner:
            legal = game.get_legal_moves(turn_token)
            if not legal:
                winner = TOKEN_BLUE if turn_token == TOKEN_RED else TOKEN_RED
                reason = "Hết nước đi"

        if winner:
            return result_screen(winner, reason, player_token, ai_depth)

        draw_grid_and_pieces(game, turn_token, player_token, ai_depth)

        # 3. Lượt của AI
        if turn_token != player_token and not ai_thinking:
            ai_thinking = True
            # Force redraw để user thấy bàn cờ trước khi AI suy nghĩ
            pygame.display.flip()

            # Chạy Minimax
            start_t = time.time()
            chosen_move = ai_minimax(game, turn_token, ai_depth)
            end_t = time.time()
            print(
                f"[AI] Depth={ai_depth} Move={chosen_move} Time={end_t - start_t:.2f}s"
            )

            if chosen_move:
                game.apply_move(chosen_move[0], chosen_move[1], turn_token)

            # Đổi lượt
            turn_token = TOKEN_RED if turn_token == TOKEN_BLUE else TOKEN_BLUE
            ai_thinking = False

        # 4. Tương tác người chơi
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "MENU"

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if turn_token != player_token:
                    continue  # Chưa đến lượt bạn

                mx, my = event.pos
                for i, (x, y) in enumerate(positions):
                    # Kiểm tra click vào phạm vi quân cờ
                    if (mx - x) ** 2 + (my - y) ** 2 <= 24**2:

                        # Logic: Chọn quân hoặc Di chuyển
                        if selected is None:
                            # Chọn quân của mình
                            if game.board[i] == player_token:
                                selected = i
                        else:
                            # Thử di chuyển
                            # Kiểm tra xem 'i' có phải hàng xóm hợp lệ và trống không
                            valid_moves = game.get_legal_moves(player_token)
                            is_valid = False
                            for start, end in valid_moves:
                                if start == selected and end == i:
                                    is_valid = True
                                    break

                            if is_valid:
                                game.apply_move(selected, i, player_token)
                                turn_token = (
                                    TOKEN_RED
                                    if player_token == TOKEN_BLUE
                                    else TOKEN_BLUE
                                )
                                selected = None
                            else:
                                # Nếu click vào quân mình khác -> Chọn lại quân đó
                                if game.board[i] == player_token:
                                    selected = i
                                else:
                                    # Click lung tung -> Bỏ chọn
                                    selected = None
                        break

        # Vẽ highlight quân đang chọn
        if selected is not None:
            x, y = positions[selected]
            pygame.draw.circle(screen, GREEN, (x, y), 28, 3)

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
                # Chơi lại cùng cấu hình
                continue
            else:
                break
    except KeyboardInterrupt:
        pygame.quit()
        sys.exit()
