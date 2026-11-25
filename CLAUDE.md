# zaskroniec — kompilator podzbioru Pythona do x86-64, self-hosted

## Cel
Kompilator **zc** dla języka **zaskroniec** (ścisły podzbiór Pythona 3) do assembly x86-64
(GNU as, składnia AT&T), linkowany z małym runtime'em w C do natywnej binarki ELF na Linuksie.
Kompilator jest napisany **w zaskrońcu**, więc od pierwszego dnia uruchamia go zwykły `python3`.

## Bootstrap (najważniejsza część) — w katalogu `stages/`, testy w `build/`
```
stage0: python3 src/zc.py < src/zc.py > stages/stage1.s     # kompilator uruchomiony przez CPython
        gcc stages/stage1.s runtime/rt.c -o stages/stage1
stage1: stages/stage1 < src/zc.py > stages/stage2.s          # binarka kompiluje samą siebie
        gcc stages/stage2.s runtime/rt.c -o stages/stage2
stage2: stages/stage2 < src/zc.py > stages/stage3.s
CHECK:  cmp stages/stage2.s stages/stage3.s                  # MUSI być identyczne (fixed point)
```
Bonus: `stage1.s == stage2.s` też powinno zachodzić, jeśli generowanie kodu jest deterministyczne.

## Interfejs kompilatora
- `zc` czyta źródło ze stdin, wypisuje assembly na stdout, błędy na stderr z `linia:kolumna`, exit code 1.
- Żadnych flag na start.

## Język zaskroniec (podzbiór Pythona 3)
Typy: `None`, `bool`, `int` (**63-bitowy, bez bigintów**), `str` (tylko ASCII, niemutowalny),
`list`, `tuple`, `dict` (klucze: `int`/`str`/`tuple`), funkcje (domknięcia).

Jest:
- przypisanie, rozpakowanie `a, b = b, a`, `+=` i podobne, `if/elif/else`, `while`, `for x in <list|str|range|dict>`,
  `break`, `continue`, `return`, `pass`, `global`, `nonlocal`
- `def` (także zagnieżdżone, z domknięciami), `lambda`
- `a[i]`, `a[i] = v`, wycinki `s[a:b]` (bez kroku), literały `[...]`, `(...)`, `{k: v}`
- operatory: `+ - * // %  == != < <= > >=  and or not  in  not in  is  is not`  (unarny `-`)
- `and`/`or` zwracają operand. Fałszywe: `None`, `False`, `0`, `""`, `[]`, `()`, `{}`.
- `assert` i `raise Exception("...")`, ale tylko jako abort z komunikatem (bez łapania)
- jedyny dozwolony import: `import sys`

Nie ma: floatów, `/`, `**`, klas, wyjątków z `try/except`, generatorów/`yield`, list comprehension,
f-stringów, dekoratorów, `*args`/`**kwargs`, argumentów domyślnych i nazwanych, `with`, `async`.

Wbudowane (minimum potrzebne do napisania kompilatora):
`print` (kilka argumentów, separator spacja), `len`, `str`, `int` (z `str`), `repr`, `ord`, `chr`, `range`,
`isinstance` (tylko z typami wbudowanymi), `sys.stdin.read()`, `sys.stdout.write`, `sys.stderr.write`,
`sys.exit`, `sys.setrecursionlimit` (w zc no-op),
metody: `list.append`, `list.pop`, `dict.get`, `dict.keys`, `dict.items`, `str.join`, `str.isdigit`,
`str.isalpha`, `str.isalnum`, `str.startswith`, `str.split` (bez argumentów i z jednym).

Uwaga: w zc `dict.keys()`/`dict.items()` zwracają listy, nie widoki — wolno po nich iterować, nie wolno ich printować.
Literały intów muszą mieścić się w 63 bitach (|n| < 2^62).

Zasada: **każdy program w zaskrońcu musi dawać identyczny output pod `python3` i po skompilowaniu.**
Jeśli nie daje, to bug w zc, nie „inna semantyka”. Jedyna dozwolona różnica to overflow intów powyżej 2^62.

## Architektura
```
src/zc.py         # cały kompilator w jednym pliku (import jest tylko sys, więc dzielenie odpada)
  lexer    -> tokeny, w tym INDENT/DEDENT ze stosem wcięć
  parser   -> AST jako tuple/listy/dicty, np. ("call", fn, args, line, col)
  resolver -> zakresy funkcyjne: local / global / nonlocal / cell (przechwycone przez domknięcie)
  codegen  -> assembly, naiwny model stosowy (push/pop), %rax jako akumulator
runtime/rt.c      # alokacja, str/list/tuple/dict, repr, porównania, builtiny, błędy runtime
tests/*.py        # programy testowe
tests/run.sh      # testy różnicowe: python3 vs skompilowana binarka, diff stdout i exit code
```

Reprezentacja wartości: 64-bitowe słowo z tagiem w niskich bitach.
- int: `(n << 1) | 1`
- wskaźniki (str/list/tuple/dict/closure/cell): wyrównane do 8, tag 0, typ w nagłówku obiektu
- `None`, `False`, `True`: małe stałe specjalne

Pamięć: na start **bump allocator bez GC**. Kompilator żyje sekundę, wolno mu ciec. GC to tortura na później.

## Kamienie milowe
- **M0** Szkielet repo, `tests/run.sh` z testami różnicowymi, Makefile: `stage1 stage2 stage3 bootstrap test`.
- **M1** Lekser (z INDENT/DEDENT) i parser w zaskrońcu, działają pod `python3`. Test: sparsowanie samego siebie + dump AST.
- **M2** Codegen: inty, arytmetyka, zmienne, `if`/`while`, funkcje, rekurencja, `print` intów. Test: fib(30).
- **M3** `str`, `list`, `tuple`, `dict`, `for`, `in`, wycinki, `repr`/`print` dla kontenerów.
- **M4** Domknięcia: komórki dla zmiennych przechwyconych, `nonlocal`, `lambda`. Test: domknięcia w pętli (późne wiązanie!).
- **M5** Wszystko, czego używa `zc.py`. Skompilowanie samego siebie → stage1.
- **M6** Bootstrap: `stage2.s == stage3.s`. Tag `fixed-point`. Szampan.

Tortury (po M6, w dowolnej kolejności):
- **T1** Mark-and-sweep GC ze skanowaniem stosu.
- **T2** Runtime bez libc: syscalle `read`/`write`/`mmap`/`exit` bezpośrednio.
- **T3** Alokacja rejestrów (linear scan) zamiast push/pop. Benchmark kontra CPython (powinno być wstyd CPythonowi).
- **T4** Klasy bez dziedziczenia: atrybuty, metody, bound methods, `__init__`.
- **T5** Trusting Trust: backdoor w stage1, który przenosi się do kolejnych stage'y, choć w źródle go nie ma.

## Pułapki, o których trzeba pamiętać
- **Zakres w Pythonie jest funkcyjny, nie blokowy.** Przypisanie gdziekolwiek w funkcji czyni zmienną lokalną
  w CAŁEJ funkcji (stąd `UnboundLocalError`). Resolver musi przejść całe ciało funkcji przed codegenem.
- **Domknięcia łapią zmienne, nie wartości.** `[lambda: i for ...]` w pętli zwróci ostatnie `i`. Tak ma być.
- **dict zachowuje kolejność wstawiania.** Implementacja musi to odwzorować, inaczej testy różnicowe padną.
  Za to fixed point przy tym nie ucierpi, bo kolejność jest deterministyczna.
- `//` i `%` są floorowane, nie obcinane jak w C: `-7 // 2 == -4`, `-7 % 2 == 1`.
- `repr` stringów: CPython wybiera `'` albo `"` zależnie od zawartości i escapuje `\n`, `\\`, `\t`. Do odtworzenia co do znaku.
- `print([1, 'a'])` używa `repr` dla elementów, `print('a')` używa `str`.
- `==` na listach/tuple/dictach porównuje strukturalnie; `True == 1` i `hash(True) == hash(1)`, więc `{1: 'a'}[True]` działa.
- Ujemne indeksy i wycinki poza zakresem (`s[-1]`, `s[2:100]`) muszą działać jak w CPythonie.
- Domyślny limit rekurencji CPythona to 1000; rekurencyjny parser na własnym źródle może go przebić,
  dlatego `sys.setrecursionlimit` na początku `zc.py`.
- Wyrównanie stosu do 16 bajtów przed każdym `call` do C. Jeśli runtime losowo segfaultuje w `printf`, to przez to.
- Kolejność ewaluacji od lewej do prawej, także `d[k] = v` (najpierw `v`, potem `d`, potem `k` — sprawdź w CPythonie i odwzoruj).

## Zasady pracy dla Claude
- Po każdej zmianie: `make test`. Po M5: także `make bootstrap`. Czerwone testy = nie skończone.
- Nowa funkcja języka = najpierw test w `tests/`, który przechodzi pod `python3`, potem implementacja.
- Nie dodawać do języka niczego spoza podzbioru „bo się przyda”. Najpierw aktualizacja tej specyfikacji.
- W `zc.py` nie wolno używać niczego, czego zc nie umie skompilować. CPython to przełknie, ale bootstrap pęknie.
