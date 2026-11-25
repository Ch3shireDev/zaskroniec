#!/bin/bash
# Testy bledow kompilacji: zc musi wyjsc z kodem 1 i wypisac "linia:kolumna: error" z naglowka "# error: L:C".
ZC=${ZC:-"python3 src/zc.py"}
pass=0; fail=0
for t in tests/cerr/*.py; do
    name=$(basename "$t" .py)
    want=$(sed -n '1s/^# error: //p' "$t")
    err=$($ZC < "$t" 2>&1 >/dev/null); code=$?
    if [ $code -ne 1 ]; then echo "FAIL cerr/$name (exit $code)"; fail=$((fail+1)); continue; fi
    if [[ "$err" != "$want: error"* ]]; then echo "FAIL cerr/$name: want $want, got: $err"; fail=$((fail+1)); continue; fi
    pass=$((pass+1))
done
echo "cerr passed: $pass, failed: $fail"
[ $fail -eq 0 ]
