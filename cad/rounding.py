# Builds the rounding of every printed part as native features in DeskMount.FCStd.
#   cad/build_rounding.sh Wall_Lid Floor      headless, logs to cad/out/build_rounding.log (close the model in the GUI
#                                             first, or reload it after); a wall takes 40-50 minutes
#   in the GUI: exec(open("cad/rounding.py").read()); build("Floor")   (small parts only: a long GUI call times out)
# Each part gets a chain of features ending in "<part>_Rounded" (group Rounding); the chain recomputes with the model.
# Run build() again for a part after editing it: the edge lists in the chain are fixed.
#
# Edge rules. Mount parts: R1.5 if both faces lie on the part's bounding-box planes ("major"), else R0.4 ("ridge").
# Concave edges get R1.5, or R0.4 where R1.5 fails; on the walls only the cell corners (along X). Edges that touch
# another mount part away from their ends are skipped so the joins stay flush; mount_fuse.py rounds some joins after the fuse. The cartridge groove zone and detent-hole rims are skipped.
# Cartridge: R1.5 where both faces lie on the outer planes of the body or tongues, else R0.4, then R0.2 where R0.4
# fails. Breakaway ties, detent balls and concave edges are left as modelled.
#
# Chain: _A15/_A04 Part::Fillet (concave, R1.5 then R0.4) -> _B Part::Cut (flared cutters: an R0.4 lip on every closed
# loop of ridge edges on an axis plane, i.e. the cell mouths) -> _D Part::Fillet (majors, R1.5) -> _C Part::Fillet
# (remaining ridges and failed majors, R0.4) -> _E Part::Cut (edge cutters for the edges a fillet cannot round, e.g. where
# the ribs meet the rails) -> _F Part::Fillet (R0.4 on the convex edges the rounds create, such as the end arcs of the
# cell-corner rounds). A fixed fillet list cannot fall back per edge at recompute, so build() tests the edges here, on blocks of
# the part, and moves the edges that fail into the next stage.
import math
import os
import time

import FreeCAD as App
import Part

V = App.Vector
ROOT = "/Users/tom/projects/fun/macbook-mount"
R_MAJOR, R_RIDGE, R_SMALL, SHARP = 1.5, 0.4, 0.2, 0.985
XL, XF = -11.493, 9.248
MOUNT_PARTS = ["Wall_Lid", "Wall_Feet", "Floor", "Riser_Grid", "RearStop", "DeskPlate", "Gussets", "CartRail_Lid", "CartRail_Feet"]
d = App.getDocument("DeskMount") if "DeskMount" in App.listDocuments() else App.openDocument(ROOT + "/DeskMount.FCStd")


# ---------------------------------------------------------------- edge rules
def mid(e):
    if e.Degenerated:                                  # a fillet can leave a zero-length seam edge with no curve
        return e.Vertexes[0].Point
    return e.valueAt((e.FirstParameter + e.LastParameter) / 2)


def on_planes(f, planes):
    if f.Surface.__class__.__name__ != "Plane":
        return False
    n = f.Surface.Axis
    for ax, comp, val in (("x", n.x, f.BoundBox.XMin), ("y", n.y, f.BoundBox.YMin), ("z", n.z, f.BoundBox.ZMin)):
        if abs(abs(comp) - 1) < 1e-6:
            return (ax, round(val, 2)) in planes
    return False


def box_planes(b):
    return {("x", round(b.XMin, 2)), ("x", round(b.XMax, 2)), ("y", round(b.YMin, 2)), ("y", round(b.YMax, 2)),
            ("z", round(b.ZMin, 2)), ("z", round(b.ZMax, 2))}


def edge_faces(shape):
    emap = {}
    for f in shape.Faces:
        for fe in f.Edges:
            emap.setdefault(fe.hashCode(), []).append(f)
    return emap


def normals(fs, p):
    return [f.normalAt(*f.Surface.parameter(p)) for f in fs]


def other_parts(name):
    """(bounding box, shape) of the other mount parts, for touches_other."""
    out = []
    for o in d.getObject("Mount_Fused").Shapes:
        if o.Name != name:
            b = o.Shape.BoundBox
            b.enlarge(0.05)
            out.append((b, o.Shape))
    return out


def touches_other(e, p, obox):
    """True if another part touches the edge away from its ends (within 0.5 mm of an end does not count). Such an edge
    is a join, or partly one, and stays sharp: a round there would leave a groove inside the join. An edge that touches
    another part only at an end vertex is rounded."""
    L = e.Length
    if L > 1.2:
        inner = e.Curve.toShape(e.getParameterByLength(0.5), e.getParameterByLength(L - 0.5))
    else:
        inner = Part.Vertex(p)
    for b, s in obox:
        if b.intersect(inner.BoundBox) and inner.distToShape(s)[0] < 0.02:
            return True
    return False


def skip_zone(p):
    """The cartridge groove zone of the rails and walls."""
    in_x = (XF - 0.05 <= p.x <= XF + 2.6) or (XL - 2.6 <= p.x <= XL + 0.05)
    return in_x and 329.4 <= p.y <= 334.6 and p.z <= 61.8


def detent_rim(fs):
    return any(f.Surface.__class__.__name__ == "Cylinder" and abs(f.Surface.Radius - 1.3265) < 0.01 for f in fs)


def sharp_convex(sh, name):
    """Convex sharp edges that the rounds themselves create, such as the end arcs of the cell-corner rounds: edges of
    0.2 mm or more between a round (any curved face) and another face, with the same skips as classify(). Plane-to-plane
    edges are left to the classify() rules; shorter slivers make OpenCascade fillets crash."""
    obox = other_parts(name)
    emap = edge_faces(sh)
    out = []
    for e in sh.Edges:
        fs = emap.get(e.hashCode(), [])
        if len(fs) != 2 or e.Length < 0.2 or all(f.Surface.__class__.__name__ == "Plane" for f in fs):
            continue
        p = mid(e)
        if skip_zone(p) or detent_rim(fs):
            continue
        try:
            n1, n2 = normals(fs, p)
        except Exception:
            continue
        if n1.dot(n2) > SHARP or sh.isInside(p - n1 * 0.03 + n2 * 0.03, 1e-7, True) or touches_other(e, p, obox):
            continue
        out.append(e)
    return out


def classify(name):
    """Edges of a mount part's source shape by rounding class: (concave, major, ridge)."""
    shape = d.getObject(name).Shape
    obox = other_parts(name)
    planes = box_planes(shape.BoundBox)

    if name == "Gussets":                              # R1.5 on the sloped-face edges only
        out = []
        for s in shape.Solids:
            slope = [f for f in s.Faces if abs(abs(f.normalAt(0, 0).x) - 0.7071) < 0.01 and abs(abs(f.normalAt(0, 0).z) - 0.7071) < 0.01]
            out += [e for e in slope[0].Edges if abs(e.tangentAt(e.FirstParameter).y) < 0.01]
        return [], out, []
    concave, major, ridge = [], [], []
    emap = edge_faces(shape)
    for e in shape.Edges:
        fs = emap.get(e.hashCode(), [])
        if len(fs) != 2 or e.Length < 0.05:
            continue
        p = mid(e)
        if skip_zone(p) or detent_rim(fs):
            continue
        try:
            n1, n2 = normals(fs, p)
        except Exception:
            continue
        if n1.dot(n2) > SHARP or touches_other(e, p, obox):
            continue
        if shape.isInside(p - n1 * 0.03 + n2 * 0.03, 1e-7, True):
            if not name.startswith("Wall_") or abs(e.tangentAt(e.FirstParameter).x) > 0.99:
                concave.append(e)                      # on the walls only cell corners (along X)
            continue
        (major if on_planes(fs[0], planes) and on_planes(fs[1], planes) else ridge).append(e)
    return concave, major, ridge


def classify_cartridge():
    """Edges of USBC_Cartridge by rounding class: (major, ridge)."""
    shape = d.getObject("USBC_Cartridge").Shape
    tongues = [d.getObject(n).Shape for n in ("Cart_Tongue_Lid", "Cart_Tongue_Feet")]
    keep = [s.BoundBox for n in ("Cart_Breakaway_Lid", "Cart_Breakaway_Feet") for s in d.getObject(n).Shape.Solids]
    for b in keep:
        b.enlarge(0.1)
    planes = set()
    for s in [d.getObject("Cart_Body_Cut").Shape] + tongues:
        planes |= box_planes(s.BoundBox)
    for s in tongues:                                  # the tongue tops (Z >= 63.9) count as outer faces too
        for f in s.Faces:
            if f.Surface.__class__.__name__ == "Plane" and f.BoundBox.ZMin >= 63.9:
                n = f.Surface.Axis
                for ax, comp, val in (("x", n.x, f.BoundBox.XMin), ("y", n.y, f.BoundBox.YMin), ("z", n.z, f.BoundBox.ZMin)):
                    if abs(abs(comp) - 1) < 1e-6:
                        planes.add((ax, round(val, 2)))
    major, ridge = [], []
    emap = edge_faces(shape)
    for e in shape.Edges:
        fs = emap.get(e.hashCode(), [])
        if len(fs) != 2 or e.Length < 0.05 or any(f.Surface.__class__.__name__ == "Sphere" for f in fs):
            continue
        p = mid(e)
        if any(b.isInside(p) for b in keep):
            continue
        try:
            n1, n2 = normals(fs, p)
        except Exception:
            continue
        if n1.dot(n2) > SHARP or shape.isInside(p - n1 * 0.03 + n2 * 0.03, 1e-7, True):
            continue
        (major if on_planes(fs[0], planes) and on_planes(fs[1], planes) else ridge).append(e)
    return major, ridge


# ---------------------------------------------------------------- geometry helpers
def strict_ok(s):
    try:
        s.check(True)
        return True
    except Exception:
        return False


def on_edge(sh, e0):
    """Indices (1-based) of the edges of sh that run along the source edge e0: trimmed pieces, longer edges, overlaps."""
    def pts(e):
        return [e.valueAt(e.FirstParameter + f * (e.LastParameter - e.FirstParameter)) for f in (0.1, 0.3, 0.5, 0.7, 0.9)]
    bb = e0.BoundBox
    bb.enlarge(1e-3)
    out = []
    for i, e in enumerate(sh.Edges):
        if e.Length < 0.02 or not e.BoundBox.intersect(bb):
            continue
        if sum(e0.distToShape(Part.Vertex(q))[0] < 1e-4 for q in pts(e)) >= 2 or sum(e.distToShape(Part.Vertex(q))[0] < 1e-4 for q in pts(e0)) >= 2:
            out.append(i + 1)
    return out


def round_area(sh, e, r):
    """Cross-section area a round of radius r takes off (or fills into) an edge whose faces meet at angle theta:
    r^2 (cot(theta/2) - (pi - theta)/2); (1 - pi/4) r^2 for 90 degrees."""
    fs = sh.ancestorsOfType(e, Part.Face)
    try:
        n1, n2 = normals(fs, mid(e))
        theta = math.pi - math.acos(max(-1.0, min(1.0, n1.dot(n2))))
        return r * r * (1 / math.tan(theta / 2) - (math.pi - theta) / 2)
    except Exception:
        return (1 - math.pi / 4) * r * r


def fillet_ok(sh, edges, r, convex=True):
    """Test on a copy: OpenCascade operations can raise the tolerances of their input shape in place.
    Besides validity, the volume change must match the rounds: a fillet can return a valid shape that fills a whole
    cell. A round of radius r along an edge of length L removes (convex) or adds (concave) round_area * L."""
    sh = sh.copy()
    try:
        es = [sh.Edges[i - 1] for i in edges]
        n = sh.makeFillet(r, es)
        if not (n.isValid() and len(n.Solids) == len(sh.Solids) and strict_ok(n)):
            return False
        if max(v.Tolerance for v in n.Vertexes) > 0.01:   # a valid round on a rail left a 0.38 mm vertex; it broke the fuse
            return False
        expect = sum(round_area(sh, e, r) * e.Length for e in es)
        dv = (sh.Volume - n.Volume) if convex else (n.Volume - sh.Volume)
        return -0.01 <= dv <= 2.0 * expect + 0.01
    except Exception:
        return False


def select(base, items, r, convex=True, window=60.0, margin=8.0):
    """Split source edges into (kept, dropped, gone): kept ones fillet together at r on base, dropped ones make the
    fillet fail, gone ones no longer exist on base (an earlier round took them). Tested block by block (cheap), then once
    on the whole part; a whole-part failure falls back to testing on the whole part."""
    mapped = [(e, on_edge(base, e)) for e in items]
    gone = [e for e, ii in mapped if not ii]
    items = [e for e, ii in mapped if ii]
    if not items:
        return [], [], gone
    bb = base.BoundBox
    ax = max(range(3), key=lambda i: (bb.XLength, bb.YLength, bb.ZLength)[i])
    lo, hi = (bb.XMin, bb.YMin, bb.ZMin)[ax], (bb.XMax, bb.YMax, bb.ZMax)[ax]

    def keep(sh, edges, kept, dropped):
        """edges: list of (source edge, [indices on sh]). Cumulative: add while the whole list still fillets."""
        if not edges:
            return kept
        idx = [i for _, ii in kept + edges for i in ii]
        if fillet_ok(sh, idx, r, convex):
            return kept + edges
        if len(edges) == 1:
            dropped.append(edges[0][0])
            return kept
        h = len(edges) // 2
        return keep(sh, edges[h:], keep(sh, edges[:h], kept, dropped), dropped)

    dropped = []
    if hi - lo > window + 2 * margin:                  # large part: find the failing edges on blocks first
        a = lo
        while a < hi:
            b = min(a + window, hi + 1)
            box = [bb.XMin - 1, bb.YMin - 1, bb.ZMin - 1, bb.XLength + 2, bb.YLength + 2, bb.ZLength + 2]
            box[ax], box[ax + 3] = a - margin, (b - a) + 2 * margin
            sh = base.copy().common(Part.makeBox(box[3], box[4], box[5], V(box[0], box[1], box[2])))
            edges = [(e, on_edge(sh, e)) for e in items if a <= (mid(e).x, mid(e).y, mid(e).z)[ax] < b]
            keep(sh, [x for x in edges if x[1]], [], dropped)
            a = b
    full = [(e, ii) for e, ii in mapped if ii and not any(e is x for x in dropped)]
    if not fillet_ok(base, [i for _, ii in full for i in ii], r, convex):
        print("   whole-part fillet failed after block tests; testing on the whole part", flush=True)
        full = keep(base, full, [], dropped)
    return [e for e, _ in full], dropped, gone


def flare(W, solid, ax, r=R_RIDGE):
    """Cutter that rounds the mouth edge loop W (on a plane normal to axis ax) with an R lip; None if W is not a mouth."""
    A = [V(1, 0, 0), V(0, 1, 0), V(0, 0, 1)][ax]
    F = Part.Face(W)
    try:
        out = F.makeOffset2D(0.2, join=0).OuterWire.Edges[0]
        inn = F.makeOffset2D(-0.2, join=0).OuterWire.Edges[0]
    except Exception:
        return None
    q = mid(out)
    qi = mid(inn)
    s1, s2 = solid.isInside(q + A * 0.1, 1e-7, True), solid.isInside(q - A * 0.1, 1e-7, True)
    if s1 == s2 or solid.isInside(qi + A * 0.1, 1e-7, True) or solid.isInside(qi - A * 0.1, 1e-7, True):
        return None                                    # solid inside the loop: an outer edge, not a mouth
    sgn = 1 if s1 else -1
    ring = F.makeOffset2D(r, join=0)
    slab = ring.translated(A * (-sgn * 1.0)).extrude(A * (sgn * (1.0 + r)))
    C = ring.OuterWire.translated(A * (sgn * r))
    e0 = C.Edges[0]
    ps = Part.BRepOffsetAPI.MakePipeShell(C)
    ps.setTransitionMode(2)
    ps.add(Part.Wire(Part.makeCircle(r, e0.valueAt(e0.FirstParameter), e0.tangentAt(e0.FirstParameter))))
    ps.build()
    ps.makeSolid()
    c = slab.cut(ps.shape())
    return c if c.isValid() and c.Volume > 0 else None


def side_solid(f, keep_pt, big=60):
    """Half-space (plane) or cylinder solid bounded by face f's surface, on the side of keep_pt."""
    su = f.Surface
    if isinstance(su, Part.Plane):
        n, p0 = su.Axis, su.Position
        s = 1 if (keep_pt - p0).dot(n) > 0 else -1
        bx = Part.makeBox(2 * big, 2 * big, big, V(-big, -big, 0))
        return bx.transformed(App.Placement(p0, App.Rotation(V(0, 0, 1), n * s)).toMatrix())
    if isinstance(su, Part.Cylinder):
        c = Part.makeCylinder(su.Radius, 2 * big, su.Center - su.Axis * big, su.Axis)
        if c.isInside(keep_pt, 1e-7, True):
            return c
        return Part.makeBox(2 * big, 2 * big, 2 * big, keep_pt - V(big, big, big)).cut(c)
    return None


def edge_cutter(sh, e, r):
    """Cutter that rounds the 90° convex edge e of sh at r, trimmed at each end by the face the edge ends against."""
    fs = sh.ancestorsOfType(e, Part.Face)
    m = mid(e)
    ends = []
    for par, sgn in ((e.FirstParameter, -1), (e.LastParameter, 1)):
        p = e.valueAt(par)
        t = e.tangentAt(par) * sgn                     # pointing out of the edge
        v = [x for x in e.Vertexes if (x.Point - p).Length < 1e-6][0]
        own = normals(fs, p)
        stops = [f for f in sh.ancestorsOfType(v, Part.Face) if not any(f.isSame(x) for x in fs)
                 and not any(abs(f.normalAt(*f.Surface.parameter(p)).dot(n)) > 0.999 for n in own)]
        ends.append((p, t, stops))
    (p0, t0, st0), (p1, t1, st1) = ends
    d1, d2 = [-n for n in normals(fs, p0)]
    segs = ([Part.makeLine(p0 + t0, p0)] if st0 else []) + [e.copy()] + ([Part.makeLine(p1, p1 + t1)] if st1 else [])
    start = p0 + t0 if st0 else p0
    prof = Part.Face(Part.makePolygon([start, start + d1 * r, start + d1 * r + d2 * r, start + d2 * r, start]))
    prof = prof.cut(Part.Face(Part.Wire(Part.makeCircle(r, start + d1 * r + d2 * r, -t0)))).Faces[0]
    ps = Part.BRepOffsetAPI.MakePipeShell(Part.Wire(segs))
    ps.setFrenetMode(False)
    ps.setTransitionMode(1)
    ps.add(prof.OuterWire)
    ps.build()
    ps.makeSolid()
    c = ps.shape()
    for p, t, stops in ends:
        for f in stops:
            hs = side_solid(f, m)
            if hs is not None:
                c = c.common(hs)
    return c


# ---------------------------------------------------------------- chain
group = d.getObject("Rounding") or d.addObject("App::DocumentObjectGroup", "Rounding")


def clear(name):
    """Remove the old chain of a part (and any helper shapes)."""
    for o in list(d.Objects):
        if o.Name.startswith(name + "_") and o.Name[len(name) + 1:] in ("A15", "A04", "B", "B_Cutters", "C", "C2", "D", "E", "E_Cutters", "F", "F2", "R15", "Rounded"):
            d.removeObject(o.Name)


def stage(kind, name, tool_name, base, payload):
    """Create one feature of the chain on base. The fillet edges are mapped onto base's recomputed shape."""
    if kind == "fillet":
        kept, r = payload
        o = d.addObject("Part::Fillet", name)
        o.Base = base
        o.Edges = [(i, r, r) for i in sorted({i for e in kept for i in on_edge(base.Shape, e)})]
    else:
        tool = d.getObject(tool_name) or d.addObject("Part::Feature", tool_name)
        tool.Shape = Part.makeCompound(payload)
        if tool.ViewObject:
            tool.ViewObject.Visibility = False
        o = d.addObject("Part::Cut", name)
        o.Base = base
        o.Tool = tool
        o.Refine = False                               # refining these cuts leaves invalid curve-on-surface edges
    if o.ViewObject:
        o.ViewObject.Visibility = False
    d.recompute()
    if "Invalid" in o.State or o.Shape.isNull() or not o.Shape.isValid():
        raise RuntimeError("%s did not recompute" % name)
    return o


def build(name):
    """Build the chain stage by stage: each stage is tested on the recomputed shape of the feature before it."""
    t0 = time.time()
    clear(name)
    src = d.getObject(name)
    cur = src
    last = None                                        # (suffix, kind, payload) of the newest feature

    def log(msg):
        print("  %s (%.0fs)" % (msg, time.time() - t0), flush=True)

    def add(suffix, kind, payload):
        nonlocal cur, last
        cur = stage(kind, "%s_%s" % (name, suffix), "%s_%s_Cutters" % (name, suffix), cur, payload)
        last = (suffix, kind, payload, cur.Base)

    def fillet(suffix, items, r, convex=True):
        kept, dropped, gone = select(cur.Shape, items, r, convex)
        if kept:
            add(suffix, "fillet", (kept, r))
        log("%s R%.1f: %d rounded, %d fail, %d already taken by earlier rounds" % (suffix, r, len(kept), len(dropped), len(gone)))
        return dropped

    sharp, concave_sharp = [], []
    if name == "USBC_Cartridge":
        major, ridge = classify_cartridge()
        print("%s: major %d ridge %d" % (name, len(major), len(ridge)), flush=True)
        bad_m = fillet("D", major, R_MAJOR)
        bad_r = fillet("C", ridge + bad_m, R_RIDGE)
        sharp = fillet("C2", bad_r, R_SMALL)
    else:
        concave, major, ridge = classify(name)
        print("%s: concave %d major %d ridge %d" % (name, len(concave), len(major), len(ridge)), flush=True)
        concave_sharp = fillet("A04", fillet("A15", concave, R_MAJOR, False), R_RIDGE, False)
        # flared cutters on closed loops of ridge edges lying on an axis plane
        byplane = {}
        for e in ridge:
            b = e.BoundBox
            for ax, ln, v in ((0, b.XLength, b.XMin), (1, b.YLength, b.YMin), (2, b.ZLength, b.ZMin)):
                if ln < 1e-6:
                    byplane.setdefault((ax, round(v, 3)), []).append(e)
                    break
        flares = []
        sh = cur.Shape
        for (ax, v), es in byplane.items():
            for ch in Part.sortEdges(es):
                W = Part.Wire(ch)
                if not W.isClosed():
                    continue
                wb = W.BoundBox
                wb.enlarge(1.0)
                cand = [e for e in sh.Edges if wb.intersect(e.BoundBox) and (e.BoundBox.XLength, e.BoundBox.YLength, e.BoundBox.ZLength)[ax] < 1e-6
                        and abs((e.BoundBox.XMin, e.BoundBox.YMin, e.BoundBox.ZMin)[ax] - v) < 1e-6 and W.distToShape(Part.Vertex(mid(e)))[0] < 1.0]
                ws = [x for x in (Part.Wire(c) for c in Part.sortEdges(cand)) if x.isClosed()]
                try:
                    f = flare(ws[0], sh, ax) if len(ws) == 1 else None
                except Part.OCCError:                  # the sweep fails on some loops; their edges go to stage C
                    f = None
                if f is not None:
                    flares.append(f)
        if flares:
            add("B", "cut", flares)
        rest = [e for e in ridge if on_edge(cur.Shape, e)]   # the edges of a flared loop are gone: its cutter rounded them
        log("B: %d flared loops; %d ridge edges left" % (len(flares), len(rest)))
        bad_m = fillet("D", major, R_MAJOR)
        sharp = fillet("C", rest + bad_m, R_RIDGE)

    # edge cutters for the convex 90° edges no fillet could round
    sh = cur.Shape
    cutters, not_cut = [], 0
    for e0 in sharp:
        for i in on_edge(sh, e0):
            e = sh.Edges[i - 1]
            fs = sh.ancestorsOfType(e, Part.Face)
            try:
                n1, n2 = normals(fs, mid(e))
                if len(fs) != 2 or abs(n1.dot(n2)) > 1e-3:
                    raise ValueError("not a 90° edge")
                c = edge_cutter(sh, e, R_RIDGE if name != "USBC_Cartridge" else R_SMALL)
                if c.Volume > 1e-6:
                    cutters.append(c)
            except Exception:
                not_cut += 1
    if cutters:
        test = sh.copy().cut(Part.makeCompound(cutters))
        if test.isValid() and len(test.Solids) == len(sh.Solids) and strict_ok(test):
            add("E", "cut", cutters)
        else:
            log("E: the edge cutters together fail; dropped")
            cutters = []
    log("E: %d edge cutters; left sharp: %d convex, %d concave" % (len(cutters), not_cut, len(concave_sharp)))
    if name != "USBC_Cartridge":                       # F: sweep up the convex edges still sharp on the result
        left = sharp_convex(cur.Shape, name)
        log("F: %d convex edges still sharp" % len(left))
        if left:
            left = fillet("F", left, R_RIDGE)          # no R0.2 fallback: a fillet there crashed FreeCAD on the riser
        log("F: left sharp: %d convex" % len(left))
    if last is None:
        raise RuntimeError("%s: nothing to round" % name)

    # the newest feature is the result: recreate it under the name <part>_Rounded
    suffix, kind, payload, base = last
    d.removeObject(cur.Name)
    if kind == "cut":
        d.removeObject("%s_%s_Cutters" % (name, suffix))
    cur = stage(kind, name + "_Rounded", "%s_%s_Cutters" % (name, suffix), base, payload)
    group.addObject(cur)
    print("%s_Rounded: valid %s strict %s vol %.1f -> %.1f (%.0fs)" % (
        name, cur.Shape.isValid(), strict_ok(cur.Shape), src.Shape.Volume, cur.Shape.Volume, time.time() - t0), flush=True)
    return cur


def build_all():
    for n in MOUNT_PARTS + ["USBC_Cartridge"]:
        build(n)
    d.save()


if os.environ.get("BUILD_PARTS"):                     # headless run from build_rounding.sh
    import traceback
    for part in os.environ["BUILD_PARTS"].split():
        try:
            build(part)
        except Exception:
            traceback.print_exc()                      # freecadcmd prints only the message
            raise
        d.save()                                       # after each part, so a later failure keeps the finished ones
    print("BUILD DONE", flush=True)
