# Edge rules shared by round_part.py (headless) and model_fillets.py (in the model).
# R1.5 if both faces lie on the component's bounding-box planes, else R0.4. Concave edges (on the walls only the cell
# corners, along X) get R1.5. Edges touching another mount component are skipped so the joins stay flush. Groove zone
# and detent-hole rims skipped.
import FreeCAD as App

R_MAJOR, R_RIDGE, SHARP = 1.5, 0.4, 0.985
XL, XF = -11.493, 9.248


def mid(e):
    return e.valueAt((e.FirstParameter + e.LastParameter) / 2)


def key(p):
    return (round(p.x, 3), round(p.y, 3), round(p.z, 3))


def skip_zone(p):
    in_x = (XF - 0.05 <= p.x <= XF + 2.6) or (XL - 2.6 <= p.x <= XL + 0.05)
    return in_x and 329.4 <= p.y <= 334.6 and p.z <= 61.8


def classify(d, name):
    """Return (concave, major, ridge): edge midpoints of the part's source shape, by rounding class."""
    shape = d.getObject(name).Shape
    obox = []
    for o in d.getObject("Mount_Fused").Shapes:
        if o.Name != name:
            b = o.Shape.BoundBox
            b.enlarge(0.05)
            obox.append((b, o.Shape))
    bb = shape.BoundBox
    planes = {("x", round(bb.XMin, 2)), ("x", round(bb.XMax, 2)), ("y", round(bb.YMin, 2)), ("y", round(bb.YMax, 2)),
              ("z", round(bb.ZMin, 2)), ("z", round(bb.ZMax, 2))}

    def on_box(f):
        if f.Surface.__class__.__name__ != "Plane":
            return False
        n = f.Surface.Axis
        for ax, comp, val in (("x", n.x, f.BoundBox.XMin), ("y", n.y, f.BoundBox.YMin), ("z", n.z, f.BoundBox.ZMin)):
            if abs(abs(comp) - 1) < 1e-6:
                return (ax, round(val, 2)) in planes
        return False

    def touches_other(e, p):
        """True if the edge touches another component anywhere: midpoint, either end, or along its length."""
        probes = [p] + [v.Point for v in e.Vertexes]
        for b, s in obox:
            if any(b.isInside(q) for q in probes) or b.intersect(e.BoundBox):
                if e.distToShape(s)[0] < 0.02:
                    return True
        return False

    major, ridge, concave = [], [], []
    emap = {}
    for f in shape.Faces:
        for fe in f.Edges:
            emap.setdefault(fe.hashCode(), []).append(f)
    for e in shape.Edges:
        fs = emap.get(e.hashCode(), [])
        if len(fs) != 2 or e.Length < 0.05:
            continue
        p = mid(e)
        if skip_zone(p) or any(f.Surface.__class__.__name__ == "Cylinder" and abs(f.Surface.Radius - 1.3265) < 0.01 for f in fs):
            continue
        try:
            n1 = fs[0].normalAt(*fs[0].Surface.parameter(p)); n2 = fs[1].normalAt(*fs[1].Surface.parameter(p))
        except Exception:
            continue
        if n1.dot(n2) > SHARP:
            continue
        eps = 0.03
        if touches_other(e, p):
            continue                                   # join with another component
        if shape.isInside(p - n1 * eps + n2 * eps, 1e-7, True):
            if not name.startswith("Wall_") or abs(e.tangentAt(e.FirstParameter).x) > 0.99:
                concave.append(p)                      # sharp internal corner; on the walls only cell corners (along X)
            continue
        (major if on_box(fs[0]) and on_box(fs[1]) else ridge).append(p)
    return concave, major, ridge
