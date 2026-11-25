# Interpreter Brainfucka; program na stdin, bez wejscia (",").
# Uzycie: ./brainfuck < hello.bf
import sys

def run(code):
    jump = {}
    stack = []
    for i in range(len(code)):
        if code[i] == "[":
            stack.append(i)
        elif code[i] == "]":
            j = stack.pop()
            jump[i] = j
            jump[j] = i
    tape = [0] * 30000
    ptr = 0
    pc = 0
    out = []
    while pc < len(code):
        c = code[pc]
        if c == ">":
            ptr += 1
        elif c == "<":
            ptr -= 1
        elif c == "+":
            tape[ptr] = (tape[ptr] + 1) % 256
        elif c == "-":
            tape[ptr] = (tape[ptr] - 1) % 256
        elif c == ".":
            out.append(chr(tape[ptr]))
        elif c == "[" and tape[ptr] == 0:
            pc = jump[pc]
        elif c == "]" and tape[ptr] != 0:
            pc = jump[pc]
        pc += 1
    sys.stdout.write("".join(out))

run(sys.stdin.read())
