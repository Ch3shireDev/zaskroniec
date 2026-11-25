import sys
sys.setrecursionlimit(20000)
x = "global"
def f():
    return x
def g():
    x = "local"
    return x
def h():
    global x
    x = "changed"
print(f(), g(), x)
h()
print(f(), x)

def a():
    v = 1
    def b():
        def c():
            nonlocal v
            v += 10
            return v
        return c
    k = b()
    k()
    k()
    return v
print(a())

def counter_pair():
    n = 0
    def inc():
        nonlocal n
        n += 1
    def get():
        return n
    return inc, get
inc, get = counter_pair()
inc()
inc()
inc()
print(get())

def make_adders():
    res = []
    for i in range(3):
        def mk(j):
            return lambda: j
        res.append(mk(i))
    return res
for fn in make_adders():
    print(fn())

def loopvar():
    fs = []
    i = 0
    while i < 3:
        fs.append(lambda: i)
        i += 1
    return fs
for fn in loopvar():
    print(fn())

def shadow(print_it):
    len = 5
    return len + print_it
print(shadow(1))

def deep(n):
    if n == 0:
        return 0
    return 1 + deep(n - 1)
print(deep(10000))
