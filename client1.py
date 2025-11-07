import pygame
import sys
import socket, threading, json

# ==== Cấu hình mạng ====
SERVER_IP = "127.0.0.1"  # 🧠 đổi thành IP VPS hoặc LAN server
SERVER_PORT = 5555

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((SERVER_IP, SERVER_PORT))

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (180, 180, 180)
RED = (220, 50, 50)
BLUE = (50, 80, 220)
GREEN = (0, 200, 0)

# Người 1 luôn là Đỏ, người 2 là Xanh
local_color = RED  # máy 1 để RED
turn = {"color": RED}
selected_piece = None

# ✅ Thêm Lock để đồng bộ dữ liệu giữa các thread
turn_lock = threading.Lock()
pieces_lock = threading.Lock()

# Quân cờ: danh sách gồm (vị trí, màu)
pieces = [
    # Xanh (người 2) - phía trên
    {"pos": 0, "color": BLUE}, {"pos": 1, "color": BLUE}, {"pos": 2, "color": BLUE},
    {"pos": 3, "color": BLUE}, {"pos": 4, "color": BLUE}, {"pos": 5, "color": BLUE}, 
    {"pos": 9, "color": BLUE}, {"pos": 14, "color": BLUE},
    # Đỏ (người 1) - phía dưới
    {"pos": 10, "color": RED}, {"pos": 15, "color": RED}, {"pos": 19, "color": RED},
    {"pos": 20, "color": RED}, {"pos": 21, "color": RED}, {"pos": 22, "color": RED},
    {"pos": 23, "color": RED}, {"pos": 24, "color": RED},
]

# ==== Lắng nghe luồng từ server ====
def listen_server():
    global pieces, turn
    while True:
        try:
            data = sock.recv(1024)
            if not data:
                break
            move = json.loads(data.decode())
            
            # ✅ Sử dụng lock khi cập nhật pieces
            with pieces_lock:
                for p in pieces:
                    if p["pos"] == move["from"]:
                        p["pos"] = move["to"]
                        break
            
            # ✅ Sử dụng lock khi cập nhật turn
            # Chuyển list từ JSON về tuple
            with turn_lock:
                turn["color"] = tuple(move["next_turn"]) if isinstance(move["next_turn"], list) else move["next_turn"]
            
            print(f"[RECEIVE] {move}")

        except Exception as e:
            print(f"[ERROR] {e}")
            break

threading.Thread(target=listen_server, daemon=True).start()

pygame.init()
WIDTH, HEIGHT = 300, 300
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Cờ gánh - RED Client")

# ==== BẢNG 5x5 ====
size = 5
cell_size = WIDTH // (size + 1)
offset = cell_size

positions = []
for r in range(size):
    for c in range(size):
        x = offset + c * cell_size
        y = offset + r * cell_size
        positions.append((x, y))

# ==== SINH CONNECTIONS ====
connections = []
def index(r, c): return r * size + c

for r in range(size):
    for c in range(size):
        i = index(r, c)
        # phải
        if c + 1 < size:
            connections.append((i, index(r, c + 1)))
        # xuống
        if r + 1 < size:
            connections.append((i, index(r + 1, c)))
        # chéo nếu r + c chẵn
        if (r + c) % 2 == 0:
            if r + 1 < size and c + 1 < size:
                connections.append((i, index(r + 1, c + 1)))
            if r + 1 < size and c - 1 >= 0:
                connections.append((i, index(r + 1, c - 1)))

# ==== VẼ BoardGame ====
def draw_board():
    screen.fill(WHITE)
    # vẽ các line từ connections
    for a, b in connections:
        pygame.draw.line(screen, BLACK, positions[a], positions[b], 2)

    # vẽ các điểm giao
    for i, (x, y) in enumerate(positions):
        pygame.draw.circle(screen, BLACK, (x, y), 6)
    
    # ✅ Sử dụng lock khi đọc pieces
    with pieces_lock:
        for p in pieces:
            x, y = positions[p["pos"]]
            pygame.draw.circle(screen, p["color"], (x, y), 22)
            if p == selected_piece:
                pygame.draw.circle(screen, GREEN, (x, y), 26, 3)
    
    pygame.display.flip()

def get_piece_at_pos(mouse_pos):
    # ✅ Sử dụng lock khi đọc pieces
    with pieces_lock:
        for p in pieces:
            x, y = positions[p["pos"]]
            if (mouse_pos[0]-x)**2 + (mouse_pos[1]-y)**2 < 22**2:
                return p
    return None

def is_connected(pos1, pos2):
    return (pos1, pos2) in connections or (pos2, pos1) in connections

# ==== MAIN LOOP ====
clock = pygame.time.Clock()
while True:
    draw_board()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        elif event.type == pygame.MOUSEBUTTONDOWN:
            # ✅ Sử dụng lock khi kiểm tra turn
            with turn_lock:
                current_turn = turn["color"]
            
            if current_turn != local_color:
                continue  # không đến lượt mình

            mouse_pos = pygame.mouse.get_pos()
            clicked_piece = get_piece_at_pos(mouse_pos)

            if selected_piece:
                # thử di chuyển
                for i, (x, y) in enumerate(positions):
                    if (mouse_pos[0]-x)**2 + (mouse_pos[1]-y)**2 < 22**2:
                        # ✅ Kiểm tra ô trống với lock
                        with pieces_lock:
                            occupied = any(p["pos"] == i for p in pieces)
                        
                        if not occupied and is_connected(selected_piece["pos"], i):
                            old_pos = selected_piece["pos"]
                            
                            # ✅ Cập nhật vị trí với lock
                            with pieces_lock:
                                selected_piece["pos"] = i
                            
                            next_turn = RED if current_turn == BLUE else BLUE

                            move = {"from": old_pos, "to": i, "next_turn": list(next_turn)}  # ✅ Chuyển tuple sang list để JSON serialize
                            
                            try:
                                sock.sendall(json.dumps(move).encode())
                                print(f"[SEND] {move}")
                                
                                # ✅ Cập nhật turn với lock
                                with turn_lock:
                                    turn["color"] = next_turn
                            except Exception as e:
                                print(f"[SEND ERROR] {e}")
                        
                        selected_piece = None
                        break
            else:
                if clicked_piece and clicked_piece["color"] == local_color:
                    selected_piece = clicked_piece
    
    clock.tick(60)  # ✅ Giới hạn FPS để giảm tải CPU