# Run inside the FreeCAD GUI, by fc_evidence_export.py. Re-anchors the DFM_Clearances dimensions by geometry, because
# TechDraw stores dimension references as edge indices and the indices change whenever the model changes.
# - Lid-side dimensions are the mirror (view X -> -X) of their feet-side partner.
# - Other dimensions are found as the pair of parallel visible edges at the target spacing, inside an X window.
import FreeCAD as App

d = App.getDocument("DeskMount")
TOL = 0.03                                     # view units (scaled mm)


def ends(e):
    return [(p.x, p.y) for p in (e.Vertexes[0].Point, e.Vertexes[-1].Point)]


def visible(view):
    return {"Edge%d" % i: e for i, e in enumerate(view.getVisibleEdges())}


def mirror(bad, good):
    """Point dimension `bad` at the X-mirror of the edges `good` references, in the same view."""
    g = d.getObject(good)
    view, names = g.References2D[0][0], g.References2D[0][1]
    edges = visible(view)
    refs = []
    for n in names:
        want = sorted((-x, y) for x, y in ends(edges[n]))
        hit = [m for m, e in edges.items() if all(abs(a[0] - b[0]) < TOL and abs(a[1] - b[1]) < TOL for a, b in zip(sorted(ends(e)), want))]
        if not hit:
            raise RuntimeError("no mirror of %s.%s for %s" % (view.Name, n, bad))
        refs.append(hit[0])
    b = d.getObject(bad)
    b.Type = g.Type
    b.References2D = [(view, tuple(refs))]
    return b


def spacing(dim, view_name, mm, xwin, horizontal=True):
    """Point `dim` at the two parallel edges (horizontal or vertical in the view) `mm` apart, overlapping inside xwin."""
    view = d.getObject(view_name)
    edges = visible(view)
    target = mm * view.Scale
    lines = []
    for n, e in edges.items():
        (x0, y0), (x1, y1) = ends(e)
        if horizontal and abs(y0 - y1) < 1e-6 and abs(x1 - x0) > 0.5:
            lo, hi = sorted((x0, x1))
            if hi > xwin[0] and lo < xwin[1]:
                lines.append((n, y0, lo, hi))
        if not horizontal and abs(x0 - x1) < 1e-6 and abs(y1 - y0) > 0.5:
            lo, hi = sorted((y0, y1))
            lines.append((n, x0, lo, hi))
    best = None
    for i, a in enumerate(lines):
        for b in lines[i + 1:]:
            if abs(abs(a[1] - b[1]) - target) < TOL * 3:
                ov = min(a[3], b[3]) - max(a[2], b[2])
                if best is None or ov > best[0]:
                    best = (ov, a[0], b[0])
    if best is None:
        raise RuntimeError("no edge pair %.2f mm apart in %s for %s" % (mm, view_name, dim))
    o = d.getObject(dim)
    o.Type = "DistanceY" if horizontal else "DistanceX"
    o.References2D = [(view, (best[1], best[2]))]
    return o


MIRRORS = {"DFM_Dim003": "DFM_Dim002", "DFM_Dim006": "DFM_Dim005", "DFM_Dim008": "DFM_Dim007", "DFM_Dim013": "DFM_Dim012"}
for bad, good in MIRRORS.items():
    mirror(bad, good)
# D-D (Z 67): squeeze pad front face to the wall's rear end (Measure M_10 / M_11)
spacing("DFM_Dim009", "DFM_Sec_Z67", 6.775, (10, 70))
spacing("DFM_Dim010", "DFM_Sec_Z67", 6.775, (-70, -10))
# E-E (Y 332): tongue engagement, tongue bottom (floor top, Z 2.15) to groove top (Z 60.5)
spacing("DFM_Dim011", "DFM_Sec_Y332", 58.35, (25, 50))
for o in d.getObject("DFM_Clearances").Views:
    if o.TypeId == "TechDraw::DrawViewDimension":
        o.FormatSpec = "%.2f"
        o.FormatSpecOverTolerance = o.FormatSpecUnderTolerance = "%.2f"
d.recompute()
for o in d.getObject("DFM_Clearances").Views:
    if o.TypeId == "TechDraw::DrawViewDimension":
        print(o.Name, o.References2D[0][0].Name, o.References2D[0][1], round(o.getRawValue(), 3))
