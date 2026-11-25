import sys
data = sys.stdin.read()
words = data.split()
print(len(words))
total = 0
for w in words:
    if w.isdigit():
        total += int(w)
print(total)
lines = data.split("\n")
print(lines)
