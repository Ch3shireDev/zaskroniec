print(repr(""), repr("'"), repr('"'), repr("\\"), repr("\0"), repr("a'b\"c"))
print(["a'", 'b"', "\n"], ("x",), {"k": ("v", [1])})
print(None, True, False, [None, True, False])
print(repr(1), repr(-5), repr([]), repr(()), repr({}), str([1, "a"]))
print("tab\there", "nul", "end")
print(str(None), str(True), str("x"), str((1, 2)))
nested = [[[]], [()], ({},)]
print(nested, len(nested))
print(repr(chr(1)), repr(chr(127)), repr(chr(31)))
