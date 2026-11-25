# Gra w zycie Conwaya: szybowiec na planszy 10x10, 4 pokolenia.
W = 10
H = 10

def show(board):
    for row in board:
        line = []
        for cell in row:
            if cell:
                line.append("#")
            else:
                line.append(".")
        print("".join(line))
    print()

def step(board):
    new = []
    for y in range(H):
        row = []
        for x in range(W):
            n = 0
            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    if dy != 0 or dx != 0:
                        n += board[(y + dy) % H][(x + dx) % W]
            alive = board[y][x]
            row.append(int((alive and (n == 2 or n == 3)) or (not alive and n == 3)))
        new.append(row)
    return new

board = []
for y in range(H):
    board.append([0] * W)
board[0][1] = 1
board[1][2] = 1
board[2][0] = 1
board[2][1] = 1
board[2][2] = 1

for gen in range(4):
    print("pokolenie", gen)
    show(board)
    board = step(board)
