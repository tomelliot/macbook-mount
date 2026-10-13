# Run by fc_dfm_run.py (headless). Covers what FreeCAD Measure objects can't: laptop fit (the laptop is a mesh) and
# the detent preload overlap volume. Writes dfm/evidence/03_clearances.json. Cartridge-to-mount gaps are live
# Measure objects (fc_measures.py, 03_measures.json).
import json
import FreeCAD as App
import Part

V = App.Vector
d = App.getDocument("DeskMount")
EV = "/Users/tom/projects/fun/macbook-mount/dfm/evidence"
XL = d.getObject("Wall_Lid").Shape.BoundBox.XMax
XF = d.getObject("Wall_Feet").Shape.BoundBox.XMin


rows = []

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

# detent preload: ball overlaps the hole edge by design
for side in ("Lid", "Feet"):
    ball = d.getObject("Cart_Detent_" + side).Shape
    wall = d.getObject("CartRail_" + side).Shape       # the detent holes are in the cassette rails
    rows.append({"check": "Detent ball vs hole edge (%s side) - interference = preload" % side.lower(), "class": "preload",
                 "design_mm": 0.3, "measured_overlap_mm3": round(ball.common(wall).Volume, 4)})
json.dump(rows, open(EV + "/03_clearances.json", "w"), indent=1)
for r in rows:
    print(r)
