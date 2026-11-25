# Zaskroniec

Vibe coded kompilator pythona do binarki. Bo czemu nie.

**zc** kompiluje zaskrońca (ścisły podzbiór Pythona 3) do assembly x86-64 (GNU as, AT&T),
linkowanego z małym runtime'em w C do natywnej binarki na Linuksie. Kompilator jest napisany
w zaskrońcu i kompiluje sam siebie (fixed point: `stage1.s == stage2.s == stage3.s`).

Wymagania: `python3`, `gcc`, GNU `as` (binutils). Wszystko odpalasz z katalogu głównego repo.

## Kompilacja kompilatora

```bash
make stage1        # -> stages/stage1, natywny kompilator (python już niepotrzebny)
make bootstrap     # stage1 -> stage2 -> stage3 i sprawdzenie fixed pointu
```

`python3 src/zc.py` robi dokładnie to samo co `stages/stage1`, tylko wolniej.

## Kompilacja własnego programu

zc czyta źródło ze stdin i wypisuje asm na stdout. Potem linkujesz z runtime'em:

```bash
stages/stage1 < hello.py > hello.s
gcc hello.s runtime/rt.c -o hello
./hello
```

Przykład `hello.py`:

```python
def fib(n):
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)

print("fib(30) =", fib(30))
```

Program może czytać stdin przez `sys.stdin.read()` (po `import sys`), więc działa np. `./prog < dane.txt`.

## Błędy

- **Kompilacji**: na stderr np. `3:8: error: unsupported method 'upper' with 0 argument(s)`, exit code 1.
- **Runtime**: na stderr np. `IndexError: list index out of range`, exit code 1, jak CPython (bez tracebacku).

## Co wolno pisać

Tylko podzbiór z [CLAUDE.md](CLAUDE.md): `int` (63-bitowy), `str` (ASCII), `list`, `tuple`, `dict`,
funkcje, domknięcia, `lambda`, `if`/`while`/`for`, `import sys`. Nie ma klas, `try`, floatów, `/`,
list comprehension, f-stringów ani `x if c else y`.

Zasada: jeśli program działa pod `python3`, a zc go przyjmie, wynik ma być identyczny.
Jeśli nie jest, to bug w zc.

## Testy

| Komenda                                 | Co robi                                                                                       |
|-----------------------------------------|-----------------------------------------------------------------------------------------------|
| `make test`                             | testy różnicowe (python3 vs binarka) i testy błędów kompilacji, kompiluje `python3 src/zc.py` |
| `make test-stage1` / `make test-stage2` | to samo, ale kompiluje natywna binarka                                                        |
| `make test-all`                         | testy, bootstrap i testy na obu stage'ach                                                     |
| `tests/run.sh tests/fib.py`             | pojedynczy test                                                                               |
| `ZC=stages/stage2 tests/run.sh`         | testy z dowolnym kompilatorem                                                                 |

Nowy test to plik `tests/nazwa.py`, opcjonalnie `tests/nazwa.in` jako stdin. Testy błędów kompilacji
leżą w `tests/cerr/` i mają w pierwszej linii oczekiwaną pozycję, np. `# error: 3:8`.
Wyniki i pliki `.s` lądują w `build/tests/`.

`make clean` usuwa `build/` i `stages/`.

## Struktura

```
src/zc.py      kompilator: lekser, parser, resolver zakresów, codegen
runtime/rt.c   runtime: alokacja, str/list/tuple/dict, repr, builtiny, błędy
tests/         testy różnicowe, tests/cerr/ błędy kompilacji
stages/        artefakty bootstrapu (generowane)
build/         artefakty testów (generowane)
```
