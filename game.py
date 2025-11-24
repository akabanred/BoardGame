import copy
from collections import deque

# --- Constants ---
SIZE = 5
TOKEN_RED = "R"
TOKEN_BLUE = "B"
EMPTY = None


class CoGanh:
    def __init__(self):
        self.board = [EMPTY] * (SIZE * SIZE)
        self.neighbors = self._generate_neighbors()
        self.reset()

    def _generate_neighbors(self):
        """Generates the graph connections based on Co Ganh rules."""
        neighbors = {i: [] for i in range(SIZE * SIZE)}
        for r in range(SIZE):
            for c in range(SIZE):
                i = r * SIZE + c
                # Right
                if c + 1 < SIZE:
                    j = r * SIZE + (c + 1)
                    neighbors[i].append(j)
                    neighbors[j].append(i)
                # Down
                if r + 1 < SIZE:
                    j = (r + 1) * SIZE + c
                    neighbors[i].append(j)
                    neighbors[j].append(i)
                # Diagonals (only if r+c is even)
                if (r + c) % 2 == 0:
                    if r + 1 < SIZE and c + 1 < SIZE:
                        j = (r + 1) * SIZE + (c + 1)
                        neighbors[i].append(j)
                        neighbors[j].append(i)
                    if r + 1 < SIZE and c - 1 >= 0:
                        j = (r + 1) * SIZE + (c - 1)
                        neighbors[i].append(j)
                        neighbors[j].append(i)
        return neighbors

    def reset(self):
        self.board = [EMPTY] * (SIZE * SIZE)
        blues = [0, 1, 2, 3, 4, 5, 9, 14]
        reds = [10, 15, 19, 20, 21, 22, 23, 24]
        for b in blues:
            self.board[b] = TOKEN_BLUE
        for r in reds:
            self.board[r] = TOKEN_RED
        self.turn = TOKEN_RED  # Red starts

    def get_legal_moves(self, color_token):
        moves = []
        for i, t in enumerate(self.board):
            if t == color_token:
                for nb in self.neighbors[i]:
                    if self.board[nb] is EMPTY:
                        moves.append((i, nb))
        return moves

    def _try_ganh(self, board, dst, me):
        """Internal function to check Gánh on a specific board state."""
        flips = []
        opp = TOKEN_RED if me == TOKEN_BLUE else TOKEN_BLUE
        r, c = divmod(dst, SIZE)

        # 4 Axes: Vertical, Horizontal, Diag1, Diag2
        axes = [(0, 1), (1, 0), (1, 1), (1, -1)]

        for dr, dc in axes:
            # Check neighbors on both sides
            ar, ac = r - dr, c - dc
            br, bc = r + dr, c + dc

            if 0 <= ar < SIZE and 0 <= ac < SIZE and 0 <= br < SIZE and 0 <= bc < SIZE:
                a = ar * SIZE + ac
                b = br * SIZE + bc
                # Must be connected neighbors
                if b in self.neighbors[dst] and a in self.neighbors[dst]:
                    if board[a] == opp and board[b] == opp:
                        flips.append(a)
                        flips.append(b)
        return flips

    def _try_chet(self, board, me):
        """Internal function to check Chẹt (trapping)."""
        flips = []
        opp = TOKEN_RED if me == TOKEN_BLUE else TOKEN_BLUE
        visited = set()

        for i, t in enumerate(board):
            if t == opp and i not in visited:
                # Flood fill to find group
                group = []
                q = deque([i])
                seen_local = {i}
                has_liberty = False

                while q:
                    u = q.popleft()
                    group.append(u)
                    for v in self.neighbors[u]:
                        if board[v] is EMPTY:
                            has_liberty = True
                        elif board[v] == opp and v not in seen_local:
                            seen_local.add(v)
                            q.append(v)

                visited |= seen_local
                if not has_liberty:
                    flips.extend(list(seen_local))
        return flips

    def apply_move(self, start, end, color_token):
        """
        Moves piece, checks Gánh/Chẹt, and updates board.
        Returns: dict {'flips': [list of indices flipped]}
        """
        self.board[end] = self.board[start]
        self.board[start] = EMPTY

        flips_g = self._try_ganh(self.board, end, color_token)
        # Apply Gánh flips immediately so Chẹt calculation is accurate
        for idx in flips_g:
            self.board[idx] = color_token

        flips_c = self._try_chet(self.board, color_token)
        for idx in flips_c:
            self.board[idx] = color_token

        return flips_g + flips_c

    def check_winner(self):
        """
        Returns (Winner_Token, Reason_String) or (None, None).
        """
        r_cnt = self.board.count(TOKEN_RED)
        b_cnt = self.board.count(TOKEN_BLUE)

        if r_cnt == 0:
            return TOKEN_BLUE, "RED hết quân"
        if b_cnt == 0:
            return TOKEN_RED, "BLUE hết quân"

        # Check if current player has moves
        # Note: In your original code, you checked this based on 'turn'.
        # Here we assume the external loop manages 'turn', but we can helper check.
        return None, None

    def copy(self):
        """Returns a deep copy of the game state for AI simulation."""
        new_game = CoGanh()
        new_game.board = self.board[:]
        new_game.turn = self.turn
        return new_game
