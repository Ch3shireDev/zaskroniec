# zc -- kompilator zaskronca (podzbior Pythona 3) do x86-64 (GNU as, AT&T).
# Napisany w zaskroncu: musi sie dac skompilowac samym soba.
import sys

sys.setrecursionlimit(100000)


def error(msg, line, col):
    sys.stderr.write(str(line) + ":" + str(col) + ": error: " + msg + "\n")
    sys.exit(1)


# ============================================================ lexer

KEYWORDS = {"False": 1, "None": 1, "True": 1, "and": 1, "assert": 1, "break": 1,
            "continue": 1, "def": 1, "elif": 1, "else": 1, "for": 1, "global": 1,
            "if": 1, "import": 1, "in": 1, "is": 1, "lambda": 1, "nonlocal": 1,
            "not": 1, "or": 1, "pass": 1, "raise": 1, "return": 1, "while": 1,
            "class": 1, "try": 1, "except": 1, "with": 1, "yield": 1, "from": 1,
            "del": 1, "async": 1, "await": 1, "finally": 1, "as": 1}

OPS2 = {"==": 1, "!=": 1, "<=": 1, ">=": 1, "//": 1, "+=": 1, "-=": 1, "*=": 1, "%=": 1, "->": 1, "**": 1}
OPS1 = "+-*/%<>=()[]{}:,.;"
ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", "'": "'", "\"": "\"", "0": "\0"}


def is_ident_start(c):
    return c.isalpha() or c == "_"


def is_ident_char(c):
    return c.isalnum() or c == "_"


def lex(src):
    toks = []
    i = 0
    n = len(src)
    line = 1
    linestart = 0
    indents = [0]
    depth = 0
    atline = True
    while True:
        if atline and depth == 0:
            col = 0
            while i < n and (src[i] == " " or src[i] == "\t"):
                if src[i] == "\t":
                    col = (col // 8 + 1) * 8
                else:
                    col += 1
                i += 1
            if i >= n:
                break
            c = src[i]
            if c == "\n":
                i += 1
                line += 1
                linestart = i
                continue
            if c == "\r":
                i += 1
                continue
            if c == "#":
                while i < n and src[i] != "\n":
                    i += 1
                continue
            if col > indents[len(indents) - 1]:
                indents.append(col)
                toks.append(("INDENT", "", line, col + 1))
            else:
                while col < indents[len(indents) - 1]:
                    indents.pop()
                    toks.append(("DEDENT", "", line, col + 1))
                if col != indents[len(indents) - 1]:
                    error("inconsistent dedent", line, col + 1)
            atline = False
        if i >= n:
            break
        c = src[i]
        col = i - linestart + 1
        if c == " " or c == "\t" or c == "\r":
            i += 1
        elif c == "#":
            while i < n and src[i] != "\n":
                i += 1
        elif c == "\\" and i + 1 < n and src[i + 1] == "\n":
            i += 2
            line += 1
            linestart = i
        elif c == "\n":
            if depth == 0:
                toks.append(("NEWLINE", "", line, col))
                atline = True
            i += 1
            line += 1
            linestart = i
        elif is_ident_start(c):
            j = i
            while j < n and is_ident_char(src[j]):
                j += 1
            w = src[i:j]
            if w in KEYWORDS:
                toks.append(("kw", w, line, col))
            else:
                toks.append(("name", w, line, col))
            i = j
        elif c.isdigit():
            j = i
            while j < n and src[j].isdigit():
                j += 1
            if j < n and is_ident_char(src[j]):
                error("unsupported number literal", line, col)
            toks.append(("int", int(src[i:j]), line, col))
            i = j
        elif c == "\"" or c == "'":
            q = c
            if src[i:i + 3] == q + q + q:
                error("triple-quoted strings are not supported", line, col)
            j = i + 1
            parts = []
            while True:
                if j >= n or src[j] == "\n":
                    error("unterminated string", line, col)
                d = src[j]
                if d == q:
                    break
                if d == "\\":
                    e = src[j + 1]
                    if e in ESCAPES:
                        parts.append(ESCAPES[e])
                    else:
                        error("unsupported escape", line, j - linestart + 1)
                    j += 2
                else:
                    parts.append(d)
                    j += 1
            toks.append(("str", "".join(parts), line, col))
            i = j + 1
        else:
            two = src[i:i + 2]
            if two in OPS2:
                toks.append(("op", two, line, col))
                i += 2
                if i < n and two == "//" and src[i] == "=":
                    toks[len(toks) - 1] = ("op", "//=", line, col)
                    i += 1
            elif c in OPS1:
                if c == "(" or c == "[" or c == "{":
                    depth += 1
                elif c == ")" or c == "]" or c == "}":
                    depth -= 1
                toks.append(("op", c, line, col))
                i += 1
            else:
                error("unexpected character " + repr(c), line, col)
    if not atline:
        toks.append(("NEWLINE", "", line, i - linestart + 1))
    while len(indents) > 1:
        indents.pop()
        toks.append(("DEDENT", "", line, 1))
    toks.append(("EOF", "", line, 1))
    return toks


# ============================================================ parser

TOKS = []
POS = 0
NEXT_FID = [1]


def new_fid():
    f = NEXT_FID[0]
    NEXT_FID[0] = f + 1
    return f


def tok():
    return TOKS[POS]


def advance():
    global POS
    t = TOKS[POS]
    POS += 1
    return t


def at_op(v):
    t = TOKS[POS]
    return t[0] == "op" and t[1] == v


def at_kw(v):
    t = TOKS[POS]
    return t[0] == "kw" and t[1] == v


def at_kind(k):
    return TOKS[POS][0] == k


def perr(msg):
    t = TOKS[POS]
    what = t[0]
    if t[0] == "op" or t[0] == "kw" or t[0] == "name":
        what = repr(t[1])
    error(msg + " (got " + what + ")", t[2], t[3])


def expect_op(v):
    if not at_op(v):
        perr("expected '" + v + "'")
    return advance()


def expect_kind(k):
    if not at_kind(k):
        perr("expected " + k)
    return advance()


def expect_name():
    return expect_kind("name")[1]


def starts_expr():
    t = TOKS[POS]
    k = t[0]
    if k == "int" or k == "str" or k == "name":
        return True
    if k == "op":
        return t[1] == "(" or t[1] == "[" or t[1] == "{" or t[1] == "-"
    if k == "kw":
        return t[1] == "not" or t[1] == "lambda" or t[1] == "None" or t[1] == "True" or t[1] == "False"
    return False


def parse_program():
    body = []
    while not at_kind("EOF"):
        if at_kind("NEWLINE"):
            advance()
        else:
            parse_statement(body)
    return body


def parse_block():
    expect_op(":")
    body = []
    if at_kind("NEWLINE"):
        advance()
        expect_kind("INDENT")
        while not at_kind("DEDENT"):
            if at_kind("NEWLINE"):
                advance()
            else:
                parse_statement(body)
        advance()
    else:
        parse_simple_line(body)
    return body


def parse_statement(body):
    t = tok()
    if t[0] == "kw":
        w = t[1]
        if w == "if":
            advance()
            body.append(parse_if_rest(t))
            return
        if w == "while":
            advance()
            cond = parse_expr()
            b = parse_block()
            body.append(("while", cond, b, t[2], t[3]))
            return
        if w == "for":
            advance()
            target = parse_target_list()
            if not at_kw("in"):
                perr("expected 'in'")
            advance()
            it = parse_testlist()
            b = parse_block()
            body.append(("for", target, it, b, t[2], t[3]))
            return
        if w == "def":
            advance()
            name = expect_name()
            expect_op("(")
            params = []
            while not at_op(")"):
                p = expect_name()
                if p in params:
                    error("duplicate argument", t[2], t[3])
                params.append(p)
                if at_op("="):
                    perr("default arguments are not supported")
                if not at_op(")"):
                    expect_op(",")
            advance()
            b = parse_block()
            body.append(("def", new_fid(), name, params, b, t[2], t[3]))
            return
        if w == "class" or w == "try" or w == "with" or w == "from" or w == "del" or w == "yield" or w == "async":
            perr("unsupported statement")
    parse_simple_line(body)


def parse_if_rest(t):
    cond = parse_expr()
    b = parse_block()
    orelse = []
    if at_kw("elif"):
        t2 = advance()
        orelse = [parse_if_rest(t2)]
    elif at_kw("else"):
        advance()
        orelse = parse_block()
    return ("if", cond, b, orelse, t[2], t[3])


def parse_simple_line(body):
    body.append(parse_simple())
    while at_op(";"):
        advance()
        if at_kind("NEWLINE"):
            break
        body.append(parse_simple())
    expect_kind("NEWLINE")


def parse_simple():
    t = tok()
    line = t[2]
    col = t[3]
    if t[0] == "kw":
        w = t[1]
        if w == "pass":
            advance()
            return ("pass", line, col)
        if w == "break":
            advance()
            return ("break", line, col)
        if w == "continue":
            advance()
            return ("continue", line, col)
        if w == "return":
            advance()
            e = None
            if starts_expr():
                e = parse_testlist()
            return ("return", e, line, col)
        if w == "global" or w == "nonlocal":
            advance()
            names = [expect_name()]
            while at_op(","):
                advance()
                names.append(expect_name())
            return (w, names, line, col)
        if w == "import":
            advance()
            name = expect_name()
            if name != "sys":
                error("only 'import sys' is supported", line, col)
            return ("pass", line, col)
        if w == "assert":
            advance()
            test = parse_expr()
            msg = None
            if at_op(","):
                advance()
                msg = parse_expr()
            return ("assert", test, msg, line, col)
        if w == "raise":
            advance()
            e = parse_expr()
            return ("raise", e, line, col)
    e = parse_testlist()
    if at_op("="):
        targets = [e]
        while at_op("="):
            advance()
            targets.append(parse_testlist())
        value = targets.pop()
        for tg in targets:
            check_target(tg, line, col)
        return ("assign", targets, value, line, col)
    t = tok()
    if t[0] == "op" and (t[1] == "+=" or t[1] == "-=" or t[1] == "*=" or t[1] == "//=" or t[1] == "%="):
        advance()
        if e[0] != "name" and e[0] != "index":
            error("illegal target for augmented assignment", line, col)
        value = parse_testlist()
        op = t[1][0:len(t[1]) - 1]
        return ("augassign", op, e, value, line, col)
    return ("expr", e, line, col)


def check_target(e, line, col):
    k = e[0]
    if k == "name" or k == "index":
        return
    if k == "tuple" or k == "list":
        for x in e[1]:
            check_target(x, line, col)
        return
    error("cannot assign to expression", line, col)


def parse_target_list():
    t = tok()
    e = parse_postfix()
    if not at_op(","):
        check_target(e, t[2], t[3])
        return e
    items = [e]
    while at_op(","):
        advance()
        if at_kw("in"):
            break
        items.append(parse_postfix())
    e = ("tuple", items)
    check_target(e, t[2], t[3])
    return e


def parse_testlist():
    e = parse_expr()
    if not at_op(","):
        return e
    items = [e]
    while at_op(","):
        advance()
        if not starts_expr():
            break
        items.append(parse_expr())
    return ("tuple", items)


def parse_expr():
    if at_kw("lambda"):
        t = advance()
        params = []
        while not at_op(":"):
            params.append(expect_name())
            if not at_op(":"):
                expect_op(",")
        advance()
        body = parse_expr()
        return ("lambda", new_fid(), params, body, t[2], t[3])
    e = parse_or()
    if at_kw("if"):
        perr("conditional expressions are not supported")
    return e


def parse_or():
    a = parse_and()
    while at_kw("or"):
        advance()
        b = parse_and()
        a = ("or", a, b)
    return a


def parse_and():
    a = parse_not()
    while at_kw("and"):
        advance()
        b = parse_not()
        a = ("and", a, b)
    return a


def parse_not():
    if at_kw("not"):
        advance()
        return ("not", parse_not())
    return parse_cmp()


CMPOPS = {"==": 1, "!=": 1, "<": 1, "<=": 1, ">": 1, ">=": 1}


def cmp_op():
    t = tok()
    if t[0] == "op" and t[1] in CMPOPS:
        advance()
        return t[1]
    if t[0] == "kw":
        if t[1] == "in":
            advance()
            return "in"
        if t[1] == "is":
            advance()
            if at_kw("not"):
                advance()
                return "is not"
            return "is"
        if t[1] == "not":
            t2 = TOKS[POS + 1]
            if t2[0] == "kw" and t2[1] == "in":
                advance()
                advance()
                return "not in"
    return None


def parse_cmp():
    t = tok()
    a = parse_arith()
    op = cmp_op()
    if op is None:
        return a
    b = parse_arith()
    if cmp_op() is not None:
        error("chained comparisons are not supported", t[2], t[3])
    return ("cmp", op, a, b, t[2], t[3])


def parse_arith():
    a = parse_term()
    while at_op("+") or at_op("-"):
        t = advance()
        b = parse_term()
        a = ("binop", t[1], a, b, t[2], t[3])
    return a


def parse_term():
    a = parse_factor()
    while at_op("*") or at_op("//") or at_op("%") or at_op("/"):
        t = advance()
        if t[1] == "/":
            error("'/' is not supported (use //)", t[2], t[3])
        b = parse_factor()
        a = ("binop", t[1], a, b, t[2], t[3])
    return a


def parse_factor():
    if at_op("-"):
        t = advance()
        e = parse_factor()
        if e[0] == "int":
            return ("int", -e[1])
        return ("neg", e, t[2], t[3])
    e = parse_postfix()
    if at_op("**"):
        perr("'**' is not supported")
    return e


def parse_postfix():
    e = parse_atom()
    while True:
        t = tok()
        if at_op("("):
            advance()
            args = []
            while not at_op(")"):
                args.append(parse_expr())
                if at_op("="):
                    perr("keyword arguments are not supported")
                if not at_op(")"):
                    expect_op(",")
            advance()
            e = ("call", e, args, t[2], t[3])
        elif at_op("["):
            advance()
            lo = None
            if not at_op(":"):
                lo = parse_testlist()
            if at_op(":"):
                advance()
                hi = None
                if not at_op("]"):
                    hi = parse_expr()
                if at_op(":"):
                    perr("slice step is not supported")
                expect_op("]")
                e = ("slice", e, lo, hi, t[2], t[3])
            else:
                expect_op("]")
                e = ("index", e, lo, t[2], t[3])
        elif at_op("."):
            advance()
            name = expect_name()
            e = ("attr", e, name, t[2], t[3])
        else:
            return e


def parse_atom():
    t = tok()
    k = t[0]
    if k == "int":
        advance()
        return ("int", t[1])
    if k == "str":
        advance()
        parts = [t[1]]
        while at_kind("str"):
            parts.append(advance()[1])
        return ("str", "".join(parts))
    if k == "name":
        advance()
        return ("name", t[1], t[2], t[3])
    if k == "kw" and (t[1] == "None" or t[1] == "True" or t[1] == "False"):
        advance()
        return ("const", t[1])
    if k == "op":
        if t[1] == "(":
            advance()
            if at_op(")"):
                advance()
                return ("tuple", [])
            e = parse_expr()
            if at_op(")"):
                advance()
                return e
            items = [e]
            while at_op(","):
                advance()
                if at_op(")"):
                    break
                items.append(parse_expr())
            expect_op(")")
            return ("tuple", items)
        if t[1] == "[":
            advance()
            items = []
            while not at_op("]"):
                items.append(parse_expr())
                if at_kw("for"):
                    perr("list comprehensions are not supported")
                if not at_op("]"):
                    expect_op(",")
            advance()
            return ("list", items)
        if t[1] == "{":
            advance()
            items = []
            while not at_op("}"):
                items.append(parse_expr())
                expect_op(":")
                items.append(parse_expr())
                if not at_op("}"):
                    expect_op(",")
            advance()
            return ("dict", items)
    perr("expected expression")


# ============================================================ resolver
# Scope: dict z polami. fid 0 = modul.

SCOPES = {}


def new_scope(fid, parent, params):
    sc = {"fid": fid, "parent": parent, "params": params, "assigned": {}, "globals": {},
          "nonlocals": {}, "free": [], "freeidx": {}, "cells": {}}
    for p in params:
        sc["assigned"][p] = 1
    SCOPES[fid] = sc
    return sc


def is_local(sc, n):
    if sc["fid"] == 0:
        return False
    return n in sc["assigned"] and not (n in sc["globals"]) and not (n in sc["nonlocals"])


def expr_children(e):
    k = e[0]
    if k == "name" or k == "int" or k == "str" or k == "const" or k == "lambda":
        return []
    if k == "binop" or k == "cmp":
        return [e[2], e[3]]
    if k == "and" or k == "or":
        return [e[1], e[2]]
    if k == "not" or k == "neg" or k == "attr":
        return [e[1]]
    if k == "call":
        return [e[1]] + e[2]
    if k == "index":
        return [e[1], e[2]]
    if k == "slice":
        r = [e[1]]
        if e[2] is not None:
            r.append(e[2])
        if e[3] is not None:
            r.append(e[3])
        return r
    if k == "list" or k == "tuple" or k == "dict":
        return e[1]
    error("internal: unknown expr " + k, 0, 0)


# ---- faza 1: deklaracje

def decl_stmts(stmts, sc):
    for s in stmts:
        k = s[0]
        if k == "assign":
            for t in s[1]:
                decl_target(t, sc)
            decl_expr(s[2], sc)
        elif k == "augassign":
            decl_target(s[2], sc)
            decl_expr(s[3], sc)
        elif k == "for":
            decl_target(s[1], sc)
            decl_expr(s[2], sc)
            decl_stmts(s[3], sc)
        elif k == "if":
            decl_expr(s[1], sc)
            decl_stmts(s[2], sc)
            decl_stmts(s[3], sc)
        elif k == "while":
            decl_expr(s[1], sc)
            decl_stmts(s[2], sc)
        elif k == "def":
            sc["assigned"][s[2]] = 1
            inner = new_scope(s[1], sc, s[3])
            decl_stmts(s[4], inner)
        elif k == "global":
            for n in s[1]:
                if n in sc["assigned"]:
                    error("name '" + n + "' is assigned to before global declaration", s[2], s[3])
                sc["globals"][n] = 1
        elif k == "nonlocal":
            if sc["fid"] == 0:
                error("nonlocal declaration not allowed at module level", s[2], s[3])
            for n in s[1]:
                sc["nonlocals"][n] = 1
        elif k == "return" or k == "expr" or k == "raise":
            if s[1] is not None:
                decl_expr(s[1], sc)
        elif k == "assert":
            decl_expr(s[1], sc)
            if s[2] is not None:
                decl_expr(s[2], sc)


def decl_target(t, sc):
    if t[0] == "name":
        sc["assigned"][t[1]] = 1
    elif t[0] == "tuple" or t[0] == "list":
        for x in t[1]:
            decl_target(x, sc)
    else:
        decl_expr(t, sc)


def decl_expr(e, sc):
    if e[0] == "lambda":
        inner = new_scope(e[1], sc, e[2])
        decl_expr(e[3], inner)
        return
    for c in expr_children(e):
        decl_expr(c, sc)


# ---- faza 2: referencje

def ref_name(n, sc, line, col):
    if sc["fid"] == 0:
        return
    if n in sc["globals"] or is_local(sc, n) or n in sc["freeidx"]:
        return
    chain = [sc]
    p = sc["parent"]
    while p["fid"] != 0:
        if n in p["globals"]:
            break
        if is_local(p, n) or n in p["freeidx"]:
            if is_local(p, n):
                p["cells"][n] = 1
            for s in chain:
                if not (n in s["freeidx"]):
                    s["freeidx"][n] = len(s["free"])
                    s["free"].append(n)
            return
        chain.append(p)
        p = p["parent"]
    if n in sc["nonlocals"]:
        error("no binding for nonlocal '" + n + "' found", line, col)


def ref_stmts(stmts, sc):
    for s in stmts:
        k = s[0]
        if k == "assign":
            for t in s[1]:
                ref_expr(t, sc)
            ref_expr(s[2], sc)
        elif k == "augassign":
            ref_expr(s[2], sc)
            ref_expr(s[3], sc)
        elif k == "for":
            ref_expr(s[1], sc)
            ref_expr(s[2], sc)
            ref_stmts(s[3], sc)
        elif k == "if":
            ref_expr(s[1], sc)
            ref_stmts(s[2], sc)
            ref_stmts(s[3], sc)
        elif k == "while":
            ref_expr(s[1], sc)
            ref_stmts(s[2], sc)
        elif k == "def":
            ref_name(s[2], sc, s[5], s[6])
            ref_stmts(s[4], SCOPES[s[1]])
        elif k == "nonlocal":
            for n in s[1]:
                ref_name(n, sc, s[2], s[3])
        elif k == "return" or k == "expr" or k == "raise":
            if s[1] is not None:
                ref_expr(s[1], sc)
        elif k == "assert":
            ref_expr(s[1], sc)
            if s[2] is not None:
                ref_expr(s[2], sc)


def ref_expr(e, sc):
    if e[0] == "name":
        ref_name(e[1], sc, e[2], e[3])
        return
    if e[0] == "lambda":
        ref_expr(e[3], SCOPES[e[1]])
        return
    for c in expr_children(e):
        ref_expr(c, sc)


def var_kind(sc, n):
    if sc["fid"] == 0 or n in sc["globals"]:
        return "global"
    if n in sc["freeidx"]:
        return "free"
    if is_local(sc, n):
        if n in sc["cells"]:
            return "cell"
        return "local"
    return "global"


# ============================================================ codegen

BUILTINS = {"print": 1, "len": 1, "str": 1, "int": 1, "repr": 1, "ord": 1, "chr": 1,
            "range": 1, "isinstance": 1, "Exception": 1}
TYPECODES = {"int": 1, "str": 2, "list": 3, "tuple": 4, "dict": 5, "bool": 6}
METHODS = {"append_1": 1, "pop_0": 1, "pop_1": 1, "get_1": 1, "get_2": 1, "keys_0": 1,
           "values_0": 1, "items_0": 1, "join_1": 1, "isdigit_0": 1, "isalpha_0": 1,
           "isalnum_0": 1, "startswith_1": 1, "split_0": 1, "split_1": 1}
BINOPS = {"+": "rt_add", "-": "rt_sub", "*": "rt_mul", "//": "rt_floordiv", "%": "rt_mod"}
CMPFUNCS = {"==": "rt_eq", "!=": "rt_ne", "<": "rt_lt", "<=": "rt_le", ">": "rt_gt", ">=": "rt_ge",
            "in": "rt_contains", "not in": "rt_notcontains"}

FUNCS = []
STRS = {}
GLOBALS = {}
LABELS = [0]
FS = {}


def new_label():
    LABELS[0] = LABELS[0] + 1
    return ".L" + str(LABELS[0])


def emit(s):
    FS["code"].append("    " + s)


def emit_label(l):
    FS["code"].append(l + ":")


def ccall(fn):
    emit("mov %rsp, %r12")
    emit("and $-16, %rsp")
    emit("call " + fn)
    emit("mov %r12, %rsp")


def str_label(s):
    if s in STRS:
        return STRS[s]
    l = "S" + str(len(STRS))
    STRS[s] = l
    return l


def new_slot():
    FS["nslots"] = FS["nslots"] + 1
    return str(-8 * FS["nslots"]) + "(%rbp)"


def var_addr(n):
    slots = FS["slots"]
    if n in slots:
        return slots[n]
    a = new_slot()
    slots[n] = a
    return a


def closure_addr():
    return str(16 + 8 * FS["nargs"]) + "(%rbp)"


def is_builtin(n):
    return n in BUILTINS and not (n in SCOPES[0]["assigned"])


def gen_int(v):
    if v >= -1073741824 and v <= 1073741823:
        emit("mov $" + str(v * 2 + 1) + ", %rax")
    else:
        # tagujemy w CPU, zeby kompilator nie przepelnil 63-bitowego inta
        emit("movabsq $" + str(v) + ", %rax")
        emit("lea 1(%rax,%rax), %rax")


def gen_load(n, line, col):
    sc = FS["sc"]
    k = var_kind(sc, n)
    if k == "global":
        if is_builtin(n):
            error("builtin '" + n + "' can only be called", line, col)
        GLOBALS[n] = 1
        emit("mov G_" + n + "(%rip), %rax")
        emit("test %rax, %rax")
        emit("jz zc_nameerr")
    elif k == "local":
        emit("mov " + var_addr(n) + ", %rax")
    elif k == "cell":
        emit("mov " + var_addr(n) + ", %rax")
        emit("mov 8(%rax), %rax")
    else:
        emit("mov " + closure_addr() + ", %rax")
        emit("mov " + str(24 + 8 * sc["freeidx"][n]) + "(%rax), %rax")
        emit("mov 8(%rax), %rax")


def gen_store_name(n):
    sc = FS["sc"]
    k = var_kind(sc, n)
    if k == "global":
        GLOBALS[n] = 1
        emit("mov %rax, G_" + n + "(%rip)")
    elif k == "local":
        emit("mov %rax, " + var_addr(n))
    elif k == "cell":
        emit("mov " + var_addr(n) + ", %rcx")
        emit("mov %rax, 8(%rcx)")
    else:
        emit("mov " + closure_addr() + ", %rcx")
        emit("mov " + str(24 + 8 * sc["freeidx"][n]) + "(%rcx), %rcx")
        emit("mov %rax, 8(%rcx)")


def gen_bool_from_flag(setcc):
    emit(setcc + " %al")
    emit("movzbl %al, %eax")
    emit("lea 4(,%rax,2), %rax")


def gen_truthy_eax():
    emit("mov %rax, %rdi")
    ccall("rt_truthy")
    emit("test %eax, %eax")


def gen_push_items(items):
    for x in items:
        gen_expr(x)
        emit("push %rax")


def gen_expr(e):
    k = e[0]
    if k == "int":
        gen_int(e[1])
    elif k == "str":
        emit("lea " + str_label(e[1]) + "(%rip), %rax")
    elif k == "const":
        if e[1] == "None":
            emit("mov $2, %rax")
        elif e[1] == "True":
            emit("mov $6, %rax")
        else:
            emit("mov $4, %rax")
    elif k == "name":
        gen_load(e[1], e[2], e[3])
    elif k == "binop":
        gen_expr(e[2])
        emit("push %rax")
        gen_expr(e[3])
        emit("mov %rax, %rsi")
        emit("pop %rdi")
        ccall(BINOPS[e[1]])
    elif k == "neg":
        gen_expr(e[1])
        emit("mov %rax, %rdi")
        ccall("rt_neg")
    elif k == "not":
        gen_expr(e[1])
        gen_truthy_eax()
        gen_bool_from_flag("sete")
    elif k == "and" or k == "or":
        end = new_label()
        gen_expr(e[1])
        emit("push %rax")
        gen_truthy_eax()
        emit("pop %rax")
        if k == "and":
            emit("jz " + end)
        else:
            emit("jnz " + end)
        gen_expr(e[2])
        emit_label(end)
    elif k == "cmp":
        op = e[1]
        if op == "is" or op == "is not":
            gen_expr(e[2])
            emit("push %rax")
            gen_expr(e[3])
            emit("pop %rcx")
            emit("cmp %rax, %rcx")
            if op == "is":
                gen_bool_from_flag("sete")
            else:
                gen_bool_from_flag("setne")
        elif op == "in" or op == "not in":
            gen_expr(e[2])
            emit("push %rax")
            gen_expr(e[3])
            emit("mov %rax, %rdi")
            emit("pop %rsi")
            ccall(CMPFUNCS[op])
        else:
            gen_expr(e[2])
            emit("push %rax")
            gen_expr(e[3])
            emit("mov %rax, %rsi")
            emit("pop %rdi")
            ccall(CMPFUNCS[op])
    elif k == "call":
        gen_call(e)
    elif k == "index":
        gen_expr(e[1])
        emit("push %rax")
        gen_expr(e[2])
        emit("mov %rax, %rsi")
        emit("pop %rdi")
        ccall("rt_getitem")
    elif k == "slice":
        gen_expr(e[1])
        emit("push %rax")
        if e[2] is None:
            emit("mov $2, %rax")
        else:
            gen_expr(e[2])
        emit("push %rax")
        if e[3] is None:
            emit("mov $2, %rax")
        else:
            gen_expr(e[3])
        emit("mov %rax, %rdx")
        emit("pop %rsi")
        emit("pop %rdi")
        ccall("rt_slice")
    elif k == "list" or k == "tuple" or k == "dict":
        items = e[1]
        gen_push_items(items)
        n = len(items)
        if k == "dict":
            n = n // 2
        emit("mov $" + str(n) + ", %rdi")
        emit("mov %rsp, %rsi")
        ccall("rt_mk" + k)
        if len(items) > 0:
            emit("add $" + str(8 * len(items)) + ", %rsp")
    elif k == "lambda":
        label = gen_function(e[1], e[2], e[3], True)
        gen_closure(e[1], label, len(e[2]))
    elif k == "attr":
        error("attribute access outside of a call is not supported", e[3], e[4])
    else:
        error("internal: cannot generate " + k, 0, 0)


def is_name(e, n):
    return e[0] == "name" and e[1] == n


def gen_call(e):
    fn = e[1]
    args = e[2]
    line = e[3]
    col = e[4]
    n = len(args)
    if fn[0] == "attr":
        gen_method_call(fn, args, line, col)
        return
    if fn[0] == "name" and var_kind(FS["sc"], fn[1]) == "global" and is_builtin(fn[1]):
        gen_builtin(fn[1], args, line, col)
        return
    gen_expr(fn)
    emit("push %rax")
    gen_push_items(args)
    emit("mov " + str(8 * n) + "(%rsp), %rax")
    emit("test $7, %al")
    emit("jnz zc_badcall")
    emit("cmpq $" + str(5 + 256 * n) + ", (%rax)")
    emit("jne zc_badcall")
    emit("call *8(%rax)")
    emit("add $" + str(8 * (n + 1)) + ", %rsp")


def need_args(name, args, lo, hi, line, col):
    if len(args) < lo or len(args) > hi:
        error("wrong number of arguments to " + name, line, col)


def gen_builtin(name, args, line, col):
    if name == "print":
        gen_push_items(args)
        emit("mov $" + str(len(args)) + ", %rdi")
        emit("mov %rsp, %rsi")
        ccall("rt_print")
        if len(args) > 0:
            emit("add $" + str(8 * len(args)) + ", %rsp")
    elif name == "len" or name == "str" or name == "repr" or name == "ord" or name == "chr" or name == "int":
        need_args(name, args, 1, 1, line, col)
        gen_expr(args[0])
        emit("mov %rax, %rdi")
        ccall("rt_" + name)
    elif name == "range":
        need_args(name, args, 1, 3, line, col)
        if len(args) == 1:
            emit("mov $1, %rax")
            emit("push %rax")
            gen_expr(args[0])
            emit("push %rax")
            emit("mov $3, %rax")
        else:
            gen_push_items(args)
            if len(args) == 2:
                emit("mov $3, %rax")
            else:
                emit("pop %rax")
        emit("mov %rax, %rdx")
        emit("pop %rsi")
        emit("pop %rdi")
        ccall("rt_range")
    elif name == "isinstance":
        need_args(name, args, 2, 2, line, col)
        t = args[1]
        if t[0] != "name" or not (t[1] in TYPECODES):
            error("isinstance() supports only builtin types", line, col)
        gen_expr(args[0])
        emit("mov %rax, %rdi")
        emit("mov $" + str(TYPECODES[t[1]]) + ", %rsi")
        ccall("rt_isinstance")
    else:
        error("'" + name + "' can only be used in raise", line, col)


def gen_method_call(fn, args, line, col):
    obj = fn[1]
    m = fn[2]
    if is_name(obj, "sys") and var_kind(FS["sc"], "sys") == "global":
        if m == "exit":
            need_args("sys.exit", args, 0, 1, line, col)
            if len(args) == 0:
                emit("mov $2, %rax")
            else:
                gen_expr(args[0])
            emit("mov %rax, %rdi")
            ccall("rt_exit")
            return
        if m == "setrecursionlimit":
            need_args("sys.setrecursionlimit", args, 1, 1, line, col)
            gen_expr(args[0])
            emit("mov $2, %rax")
            return
        error("unsupported sys function '" + m + "'", line, col)
    if obj[0] == "attr" and is_name(obj[1], "sys"):
        f = obj[2] + "." + m
        if f == "stdin.read":
            need_args(f, args, 0, 0, line, col)
            ccall("rt_stdin_read")
            return
        if f == "stdout.write" or f == "stderr.write":
            need_args(f, args, 1, 1, line, col)
            gen_expr(args[0])
            emit("mov %rax, %rdi")
            if f == "stdout.write":
                ccall("rt_write_out")
            else:
                ccall("rt_write_err")
            return
        error("unsupported sys function '" + f + "'", line, col)
    key = m + "_" + str(len(args))
    if not (key in METHODS):
        error("unsupported method '" + m + "' with " + str(len(args)) + " argument(s)", line, col)
    gen_expr(obj)
    emit("push %rax")
    gen_push_items(args)
    regs = ["%rdi", "%rsi", "%rdx"]
    i = len(args)
    while i >= 0:
        emit("pop " + regs[i])
        i -= 1
    ccall("rt_m_" + key)


def gen_closure(fid, label, nparams):
    sc = SCOPES[fid]
    cur = FS["sc"]
    for n in sc["free"]:
        k = var_kind(cur, n)
        if k == "cell":
            emit("mov " + var_addr(n) + ", %rax")
        elif k == "free":
            emit("mov " + closure_addr() + ", %rax")
            emit("mov " + str(24 + 8 * cur["freeidx"][n]) + "(%rax), %rax")
        else:
            error("internal: free variable " + n + " is " + k, 0, 0)
        emit("push %rax")
    nf = len(sc["free"])
    emit("lea " + label + "(%rip), %rdi")
    emit("mov $" + str(nparams) + ", %rsi")
    emit("mov $" + str(nf) + ", %rdx")
    emit("mov %rsp, %rcx")
    ccall("rt_mkclosure")
    if nf > 0:
        emit("add $" + str(8 * nf) + ", %rsp")


def gen_function(fid, params, body, is_lambda):
    global FS
    saved = FS
    sc = SCOPES[fid]
    label = "F" + str(fid)
    nargs = len(params)
    FS = {"code": [], "sc": sc, "nslots": 0, "slots": {}, "loops": [], "nargs": nargs}
    i = 0
    for p in params:
        paddr = str(16 + 8 * (nargs - 1 - i)) + "(%rbp)"
        if p in sc["cells"]:
            emit("mov " + paddr + ", %rdi")
            ccall("rt_mkcell")
            emit("mov %rax, " + var_addr(p))
        else:
            FS["slots"][p] = paddr
        i += 1
    for n in sc["cells"]:
        if not (n in params):
            emit("mov $0, %rdi")
            ccall("rt_mkcell")
            emit("mov %rax, " + var_addr(n))
    if is_lambda:
        gen_expr(body)
    else:
        gen_stmts(body)
        emit("mov $2, %rax")
    emit("leave")
    emit("ret")
    finish_function(label)
    FS = saved
    return label


def finish_function(label):
    n = FS["nslots"]
    if n % 2 == 1:
        n += 1
    head = [label + ":", "    push %rbp", "    mov %rsp, %rbp"]
    if n > 0:
        head.append("    sub $" + str(8 * n) + ", %rsp")
    i = 0
    while i < FS["nslots"]:
        head.append("    movq $0, " + str(-8 * (i + 1)) + "(%rbp)")
        i += 1
    FUNCS.append("\n".join(head + FS["code"]))


def gen_stmts(stmts):
    for s in stmts:
        gen_stmt(s)


def gen_store_target(t):
    # value in %rax
    k = t[0]
    if k == "name":
        gen_store_name(t[1])
    elif k == "index":
        emit("push %rax")
        gen_expr(t[1])
        emit("push %rax")
        gen_expr(t[2])
        emit("mov %rax, %rsi")
        emit("pop %rdi")
        emit("pop %rdx")
        ccall("rt_setitem")
    else:
        items = t[1]
        emit("push %rax")
        emit("mov %rax, %rdi")
        emit("mov $" + str(len(items)) + ", %rsi")
        ccall("rt_unpack")
        i = 0
        for x in items:
            emit("mov (%rsp), %rdi")
            emit("mov $" + str(i) + ", %rsi")
            ccall("rt_index_raw")
            gen_store_target(x)
            i += 1
        emit("add $8, %rsp")


def jump_if_false(e, label):
    k = e[0]
    if k == "not":
        jump_if_true(e[1], label)
    elif k == "and":
        jump_if_false(e[1], label)
        jump_if_false(e[2], label)
    elif k == "or":
        ok = new_label()
        jump_if_true(e[1], ok)
        jump_if_false(e[2], label)
        emit_label(ok)
    else:
        gen_expr(e)
        skip = new_label()
        emit("cmp $4, %rax")
        emit("je " + label)
        emit("cmp $6, %rax")
        emit("je " + skip)
        gen_truthy_eax()
        emit("jz " + label)
        emit_label(skip)


def jump_if_true(e, label):
    k = e[0]
    if k == "not":
        jump_if_false(e[1], label)
    elif k == "or":
        jump_if_true(e[1], label)
        jump_if_true(e[2], label)
    elif k == "and":
        no = new_label()
        jump_if_false(e[1], no)
        jump_if_true(e[2], label)
        emit_label(no)
    else:
        gen_expr(e)
        skip = new_label()
        emit("cmp $6, %rax")
        emit("je " + label)
        emit("cmp $4, %rax")
        emit("je " + skip)
        gen_truthy_eax()
        emit("jnz " + label)
        emit_label(skip)


def binop_func(op):
    if op == "+":
        return "rt_iadd"
    return BINOPS[op]


def is_range_call(e):
    return (e[0] == "call" and is_name(e[1], "range") and var_kind(FS["sc"], "range") == "global"
            and is_builtin("range") and len(e[2]) >= 1 and len(e[2]) <= 2)


def gen_stmt(s):
    k = s[0]
    if k == "expr":
        gen_expr(s[1])
    elif k == "assign":
        gen_expr(s[2])
        targets = s[1]
        i = 0
        for t in targets:
            if i < len(targets) - 1:
                emit("push %rax")
                gen_store_target(t)
                emit("pop %rax")
            else:
                gen_store_target(t)
            i += 1
    elif k == "augassign":
        t = s[2]
        if t[0] == "name":
            gen_load(t[1], s[4], s[5])
            emit("push %rax")
            gen_expr(s[3])
            emit("mov %rax, %rsi")
            emit("pop %rdi")
            ccall(binop_func(s[1]))
            gen_store_name(t[1])
        else:
            gen_expr(t[1])
            emit("push %rax")
            gen_expr(t[2])
            emit("push %rax")
            emit("mov 8(%rsp), %rdi")
            emit("mov %rax, %rsi")
            ccall("rt_getitem")
            emit("push %rax")
            gen_expr(s[3])
            emit("mov %rax, %rsi")
            emit("pop %rdi")
            ccall(binop_func(s[1]))
            emit("mov %rax, %rdx")
            emit("pop %rsi")
            emit("pop %rdi")
            ccall("rt_setitem")
    elif k == "if":
        lelse = new_label()
        lend = new_label()
        jump_if_false(s[1], lelse)
        gen_stmts(s[2])
        if len(s[3]) > 0:
            emit("jmp " + lend)
        emit_label(lelse)
        gen_stmts(s[3])
        emit_label(lend)
    elif k == "while":
        top = new_label()
        end = new_label()
        emit_label(top)
        jump_if_false(s[1], end)
        FS["loops"].append((top, end))
        gen_stmts(s[2])
        FS["loops"].pop()
        emit("jmp " + top)
        emit_label(end)
    elif k == "for":
        gen_for(s)
    elif k == "break" or k == "continue":
        if len(FS["loops"]) == 0:
            error("'" + k + "' outside loop", s[1], s[2])
        lp = FS["loops"][len(FS["loops"]) - 1]
        if k == "break":
            emit("jmp " + lp[1])
        else:
            emit("jmp " + lp[0])
    elif k == "pass" or k == "global" or k == "nonlocal":
        pass
    elif k == "return":
        if FS["sc"]["fid"] == 0:
            error("'return' outside function", s[2], s[3])
        if s[1] is None:
            emit("mov $2, %rax")
        else:
            gen_expr(s[1])
        emit("leave")
        emit("ret")
    elif k == "def":
        label = gen_function(s[1], s[3], s[4], False)
        gen_closure(s[1], label, len(s[3]))
        gen_store_name(s[2])
    elif k == "assert":
        ok = new_label()
        jump_if_true(s[1], ok)
        if s[2] is None:
            emit("mov $2, %rax")
        else:
            gen_expr(s[2])
        emit("mov %rax, %rdi")
        ccall("rt_assert_fail")
        emit_label(ok)
    elif k == "raise":
        e = s[1]
        if e[0] == "call" and e[1][0] == "name" and len(e[2]) <= 1:
            emit("lea " + str_label(e[1][1]) + "(%rip), %rax")
            emit("push %rax")
            if len(e[2]) == 0:
                emit("mov $2, %rax")
            else:
                gen_expr(e[2][0])
            emit("mov %rax, %rsi")
            emit("pop %rdi")
            ccall("rt_raise")
        else:
            error("only 'raise Name(msg)' is supported", s[2], s[3])
    else:
        error("internal: unknown statement " + k, 0, 0)


def gen_for(s):
    target = s[1]
    it = s[2]
    top = new_label()
    cont = new_label()
    end = new_label()
    if is_range_call(it):
        args = it[2]
        cur = new_slot()
        stop = new_slot()
        if len(args) == 1:
            emit("mov $1, %rax")
            emit("push %rax")
            gen_expr(args[0])
        else:
            gen_expr(args[0])
            emit("push %rax")
            gen_expr(args[1])
        emit("mov %rax, " + stop)
        emit("pop %rax")
        emit("mov %rax, " + cur)
        emit("mov %rax, %rdi")
        emit("and " + stop + ", %rdi")
        emit("test $1, %dil")
        emit("jnz " + top)
        emit("mov " + cur + ", %rdi")
        emit("mov " + stop + ", %rsi")
        emit("mov $3, %rdx")
        ccall("rt_range")
        emit_label(top)
        emit("mov " + cur + ", %rax")
        emit("cmp " + stop + ", %rax")
        emit("jge " + end)
        gen_store_target(target)
        FS["loops"].append((cont, end))
        gen_stmts(s[3])
        FS["loops"].pop()
        emit_label(cont)
        emit("addq $2, " + cur)
        emit("jmp " + top)
        emit_label(end)
        return
    seq = new_slot()
    idx = new_slot()
    gen_expr(it)
    emit("mov %rax, " + seq)
    emit("movq $1, " + idx)
    emit_label(top)
    emit("mov " + seq + ", %rdi")
    emit("mov " + idx + ", %rsi")
    ccall("rt_iter_get")
    emit("test %rax, %rax")
    emit("jz " + end)
    gen_store_target(target)
    FS["loops"].append((cont, end))
    gen_stmts(s[3])
    FS["loops"].pop()
    emit_label(cont)
    emit("addq $2, " + idx)
    emit("jmp " + top)
    emit_label(end)


def asm_bytes(s):
    out = []
    i = 0
    n = len(s)
    while i < n:
        chunk = []
        j = i
        while j < n and j < i + 32:
            chunk.append(str(ord(s[j])))
            j += 1
        out.append("    .byte " + ",".join(chunk))
        i = j
    out.append("    .byte 0")
    return out


def compile_program(src):
    global TOKS
    global POS
    global FS
    TOKS = lex(src)
    POS = 0
    prog = parse_program()
    mod = new_scope(0, None, [])
    decl_stmts(prog, mod)
    ref_stmts(prog, mod)
    FS = {"code": [], "sc": mod, "nslots": 0, "slots": {}, "loops": [], "nargs": 0}
    gen_stmts(prog)
    emit("mov $2, %rax")
    emit("leave")
    emit("ret")
    finish_function("Zmodule")
    out = [".text",
           ".globl zmain",
           "zmain:",
           "    push %rbp",
           "    mov %rsp, %rbp",
           "    push %rbx",
           "    push %r12",
           "    push %r13",
           "    push %r14",
           "    push %r15",
           "    sub $8, %rsp",
           "    call Zmodule",
           "    add $8, %rsp",
           "    pop %r15",
           "    pop %r14",
           "    pop %r13",
           "    pop %r12",
           "    pop %rbx",
           "    pop %rbp",
           "    ret",
           "zc_badcall:",
           "    and $-16, %rsp",
           "    call rt_badcall",
           "zc_nameerr:",
           "    and $-16, %rsp",
           "    call rt_nameerr"]
    for f in FUNCS:
        out.append(f)
    out.append(".data")
    for g in GLOBALS:
        out.append(".balign 8")
        out.append("G_" + g + ": .quad 0")
    for s in STRS:
        out.append(".balign 8")
        out.append(STRS[s] + ":")
        out.append("    .quad 1, " + str(len(s)) + ", 0")
        for b in asm_bytes(s):
            out.append(b)
    out.append(".section .note.GNU-stack,\"\",@progbits")
    return "\n".join(out) + "\n"


sys.stdout.write(compile_program(sys.stdin.read()))
