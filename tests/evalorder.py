log = []
def t(x):
    log.append(x)
    return x
d = {}
t(d)[t("k")] = t("v")
print(log)
log = []
print(t(1) + t(2) * t(3), log)
log = []
f = lambda a, b, c: a
f(t("a"), t("b"), t("c"))
print(log)
log = []
x = {t("k1"): t("v1"), t("k2"): t("v2")}
print(log, x)
log = []
a = [0, 0]
a[t(0)] += t(5)
print(log, a)
log = []
print(t(0) and t(1), t(2) or t(3), log)
a = b = [1]
b.append(2)
print(a, a is b)
