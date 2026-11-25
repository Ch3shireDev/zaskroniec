#!/bin/bash
# Testy roznicowe: python3 vs skompilowana binarka. ZC = komenda kompilatora (stdin -> asm).
# Uzycie: tests/run.sh [plik.py ...]    ZC="build/stage1" tests/run.sh
ZC=${ZC:-"python3 src/zc.py"}
OUT=build/tests
mkdir -p "$OUT"
pass=0; fail=0
files=("$@"); [ ${#files[@]} -eq 0 ] && files=(tests/*.py)
for t in "${files[@]}"; do
    name=$(basename "$t" .py)
    in=/dev/null; [ -f "tests/$name.in" ] && in="tests/$name.in"
    python3 "$t" < "$in" > "$OUT/$name.expected" 2>/dev/null; ecode=$?
    if ! $ZC < "$t" > "$OUT/$name.s" 2> "$OUT/$name.cerr"; then
        echo "FAIL $name (compile)"; head -3 "$OUT/$name.cerr"; fail=$((fail+1)); continue
    fi
    if ! gcc -O0 -o "$OUT/$name" "$OUT/$name.s" runtime/rt.c 2> "$OUT/$name.gccerr"; then
        echo "FAIL $name (assemble/link)"; head -5 "$OUT/$name.gccerr"; fail=$((fail+1)); continue
    fi
    "$OUT/$name" < "$in" > "$OUT/$name.actual" 2>/dev/null; acode=$?
    if [ $ecode -ne $acode ]; then
        echo "FAIL $name (exit code: python $ecode, zc $acode)"; fail=$((fail+1)); continue
    fi
    if ! diff -q "$OUT/$name.expected" "$OUT/$name.actual" > /dev/null; then
        echo "FAIL $name (output differs)"; diff "$OUT/$name.expected" "$OUT/$name.actual" | head -10; fail=$((fail+1)); continue
    fi
    pass=$((pass+1))
done
echo "passed: $pass, failed: $fail"
[ $fail -eq 0 ]
