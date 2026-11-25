# Domkniecia: licznik, kompozycja funkcji i pulapka z pozno wiazanym i.
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
print("licznik:", c())

compose = lambda f, g: lambda x: f(g(x))
inc_then_double = compose(lambda x: x * 2, lambda x: x + 1)
print("(5 + 1) * 2 =", inc_then_double(5))

fs = []
for i in range(3):
    fs.append(lambda: i)
print("pozne wiazanie:", fs[0](), fs[1](), fs[2]())
