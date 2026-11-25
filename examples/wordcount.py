# Liczy slowa ze stdin i wypisuje 5 najczestszych.
# Uzycie: ./wordcount < plik.txt
import sys

counts = {}
for w in sys.stdin.read().split():
    counts[w] = counts.get(w, 0) + 1

pairs = []
for w, c in counts.items():
    pairs.append((-c, w))

# sortowanie przez wstawianie (nie ma sorted())
i = 1
while i < len(pairs):
    x = pairs[i]
    j = i - 1
    while j >= 0 and pairs[j] > x:
        pairs[j + 1] = pairs[j]
        j -= 1
    pairs[j + 1] = x
    i += 1

print("slow:", len(counts))
for p in pairs[:5]:
    print(-p[0], p[1])
