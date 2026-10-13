# Headless: round the cartridge (USBC_Cartridge) with self-intersection checks. R1.5 where both faces lie on the
# outer planes of the body or tongues, else R0.4, then R0.2 for edges that fail. Breakaway ties, detent balls and
# concave edges are left as modelled. Output: $BUILD_OUT/cart_rounded.brep.
import os, time
import FreeCAD as App, Part

ROOT = "/Users/tom/projects/fun/macbook-mount"
S = os.environ.get("BUILD_OUT", ROOT + "/build/out") + "/"
d = App.openDocument(ROOT + "/DeskMount.FCStd")
R_MAJOR, R_RIDGE, SHARP = 1.5, 0.4, 0.985
t0 = time.time()
shape = d.getObject("USBC_Cartridge").Shape
tongues = [d.getObject(n).Shape for n in ("Cart_Tongue_Lid", "Cart_Tongue_Feet")]
keep = [s.BoundBox for n in ("Cart_Breakaway_Lid", "Cart_Breakaway_Feet") for s in d.getObject(n).Shape.Solids]
for b in keep:
    b.enlarge(0.1)
planes = set()
for s in [d.getObject("Cart_Body_Cut").Shape] + tongues:
    b = s.BoundBox
    for ax, lo, hi in (("x", b.XMin, b.XMax), ("y", b.YMin, b.YMax), ("z", b.ZMin, b.ZMax)):
        planes.update({(ax, round(lo, 2)), (ax, round(hi, 2))})
for s in tongues:                                  # the tongue tops (Z >= 63.9) count as outer faces too
    for f in s.Faces:
        if f.Surface.__class__.__name__ == "Plane" and f.BoundBox.ZMin >= 63.9:
            n = f.Surface.Axis
            for ax, comp, val in (("x", n.x, f.BoundBox.XMin), ("y", n.y, f.BoundBox.YMin), ("z", n.z, f.BoundBox.ZMin)):
                if abs(abs(comp) - 1) < 1e-6:
                    planes.add((ax, round(val, 2)))


def mid(e):
    return e.valueAt((e.FirstParameter + e.LastParameter) / 2)


def key(p):
    return (round(p.x, 3), round(p.y, 3), round(p.z, 3))


def on_plane(f):
    if f.Surface.__class__.__name__ != "Plane":
        return False
    n = f.Surface.Axis
    for ax, comp, val in (("x", n.x, f.BoundBox.XMin), ("y", n.y, f.BoundBox.YMin), ("z", n.z, f.BoundBox.ZMin)):
        if abs(abs(comp) - 1) < 1e-6:
            return (ax, round(val, 2)) in planes
    return False


def strict_ok(sh):
    try:
        sh.check(True)
        return True
    except Exception:
        return False


major, ridge = [], []
emap = {}
for f in shape.Faces:
    for fe in f.Edges:
        emap.setdefault(fe.hashCode(), []).append(f)
for e in shape.Edges:
    fs = emap.get(e.hashCode(), [])
    if len(fs) != 2 or e.Length < 0.05 or any(f.Surface.__class__.__name__ == "Sphere" for f in fs):
        continue
    p = mid(e)
    if any(b.isInside(p) for b in keep):
        continue
    try:
        n1 = fs[0].normalAt(*fs[0].Surface.parameter(p)); n2 = fs[1].normalAt(*fs[1].Surface.parameter(p))
    except Exception:
        continue
    if n1.dot(n2) > SHARP or shape.isInside(p - n1 * 0.03 + n2 * 0.03, 1e-7, True):
        continue                                   # tangent, flat or concave
    (major if on_plane(fs[0]) and on_plane(fs[1]) else ridge).append(p)
print("CART classified major %d ridge %d (%.0fs)" % (len(major), len(ridge), time.time() - t0), flush=True)


def edges_at(sh, pts):
    m = {key(mid(e)): e for e in sh.Edges}
    return [m[key(p)] for p in pts if key(p) in m]


def fillet(sh, pts, r):
    """Fillet the edges at pts; bisect on failure. Returns (shape, points that could not be filleted)."""
    edges = edges_at(sh, pts)
    if not edges:
        return sh, []
    try:
        out = sh.makeFillet(r, edges)
        if out.isValid() and len(out.Solids) == 1 and strict_ok(out):
            return out, []
    except Exception:
        pass
    if len(pts) == 1:
        return sh, pts
    h = len(pts) // 2
    sh, b1 = fillet(sh, pts[:h], r)
    sh, b2 = fillet(sh, pts[h:], r)
    return sh, b1 + b2


shape, bad_m = fillet(shape, major, R_MAJOR)
shape, bad_r = fillet(shape, ridge + bad_m, R_RIDGE)
shape, bad_r2 = fillet(shape, bad_r, 0.2)
print("CART RESULT major %d (%d too tight), ridge %d, %d at R0.2, %d left sharp, valid %s strict %s vol %.3f cm3 (%.0fs)" % (
    len(major), len(bad_m), len(ridge) + len(bad_m), len(bad_r) - len(bad_r2), len(bad_r2), shape.isValid(), strict_ok(shape),
    shape.Volume / 1000, time.time() - t0), flush=True)
shape.exportBrep(S + "cart_rounded.brep")
