def make_counter():
    n = 0
    def inc():
        nonlocal n
        n += 1
        return n
    return inc

c = make_counter()
c()
c()
print(c())
c2 = make_counter()
print(c2(), c())

fs = []
for i in range(3):
    fs.append(lambda: i)
print(fs[0](), fs[1](), fs[2]())

def adder(k):
    return lambda x: x + k
add5 = adder(5)
print(add5(10))

def outer():
    x = 1
    def mid():
        def inner():
            return x * 100
        return inner()
    x = 2
    return mid()
print(outer())

G = 0
def bump():
    global G
    G += 1
bump()
bump()
print(G)

def rec(n):
    def go(k):
        if k == 0:
            return 0
        return k + go(k - 1)
    return go(n)
print(rec(10))

def param_cell(a):
    def get():
        return a
    a = a * 2
    return get
print(param_cell(21)())
compose = lambda f, g: lambda x: f(g(x))
print(compose(lambda x: x + 1, lambda x: x * 2)(5))
