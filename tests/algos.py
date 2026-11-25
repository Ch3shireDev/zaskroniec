def qsort(a):
    if len(a) <= 1:
        return a
    p = a[0]
    lo = []
    hi = []
    for x in a[1:]:
        if x < p:
            lo.append(x)
        else:
            hi.append(x)
    return qsort(lo) + [p] + qsort(hi)

seed = 12345
def rnd():
    global seed
    seed = (seed * 1103515245 + 12345) % 2147483648
    return seed
xs = []
for i in range(200):
    xs.append(rnd() % 1000)
print(qsort(xs)[:20])
print(qsort(["pear", "apple", "fig", "banana"]))

def sieve(n):
    is_p = [True] * (n + 1)
    is_p[0] = False
    is_p[1] = False
    i = 2
    while i * i <= n:
        if is_p[i]:
            j = i * i
            while j <= n:
                is_p[j] = False
                j += i
        i += 1
    out = []
    for k in range(n + 1):
        if is_p[k]:
            out.append(k)
    return out
p = sieve(10000)
print(len(p), p[-5:])

def hanoi(n, a, b, c, moves):
    if n == 0:
        return
    hanoi(n - 1, a, c, b, moves)
    moves.append((a, c))
    hanoi(n - 1, b, a, c, moves)
m = []
hanoi(10, "A", "B", "C", m)
print(len(m), m[:3])

def fact(n):
    r = 1
    for i in range(2, n + 1):
        r *= i
    return r
print(fact(20))
memo = {}
def fibm(n):
    if n in memo:
        return memo[n]
    r = n
    if n >= 2:
        r = fibm(n - 1) + fibm(n - 2)
    memo[n] = r
    return r
print(fibm(90))
