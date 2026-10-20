# Builds the rounding of every printed part as native features in DeskMount.FCStd.
#   cad/build_rounding.sh MountBody           headless, logs to cad/out/build_rounding.log (close the model in the GUI
#                                             first, or reload it after); a wall takes 40-50 minutes
#   in the GUI: exec(open("cad/rounding.py").read()); build("CartRail_Lid")   (small parts only: a long GUI call times out)
# Each part gets a chain of features ending in "<part>_Rounded" (group Rounding). Each stage stores the shape it
# computed (Part::Feature): run build() again for a part after editing it.
#
# Edge rules. Mount parts: R1.5 if both faces lie on the part's bounding-box planes ("major"), else R0.4 ("ridge").
# Concave edges get R1.5, or R0.4 where R1.5 fails; on the walls (Wall_* or MountBody below the riser) only the cell
# corners (along X). The edges of a gusset's sloped face are majors. Edges that touch
# another mount part away from their ends are skipped so the joins stay flush; mount_fuse.py rounds some joins after the fuse. The cartridge groove zone and detent-hole rims are skipped.
# Cartridge: R1.5 where both faces lie on the outer planes of the body or tongues, else R0.4, then R0.2 where R0.4
# fails. Breakaway ties, detent balls and concave edges are left as modelled.
#
# Chain (each a Part::Feature with the computed shape): _A fillet (R1.5: concave edges and majors in one feature) -> _B cut (flared cutters: an R0.4 lip on
# every closed loop of ridge edges on an axis plane, i.e. the cell mouths) -> _C fillet (R0.4: the ridges left,
# the edges that failed at R1.5, and the sharp convex edges the R1.5 rounds create) -> _E cut (edge cutters for
# the convex edges no fillet can round, e.g. where the ribs meet the rails) -> _F fillet (R0.4 on convex edges
# still sharp, if any). <part>_Rounded is a Part::Compound of the last one. A fixed fillet list cannot fall back per
# edge at recompute, so build() tests the edges here, on blocks of the part in parallel workers (cad/round_check.py),
# and moves the edges that fail into the next stage. Each stage's whole-part check is the stage's own shape.
import importlib.util
import json
import math
import os
import subprocess
import time

import FreeCAD as App
import Part

V = App.Vector
ROOT = "/Users/tom/projects/fun/macbook-mount"
R_MAJOR, R_RIDGE, R_SMALL, SHARP = 1.5, 0.4, 0.2, 0.985
XL, XF = -11.493, 9.248
MOUNT_PARTS = ["MountBody", "CartRail_Lid", "CartRail_Feet"]       # MountBody: cad/mount_body.py
d = App.getDocument("DeskMount") if "DeskMount" in App.listDocuments() else App.openDocument(ROOT + "/DeskMount.FCStd")
_spec = importlib.util.spec_from_file_location("round_check", ROOT + "/cad/round_check.py")
rc = importlib.util.module_from_spec(_spec)          # by path: cad/ on sys.path breaks the model's FeaturePython modules
_spec.loader.exec_module(rc)
mid, normals, strict_ok, on_edge, round_area, fillet_ok = rc.mid, rc.normals, rc.strict_ok, rc.on_edge, rc.round_area, rc.fillet_ok
CACHE_FILE = ROOT + "/cad/out/rounding_cache.json"
try:                                                   # per stage: the edges that rounded and failed last time
    CACHE = {} if os.environ.get("ROUND_NOCACHE") else json.load(open(CACHE_FILE))
except Exception:
    CACHE = {}


def ekey(e):
    """An edge's cache key: its middle point and length, to 0.01 mm. Same geometry, same key, run after run."""
    p = mid(e)
    return "%.2f %.2f %.2f %.2f" % (p.x, p.y, p.z, e.Length)


FC = os.environ.get("FREECADCMD", "/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd")
WORKERS = int(os.environ.get("ROUND_WORKERS", max(1, min(8, (os.cpu_count() or 2) // 2))))


# ---------------------------------------------------------------- edge rules
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


def other_parts(name):
    """(bounding box, [(face bound box, face)]) of the other mount parts, for touches_other."""
    out = []
    for o in d.getObject("Mount_Fused").Shapes:
        if o.Name != name:
            b = o.Shape.BoundBox
            b.enlarge(0.05)
            fs = []
            for f in o.Shape.Faces:
                fb = f.BoundBox
                fb.enlarge(0.05)
                fs.append((fb, f))
            out.append((b, fs))
    return out


def touches_other(e, p, obox):
    """True if another part touches the edge away from its ends (within 0.5 mm of an end does not count). Such an edge
    is a join, or partly one, and stays sharp: a round there would leave a groove inside the join. An edge that touches
    another part only at an end vertex is rounded. Only the faces near the edge are measured: a distance to a whole
    part made classify() take 16 minutes on MountBody."""
    L = e.Length
    if L > 1.2:
        inner = e.Curve.toShape(e.getParameterByLength(0.5), e.getParameterByLength(L - 0.5))
    else:
        inner = Part.Vertex(p)
    ib = inner.BoundBox
    for b, fs in obox:
        if not b.intersect(ib):
            continue
        for fb, f in fs:
            if fb.intersect(ib) and inner.distToShape(f)[0] < 0.02:
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
        if n1.dot(n2) > SHARP or rc.concave(sh, e, fs, p, n1, n2) or touches_other(e, p, obox):
            continue
        out.append(e)
    return out


def in_walls(name, p):
    """The side walls below the riser: Wall_* parts, or that zone of MountBody. Their concave rounds are the cell
    corners along X only; the corners where the cells meet the 2.4 mm skins (about 460 edges) stay sharp, as on the
    separate walls before MountBody."""
    if name.startswith("Wall_"):
        return True
    return name == "MountBody" and p.z < 228.0 and (p.x <= XL + 0.05 or p.x >= XF - 0.05)


def gusset_slope(f):
    """A gusset's sloped face (a plane sloped in XZ, under DeskPlate's overhang: RearStop's diamond cells have such
    faces too): its edges get R1.5, as on the separate Gussets part. Not 45 degrees since the gussets reach Z 235."""
    b = f.BoundBox
    if not isinstance(f.Surface, Part.Plane) or b.XMin < 17.2 or b.ZMin < 234.9:
        return False
    n = f.Surface.Axis
    return abs(n.y) < 1e-6 and abs(n.x) > 0.1 and abs(n.z) > 0.1


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
        if rc.concave(shape, e, fs, p, n1, n2):
            if not in_walls(name, p) or (isinstance(e.Curve, Part.Line) and abs(e.tangentAt(e.FirstParameter).x) > 0.99):
                concave.append(e)                      # on the walls only cell corners (straight, along X): not the
                                                       # short curves where the cells' lips meet their corners
            continue
        if (on_planes(fs[0], planes) and on_planes(fs[1], planes)) or any(gusset_slope(f) for f in fs):
            major.append(e)
        else:
            ridge.append(e)
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
        if n1.dot(n2) > SHARP or rc.concave(shape, e, fs, p, n1, n2):
            continue
        (major if on_planes(fs[0], planes) and on_planes(fs[1], planes) else ridge).append(e)
    return major, ridge


# ---------------------------------------------------------------- edge selection
_SEQ = [0]


def worker(sh, groups, r, convex, tag, result=None, single=False):
    """Start a freecadcmd worker (cad/round_check.py) on sh: bisect the edge groups, or (result: a BREP path) fillet
    them all and write the shape. Returns (process, file base)."""
    tmp = os.path.join(ROOT, "cad", "out", "blocks")
    os.makedirs(tmp, exist_ok=True)
    _SEQ[0] += 1
    base = os.path.join(tmp, "%s_%d" % (tag, _SEQ[0]))
    sh.exportBrep(base + ".brep")
    for f in (base + ".json", result):
        if f and os.path.exists(f):
            os.remove(f)
    json.dump({"brep": base + ".brep", "groups": groups, "r": r, "convex": convex, "out": base + ".json",
               "result": result, "single": single}, open(base + ".job", "w"))
    env = dict(os.environ, ROUND_JOB=base + ".job")
    env.pop("BUILD_PARTS", None)
    return subprocess.Popen([FC, ROOT + "/cad/round_check.py"], env=env, stdout=open(base + ".log", "w"),
                            stderr=subprocess.STDOUT), base


def run_blocks(jobs, r, tag):
    """Bisect each block (crop shape, edge groups, flags, label) in parallel workers. Returns, per job, the dropped
    group numbers. A worker that crashes (OpenCascade can segfault in a fillet) is split in two and run again; a
    single group that crashes is dropped. No fillet runs in this process, so a crash cannot end the build."""
    pend = [(k, list(range(len(jobs[k][1])))) for k in range(len(jobs))]   # (job, its group numbers to test)
    running, out = {}, [[] for _ in jobs]
    t0 = time.time()
    while pend or running:
        while pend and len(running) < WORKERS:
            k, gids = pend.pop(0)
            sh, groups, convex, label = jobs[k]
            pr, base = worker(sh, [groups[g] for g in gids], r, [convex[g] for g in gids], tag)
            running[pr] = (k, gids, base)
        time.sleep(1)
        for pr, (k, gids, base) in list(running.items()):
            if pr.poll() is None:
                continue
            del running[pr]
            sh, groups, convex, label = jobs[k]
            try:
                res = json.load(open(base + ".json"))
                if res["edges"] != len(sh.Edges):
                    raise ValueError("edge count changed in the BREP round trip")
                out[k] += [gids[g] for g in res["dropped"]]
                print("   %s: %d edges, %d fail, %d tests (%.0fs, %.0fs in all)" % (
                    label, len(gids), len(res["dropped"]), res["tests"], res["seconds"], time.time() - t0), flush=True)
            except Exception:
                if len(gids) == 1:
                    out[k] += gids
                    print("   %s: an edge crashes the fillet; dropped" % label, flush=True)
                else:
                    h = len(gids) // 2
                    pend += [(k, gids[:h]), (k, gids[h:])]
                    print("   %s: worker crashed (exit %s) on %d edges; split in two" % (label, pr.returncode, len(gids)), flush=True)
    return out


def iso_ok(sh, idx, r, flags):
    """fillet_ok in a worker: False if the fillet fails its checks or crashes."""
    pr, base = worker(sh, [idx], r, list(flags), "whole", single=True)
    pr.wait()
    try:
        return not json.load(open(base + ".json"))["dropped"]
    except Exception:
        print("   whole-part test crashed (exit %s)" % pr.returncode, flush=True)
        return False


def iso_fillet(sh, idx, r, tag):
    """sh.makeFillet(r, edges idx) in a worker; the shape, or None if it fails or crashes."""
    res = os.path.join(ROOT, "cad", "out", "blocks", "%s_result.brep" % tag)
    pr, base = worker(sh, [idx], r, [True], tag, result=res)
    pr.wait()
    if pr.returncode != 0 or not os.path.exists(res):
        return None
    return Part.read(res)


def select(base, items, r, convex=True, whole=True, window=60.0, margin=8.0, tag=None):
    """Split source edges into (kept, dropped, gone): kept ones fillet together at r on base, dropped ones make the
    fillet fail, gone ones no longer exist on base (an earlier round took them). At R1.5, edges where the round cannot
    fit (rc.fits) drop without a test. A large part is tested block by block in parallel workers, in two passes (the
    second shifted half a block, so the edges at the seams sit mid-block), then once on the whole part; a whole-part
    failure falls back to adding block by block. convex: a flag, or a function of the source edge. whole=False skips
    the whole-part test: the caller checks the stage's recomputed feature instead (one whole-part fillet, not two).
    tag: the stage's cache entry (CACHE_FILE). Edges that failed last time drop without a test; when every other
    edge rounded last time, the block tests are skipped and the stage's own check decides."""
    t0 = time.time()
    flag = convex if callable(convex) else (lambda e: convex)
    mapped = [(e, on_edge(base, e)) for e in items]
    gone = [e for e, ii in mapped if not ii]
    mapped = [(e, ii) for e, ii in mapped if ii]
    dropped = []
    if r >= 1.0:
        es = base.Edges
        nofit = [e for e, ii in mapped if not rc.fits(base, es[ii[0] - 1], r)]
        dropped += nofit
        mapped = [(e, ii) for e, ii in mapped if not any(e is x for x in nofit)]
    nofit_n = len(dropped)
    known = CACHE.get(tag) if tag else None
    if known:
        bad, good = set(known["drop"]), set(known["keep"])
        cached = [e for e, ii in mapped if ekey(e) in bad]
        dropped += cached
        mapped = [(e, ii) for e, ii in mapped if ekey(e) not in bad]
        new = sum(ekey(e) not in good for e, _ in mapped)
    print("   select R%.1f: %d edges, %d gone, %d do not fit%s (%.0fs)" % (
        r, len(mapped), len(gone), nofit_n, ", %d failed last time, %d new" % (len(cached), new) if known else "",
        time.time() - t0), flush=True)
    if not mapped:
        return [], dropped, gone
    if known and not new and not whole:                # all as last time: no block tests
        return [e for e, _ in mapped], dropped, gone
    bb = base.BoundBox
    ax = max(range(3), key=lambda i: (bb.XLength, bb.YLength, bb.ZLength)[i])
    lo, hi = (bb.XMin, bb.YMin, bb.ZMin)[ax], (bb.XMax, bb.YMax, bb.ZMax)[ax]

    def crop(sh, a, b):
        box = [bb.XMin - 1, bb.YMin - 1, bb.ZMin - 1, bb.XLength + 2, bb.YLength + 2, bb.ZLength + 2]
        box[ax], box[ax + 3] = a - margin, (b - a) + 2 * margin
        return sh.copy(False).common(Part.makeBox(box[3], box[4], box[5], V(box[0], box[1], box[2])))

    def blocks(start):
        a, out = start, []
        while a < hi:
            out.append((a, min(a + window, hi + 1)))
            a += window
        return out

    def inside(e, a, b):
        return a <= (mid(e).x, mid(e).y, mid(e).z)[ax] < b

    def flags(part):
        return [flag(e) for e, ii in part for _ in ii]

    def bisect_here(sh, part):
        """part: (source edge, indices on base); bisected on sh. Returns the kept part."""
        groups = [(e, on_edge(sh, e)) for e, _ in part]
        groups = [g for g in groups if g[1]]
        drop = run_blocks([(sh, [ii for _, ii in groups], [flag(e) for e, _ in groups], "fallback block")], r, "fb")[0]
        kept = [g for g in range(len(groups)) if g not in drop]
        dropped.extend(groups[g][0] for g in drop)
        ks = [groups[g][0] for g in kept]
        return [x for x in part if any(x[0] is e for e in ks)]

    def bisect_whole(kept, part):
        """Add part's edges to kept while the whole part still fillets; split a list that fails."""
        if not part:
            return kept
        sel = kept + part
        if iso_ok(base, [i for _, ii in sel for i in ii], r, flags(sel)):
            return sel
        if len(part) == 1:
            dropped.append(part[0][0])
            return kept
        h = len(part) // 2
        return bisect_whole(bisect_whole(kept, part[:h]), part[h:])

    big = hi - lo > window + 2 * margin
    # an edge longer than a block is only partly in any crop, where it may pass and then fail on the whole part:
    # it is tested on the whole part, after the blocks
    longs = [(e, ii) for e, ii in mapped if big and e.Length > window]
    if big:                                            # large part: find the failing edges on blocks first
        for k, start in enumerate((lo, lo - window / 2)):   # second pass shifted: seam edges sit mid-block
            jobs, srcs = [], []
            for a, b in blocks(start):
                sh = crop(base, a, b)
                gs = [(e, on_edge(sh, e)) for e, _ in mapped if inside(e, a, b) and not any(e is x for x in dropped)
                      and not any(e is x for x, _ in longs)]
                gs = [g for g in gs if g[1]]
                if gs:
                    jobs.append((sh, [ii for _, ii in gs], [flag(e) for e, _ in gs], "pass %d block %.0f..%.0f" % (k + 1, a, b)))
                    srcs.append([e for e, _ in gs])
            print("   pass %d: %d blocks on %d workers (%.0fs)" % (k + 1, len(jobs), WORKERS, time.time() - t0), flush=True)
            for src, drop in zip(srcs, run_blocks(jobs, r, "r%g_p%d" % (r, k + 1))):
                dropped.extend(src[g] for g in drop)
    full = [(e, ii) for e, ii in mapped if not any(e is x for x in dropped) and not any(e is x for x, _ in longs)]
    if longs:
        t1 = time.time()
        n0 = len(full)
        full = bisect_whole(full, longs)
        print("   %d long edges on the whole part: %d kept (%.0fs)" % (len(longs), len(full) - n0, time.time() - t1), flush=True)
    if not whole:
        return [e for e, _ in full], dropped, gone
    print("   whole-part test: %d edges ..." % len(full), flush=True)
    t1 = time.time()
    ok = iso_ok(base, [i for _, ii in full for i in ii], r, flags(full))
    print("   whole-part test %s (%.0fs)" % ("ok" if ok else "failed", time.time() - t1), flush=True)
    if not ok and big:
        # Bounded fallback: add block by block on the whole part (one whole-part test per block);
        # a block that fails is bisected on a crop of the shape, not on the whole part.
        print("   whole-part fillet failed after block tests; adding block by block", flush=True)
        kept = []
        for a, b in blocks(lo):
            part = [x for x in full if inside(x[0], a, b)]
            if not part:
                continue
            if iso_ok(base, [i for _, ii in kept + part for i in ii], r, flags(kept + part)):
                kept += part
            else:
                part = bisect_here(crop(base, a - window / 2, b + window / 2), part)
                if part and iso_ok(base, [i for _, ii in kept + part for i in ii], r, flags(kept + part)):
                    kept += part
                elif part:
                    # fails only with the rest of the part: bisect this block's edges on the whole part, with the
                    # kept blocks fixed (dropping the whole block lost 460 of 614 edges in one run)
                    n0 = len(kept)
                    kept = bisect_whole(kept, part)
                    print("   block %.0f..%.0f: %d of %d kept on the whole part" % (a, b, len(kept) - n0, len(part)), flush=True)
            print("   block %.0f..%.0f added: %d kept so far" % (a, b, len(kept)), flush=True)
        full = kept
    elif not ok:
        print("   whole-part fillet failed; bisecting on the part", flush=True)
        full = bisect_here(base, full)
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
        if o.Name.startswith(name + "_") and o.Name[len(name) + 1:] in ("A", "A15", "A04", "B", "B_Cutters", "C", "C2", "D", "E", "E_Cutters", "F", "F2", "R15", "Rounded"):
            d.removeObject(o.Name)


def stage(kind, name, tool_name, base, payload):
    """Create one stage of the chain on base, as a Part::Feature holding the shape computed here. A Part::Fillet with
    the same edges recomputed differently from the tested makeFillet (twice it would not recompute where the test
    passed), so the stored shape is the tested one; the chain does not recompute with the model: run build() again."""
    sh = base.Shape
    try:
        if kind == "fillet":
            kept, r = payload
            res = iso_fillet(sh, sorted({i for e in kept for i in on_edge(sh, e)}), r, name)   # in a worker: a crash
            if res is None:                                                                     # ends only it
                raise RuntimeError("%s: the fillet failed or crashed" % name)
        else:
            tool = d.getObject(tool_name) or d.addObject("Part::Feature", tool_name)
            tool.Shape = Part.makeCompound(payload)
            if tool.ViewObject:
                tool.ViewObject.Visibility = False
            res = sh.cut(tool.Shape)
    except Part.OCCError as ex:
        raise RuntimeError("%s failed: %s" % (name, ex))
    if res.isNull() or not res.isValid():
        raise RuntimeError("%s is not valid" % name)
    o = d.addObject("Part::Feature", name)
    o.Shape = res
    if o.ViewObject:
        o.ViewObject.Visibility = False
    return o


def build(name):
    """Build the chain stage by stage: each stage is tested on the recomputed shape of the feature before it."""
    t0 = time.time()
    clear(name)
    src = d.getObject(name)
    cur = src
    if not strict_ok(src.Shape):                      # every fillet test fails on a self-intersecting base
        raise RuntimeError("%s fails the strict check before rounding; fix its source first" % name)
    print("  %s base: strict ok (%.0fs)" % (name, time.time() - t0), flush=True)
    last = None                                        # (suffix, kind, payload) of the newest feature

    def log(msg):
        print("  %s (%.0fs)" % (msg, time.time() - t0), flush=True)

    def add(suffix, kind, payload):
        nonlocal cur, last
        cur = stage(kind, "%s_%s" % (name, suffix), "%s_%s_Cutters" % (name, suffix), cur, payload)
        last = (suffix, kind, payload)

    def fillet(suffix, items, r, convex=True):
        """Block-test the edges, create the stage, and check its recomputed shape (the one whole-part fillet of the
        stage). If that check fails, remove it and test on the whole part (select's fallback), then create it again."""
        nonlocal cur, last
        base = cur.Shape
        tag = "%s %s R%.1f" % (name, suffix, r)
        kept, dropped, gone = select(base, items, r, convex, whole=False, tag=tag)
        if kept:
            prev = (cur, last)
            flag = convex if callable(convex) else (lambda e: convex)
            t = time.time()
            try:
                add(suffix, "fillet", (kept, r))
                idx = [(i, flag(e)) for e in kept for i in on_edge(base, e)]
                ok = rc.result_ok(base, cur.Shape, [i for i, _ in idx], r, [f for _, f in idx])
            except RuntimeError:
                ok = False
            log("%s: feature with %d edges %s" % (suffix, len(kept), "ok" if ok else "fails the checks"))
            if not ok:
                if d.getObject("%s_%s" % (name, suffix)):
                    d.removeObject("%s_%s" % (name, suffix))
                cur, last = prev
                kept, more, _ = select(base, kept, r, convex, whole=True)    # no cache: test them all
                dropped += more
                if kept:
                    try:
                        add(suffix, "fillet", (kept, r))
                    except RuntimeError as ex:      # should not happen: the stage is the shape the tests passed
                        log("%s: %s; the stage is left out" % (suffix, ex))
                        cur, last = prev
                        dropped += kept
                        kept = []
        log("%s R%.1f: %d rounded, %d fail, %d already taken by earlier rounds" % (suffix, r, len(kept), len(dropped), len(gone)))
        CACHE[tag] = {"keep": [ekey(e) for e in kept], "drop": [ekey(e) for e in dropped]}
        try:
            json.dump(CACHE, open(CACHE_FILE, "w"))
        except Exception as ex:
            log("cache not saved: %s" % ex)
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
        conc = {id(e) for e in concave}
        isconvex = lambda e: id(e) not in conc         # sharp_convex edges are new objects: convex
        bad_a = fillet("A", concave + major, R_MAJOR, isconvex)   # one R1.5 stage: concave and major edges
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
            test = sh.copy().cut(Part.makeCompound(flares))
            if not (test.isValid() and len(test.Solids) == len(sh.Solids)):
                # one cut with all the flares can be invalid where each alone is fine: keep those that cut cleanly in
                # turn; the edges of the others stay ridge edges and go to stage C
                kept, t = [], sh.copy()
                for f in flares:
                    nt = t.cut(f)
                    if nt.isValid() and len(nt.Solids) == len(sh.Solids):
                        kept.append(f)
                        t = nt
                log("B: the flares together fail; %d of %d kept one by one" % (len(kept), len(flares)))
                flares = kept
        if flares:
            add("B", "cut", flares)
        sh = cur.Shape                                 # once: each .Shape is a new object, and on_edge caches by object
        rest = [e for e in ridge if on_edge(sh, e)]    # the edges of a flared loop are gone: its cutter rounded them
        log("B: %d flared loops; %d ridge edges left" % (len(flares), len(rest)))
        # one R0.4 stage: the ridges left, the edges that failed at R1.5, and the sharp convex edges the R1.5 rounds
        # created (such as the end arcs of the cell-corner rounds)
        sh = cur.Shape
        taken = {i for e in rest + bad_a for i in on_edge(sh, e)}
        arcs = [e for e in sharp_convex(sh, name) if not taken & set(on_edge(sh, e))]
        log("C: %d sharp convex edges from the R1.5 rounds" % len(arcs))
        bad_c = fillet("C", rest + bad_a + arcs, R_RIDGE, isconvex)
        concave_sharp = [e for e in bad_c if id(e) in conc]
        sharp = [e for e in bad_c if id(e) not in conc]

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
        sh = cur.Shape
        failed = {i for e in sharp for i in on_edge(sh, e)}   # stage C could not round these: no second try
        left = [e for e in sharp_convex(sh, name) if not failed & set(on_edge(sh, e))]
        log("F: %d convex edges still sharp" % len(left))
        if left:
            left = fillet("F", left, R_RIDGE)          # no R0.2 fallback: a fillet there crashed FreeCAD on the riser
        log("F: left sharp: %d convex" % len(left))
    if last is None:
        raise RuntimeError("%s: nothing to round" % name)

    # <part>_Rounded: a compound of the newest feature (recomputing that feature again under a new name would cost
    # one more whole-part fillet)
    out = d.addObject("Part::Compound", name + "_Rounded")
    out.Links = [cur]
    if out.ViewObject:
        out.ViewObject.Visibility = False
    group.addObject(out)
    d.recompute()
    print("%s_Rounded: valid %s strict %s vol %.1f -> %.1f (%.0fs)" % (
        name, out.Shape.isValid(), strict_ok(out.Shape), src.Shape.Volume, out.Shape.Volume, time.time() - t0), flush=True)
    return out


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
