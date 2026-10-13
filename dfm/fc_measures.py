# Run inside the FreeCAD GUI (freecad-mcp execute_code: exec(open(<this file>).read())).
# Creates live Measure::MeasureDistance objects in group DFM_Measures for checks 10-12 and 18, linked to the source
# features' faces, and writes their values to dfm/evidence/03_measures.json. Re-run after the geometry changes: the
# group is rebuilt, because face numbers change when a feature's shape is replaced.
import json

import FreeCAD as App
import Part

V = App.Vector
EV = "/Users/tom/projects/fun/macbook-mount/dfm/evidence"
d = App.getDocument("DeskMount")
MOUNT = [d.getObject(n) for n in ("Wall_Lid", "Wall_Feet", "CartRail_Lid", "CartRail_Feet", "Floor", "RearStop")]
CART = [d.getObject(n) for n in ("Cart_Body_Cut", "Cart_Tongue_Lid", "Cart_Tongue_Feet", "Cart_Detent_Lid", "Cart_Detent_Feet")]
XL = d.getObject("Wall_Lid").Shape.BoundBox.XMax
XF = d.getObject("Wall_Feet").Shape.BoundBox.XMin
PORT_X = -0.919


def hits(objs, a, b):
    """Solid segments along a->b for a group of features, as sorted (s0, s1) distances from a."""
    edge = Part.LineSegment(a, b).toShape()
    axis = (b - a).normalize()
    segs = []
    for o in objs:
        for e in o.Shape.common(edge).Edges:
            s = sorted(((e.Vertexes[0].Point - a).dot(axis), (e.Vertexes[-1].Point - a).dot(axis)))
            segs.append(tuple(s))
    return sorted(segs), axis


def face_at(objs, p, axis):
    for o in objs:
        for i, f in enumerate(o.Shape.Faces):
            if f.Surface.__class__.__name__ == "Plane" and abs(f.normalAt(0, 0).dot(axis)) > 0.999 \
                    and f.distToShape(Part.Vertex(p))[0] < 1e-4:
                return o, "Face%d" % (i + 1)
    raise RuntimeError("no face at %s" % p)


def pair(first, second, a, b):
    """Faces bounding the first gap on a->b that runs from a `first` segment to a `second` segment."""
    s1, axis = hits(first, a, b)
    s2, _ = hits(second, a, b)
    tagged = sorted([(s, 1) for s in s1] + [(s, 2) for s in s2])
    for ((x0, x1), t1), ((y0, y1), t2) in zip(tagged, tagged[1:]):
        if t1 == 1 and t2 == 2:
            return face_at(first, a + axis * x1, axis), face_at(second, a + axis * y0, axis)
    raise RuntimeError("no gap on probe")


PROBES = [
    # label, check, first group, second group, ray start, ray end, design value
    # (the flex arm's outer face is the same plane face as the tongue tip, so the tip measures cover the arm too)
    ("Tongue to groove, front face (feet, Z 10)", 10, MOUNT, CART, V(XF + 1, 320, 10), V(XF + 1, 340, 10), 0.4),
    ("Tongue to groove, rear face (feet, Z 10)", 10, CART, MOUNT, V(XF + 1, 320, 10), V(XF + 1, 340, 10), 0.4),
    ("Tongue to groove, front face (lid, Z 10)", 10, MOUNT, CART, V(XL - 1, 320, 10), V(XL - 1, 340, 10), 0.4),
    ("Tongue to groove, rear face (lid, Z 10)", 10, CART, MOUNT, V(XL - 1, 320, 10), V(XL - 1, 340, 10), 0.4),
    ("Tongue tip and arm to groove bottom (feet, Z 10)", 10, CART, MOUNT, V(0, 332, 10), V(XF + 6, 332, 10), 0.4),
    ("Tongue tip and arm to groove bottom (lid, Z 10)", 10, CART, MOUNT, V(0, 332, 10), V(XL - 6, 332, 10), 0.4),
    ("Cartridge front to RearStop (Z 10)", 11, MOUNT, CART, V(5, 315, 10), V(5, 330, 10), 0.5),
    # the pads sit above the rails and behind the walls' rear end (walls end at Y 320.2 above Z 60.5)
    ("Squeeze pad to rail top (feet, X 12.5)", 12, CART, MOUNT, V(12.5, 328, 67), V(12.5, 328, 50), None),
    ("Squeeze pad to rail top (lid, X -14.7)", 12, CART, MOUNT, V(-14.7, 328, 67), V(-14.7, 328, 50), None),
    ("Squeeze pad to wall rear end (feet, Z 67)", 12, CART, MOUNT, V(14, 336, 67), V(14, 310, 67), None),
    ("Squeeze pad to wall rear end (lid, Z 67)", 12, CART, MOUNT, V(-16.5, 336, 67), V(-16.5, 310, 67), None),
    ("Cartridge base on Floor (Z 2.15)", 18, MOUNT, CART, V(5, 325, -1), V(5, 325, 10), 0.0),
]

old = d.getObject("DFM_Measures")
if old:
    for o in list(old.Group):
        d.removeObject(o.Name)
    d.removeObject(old.Name)
grp = d.addObject("App::DocumentObjectGroup", "DFM_Measures")
rows = []
for label, check, first, second, a, b, design in PROBES:
    (o1, f1), (o2, f2) = pair(first, second, a, b)
    m = d.addObject("Measure::MeasureDistance", "M_%02d" % (len(rows) + 1))
    m.Label2 = "Check %d: %s" % (check, label)      # Label is overwritten with the value by FreeCAD
    m.Element1 = (o1, [f1])
    m.Element2 = (o2, [f2])
    grp.addObject(m)
    rows.append((m, label, check, design, o1.Name + "." + f1, o2.Name + "." + f2))

# check 18: port centre height above the floor datum, from the pocket floor and roof faces
PX = PORT_X + 2.8          # beside the 5 mm cable slot, which opens the roof over the port centre
seg, axis = hits(CART, V(PX, 324, 0), V(PX, 324, 75))
floor_face = face_at(MOUNT, V(5, 325, 2.15), V(0, 0, 1))
for name, z in (("pocket floor", seg[0][1]), ("pocket roof", seg[1][0])):
    m = d.addObject("Measure::MeasureDistance", "M_%02d" % (len(rows) + 1))
    m.Label2 = "Check 18: Floor top to %s" % name
    m.Element1 = (floor_face[0], [floor_face[1]])
    f = face_at(CART, V(PX, 324, z), V(0, 0, 1))
    m.Element2 = (f[0], [f[1]])
    grp.addObject(m)
    rows.append((m, "Floor top to %s" % name, 18, None, floor_face[0].Name + "." + floor_face[1], f[0].Name + "." + f[1]))
d.recompute()

out = [{"object": m.Name, "check": c, "measure": l, "design_mm": dz, "measured_mm": round(m.Distance.Value, 3),
        "between": [e1, e2]} for m, l, c, dz, e1, e2 in rows]
lo, hi = out[-2]["measured_mm"], out[-1]["measured_mm"]
out.append({"check": 18, "measure": "Pocket centre above floor top (derived)", "measured_mm": round((lo + hi) / 2, 3),
            "port_centre_above_floor_mm": round(50.44 - 2.15, 3)})
json.dump(out, open(EV + "/03_measures.json", "w"), indent=1)
for r in out:
    print(r)
