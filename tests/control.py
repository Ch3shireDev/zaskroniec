def classify(n):
    if n < 0:
        return "neg"
    elif n == 0:
        return "zero"
    elif n < 10:
        return "small"
    else:
        return "big"

for v in [-5, 0, 3, 42]:
    print(v, classify(v))

total = 0
for i in range(100):
    if i % 3 == 0:
        continue
    if i > 50:
        break
    total += i
print(total)
for i in range(5, 8):
    print(i)
for i in range(10, 0, -3):
    print(i)
n = 0
while True:
    n += 1
    if n == 5:
        break
print(n)
print(1 and 2, 0 and 2, 1 or 2, 0 or 2, None or "x", [] or [1])
print(not 0, not 1, not "", not "a")
x = None
print(x is None, x is not None)
if not x and 1:
    print("ok")
def f():
    pass
print(f())
