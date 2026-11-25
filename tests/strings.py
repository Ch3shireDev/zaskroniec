s = "hello"
t = 'world'
print(s + " " + t)
print(len(s), s[0], s[-1], s[1:3], s[:2], s[3:], s[-3:], s[2:100], s[10:])
print(s * 3, "ab" * 0)
print("ell" in s, "z" in s, "z" not in s)
print(s == "hello", s != "hello", "a" < "b", "abc" < "abd", "ab" < "abc")
print(repr("it's"), repr('say "hi"'), repr("both ' and \""), repr("a\nb\tc\\d"))
print(str(42), int("123") + 1, int("-7"), repr(str(-3)))
print(ord("A"), chr(66))
print(",".join(["a", "b", "c"]), "".join([]))
print("a b  c\n d".split(), "a,b,,c".split(","))
print("123".isdigit(), "12a".isdigit(), "abc".isalpha(), "ab1".isalnum(), "".isdigit())
print("hello".startswith("he"), "hello".startswith("lo"))
for c in "abc":
    print(c)
print("x\ty")
print('')
print("")
