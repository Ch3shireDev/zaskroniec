def fib(n):
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)

print(fib(30))
i = 0
while i < 10:
    print(i, fib(i))
    i += 1
