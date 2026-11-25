s = "abcdef"
l = [0, 1, 2, 3, 4, 5]
t = (0, 1, 2, 3, 4, 5)
for i in range(-6, 6):
    print(i, s[i], l[i], t[i])
for a in [-100, -3, -1, 0, 2, 6, 100]:
    for b in [-100, -2, 0, 3, 100]:
        print(a, b, s[a:b], l[a:b], t[a:b])
print(s[:], l[:], t[:], s[:-1], l[1:])
