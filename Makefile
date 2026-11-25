CC = gcc
CFLAGS = -O2
RT = runtime/rt.c

.PHONY: all stage1 stage2 stage3 bootstrap test test-stage1 test-stage2 clean

all: stage1

build:
	mkdir -p build

build/stage1.s: src/zc.py | build
	python3 src/zc.py < src/zc.py > $@

build/stage1: build/stage1.s $(RT)
	$(CC) $(CFLAGS) $< $(RT) -o $@

build/stage2.s: build/stage1 src/zc.py
	build/stage1 < src/zc.py > $@

build/stage2: build/stage2.s $(RT)
	$(CC) $(CFLAGS) $< $(RT) -o $@

build/stage3.s: build/stage2 src/zc.py
	build/stage2 < src/zc.py > $@

stage1: build/stage1
stage2: build/stage2
stage3: build/stage3.s

bootstrap: build/stage3.s
	cmp build/stage2.s build/stage3.s
	@cmp -s build/stage1.s build/stage2.s && echo "stage1.s == stage2.s == stage3.s" || echo "stage2.s == stage3.s (stage1.s differs)"
	@echo "fixed point reached"

test:
	tests/run.sh

test-stage1: build/stage1
	ZC=build/stage1 tests/run.sh

test-stage2: build/stage2
	ZC=build/stage2 tests/run.sh

clean:
	rm -rf build
