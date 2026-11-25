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

W jednym kroku, skryptem `zcc`:

```bash
./zcc hello.py              # -> ./hello
./zcc hello.py -o prog      # -> ./prog
./zcc hello.py -S           # -> hello.s (sam asm)
```

`zcc` używa `stages/stage1`, jeśli jest zbudowany, a inaczej `python3 src/zc.py`.
Można go wywoływać z dowolnego katalogu (np. przez symlink w `~/.local/bin`).

Ręcznie: zc czyta źródło ze stdin i wypisuje asm na stdout. Potem linkujesz z runtime'em:

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

## Przykłady

W [examples/](examples) leżą gotowe programy:

| Plik            | Co robi                                                 | Wejście                     |
|-----------------|---------------------------------------------------------|-----------------------------|
| `hello.py`      | Hello, world                                            | —                           |
| `fizzbuzz.py`   | FizzBuzz od 1 do 30                                     | —                           |
| `primes.py`     | sito Eratostenesa, pierwsze mniejsze od 100             | —                           |
| `closures.py`   | licznik na `nonlocal`, kompozycja lambd, późne wiązanie | —                           |
| `life.py`       | gra w życie, szybowiec przez 4 pokolenia                | —                           |
| `calc.py`       | kalkulator wyrażeń (`+ - * // %`, nawiasy)              | wyrażenia, po jednym w linii |
| `wordcount.py`  | liczy słowa i wypisuje 5 najczęstszych                  | dowolny tekst               |
| `brainfuck.py`  | interpreter Brainfucka                                  | program `.bf`               |

Pojedynczy przykład:

```bash
./zcc examples/fizzbuzz.py -o fizzbuzz
./fizzbuzz
```

Te, które czytają stdin, mają obok przykładowe wejście:

```bash
./zcc examples/calc.py -o calc
./calc < examples/calc.in
echo "2 * (3 + 4)" | ./calc

./zcc examples/wordcount.py -o wordcount
./wordcount < examples/wordcount.in

./zcc examples/brainfuck.py -o bf
./bf < examples/hello.bf
```

Wszystkie naraz: `make examples` kompiluje każdy przykład do `build/examples/<nazwa>`.
Dla porównania każdy można też odpalić zwykłym Pythonem, np. `python3 examples/calc.py < examples/calc.in`,
i wynik musi być identyczny.

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
examples/      przykładowe programy
zcc            kompilacja do binarki w jednym kroku
stages/        artefakty bootstrapu (generowane)
build/         artefakty testów (generowane)
```
