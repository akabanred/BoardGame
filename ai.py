# ai.py  (Minimax + Alpha-Beta, depth 1|3|5, có luật GÁNH + CHẸT)
import sys
import socket
import threading
import json
import time
import argparse
import random
from typing import List, Tuple, Optional, Set, Deque
from collections import deque

# ---------- CLI ----------
parser = argparse.ArgumentParser(
    description="Co Ganh AI (Minimax + Alpha-Beta). Use --depth 1|3|5."
)
parser.add_argument("--server-ip", default="127.0.0.1")
parser.add_argument("--server-port", type=int, default=5555)
parser.add_argument("--color", choices=["red", "blue"], required=True)
parser.add_argument("--depth", type=int, choices=[1,3,5], default=3)
parser.add_argument("--delay", type=float, default=0.25, help="Think time (seconds)")
args = parser.parse_args()

# ---------- Colors ----------
RED   = (220, 50, 50)
BLUE  = (50, 80, 220)
LOCAL_COLOR = RED if args.color == "red" else BLUE

# ---------- Board / Graph (5x5 giống client) ----------
SIZE = 5
def index(r, c): return r * SIZE + c

# danh sách cạnh hợp lệ (ngang, dọc, chéo chỉ ở ô (r+c) chẵn – giống client)
CONN = set()
for r in range(SIZE):
    for c in range(SIZE):
        i = index(r, c)
        if c + 1 < SIZE:
            CONN.add((i, index(r, c + 1))); CONN.add((index(r, c + 1), i))
        if r + 1 < SIZE:
            CONN.add((i, index(r + 1, c))); CONN.add((index(r + 1, c), i))
        if (r + c) % 2 == 0:
            if r + 1 < SIZE and c + 1 < SIZE:
                CONN.add((i, index(r + 1, c + 1))); CONN.add((index(r + 1, c + 1), i))
            if r + 1 < SIZE and c - 1 >= 0:
                CONN.add((i, index(r + 1, c - 1))); CONN.add((index(r + 1, c - 1), i))

def neighbors(pos: int) -> List[int]:
    return [b for (a,b) in CONN if a == pos]

def are_connected(a: int, b: int) -> bool:
    return (a, b) in CONN

def rc(i: int) -> Tuple[int,int]:
    return (i // SIZE, i % SIZE)

# ---------- Current pieces (khởi tạo như client) ----------
pieces_lock = threading.Lock()
pieces = [
    # BLUE (trên)
    {"pos": 0, "color": BLUE}, {"pos": 1, "color": BLUE}, {"pos": 2, "color": BLUE},
    {"pos": 3, "color": BLUE}, {"pos": 4, "color": BLUE}, {"pos": 5, "color": BLUE},
    {"pos": 9, "color": BLUE}, {"pos": 14, "color": BLUE},
    # RED (dưới)
    {"pos": 10, "color": RED}, {"pos": 15, "color": RED}, {"pos": 19, "color": RED},
    {"pos": 20, "color": RED}, {"pos": 21, "color": RED}, {"pos": 22, "color": RED},
    {"pos": 23, "color": RED}, {"pos": 24, "color": RED},
]
turn_lock = threading.Lock()
turn = {"color": RED}  # RED đi trước

# ---------- Socket ----------
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((args.server_ip, args.server_port))
print(f"[AI] Connected to {args.server_ip}:{args.server_port} as {args.color.upper()} | depth={args.depth}")

# ---------- Board helpers ----------
# biểu diễn bàn cờ: 1 = RED, -1 = BLUE, 0 = trống
def board_from_pieces() -> List[int]:
    b = [0]*25
    with pieces_lock:
        for p in pieces:
            b[p["pos"]] = 1 if p["color"] == RED else -1
    return b

def color_to_player(color: Tuple[int,int,int]) -> int:
    return 1 if color == RED else -1

def legal_moves_board(b: List[int], player: int) -> List[Tuple[int,int]]:
    occ = {i for i,v in enumerate(b) if v != 0}
    my  = [i for i,v in enumerate(b) if v == player]
    moves=[]
    for src in my:
        for dst in neighbors(src):
            if dst not in occ:
                moves.append((src, dst))
    return moves

# --------- LUẬT: GÁNH + CHẸT ---------
# 1) GÁNH: tại ô đích d, nếu hai đầu a & c là quân đối phương, collinear với d và đều có cạnh hợp lệ, thì flip a & c.
AXES = [(0,1), (1,0), (1,1), (1,-1)]  # 4 trục kiểm tra gánh

def try_ganh(nb: List[int], dst: int, me: int) -> None:
    opp = -me
    drc = [rc(dst)]
    dr, dc = drc[0]
    for (drd, dcd) in AXES:
        ar, ac = dr - drd, dc - dcd
        cr, cc = dr + drd, dc + dcd
        if 0 <= ar < SIZE and 0 <= ac < SIZE and 0 <= cr < SIZE and 0 <= cc < SIZE:
            a = ar*SIZE + ac
            c = cr*SIZE + cc
            # cần các cạnh hợp lệ a-dst và dst-c
            if are_connected(a, dst) and are_connected(dst, c):
                if nb[a] == opp and nb[c] == opp:
                    nb[a] = me
                    nb[c] = me

# 2) CHẸT: nhóm quân đối phương không còn "tự do" (liberty) → bị flip toàn nhóm.
def group_and_liberty(nb: List[int], start: int) -> Tuple[Set[int], bool]:
    """Trả về (tập nhóm, còn_tự_do?) theo cạnh hợp lệ trong CONN."""
    color = nb[start]
    q: Deque[int] = deque([start])
    group: Set[int] = set([start])
    has_liberty = False
    while q:
        u = q.popleft()
        for v in neighbors(u):
            if nb[v] == 0:
                has_liberty = True
            elif nb[v] == color and v not in group:
                group.add(v)
                q.append(v)
    return group, has_liberty

def try_chet(nb: List[int], me: int) -> None:
    opp = -me
    visited: Set[int] = set()
    for i, v in enumerate(nb):
        if v == opp and i not in visited:
            grp, lib = group_and_liberty(nb, i)
            visited |= grp
            if not lib:
                # bị vây: lật hết sang màu người vừa đi
                for u in grp:
                    nb[u] = me

def apply_move_with_rules(b: List[int], move: Tuple[int,int], me: int) -> List[int]:
    """Thực hiện nước đi + xử lý Gánh → rồi Chẹt (đổi màu)."""
    src, dst = move
    nb = b[:]
    nb[src] = 0
    nb[dst] = me
    # GÁNH trước
    try_ganh(nb, dst, me)
    # CHẸT sau
    try_chet(nb, me)
    return nb

# ---------- Evaluation (material + center + ganh tiềm năng + mobility) ----------
CENTER=(2,2)

W_MATERIAL=2.0
W_CENTER=0.6
W_GANH=1.2
W_MOBILITY=0.15

def center_score_for_player(b, player):
    cr,cc=CENTER; s=0.0
    for i,v in enumerate(b):
        if v==player:
            r,c=rc(i); s += -(abs(r-cr)+abs(c-cc))
    return s

def potential_ganh_targets(b: List[int], player: int) -> int:
    """Đếm số 'cơ hội gánh' nếu đặt quân vào 1 ô trống (xấp xỉ)."""
    opp=-player; cnt=0
    empties=[i for i,v in enumerate(b) if v==0]
    for e in empties:
        er,ec=rc(e)
        for drd,dcd in AXES:
            ar,ac=er-drd, ec-dcd
            cr,cc=er+drd, ec+dcd
            if 0<=ar<SIZE and 0<=ac<SIZE and 0<=cr<SIZE and 0<=cc<SIZE:
                a=ar*SIZE+ac; c=cr*SIZE+cc
                if are_connected(a,e) and are_connected(e,c) and b[a]==opp and b[c]==opp:
                    cnt += 1
    return cnt

def evaluate(b: List[int], player_view: int) -> float:
    my = sum(1 for v in b if v==player_view)
    op = sum(1 for v in b if v==-player_view)
    material = (my-op)*W_MATERIAL
    center   = (center_score_for_player(b,player_view)-center_score_for_player(b,-player_view))*W_CENTER
    ganh     = (potential_ganh_targets(b,player_view)-potential_ganh_targets(b,-player_view))*W_GANH
    mob      = (len(legal_moves_board(b,player_view))-len(legal_moves_board(b,-player_view)))*W_MOBILITY
    return material + center + ganh + mob

# ---------- Minimax + Alpha-Beta (có move ordering) ----------
def minimax(b: List[int], depth: int, player_to_move: int, player_view: int,
            alpha: float, beta: float) -> Tuple[float, Optional[Tuple[int,int]]]:
    if depth == 0:
        return evaluate(b, player_view), None

    moves = legal_moves_board(b, player_to_move)
    if not moves:
        return evaluate(b, player_view), None

    # Move ordering: ưu tiên tiến gần trung tâm khi maximize, xa khi minimize
    if player_to_move == player_view:
        moves.sort(key=lambda mv: -(abs(rc(mv[1])[0]-2)+abs(rc(mv[1])[1]-2)))
        best_move=None
        val=-1e18
        for mv in moves:
            nb = apply_move_with_rules(b, mv, player_to_move)
            sc,_ = minimax(nb, depth-1, -player_to_move, player_view, alpha, beta)
            if sc > val:
                val = sc; best_move = mv
            alpha = max(alpha, val)
            if beta <= alpha: break
        return val, best_move
    else:
        moves.sort(key=lambda mv: (abs(rc(mv[1])[0]-2)+abs(rc(mv[1])[1]-2)))
        best_move=None
        val=1e18
        for mv in moves:
            nb = apply_move_with_rules(b, mv, player_to_move)
            sc,_ = minimax(nb, depth-1, -player_to_move, player_view, alpha, beta)
            if sc < val:
                val = sc; best_move = mv
            beta = min(beta, val)
            if beta <= alpha: break
        return val, best_move

# ---------- Chọn nước ----------
def choose_move_by_depth(depth: int) -> Optional[Tuple[int,int]]:
    b = board_from_pieces()
    player = color_to_player(LOCAL_COLOR)
    legal = legal_moves_board(b, player)
    if not legal: return None
    _, mv = minimax(b, depth, player, player, -1e18, 1e18)
    return mv or random.choice(legal)

# ---------- Listen server ----------
def listen_server():
    global pieces, turn
    while True:
        try:
            data = sock.recv(1024)
            if not data:
                print("[AI] Server closed.")
                break
            move = json.loads(data.decode())
            with pieces_lock:
                if move.get("from",-1)!=-1 and move.get("to",-1)!=-1:
                    for p in pieces:
                        if p["pos"] == move["from"]:
                            p["pos"] = move["to"]
                            break
            with turn_lock:
                nxt = move.get("next_turn", None)
                if isinstance(nxt, list):
                    nxt = tuple(nxt)
                turn["color"] = nxt
        except Exception as e:
            print(f"[AI][ERROR listen] {e}")
            break

threading.Thread(target=listen_server, daemon=True).start()

# ---------- Main loop ----------
try:
    while True:
        time.sleep(0.02)
        with turn_lock:
            current_turn = turn["color"]
        if current_turn != LOCAL_COLOR:
            continue

        time.sleep(max(0.0, args.delay))  # “think time”

        mv = choose_move_by_depth(args.depth)
        if mv is None:
            # không có nước → nhường lượt (hiếm)
            next_turn = RED if current_turn == BLUE else BLUE
            payload = {"from": -1, "to": -1, "next_turn": list(next_turn)}
            try:
                sock.sendall(json.dumps(payload).encode())
                with turn_lock:
                    turn["color"] = next_turn
            except Exception as e:
                print(f"[AI][SEND ERROR skip] {e}")
            continue

        src, dst = mv

        # optimistic local update (client khác sẽ nhận từ server để đồng bộ)
        with pieces_lock:
            for p in pieces:
                if p["color"] == LOCAL_COLOR and p["pos"] == src:
                    p["pos"] = dst
                    break

        next_turn = RED if current_turn == BLUE else BLUE
        payload = {"from": src, "to": dst, "next_turn": list(next_turn)}
        try:
            sock.sendall(json.dumps(payload).encode())
            print(f"[AI][SEND] {payload} | depth={args.depth}")
            with turn_lock:
                turn["color"] = next_turn
        except Exception as e:
            print(f"[AI][SEND ERROR] {e}")
            # revert nếu cần
            with pieces_lock:
                for p in pieces:
                    if p["color"] == LOCAL_COLOR and p["pos"] == dst:
                        p["pos"] = src
                        break

except KeyboardInterrupt:
    pass
finally:
    try: sock.close()
    except: pass
    print("[AI] Quit.")
