# Headless, one component per process: round its edges before fusing. Usage: PART=<object> [STRICT=1] freecadcmd build/round_part.py
# Edge rules are in edge_rules.py. Output: $BUILD_OUT/rp_<PART>.brep.
import os, sys, time
import FreeCAD as App, Part

V = App.Vector
ROOT = "/Users/tom/projects/fun/macbook-mount"
S = os.environ.get("BUILD_OUT", ROOT + "/build/out") + "/"
NAME = os.environ["PART"]
d = App.openDocument(ROOT + "/DeskMount.FCStd")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from edge_rules import R_MAJOR, R_RIDGE, classify, key, mid

t0 = time.time()
shape = d.getObject(NAME).Shape
concave, major, ridge = classify(d, NAME)
print("%s classified: concave %d major %d ridge %d (%.0fs)" % (NAME, len(concave), len(major), len(ridge), time.time() - t0), flush=True)


STRICT = os.environ.get("STRICT") == "1"


def strict_ok(sh):
    """With STRICT=1, reject fillets that leave self-intersections (BOP check)."""
    if not STRICT:
        return True
    try:
        sh.check(True)
        return True
    except Exception:
        return False


def chunked(sh, pts, r, n=120):
    pts = sorted(pts, key=lambda p: (round(p.y / 40), p.z, p.y))
    bad = []
    for i in range(0, len(pts), n):
        sh, b = fillet(sh, pts[i:i + n], r)
        bad += b
        print("%s  r%.1f batch %d/%d: %d skipped (%.0fs)" % (NAME, r, i // n + 1, (len(pts) + n - 1) // n, len(b), time.time() - t0), flush=True)
    return sh, bad


def edges_at(sh, pts):
    m = {key(mid(e)): e for e in sh.Edges}
    return [m[key(p)] for p in pts if key(p) in m]


def fillet(sh, pts, r):
    edges = edges_at(sh, pts)
    if not edges:
        return sh, []
    try:
        out = sh.makeFillet(r, edges)
        if out.isValid() and len(out.Solids) == len(sh.Solids) and strict_ok(out):
            return out, []
    except Exception:
        pass
    if len(pts) == 1:
        return sh, pts
    h = len(pts) // 2
    sh, b1 = fillet(sh, pts[:h], r)
    sh, b2 = fillet(sh, pts[h:], r)
    return sh, b1 + b2


shape, bad_c = chunked(shape, concave, R_MAJOR)
shape, bad_c2 = chunked(shape, bad_c, R_RIDGE)
print("%s concave R1.5: %d, %d at R0.4, %d left sharp (%.0fs)" % (NAME, len(concave), len(bad_c) - len(bad_c2), len(bad_c2), time.time() - t0), flush=True)
shape, bad_m = chunked(shape, major, R_MAJOR)
print("%s major R1.5: %d, %d too tight (%.0fs)" % (NAME, len(major), len(bad_m), time.time() - t0), flush=True)
shape, bad_r = chunked(shape, ridge + bad_m, R_RIDGE)
print("%s ridge R0.4: %d, %d failed (%.0fs)" % (NAME, len(ridge) + len(bad_m), len(bad_r), time.time() - t0), flush=True)
shape.exportBrep(S + "rp_" + NAME + ".brep")
print("%s STRICT check passes: %s" % (NAME, strict_ok(shape) if STRICT else "not run"), flush=True)
print("%s RESULT valid %s solids %d vol %.1f -> %.1f (%.0fs)" % (NAME, shape.isValid(), len(shape.Solids),
      d.getObject(NAME).Shape.Volume, shape.Volume, time.time() - t0), flush=True)
