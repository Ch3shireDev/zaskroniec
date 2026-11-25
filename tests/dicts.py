d = {}
for i in range(1000):
    d[i * 7 % 1000] = i
print(len(d), d[0], d[7], d[993])
keys = []
for k in d:
    keys.append(k)
print(keys[:10], keys[-5:])
s = {}
words = "the quick brown fox jumps over the lazy dog the end".split()
for w in words:
    s[w] = s.get(w, 0) + 1
print(s)
t = {(1, 2): "a", (1, (2, 3)): "b", "x": 1, 5: 2}
print(t[(1, 2)], t[(1, (2, 3))], (1, 2) in t, (2, 1) in t)
d2 = {1: "int"}
d2[True] = "bool"
print(d2)
d3 = {"a": [1]}
d3["a"].append(2)
print(d3, d3 == {"a": [1, 2]}, d3 == {"a": [1]})
big = {}
i = 0
while i < 20000:
    big[str(i)] = i
    i += 1
total = 0
for k, v in big.items():
    total += v
print(total, big["19999"])
