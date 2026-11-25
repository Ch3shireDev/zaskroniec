a = [1, 2, 3]
a.append(4)
print(a, len(a), a[0], a[-1], a[1:3])
a[0] = 10
print(a)
print(a.pop(), a, a.pop(0), a)
b = a + [7, 8]
print(b, [0] * 3)
c = b
c += [9]
print(b)
t = (1, "two", 3)
print(t, t[1], len(t), (1,), ())
x, y = 1, 2
x, y = y, x
print(x, y)
[p, q] = [3, 4]
print(p, q)
d = {"a": 1, "b": 2}
d["c"] = 3
d["a"] = 100
print(d, len(d), d["b"], "a" in d, "z" in d)
print(d.get("a"), d.get("z"), d.get("z", 0))
for k in d.keys():
    print("key", k)
for kv in d.items():
    print(kv)
for k in d:
    print(k, d[k])
for k, v in d.items():
    print(k, v)
e = {1: "one", (1, 2): "pair"}
print(e[True], e[(1, 2)])
print([1, [2, (3, "x")], {"k": None}])
print([1, 2] == [1, 2], (1, 2) == (1, 2), [1] == (1,), {1: 2} == {1: 2})
print([1, 2] < [1, 3], (1, 2) < (1, 2, 0))
print(3 in [1, 2, 3], 4 in (1, 2), [] == [])
m = [[0] * 2, [0] * 2]
m[1][0] = 5
m[0][1] += 7
print(m)
print(isinstance(1, int), isinstance("a", str), isinstance([], list), isinstance((), tuple), isinstance({}, dict), isinstance(True, int), isinstance(1, bool))
