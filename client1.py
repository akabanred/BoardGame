import pygame
import sys
import socket
import threading
import json
from game import CoGanh, TOKEN_RED, TOKEN_BLUE, SIZE, EMPTY

# ==== Cấu hình mạng ====
SERVER_IP = "127.0.0.1"
SERVER_PORT = 5555

# ==== Config UI ====
WIDTH, HEIGHT = 420, 540
cell_size = 72
header_h = 88

WHITE = (255, 255, 255)
BLACK = (20, 24, 33)
RED_COLOR = (220, 50, 50)
BLUE_COLOR = (50, 80, 220)
GREEN = (0, 170, 0)
MUTED = (115, 120, 130)
PANEL = (245, 248, 252)
OVERLAY = (0, 0, 0)

# ==== Setup Game Logic ====
game = CoGanh()
game_lock = threading.Lock()

# Người 1: RED
local_token = TOKEN_RED
selected_node = None
paused = False
pause_btn = None

# ==== Setup Socket ====
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((SERVER_IP, SERVER_PORT))
    print(f"[CONNECTED] Connected to {SERVER_IP}:{SERVER_PORT} as RED")
except Exception as e:
    print(f"[ERROR] Could not connect: {e}")
    sys.exit()


# ==== Fonts (Fix lỗi hiển thị tiếng Việt) ====
def load_fonts():
    candidates = ["Segoe UI", "Arial", "Helvetica", "Roboto", None]
    for name in candidates:
        try:
            title_f = pygame.font.SysFont(name, 40, bold=True)
            font_b = pygame.font.SysFont(name, 22, bold=True)
            font = pygame.font.SysFont(name, 20)
            tiny = pygame.font.SysFont(name, 16)
            # Test render
            _ = title_f.render("CỜ GÁNH", True, BLACK)
            return title_f, font_b, font, tiny
        except Exception:
            continue
    return (
        pygame.font.SysFont(None, 40, bold=True),
        pygame.font.SysFont(None, 22, bold=True),
        pygame.font.SysFont(None, 20),
        pygame.font.SysFont(None, 16),
    )


# ==== Geometry ====
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


def set_pause_state(value, *, remote):
    """Updates pause flag and button label."""
    global paused, selected_node
    if paused == value:
        return
    paused = value
    with game_lock:
        selected_node = None
    if pause_btn is not None:
        pause_btn.set_text("Continue" if paused else "Pause")
    source = "REMOTE" if remote else "LOCAL"
    state = "PAUSED" if paused else "RESUMED"
    print(f"[{source}] {state}")


# ==== Network Listener ====
def listen_server():
    global game
    while True:
        try:
            data = sock.recv(1024)
            if not data:
                break

            msg = json.loads(data.decode())
            msg_type = msg.get("type", "move")

            if msg_type == "move":
                src = msg["from"]
                dst = msg["to"]
                color = msg["color"]

                with game_lock:
                    game.apply_move(src, dst, color)
                    game.turn = TOKEN_RED if color == TOKEN_BLUE else TOKEN_BLUE

                print(f"[OPPONENT] Moved {src} -> {dst}")
            elif msg_type == "pause":
                set_pause_state(bool(msg.get("value", False)), remote=True)
            else:
                print(f"[WARN] Unknown message: {msg}")

        except Exception as e:
            print(f"[NET ERROR] {e}")
            break


threading.Thread(target=listen_server, daemon=True).start()

# ==== Pygame Loop ====
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Cờ Gánh - Client 1 (RED)")
title_f, font_b, font, tiny = load_fonts()
clock = pygame.time.Clock()


class Button:
    def __init__(self, rect, text, on_click):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.on_click = on_click

    def draw(self, surf):
        mx, my = pygame.mouse.get_pos()
        hover = self.rect.collidepoint(mx, my)
        base = (234, 238, 245)
        if hover:
            base = (220, 226, 236)
        pygame.draw.rect(surf, base, self.rect, border_radius=10)
        pygame.draw.rect(surf, MUTED, self.rect, 2, border_radius=10)
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


def toggle_pause():
    global paused
    new_state = not paused
    set_pause_state(new_state, remote=False)
    payload = {"type": "pause", "value": new_state}
    try:
        sock.sendall(json.dumps(payload).encode())
    except Exception as exc:
        print(f"[NET ERROR] Pause send failed: {exc}")


pause_btn = Button((WIDTH - 416, 10, 110, 38), "Pause", toggle_pause)
if paused:
    pause_btn.set_text("Continue")

def draw_board():
    screen.fill(WHITE)

    # Header Uniform Style
    pygame.draw.rect(screen, PANEL, (0, 0, WIDTH, header_h))

    # Title
    title = title_f.render("CỜ GÁNH", True, BLACK)
    screen.blit(title, title.get_rect(center=(WIDTH // 2, 28)))

    # Status Line
    turn_str = "RED" if game.turn == TOKEN_RED else "BLUE"
    p_str = "RED"  # Client 1 is RED

    # Render status text
    status = f"Lượt: {turn_str}   |   Bạn: {p_str}"
    if paused:
        status += "   |   TẠM DỪNG"
    sub = tiny.render(status, True, MUTED)
    screen.blit(sub, sub.get_rect(center=(WIDTH // 2, 58)))

    # Draw Lines
    for i in range(SIZE * SIZE):
        for j in game.neighbors[i]:
            if i < j:
                pygame.draw.line(screen, BLACK, positions[i], positions[j], 2)

    # Draw Pieces
    with game_lock:
        for i, (x, y) in enumerate(positions):
            pygame.draw.circle(screen, BLACK, (x, y), 6)  # Dot

            piece = game.board[i]
            if piece == TOKEN_RED:
                pygame.draw.circle(screen, RED_COLOR, (x, y), 24)
            elif piece == TOKEN_BLUE:
                pygame.draw.circle(screen, BLUE_COLOR, (x, y), 24)

            # Highlight selection
            if i == selected_node:
                pygame.draw.circle(screen, GREEN, (x, y), 28, 3)


def handle_click(pos):
    global selected_node
    if paused:
        return
    mx, my = pos

    clicked_idx = -1
    for i, (px, py) in enumerate(positions):
        if (mx - px) ** 2 + (my - py) ** 2 <= 24**2:
            clicked_idx = i
            break

    if clicked_idx == -1:
        selected_node = None
        return

    with game_lock:
        if selected_node is None:
            if game.board[clicked_idx] == local_token:
                selected_node = clicked_idx
        else:
            start = selected_node
            end = clicked_idx

            if (
                game.turn == local_token
                and game.board[end] == EMPTY
                and end in game.neighbors[start]
            ):

                game.apply_move(start, end, local_token)
                game.turn = TOKEN_BLUE

                payload = {"type": "move", "from": start, "to": end, "color": local_token}
                try:
                    sock.sendall(json.dumps(payload).encode())
                    print(f"[SENT] {payload}")
                except:
                    print("Send failed")

                selected_node = None
            elif game.board[end] == local_token:
                selected_node = end
            else:
                selected_node = None


while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            try:
                sock.sendall(json.dumps({"type": "pause", "value": False}).encode())
            except Exception:
                pass
            sock.close()
            pygame.quit()
            sys.exit()

        if pause_btn.handle(event):
            continue

        if paused:
            continue

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            handle_click(event.pos)

    draw_board()

    winner, reason = game.check_winner()
    if winner:
        res_text = f"THẮNG: {'RED' if winner == TOKEN_RED else 'BLUE'}"
        res_surf = font_b.render(res_text, True, GREEN)
        screen.blit(res_surf, res_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2)))

    if paused:
        overlay = pygame.Surface((WIDTH, HEIGHT))
        overlay.set_alpha(140)
        overlay.fill(OVERLAY)
        screen.blit(overlay, (0, 0))
        paused_label = font_b.render("TẠM DỪNG", True, WHITE)
        screen.blit(paused_label, paused_label.get_rect(center=(WIDTH // 2, HEIGHT // 2)))

    pause_btn.draw(screen)

    pygame.display.flip()
    clock.tick(60)
