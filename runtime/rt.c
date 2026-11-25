// zaskroniec runtime: values, containers, builtins, errors.
// Value: 64-bit word. int = (n<<1)|1, None=2, False=4, True=6, else pointer to object.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

typedef long V;
#define VNONE 2L
#define VFALSE 4L
#define VTRUE 6L
#define ISINT(v) ((v) & 1)
#define TAG(n) ((V)(((unsigned long)(n) << 1) | 1))
#define BOOL(c) ((c) ? VTRUE : VFALSE)

enum { T_STR = 1, T_LIST, T_TUPLE, T_DICT, T_CLOSURE, T_CELL };
enum { K_NONE = 100, K_BOOL, K_INT, K_OTHER };

typedef struct { long hdr; long len; unsigned long hash; char s[]; } Str;
typedef struct { long hdr; long len; long cap; V *items; } List;
typedef struct { long hdr; long len; V items[]; } Tuple;
typedef struct {
    long hdr; long len; long cap; V *keys; V *vals; unsigned long *hashes;
    long icap; long *idx;
} Dict;
typedef struct { long hdr; void *fn; long ncells; V cells[]; } Closure;
typedef struct { long hdr; V val; } Cell;

// ---------------------------------------------------------------- output
static char obuf[1 << 16];
static long olen;
static void wall(int fd, const char *p, long n) {
    while (n > 0) { long r = write(fd, p, n); if (r <= 0) return; p += r; n -= r; }
}
static void oflush(void) { wall(1, obuf, olen); olen = 0; }
static void owrite(const char *s, long n) {
    if (olen + n > (long)sizeof obuf) oflush();
    if (n > (long)sizeof obuf) { wall(1, s, n); return; }
    memcpy(obuf + olen, s, n); olen += n;
}

// ---------------------------------------------------------------- errors
static void die(const char *kind, const char *msg) {
    oflush();
    fprintf(stderr, "%s: %s\n", kind, msg);
    exit(1);
}
#define TYPEERR(m) die("TypeError", m)

// ---------------------------------------------------------------- memory (bump, no GC)
static char *hp, *hend;
static void *alloc(long n) {
    n = (n + 15) & ~15L;
    if (hp + n > hend) {
        long sz = 64L << 20;
        if (n > sz) sz = n;
        hp = malloc(sz);
        if (!hp) die("MemoryError", "out of memory");
        hend = hp + sz;
    }
    void *p = hp; hp += n; return p;
}

// ---------------------------------------------------------------- kinds
static inline long kind(V v) {
    if (v & 1) return K_INT;
    if (v == VNONE) return K_NONE;
    if (v == VTRUE || v == VFALSE) return K_BOOL;
    if ((v & 7) || v == 0) return K_OTHER;
    return *(long *)v & 0xff;
}
static inline int intlike(long k) { return k == K_INT || k == K_BOOL; }
static inline long ival(V v) { return (v & 1) ? (v >> 1) : (v == VTRUE); }
static long needint(V v, const char *what) {
    if (!intlike(kind(v))) TYPEERR(what);
    return ival(v);
}

// ---------------------------------------------------------------- constructors
static Str *mkstr(const char *s, long n) {
    Str *r = alloc(sizeof(Str) + n + 1);
    r->hdr = T_STR; r->len = n; r->hash = 0;
    memcpy(r->s, s, n); r->s[n] = 0;
    return r;
}
static Str *chars[256];
static V charstr(unsigned char c) {
    if (!chars[c]) { char b = c; chars[c] = mkstr(&b, 1); }
    return (V)chars[c];
}
static List *mklist(long cap) {
    List *l = alloc(sizeof(List));
    l->hdr = T_LIST; l->len = 0; l->cap = cap < 4 ? 4 : cap;
    l->items = alloc(l->cap * sizeof(V));
    return l;
}
static void lpush(List *l, V v) {
    if (l->len == l->cap) {
        V *n = alloc(l->cap * 2 * sizeof(V));
        memcpy(n, l->items, l->len * sizeof(V));
        l->items = n; l->cap *= 2;
    }
    l->items[l->len++] = v;
}
static Tuple *mktuple(long n) {
    Tuple *t = alloc(sizeof(Tuple) + n * sizeof(V));
    t->hdr = T_TUPLE; t->len = n;
    return t;
}
static Dict *mkdict(void) {
    Dict *d = alloc(sizeof(Dict));
    d->hdr = T_DICT; d->len = 0; d->cap = 4;
    d->keys = alloc(4 * sizeof(V)); d->vals = alloc(4 * sizeof(V));
    d->hashes = alloc(4 * sizeof(long));
    d->icap = 8; d->idx = alloc(8 * sizeof(long));
    memset(d->idx, 0, 8 * sizeof(long));
    return d;
}

// ---------------------------------------------------------------- buffers
typedef struct { char *p; long n, cap; } Buf;
static void bput(Buf *b, const char *s, long n) {
    if (b->n + n > b->cap) {
        long c = b->cap ? b->cap * 2 : 64;
        while (c < b->n + n) c *= 2;
        b->p = realloc(b->p, c); b->cap = c;
    }
    memcpy(b->p + b->n, s, n); b->n += n;
}
static void bstr(Buf *b, const char *s) { bput(b, s, strlen(s)); }
static V bdone(Buf *b) { V r = (V)mkstr(b->p, b->n); free(b->p); return r; }

// ---------------------------------------------------------------- str / repr
static void tostr(Buf *b, V v, int repr);
static void strrepr(Buf *b, Str *s) {
    int sq = 0, dq = 0;
    for (long i = 0; i < s->len; i++) { if (s->s[i] == '\'') sq = 1; if (s->s[i] == '"') dq = 1; }
    char q = (sq && !dq) ? '"' : '\'';
    bput(b, &q, 1);
    for (long i = 0; i < s->len; i++) {
        unsigned char c = s->s[i];
        char tmp[8];
        if (c == q || c == '\\') { tmp[0] = '\\'; tmp[1] = c; bput(b, tmp, 2); }
        else if (c == '\n') bstr(b, "\\n");
        else if (c == '\t') bstr(b, "\\t");
        else if (c == '\r') bstr(b, "\\r");
        else if (c < 32 || c == 127) { snprintf(tmp, sizeof tmp, "\\x%02x", c); bstr(b, tmp); }
        else bput(b, (char *)&c, 1);
    }
    bput(b, &q, 1);
}
static void tostr(Buf *b, V v, int repr) {
    char tmp[32];
    switch (kind(v)) {
    case K_INT: snprintf(tmp, sizeof tmp, "%ld", v >> 1); bstr(b, tmp); return;
    case K_NONE: bstr(b, "None"); return;
    case K_BOOL: bstr(b, v == VTRUE ? "True" : "False"); return;
    case T_STR: if (repr) strrepr(b, (Str *)v); else bput(b, ((Str *)v)->s, ((Str *)v)->len); return;
    case T_LIST: {
        List *l = (List *)v; bstr(b, "[");
        for (long i = 0; i < l->len; i++) { if (i) bstr(b, ", "); tostr(b, l->items[i], 1); }
        bstr(b, "]"); return;
    }
    case T_TUPLE: {
        Tuple *t = (Tuple *)v; bstr(b, "(");
        for (long i = 0; i < t->len; i++) { if (i) bstr(b, ", "); tostr(b, t->items[i], 1); }
        if (t->len == 1) bstr(b, ",");
        bstr(b, ")"); return;
    }
    case T_DICT: {
        Dict *d = (Dict *)v; bstr(b, "{");
        for (long i = 0; i < d->len; i++) {
            if (i) bstr(b, ", ");
            tostr(b, d->keys[i], 1); bstr(b, ": "); tostr(b, d->vals[i], 1);
        }
        bstr(b, "}"); return;
    }
    case T_CLOSURE: bstr(b, "<function>"); return;
    default: bstr(b, "<?>"); return;
    }
}
V rt_str(V v) {
    if (kind(v) == T_STR) return v;
    Buf b = {0}; tostr(&b, v, 0); return bdone(&b);
}
V rt_repr(V v) { Buf b = {0}; tostr(&b, v, 1); return bdone(&b); }

static void diev(const char *k, V v) {
    Buf b = {0}; tostr(&b, v, 1); bput(&b, "", 1); die(k, b.p);
}

// ---------------------------------------------------------------- equality / ordering / hash
static int equal(V a, V b);
static long dfind(Dict *d, V k);
static int equal(V a, V b) {
    if (a == b) return 1;
    long ka = kind(a), kb = kind(b);
    if (intlike(ka) && intlike(kb)) return ival(a) == ival(b);
    if (ka != kb) return 0;
    switch (ka) {
    case T_STR: {
        Str *x = (Str *)a, *y = (Str *)b;
        return x->len == y->len && memcmp(x->s, y->s, x->len) == 0;
    }
    case T_LIST: {
        List *x = (List *)a, *y = (List *)b;
        if (x->len != y->len) return 0;
        for (long i = 0; i < x->len; i++) if (!equal(x->items[i], y->items[i])) return 0;
        return 1;
    }
    case T_TUPLE: {
        Tuple *x = (Tuple *)a, *y = (Tuple *)b;
        if (x->len != y->len) return 0;
        for (long i = 0; i < x->len; i++) if (!equal(x->items[i], y->items[i])) return 0;
        return 1;
    }
    case T_DICT: {
        Dict *x = (Dict *)a, *y = (Dict *)b;
        if (x->len != y->len) return 0;
        for (long i = 0; i < x->len; i++) {
            long j = dfind(y, x->keys[i]);
            if (j < 0 || !equal(x->vals[i], y->vals[j])) return 0;
        }
        return 1;
    }
    }
    return 0;
}
static int compare(V a, V b) {
    long ka = kind(a), kb = kind(b);
    if (intlike(ka) && intlike(kb)) { long x = ival(a), y = ival(b); return x < y ? -1 : x > y; }
    if (ka == T_STR && kb == T_STR) {
        Str *x = (Str *)a, *y = (Str *)b;
        long n = x->len < y->len ? x->len : y->len;
        int c = memcmp(x->s, y->s, n);
        if (c) return c < 0 ? -1 : 1;
        return x->len < y->len ? -1 : x->len > y->len;
    }
    if ((ka == T_LIST && kb == T_LIST) || (ka == T_TUPLE && kb == T_TUPLE)) {
        long na, nb; V *ia, *ib;
        if (ka == T_LIST) { na = ((List *)a)->len; ia = ((List *)a)->items; nb = ((List *)b)->len; ib = ((List *)b)->items; }
        else { na = ((Tuple *)a)->len; ia = ((Tuple *)a)->items; nb = ((Tuple *)b)->len; ib = ((Tuple *)b)->items; }
        for (long i = 0; i < na && i < nb; i++)
            if (!equal(ia[i], ib[i])) return compare(ia[i], ib[i]);
        return na < nb ? -1 : na > nb;
    }
    TYPEERR("'<' not supported between these types");
    return 0;
}
V rt_eq(V a, V b) { return BOOL(equal(a, b)); }
V rt_ne(V a, V b) { return BOOL(!equal(a, b)); }
V rt_lt(V a, V b) { return BOOL(compare(a, b) < 0); }
V rt_le(V a, V b) { return BOOL(compare(a, b) <= 0); }
V rt_gt(V a, V b) { return BOOL(compare(a, b) > 0); }
V rt_ge(V a, V b) { return BOOL(compare(a, b) >= 0); }

static unsigned long hashv(V v) {
    long k = kind(v);
    if (intlike(k)) return (unsigned long)ival(v);
    if (k == T_STR) {
        Str *s = (Str *)v;
        if (!s->hash) {
            unsigned long h = 1469598103934665603UL;
            for (long i = 0; i < s->len; i++) { h ^= (unsigned char)s->s[i]; h *= 1099511628211UL; }
            s->hash = h ? h : 1;
        }
        return s->hash;
    }
    if (k == T_TUPLE) {
        Tuple *t = (Tuple *)v; unsigned long h = 0x345678;
        for (long i = 0; i < t->len; i++) h = (h ^ hashv(t->items[i])) * 1000003UL;
        return h;
    }
    if (k == K_NONE) return 0x9e3779b9;
    TYPEERR("unhashable type");
    return 0;
}

// ---------------------------------------------------------------- dict
static long *dslot(Dict *d, V k, unsigned long h) {
    unsigned long m = d->icap - 1, i = h & m;
    for (;;) {
        long e = d->idx[i];
        if (e == 0) return &d->idx[i];
        if (d->hashes[e - 1] == h && equal(d->keys[e - 1], k)) return &d->idx[i];
        i = (i + 1) & m;
    }
}
static long dfind(Dict *d, V k) {
    long e = *dslot(d, k, hashv(k));
    return e - 1;
}
static void dset(Dict *d, V k, V v) {
    unsigned long h = hashv(k);
    long *s = dslot(d, k, h);
    if (*s) { d->vals[*s - 1] = v; return; }
    if (d->len == d->cap) {
        long c = d->cap * 2;
        V *nk = alloc(c * sizeof(V)), *nv = alloc(c * sizeof(V));
        unsigned long *nh = alloc(c * sizeof(long));
        memcpy(nk, d->keys, d->len * sizeof(V)); memcpy(nv, d->vals, d->len * sizeof(V));
        memcpy(nh, d->hashes, d->len * sizeof(long));
        d->keys = nk; d->vals = nv; d->hashes = nh; d->cap = c;
    }
    d->keys[d->len] = k; d->vals[d->len] = v; d->hashes[d->len] = h; d->len++;
    *s = d->len;
    if (d->len * 2 > d->icap) {
        d->icap *= 2;
        d->idx = alloc(d->icap * sizeof(long));
        memset(d->idx, 0, d->icap * sizeof(long));
        unsigned long m = d->icap - 1;
        for (long e = 0; e < d->len; e++) {
            unsigned long i = d->hashes[e] & m;
            while (d->idx[i]) i = (i + 1) & m;
            d->idx[i] = e + 1;
        }
    }
}

// ---------------------------------------------------------------- arithmetic
V rt_add(V a, V b) {
    if (a & b & 1) return a + b - 1;
    long ka = kind(a), kb = kind(b);
    if (intlike(ka) && intlike(kb)) return TAG(ival(a) + ival(b));
    if (ka == T_STR && kb == T_STR) {
        Str *x = (Str *)a, *y = (Str *)b;
        Str *r = alloc(sizeof(Str) + x->len + y->len + 1);
        r->hdr = T_STR; r->len = x->len + y->len; r->hash = 0;
        memcpy(r->s, x->s, x->len); memcpy(r->s + x->len, y->s, y->len); r->s[r->len] = 0;
        return (V)r;
    }
    if (ka == T_LIST && kb == T_LIST) {
        List *x = (List *)a, *y = (List *)b, *r = mklist(x->len + y->len);
        memcpy(r->items, x->items, x->len * sizeof(V));
        memcpy(r->items + x->len, y->items, y->len * sizeof(V));
        r->len = x->len + y->len;
        return (V)r;
    }
    if (ka == T_TUPLE && kb == T_TUPLE) {
        Tuple *x = (Tuple *)a, *y = (Tuple *)b, *r = mktuple(x->len + y->len);
        memcpy(r->items, x->items, x->len * sizeof(V));
        memcpy(r->items + x->len, y->items, y->len * sizeof(V));
        return (V)r;
    }
    TYPEERR("unsupported operand type(s) for +");
    return 0;
}
V rt_iadd(V a, V b) {
    if (kind(a) == T_LIST && kind(b) == T_LIST) {
        List *x = (List *)a, *y = (List *)b;
        long n = y->len;
        for (long i = 0; i < n; i++) lpush(x, y->items[i]);
        return a;
    }
    return rt_add(a, b);
}
V rt_sub(V a, V b) {
    if (a & b & 1) return a - b + 1;
    return TAG(needint(a, "unsupported operand type(s) for -") - needint(b, "unsupported operand type(s) for -"));
}
static V repeat(V seq, long n) {
    if (n < 0) n = 0;
    long k = kind(seq);
    if (k == T_STR) {
        Str *s = (Str *)seq; Buf b = {0};
        for (long i = 0; i < n; i++) bput(&b, s->s, s->len);
        if (!b.p) return (V)mkstr("", 0);
        return bdone(&b);
    }
    if (k == T_LIST) {
        List *s = (List *)seq, *r = mklist(s->len * n);
        for (long i = 0; i < n; i++) for (long j = 0; j < s->len; j++) lpush(r, s->items[j]);
        return (V)r;
    }
    if (k == T_TUPLE) {
        Tuple *s = (Tuple *)seq, *r = mktuple(s->len * n);
        for (long i = 0; i < n; i++) memcpy(r->items + i * s->len, s->items, s->len * sizeof(V));
        return (V)r;
    }
    TYPEERR("unsupported operand type(s) for *");
    return 0;
}
V rt_mul(V a, V b) {
    long ka = kind(a), kb = kind(b);
    if (intlike(ka) && intlike(kb)) return TAG(ival(a) * ival(b));
    if (intlike(kb)) return repeat(a, ival(b));
    if (intlike(ka)) return repeat(b, ival(a));
    TYPEERR("unsupported operand type(s) for *");
    return 0;
}
V rt_floordiv(V a, V b) {
    long x = needint(a, "unsupported operand type(s) for //"), y = needint(b, "unsupported operand type(s) for //");
    if (y == 0) die("ZeroDivisionError", "integer division or modulo by zero");
    long q = x / y;
    if ((x % y != 0) && ((x < 0) != (y < 0))) q--;
    return TAG(q);
}
V rt_mod(V a, V b) {
    long x = needint(a, "unsupported operand type(s) for %"), y = needint(b, "unsupported operand type(s) for %");
    if (y == 0) die("ZeroDivisionError", "integer division or modulo by zero");
    long r = x % y;
    if (r != 0 && ((r < 0) != (y < 0))) r += y;
    return TAG(r);
}
V rt_neg(V a) { return TAG(-needint(a, "bad operand type for unary -")); }

// ---------------------------------------------------------------- truthiness
long rt_truthy(V v) {
    switch (kind(v)) {
    case K_INT: return v != 1;
    case K_BOOL: return v == VTRUE;
    case K_NONE: return 0;
    case T_STR: return ((Str *)v)->len != 0;
    case T_LIST: return ((List *)v)->len != 0;
    case T_TUPLE: return ((Tuple *)v)->len != 0;
    case T_DICT: return ((Dict *)v)->len != 0;
    }
    return 1;
}
V rt_not(V v) { return BOOL(!rt_truthy(v)); }

// ---------------------------------------------------------------- sequences
static long seqlen(V v, long *k) {
    *k = kind(v);
    switch (*k) {
    case T_STR: return ((Str *)v)->len;
    case T_LIST: return ((List *)v)->len;
    case T_TUPLE: return ((Tuple *)v)->len;
    case T_DICT: return ((Dict *)v)->len;
    }
    return -1;
}
V rt_len(V v) {
    long k, n = seqlen(v, &k);
    if (n < 0) TYPEERR("object has no len()");
    return TAG(n);
}
V rt_getitem(V o, V i) {
    long k = kind(o);
    if (k == T_DICT) {
        long j = dfind((Dict *)o, i);
        if (j < 0) diev("KeyError", i);
        return ((Dict *)o)->vals[j];
    }
    long n, kk; n = seqlen(o, &kk);
    if (n < 0) TYPEERR("object is not subscriptable");
    long x = needint(i, "indices must be integers");
    if (x < 0) x += n;
    if (x < 0 || x >= n) die("IndexError", k == T_STR ? "string index out of range" : k == T_LIST ? "list index out of range" : "tuple index out of range");
    if (k == T_STR) return charstr(((Str *)o)->s[x]);
    if (k == T_LIST) return ((List *)o)->items[x];
    return ((Tuple *)o)->items[x];
}
V rt_setitem(V o, V i, V v) {
    long k = kind(o);
    if (k == T_DICT) { dset((Dict *)o, i, v); return VNONE; }
    if (k == T_LIST) {
        List *l = (List *)o;
        long x = needint(i, "list indices must be integers");
        if (x < 0) x += l->len;
        if (x < 0 || x >= l->len) die("IndexError", "list assignment index out of range");
        l->items[x] = v;
        return VNONE;
    }
    TYPEERR("object does not support item assignment");
    return 0;
}
V rt_slice(V o, V lo, V hi) {
    long k, n = seqlen(o, &k);
    if (n < 0 || k == T_DICT) TYPEERR("object is not subscriptable");
    long a = lo == VNONE ? 0 : needint(lo, "slice indices must be integers");
    long b = hi == VNONE ? n : needint(hi, "slice indices must be integers");
    if (a < 0) { a += n; if (a < 0) a = 0; }
    if (b < 0) { b += n; if (b < 0) b = 0; }
    if (a > n) a = n;
    if (b > n) b = n;
    if (b < a) b = a;
    if (k == T_STR) {
        if (b - a == 1) return charstr(((Str *)o)->s[a]);
        return (V)mkstr(((Str *)o)->s + a, b - a);
    }
    if (k == T_LIST) {
        List *r = mklist(b - a);
        memcpy(r->items, ((List *)o)->items + a, (b - a) * sizeof(V));
        r->len = b - a;
        return (V)r;
    }
    Tuple *r = mktuple(b - a);
    memcpy(r->items, ((Tuple *)o)->items + a, (b - a) * sizeof(V));
    return (V)r;
}
V rt_contains(V c, V x) {
    long k = kind(c);
    if (k == T_STR) {
        if (kind(x) != T_STR) TYPEERR("'in <string>' requires string as left operand");
        Str *s = (Str *)c, *t = (Str *)x;
        if (t->len == 0) return VTRUE;
        for (long i = 0; i + t->len <= s->len; i++)
            if (memcmp(s->s + i, t->s, t->len) == 0) return VTRUE;
        return VFALSE;
    }
    if (k == T_LIST) {
        List *l = (List *)c;
        for (long i = 0; i < l->len; i++) if (equal(l->items[i], x)) return VTRUE;
        return VFALSE;
    }
    if (k == T_TUPLE) {
        Tuple *l = (Tuple *)c;
        for (long i = 0; i < l->len; i++) if (equal(l->items[i], x)) return VTRUE;
        return VFALSE;
    }
    if (k == T_DICT) return BOOL(dfind((Dict *)c, x) >= 0);
    TYPEERR("argument of type is not iterable");
    return 0;
}
V rt_notcontains(V c, V x) { return rt_contains(c, x) == VTRUE ? VFALSE : VTRUE; }

// for-loop step: returns item i of seq or 0 when exhausted (i is tagged)
V rt_iter_get(V seq, V ti) {
    long i = ti >> 1;
    switch (kind(seq)) {
    case T_LIST: { List *l = (List *)seq; return i < l->len ? l->items[i] : 0; }
    case T_TUPLE: { Tuple *t = (Tuple *)seq; return i < t->len ? t->items[i] : 0; }
    case T_STR: { Str *s = (Str *)seq; return i < s->len ? charstr(s->s[i]) : 0; }
    case T_DICT: { Dict *d = (Dict *)seq; return i < d->len ? d->keys[i] : 0; }
    }
    TYPEERR("object is not iterable");
    return 0;
}
void rt_unpack(V seq, long n) {
    long k, m = seqlen(seq, &k);
    if (m < 0 || k == T_DICT) TYPEERR("cannot unpack non-sequence");
    if (m < n) die("ValueError", "not enough values to unpack");
    if (m > n) die("ValueError", "too many values to unpack");
}
V rt_index_raw(V seq, long i) {
    switch (kind(seq)) {
    case T_LIST: return ((List *)seq)->items[i];
    case T_TUPLE: return ((Tuple *)seq)->items[i];
    case T_STR: return charstr(((Str *)seq)->s[i]);
    }
    return VNONE;
}

// ---------------------------------------------------------------- constructors called from asm
// p points at the top of stack; item pushed first is p[n-1].
V rt_mklist(long n, V *p) {
    List *l = mklist(n);
    for (long i = 0; i < n; i++) l->items[i] = p[n - 1 - i];
    l->len = n;
    return (V)l;
}
V rt_mktuple(long n, V *p) {
    Tuple *t = mktuple(n);
    for (long i = 0; i < n; i++) t->items[i] = p[n - 1 - i];
    return (V)t;
}
V rt_mkdict(long n, V *p) {
    Dict *d = mkdict();
    for (long i = 0; i < n; i++) dset(d, p[2 * n - 1 - 2 * i], p[2 * n - 2 - 2 * i]);
    return (V)d;
}
V rt_mkclosure(void *fn, long nargs, long ncells, V *p) {
    Closure *c = alloc(sizeof(Closure) + ncells * sizeof(V));
    c->hdr = T_CLOSURE | (nargs << 8); c->fn = fn; c->ncells = ncells;
    for (long i = 0; i < ncells; i++) c->cells[i] = p[ncells - 1 - i];
    return (V)c;
}
V rt_mkcell(V v) {
    Cell *c = alloc(sizeof(Cell));
    c->hdr = T_CELL; c->val = v;
    return (V)c;
}

// ---------------------------------------------------------------- builtins
V rt_print(long n, V *p) {
    Buf b = {0};
    for (long i = 0; i < n; i++) { if (i) bput(&b, " ", 1); tostr(&b, p[n - 1 - i], 0); }
    bput(&b, "\n", 1);
    owrite(b.p, b.n); free(b.p);
    return VNONE;
}
V rt_int(V v) {
    long k = kind(v);
    if (intlike(k)) return TAG(ival(v));
    if (k != T_STR) TYPEERR("int() argument must be a string or a number");
    Str *s = (Str *)v;
    long i = 0, n = s->len, neg = 0, x = 0, any = 0;
    while (i < n && (s->s[i] == ' ' || s->s[i] == '\t' || s->s[i] == '\n' || s->s[i] == '\r')) i++;
    if (i < n && (s->s[i] == '-' || s->s[i] == '+')) { neg = s->s[i] == '-'; i++; }
    while (i < n && s->s[i] >= '0' && s->s[i] <= '9') { x = x * 10 + (s->s[i] - '0'); i++; any = 1; }
    while (i < n && (s->s[i] == ' ' || s->s[i] == '\t' || s->s[i] == '\n' || s->s[i] == '\r')) i++;
    if (!any || i != n) {
        Buf b = {0}; bstr(&b, "invalid literal for int() with base 10: "); strrepr(&b, s); bput(&b, "", 1);
        die("ValueError", b.p);
    }
    return TAG(neg ? -x : x);
}
V rt_ord(V v) {
    if (kind(v) != T_STR || ((Str *)v)->len != 1) TYPEERR("ord() expected a character");
    return TAG((unsigned char)((Str *)v)->s[0]);
}
V rt_chr(V v) {
    long x = needint(v, "an integer is required");
    if (x < 0 || x > 255) die("ValueError", "chr() arg not in range (ASCII only)");
    return charstr(x);
}
V rt_range(V a, V b, V c) {
    long x = needint(a, "range() integer expected"), y = needint(b, "range() integer expected"), s = needint(c, "range() integer expected");
    if (s == 0) die("ValueError", "range() arg 3 must not be zero");
    List *l = mklist(0);
    if (s > 0) for (long i = x; i < y; i += s) lpush(l, TAG(i));
    else for (long i = x; i > y; i += s) lpush(l, TAG(i));
    return (V)l;
}
// codes: 1 int, 2 str, 3 list, 4 tuple, 5 dict, 6 bool
V rt_isinstance(V v, long code) {
    long k = kind(v);
    switch (code) {
    case 1: return BOOL(intlike(k));
    case 2: return BOOL(k == T_STR);
    case 3: return BOOL(k == T_LIST);
    case 4: return BOOL(k == T_TUPLE);
    case 5: return BOOL(k == T_DICT);
    case 6: return BOOL(k == K_BOOL);
    }
    return VFALSE;
}

// ---------------------------------------------------------------- sys
V rt_stdin_read(void) {
    Buf b = {0}; char tmp[65536]; long r;
    while ((r = read(0, tmp, sizeof tmp)) > 0) bput(&b, tmp, r);
    if (!b.p) return (V)mkstr("", 0);
    return bdone(&b);
}
V rt_write_out(V s) {
    if (kind(s) != T_STR) TYPEERR("write() argument must be str");
    owrite(((Str *)s)->s, ((Str *)s)->len);
    return TAG(((Str *)s)->len);
}
V rt_write_err(V s) {
    if (kind(s) != T_STR) TYPEERR("write() argument must be str");
    wall(2, ((Str *)s)->s, ((Str *)s)->len);
    return TAG(((Str *)s)->len);
}
void rt_exit(V v) {
    oflush();
    long k = kind(v);
    if (k == K_NONE) exit(0);
    if (intlike(k)) exit((int)ival(v));
    Buf b = {0}; tostr(&b, v, 0); bput(&b, "\n", 1); wall(2, b.p, b.n);
    exit(1);
}
void rt_raise(V name, V msg) {
    Buf b = {0};
    tostr(&b, name, 0);
    if (msg != VNONE) { bstr(&b, ": "); tostr(&b, msg, 0); }
    bput(&b, "", 1);
    oflush();
    fprintf(stderr, "%s\n", b.p);
    exit(1);
}
void rt_assert_fail(V msg) {
    if (msg == VNONE) die("AssertionError", "");
    Buf b = {0}; tostr(&b, msg, 0); bput(&b, "", 1); die("AssertionError", b.p);
}
void rt_badcall(void) { die("TypeError", "call of non-function or wrong number of arguments"); }
void rt_nameerr(void) { die("NameError", "name is not defined"); }

// ---------------------------------------------------------------- methods
static void needk(V v, long k, const char *m) { if (kind(v) != k) TYPEERR(m); }
V rt_m_append_1(V l, V v) { needk(l, T_LIST, "append() needs a list"); lpush((List *)l, v); return VNONE; }
V rt_m_pop_1(V lv, V i) {
    needk(lv, T_LIST, "pop() needs a list");
    List *l = (List *)lv;
    long x = needint(i, "pop index must be int");
    if (x < 0) x += l->len;
    if (x < 0 || x >= l->len) die("IndexError", l->len ? "pop index out of range" : "pop from empty list");
    V r = l->items[x];
    memmove(l->items + x, l->items + x + 1, (l->len - x - 1) * sizeof(V));
    l->len--;
    return r;
}
V rt_m_pop_0(V l) { return rt_m_pop_1(l, TAG(-1)); }
V rt_m_get_2(V d, V k, V def) {
    needk(d, T_DICT, "get() needs a dict");
    long j = dfind((Dict *)d, k);
    return j < 0 ? def : ((Dict *)d)->vals[j];
}
V rt_m_get_1(V d, V k) { return rt_m_get_2(d, k, VNONE); }
V rt_m_keys_0(V dv) {
    needk(dv, T_DICT, "keys() needs a dict");
    Dict *d = (Dict *)dv; List *l = mklist(d->len);
    for (long i = 0; i < d->len; i++) l->items[i] = d->keys[i];
    l->len = d->len; return (V)l;
}
V rt_m_values_0(V dv) {
    needk(dv, T_DICT, "values() needs a dict");
    Dict *d = (Dict *)dv; List *l = mklist(d->len);
    for (long i = 0; i < d->len; i++) l->items[i] = d->vals[i];
    l->len = d->len; return (V)l;
}
V rt_m_items_0(V dv) {
    needk(dv, T_DICT, "items() needs a dict");
    Dict *d = (Dict *)dv; List *l = mklist(d->len);
    for (long i = 0; i < d->len; i++) {
        Tuple *t = mktuple(2); t->items[0] = d->keys[i]; t->items[1] = d->vals[i];
        l->items[i] = (V)t;
    }
    l->len = d->len; return (V)l;
}
V rt_m_join_1(V sep, V seq) {
    needk(sep, T_STR, "join() needs a str");
    long k = kind(seq), n; V *items;
    if (k == T_LIST) { n = ((List *)seq)->len; items = ((List *)seq)->items; }
    else if (k == T_TUPLE) { n = ((Tuple *)seq)->len; items = ((Tuple *)seq)->items; }
    else { TYPEERR("join() argument must be a list or tuple"); return 0; }
    Str *s = (Str *)sep;
    long total = 0;
    for (long i = 0; i < n; i++) {
        if (kind(items[i]) != T_STR) TYPEERR("sequence item: expected str instance");
        total += ((Str *)items[i])->len + (i ? s->len : 0);
    }
    Str *r = alloc(sizeof(Str) + total + 1);
    r->hdr = T_STR; r->len = total; r->hash = 0;
    char *p = r->s;
    for (long i = 0; i < n; i++) {
        if (i) { memcpy(p, s->s, s->len); p += s->len; }
        Str *x = (Str *)items[i]; memcpy(p, x->s, x->len); p += x->len;
    }
    *p = 0;
    return (V)r;
}
static V strpred(V v, int which) {
    needk(v, T_STR, "string method on non-str");
    Str *s = (Str *)v;
    if (s->len == 0) return VFALSE;
    for (long i = 0; i < s->len; i++) {
        char c = s->s[i];
        int d = c >= '0' && c <= '9', a = (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z');
        int ok = which == 0 ? d : which == 1 ? a : (a || d);
        if (!ok) return VFALSE;
    }
    return VTRUE;
}
V rt_m_isdigit_0(V v) { return strpred(v, 0); }
V rt_m_isalpha_0(V v) { return strpred(v, 1); }
V rt_m_isalnum_0(V v) { return strpred(v, 2); }
V rt_m_startswith_1(V v, V p) {
    needk(v, T_STR, "startswith() on non-str"); needk(p, T_STR, "startswith() needs str");
    Str *s = (Str *)v, *t = (Str *)p;
    return BOOL(t->len <= s->len && memcmp(s->s, t->s, t->len) == 0);
}
static int isws(char c) { return c == ' ' || c == '\t' || c == '\n' || c == '\r' || c == '\v' || c == '\f'; }
V rt_m_split_0(V v) {
    needk(v, T_STR, "split() on non-str");
    Str *s = (Str *)v; List *l = mklist(0);
    long i = 0;
    while (i < s->len) {
        while (i < s->len && isws(s->s[i])) i++;
        if (i >= s->len) break;
        long j = i;
        while (j < s->len && !isws(s->s[j])) j++;
        lpush(l, (V)mkstr(s->s + i, j - i));
        i = j;
    }
    return (V)l;
}
V rt_m_split_1(V v, V sepv) {
    if (sepv == VNONE) return rt_m_split_0(v);
    needk(v, T_STR, "split() on non-str"); needk(sepv, T_STR, "split() separator must be str");
    Str *s = (Str *)v, *sep = (Str *)sepv; List *l = mklist(0);
    if (sep->len == 0) die("ValueError", "empty separator");
    long st = 0, i = 0;
    while (i + sep->len <= s->len) {
        if (memcmp(s->s + i, sep->s, sep->len) == 0) {
            lpush(l, (V)mkstr(s->s + st, i - st));
            i += sep->len; st = i;
        } else i++;
    }
    lpush(l, (V)mkstr(s->s + st, s->len - st));
    return (V)l;
}

// ---------------------------------------------------------------- entry
extern void zmain(void);
int main(void) {
    zmain();
    oflush();
    return 0;
}
