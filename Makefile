CC = gcc
CFLAGS = -O2
RT = runtime/rt.c
ZC_SRC = src/zc.py
# bootstrap ma wlasny katalog, niezalezny od build/ (testy)
B = stages

.PHONY: all stage1 stage2 stage3 bootstrap test test-cerr test-stage1 test-stage2 test-all examples clean

all: stage1

$(B):
	mkdir -p $(B)

$(B)/stage1.s: $(ZC_SRC) | $(B)
	python3 $(ZC_SRC) < $(ZC_SRC) > $@

$(B)/stage1: $(B)/stage1.s $(RT)
	$(CC) $(CFLAGS) $< $(RT) -o $@

$(B)/stage2.s: $(B)/stage1 $(ZC_SRC)
	$(B)/stage1 < $(ZC_SRC) > $@

$(B)/stage2: $(B)/stage2.s $(RT)
	$(CC) $(CFLAGS) $< $(RT) -o $@

$(B)/stage3.s: $(B)/stage2 $(ZC_SRC)
	$(B)/stage2 < $(ZC_SRC) > $@

stage1: $(B)/stage1
stage2: $(B)/stage2
stage3: $(B)/stage3.s

bootstrap: $(B)/stage3.s
	cmp $(B)/stage2.s $(B)/stage3.s
	@cmp -s $(B)/stage1.s $(B)/stage2.s && echo "stage1.s == stage2.s == stage3.s" || echo "stage2.s == stage3.s (stage1.s differs)"
	@echo "fixed point reached"

test:
	tests/run.sh
	tests/cerr.sh

test-stage1: $(B)/stage1
	ZC=$(B)/stage1 tests/run.sh
	ZC=$(B)/stage1 tests/cerr.sh

test-stage2: $(B)/stage2
	ZC=$(B)/stage2 tests/run.sh
	ZC=$(B)/stage2 tests/cerr.sh

test-all: test bootstrap test-stage1 test-stage2

# kompiluje wszystkie examples/*.py do build/examples/
examples:
	@mkdir -p build/examples
	@for f in examples/*.py; do ./zcc $$f -o build/examples/$$(basename $$f .py) && echo "build/examples/$$(basename $$f .py)"; done

clean:
	rm -rf build $(B)
