# Fillet tests for cad/rounding.py, with no document: rounding.py imports this module, and it also runs as a block
# worker (freecadcmd with ROUND_JOB=<job.json>), so the block tests of a large part run in parallel processes.
#   job.json: {"brep": crop.brep, "groups": [[edge index, ...], ...], "r": 1.5, "convex": [flag per group], "out": result.json}
#   result.json: {"kept": [group number, ...], "dropped": [...], "tests": n, "seconds": t}
import json
import math
import os
import time

import FreeCAD as App
import Part

V = App.Vector
SLOW = 120                                             # seconds: log any fillet test slower than this


def mid(e):
    if e.Degenerated:                                  # a fillet can leave a zero-length seam edge with no curve
        return e.Vertexes[0].Point
    return e.valueAt((e.FirstParameter + e.LastParameter) / 2)


def normals(fs, p):
    return [f.normalAt(*f.Surface.parameter(p)) for f in fs]


def strict_ok(s, window=60.0, margin=8.0):
    """Strict check (BOP self-intersection). On a large part it takes over an hour on the whole shape, so check
    overlapping crops along the longest axis instead; the fused mount gets one whole-shape check in recompute_mount."""
    bb = s.BoundBox
    ax = max(range(3), key=lambda i: (bb.XLength, bb.YLength, bb.ZLength)[i])
    lo, hi = (bb.XMin, bb.YMin, bb.ZMin)[ax], (bb.XMax, bb.YMax, bb.ZMax)[ax]
    try:
        if hi - lo <= window + 2 * margin:
            s.check(True)
            return True
        a = lo
        while a < hi:
            box = [bb.XMin - 1, bb.YMin - 1, bb.ZMin - 1, bb.XLength + 2, bb.YLength + 2, bb.ZLength + 2]
            box[ax], box[ax + 3] = a - margin, window + 2 * margin
            c = s.common(Part.makeBox(box[3], box[4], box[5], V(box[0], box[1], box[2])))
            if not c.isValid():
                return False
            c.check(True)
            a += window
        return True
    except Exception:
        return False


# ---------------------------------------------------------------- edge mapping
_EDGES = []                                            # (shape, [(edge, bound box, curve)]) for the last few shapes


def edge_list(sh):
    """sh.Edges with bound boxes and curves, kept for the last 4 shapes: sh.Edges builds new objects on every call."""
    for s, es in _EDGES:
        if s is sh:
            return es
    es = []
    for e in sh.Edges:
        try:
            c = None if e.Degenerated else e.Curve
        except Exception:
            c = None
        es.append((e, e.BoundBox, c))
    _EDGES.insert(0, (sh, es))
    del _EDGES[4:]
    return es


def near(e, c, q, tol=1e-4):
    """True if point q lies on edge e (curve c): project onto the curve, not BRepExtrema (10x per edge was the main
    cost of on_edge)."""
    if c is None:
        return e.distToShape(Part.Vertex(q))[0] < tol
    try:
        u = c.parameter(q)
        a, b = e.FirstParameter, e.LastParameter
        if c.isPeriodic():
            p = c.period()
            while u < a - 1e-9:
                u += p
            while u > b + 1e-9:
                u -= p
        if a - 1e-9 <= u <= b + 1e-9:
            return (e.valueAt(u) - q).Length < tol
        return min((e.valueAt(a) - q).Length, (e.valueAt(b) - q).Length) < tol
    except Exception:
        return e.distToShape(Part.Vertex(q))[0] < tol


def samples(e):
    return [e.valueAt(e.FirstParameter + f * (e.LastParameter - e.FirstParameter)) for f in (0.1, 0.3, 0.5, 0.7, 0.9)]


def on_edge(sh, e0):
    """Indices (1-based) of the edges of sh that run along the source edge e0: trimmed pieces, longer edges, overlaps."""
    bb = e0.BoundBox
    bb.enlarge(1e-3)
    try:
        c0 = None if e0.Degenerated else e0.Curve
    except Exception:
        c0 = None
    p0 = samples(e0)
    out = []
    for i, (e, b, c) in enumerate(edge_list(sh)):
        if not b.intersect(bb) or e.Length < 0.02:
            continue
        if sum(near(e0, c0, q) for q in samples(e)) >= 2 or sum(near(e, c, q) for q in p0) >= 2:
            out.append(i + 1)
    return out


def into_face(f, p, n, t):
    """Unit direction in face f (normal n at p) at right angles to the edge tangent t, pointing into the face; None if
    neither side is in the face's domain."""
    v = n.cross(t)
    if v.Length < 1e-9:
        return None
    v.normalize()
    for w in (v, -v):
        try:
            if f.isPartOfDomain(*f.Surface.parameter(p + w * 0.02)):
                return w
        except Exception:
            return None
    return None


def concave(sh, e, fs, p, n1, n2):
    """True for an inside corner: face 1 runs from the edge to the outer side of face 2 (n2). Geometric, with
    sh.isInside only as a fallback: isInside builds a classifier of the whole solid on every call (classify() took
    16 minutes on MountBody)."""
    try:
        t = e.tangentAt(e.Curve.parameter(p))
        v1 = into_face(fs[0], p, n1, t)
        v2 = into_face(fs[1], p, n2, t)
        if v1 is not None and v2 is not None:
            a, b = v1.dot(n2), v2.dot(n1)
            if abs(a) > 1e-3 and abs(b) > 1e-3 and (a > 0) == (b > 0):
                return a > 0
    except Exception:
        pass
    return sh.isInside(p - n1 * 0.03 + n2 * 0.03, 1e-7, True)


# ---------------------------------------------------------------- fillet tests
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


def fits(sh, e, r):
    """False if a round of radius r cannot fit on edge e: on a plane face, the round's tangent line (r cot(theta/2)
    from the edge) falls off the face at the edge's middle, as on the 2.4 mm ribs and skins at R1.5. Such an edge
    goes to the next stage without a fillet test. Curved faces and unclear cases count as fitting."""
    fs = sh.ancestorsOfType(e, Part.Face)
    if len(fs) != 2 or e.Degenerated:
        return True
    try:
        p = mid(e)
        t = e.tangentAt((e.FirstParameter + e.LastParameter) / 2)
        n1, n2 = normals(fs, p)
        theta = math.pi - math.acos(max(-1.0, min(1.0, n1.dot(n2))))
        if theta < 0.1 or theta > math.pi - 0.1:
            return True
        dt = r / math.tan(theta / 2)
        for f, n in zip(fs, (n1, n2)):
            if not isinstance(f.Surface, Part.Plane):
                continue
            v = n.cross(t)
            v.normalize()
            if not f.isPartOfDomain(*f.Surface.parameter(p + v * 0.05)):
                v = -v
                if not f.isPartOfDomain(*f.Surface.parameter(p + v * 0.05)):
                    continue
            if not f.isPartOfDomain(*f.Surface.parameter(p + v * (dt * 0.98))):
                return False
        return True
    except Exception:
        return True


def fillet_ok(sh, edges, r, convex=True):
    """Fillet edges (indices on sh) at r on a copy of sh and check the result (result_ok). convex: one flag for all
    edges, or a list of flags, one per edge: a stage can round convex and concave edges together."""
    t = time.time()
    r_ok = _fillet_ok(sh, edges, r, convex)
    if time.time() - t > SLOW:
        print("   slow fillet test: %d edges on a %.0f mm part, %s (%.0fs)" % (
            len(edges), max(sh.BoundBox.XLength, sh.BoundBox.YLength, sh.BoundBox.ZLength), "ok" if r_ok else "fail",
            time.time() - t), flush=True)
    return r_ok


def _fillet_ok(sh, edges, r, convex=True):
    # Test on a copy: OpenCascade operations can raise the tolerances of their input shape in place. The topology
    # holds the tolerances, so copy(False) (no geometry copy) is enough.
    sh = sh.copy(False)
    try:
        n = sh.makeFillet(r, [sh.Edges[i - 1] for i in edges])
        return result_ok(sh, n, edges, r, convex)
    except Exception:
        return False


def result_ok(sh, n, edges, r, convex=True):
    """Checks on the result n of rounding edges (indices on sh) at r, cheap ones first and the strict check last.
    Besides validity, the volume change must match the rounds: a fillet can return a valid shape that fills a whole
    cell. A round of radius r along an edge of length L removes (convex) or adds (concave) round_area * L; the net
    volume removed must lie between -2x the concave rounds and 2x the convex rounds."""
    try:
        if not (n.isValid() and len(n.Solids) == len(sh.Solids)):
            return False
        if max(v.Tolerance for v in n.Vertexes) > 0.01:   # a valid round on a rail left a 0.38 mm vertex; it broke the fuse
            return False
        flags = convex if isinstance(convex, (list, tuple)) else [convex] * len(edges)
        es = sh.Edges
        add = cut = 0.0
        for i, cv in zip(edges, flags):
            e = es[i - 1]
            a = round_area(sh, e, r) * e.Length
            if cv:
                cut += a
            else:
                add += a
        dv = sh.Volume - n.Volume
        if not -2.0 * add - 0.01 <= dv <= 2.0 * cut + 0.01:
            return False
        return strict_ok(n)
    except Exception:
        return False


def bisect(sh, groups, r, convex=True, order=None):
    """Groups (lists of edge indices on sh) that fillet together at r: add while the whole list still fillets, split a
    list that fails. convex: one flag, or one per group. Returns (kept, dropped, tests) as group numbers."""
    dropped, tests = [], [0]
    flag = convex if isinstance(convex, (list, tuple)) else [convex] * len(groups)

    def keep(gs, kept):
        if not gs:
            return kept
        tests[0] += 1
        sel = kept + gs
        if fillet_ok(sh, [i for g in sel for i in groups[g]], r, [flag[g] for g in sel for _ in groups[g]]):
            return kept + gs
        if len(gs) == 1:
            dropped.append(gs[0])
            return kept
        h = len(gs) // 2
        return keep(gs[h:], keep(gs[:h], kept))

    kept = keep(list(order if order is not None else range(len(groups))), [])
    return kept, dropped, tests[0]


if os.environ.get("ROUND_JOB"):                       # worker: a crash here (OpenCascade can segfault) ends only it
    job = json.load(open(os.environ["ROUND_JOB"]))
    t0 = time.time()
    sh = Part.read(job["brep"])
    if job.get("result"):                              # fillet mode: the stage's shape, written as BREP
        idx = [i for g in job["groups"] for i in g]
        sh = sh.copy(False)                            # as in the tests: on the shape as read, the same fillet can
        n = sh.makeFillet(job["r"], [sh.Edges[i - 1] for i in idx])   # fail (197 edges: "command not done")
        n.exportBrep(job["result"])
        json.dump({"kept": [], "dropped": [], "tests": 1, "seconds": time.time() - t0, "edges": len(sh.Edges)},
                  open(job["out"], "w"))
    elif job.get("single"):                            # one test of all the groups together, per-edge flags
        idx = [i for g in job["groups"] for i in g]
        ok = fillet_ok(sh, idx, job["r"], job["convex"])
        json.dump({"kept": [], "dropped": [] if ok else [0], "tests": 1, "seconds": time.time() - t0,
                   "edges": len(sh.Edges)}, open(job["out"], "w"))
    else:
        kept, dropped, tests = bisect(sh, job["groups"], job["r"], job["convex"])
        json.dump({"kept": kept, "dropped": dropped, "tests": tests, "seconds": time.time() - t0, "edges": len(sh.Edges)},
                  open(job["out"], "w"))
