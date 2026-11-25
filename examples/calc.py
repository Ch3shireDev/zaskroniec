# Kalkulator wyrazen calkowitych: + - * // % i nawiasy, jedna linia = jedno wyrazenie.
# Uzycie: echo "2 * (3 + 4)" | ./calc
import sys

def tokenize(s):
    toks = []
    i = 0
    while i < len(s):
        c = s[i]
        if c.isdigit():
            j = i
            while j < len(s) and s[j].isdigit():
                j += 1
            toks.append(int(s[i:j]))
            i = j
        elif s[i:i + 2] == "//":
            toks.append("//")
            i += 2
        elif c in "+-*%()":
            toks.append(c)
            i += 1
        elif c == " ":
            i += 1
        else:
            raise Exception("nieznany znak: " + c)
    toks.append("end")
    return toks

def evaluate(toks):
    pos = [0]
    def peek():
        return toks[pos[0]]
    def take():
        t = toks[pos[0]]
        pos[0] += 1
        return t
    def atom():
        t = take()
        if t == "(":
            v = expr()
            take()
            return v
        if t == "-":
            return -atom()
        return t
    def term():
        v = atom()
        while peek() == "*" or peek() == "//" or peek() == "%":
            op = take()
            r = atom()
            if op == "*":
                v = v * r
            elif op == "//":
                v = v // r
            else:
                v = v % r
        return v
    def expr():
        v = term()
        while peek() == "+" or peek() == "-":
            op = take()
            r = term()
            if op == "+":
                v = v + r
            else:
                v = v - r
        return v
    return expr()

for line in sys.stdin.read().split("\n"):
    if line.split():
        print(line, "=", evaluate(tokenize(line)))
