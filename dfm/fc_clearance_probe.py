# Run inside FreeCAD (via the freecad-mcp execute_code tool). Measures gaps between the cartridge,
# the mount and the laptop along probe rays, and writes dfm/evidence/03_clearances.json.
import json
import FreeCAD as App
import Part

V = App.Vector
d = App.getDocument("DeskMount")
EV = "/Users/tom/projects/fun/macbook-mount/dfm/evidence"
cart = d.getObject("USBC_Cartridge").Shape
mount = d.getObject("Mount_Fused").Shape
XL = d.getObject("Wall_Lid").Shape.BoundBox.XMax
XF = d.getObject("Wall_Feet").Shape.BoundBox.XMin


def segments(shape, a, b, tag):
    edge = Part.LineSegment(a, b).toShape()
    axis = (b - a).normalize()
    out = []
    for e in shape.common(edge).Edges:
        p, q = e.Vertexes[0].Point, e.Vertexes[-1].Point
        s0, s1 = sorted(((p - a).dot(axis), (q - a).dot(axis)))
        out.append((s0, s1, tag))
    return out


def gap(a, b, first, second, shapes):
    """Smallest gap along the ray between a segment of `first` and the next segment of `second` (either order)."""
    segs = []
    for tag in (first, second):
        segs += segments(shapes[tag], a, b, tag)
    segs.sort()
    best = None
    for (s0, s1, t1), (n0, n1, t2) in zip(segs, segs[1:]):
        if {t1, t2} == {first, second}:
            g = n0 - s1
            if best is None or abs(g) < abs(best):
                best = g
    return best


shapes = {"cartridge": cart, "mount": mount}
probes = [
    # name, start, end, pair, JLC class, design intent
    ("Tongue to groove, front face (feet side, Z 10)", V(XF + 1.0, 320, 10), V(XF + 1.0, 340, 10), ("cartridge", "mount"), "moving", 0.4),
    ("Tongue to groove, rear face (feet side, Z 10)", V(XF + 1.0, 340, 10), V(XF + 1.0, 320, 10), ("cartridge", "mount"), "moving", 0.4),
    ("Tongue to groove, front face (lid side, Z 10)", V(XL - 1.0, 320, 10), V(XL - 1.0, 340, 10), ("cartridge", "mount"), "moving", 0.4),
    ("Tongue tip to groove bottom (feet side, Z 10)", V(0, 332, 10), V(XF + 6, 332, 10), ("cartridge", "mount"), "moving", 0.4),
    ("Tongue tip to groove bottom (lid side, Z 10)", V(0, 332, 10), V(XL - 6, 332, 10), ("cartridge", "mount"), "moving", 0.4),
    ("Flex arm to groove bottom (feet side, Z 45)", V(0, 332, 45), V(XF + 6, 332, 45), ("cartridge", "mount"), "moving", 0.4),
    ("Cartridge body to RearStop (Z 10)", V(5, 315, 10), V(5, 330, 10), ("mount", "cartridge"), "assembly", 0.5),
    ("Cartridge body side to wall (feet side, Y 325, Z 30)", V(0, 325, 30), V(XF + 6, 325, 30), ("cartridge", "mount"), "assembly", 2.4),
    ("Cartridge base to Floor (rests by gravity)", V(5, 325, 10), V(5, 325, -1), ("cartridge", "mount"), "contact", 0.0),
    ("Squeeze pad to wall face (feet side, Y 328, Z 67)", V(0, 328, 67), V(XF + 6, 328, 67), ("cartridge", "mount"), "moving", 0.75),
]
rows = []
for name, a, b, (t1, t2), cls, intent in probes:
    g = gap(a, b, t1, t2, shapes)
    rows.append({"check": name, "class": cls, "design_mm": intent, "measured_mm": None if g is None else round(g, 3)})

# laptop fit, from the laptop mesh points (meshes have no solid to probe)
pts = [(v.x + o.Placement.Base.x, v.y + o.Placement.Base.y) for o in d.getObject("Laptop").Group if hasattr(o, "Mesh")
       for v in o.Mesh.Points if 27 <= v.y + o.Placement.Base.y <= 338.5]
case_x = max(v.x + d.getObject("L_geom_32").Placement.Base.x for v in d.getObject("L_geom_32").Mesh.Points)
feet_x = max(v.x + d.getObject("L_geom_30").Placement.Base.x for v in d.getObject("L_geom_30").Mesh.Points)
rs_y = d.getObject("RearStop").Shape.BoundBox.YMin
rows_laptop = [
    {"check": "Laptop lid face to Wall_Lid", "class": "fit", "design_mm": 2.0, "measured_mm": round(min(p[0] for p in pts) - XL, 3)},
    {"check": "Laptop bottom case to Wall_Feet", "class": "fit", "design_mm": 2.0, "measured_mm": round(XF - case_x, 3)},
    {"check": "Laptop rubber feet to Wall_Feet", "class": "fit", "design_mm": 1.1, "measured_mm": round(XF - feet_x, 3)},
    {"check": "Laptop end to RearStop", "class": "fit", "design_mm": 2.0, "measured_mm": round(rs_y - max(p[1] for p in pts), 3)},
]
rows += rows_laptop

# arm flex gap: arm inner face to body side, measured along X through the arm at Z 40
segs = sorted(segments(cart, V(-20, 332, 45), V(20, 332, 45), "c"))
inner_gaps = [round(n0 - s1, 3) for (s0, s1, _), (n0, n1, _) in zip(segs, segs[1:])]
rows.append({"check": "Flex arm inner face to cartridge body (squeeze travel, Z 45)", "class": "internal", "design_mm": 2.5,
             "measured_mm": [g for g in inner_gaps if g < 5]})
# detent preload: ball overlaps the hole edge by design
for side in ("Lid", "Feet"):
    ball = d.getObject("Cart_Detent_" + side).Shape
    wall = d.getObject("Wall_" + side).Shape
    rows.append({"check": "Detent ball vs hole edge (%s side) - interference = preload" % side.lower(), "class": "preload",
                 "design_mm": 0.3, "measured_overlap_mm3": round(ball.common(wall).Volume, 4)})
json.dump(rows, open(EV + "/03_clearances.json", "w"), indent=1)
for r in rows:
    print(r)
