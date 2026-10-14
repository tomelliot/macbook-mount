# Run headless by run_dfm.sh: freecadcmd dfm/fc_headless.py (env DFM_TMP = scratch dir).
# Works on the print bodies (Print_Bodies: Mount_Rounded, USBC_Cartridge_Rounded):
# - exports the STEP files and reads them back;
# - check 1-3: build volume and solids (01_build_volume.json);
# - checks 10-13: what Measure objects can't do, laptop fit and clash (the laptop is a mesh), the detent preload and the
#   total cartridge-to-mount overlap (03_clearances.json); the cartridge-to-mount gaps are live Measure objects (fc_gui.py);
# - STL meshes for mesh_scans.py, the cartridge-zone clip that fc_gui.py loads into the drawing, and facts.json for calcs.py.
import json
import os

import FreeCAD as App
import Import
import MeshPart
import Part

V = App.Vector
ROOT = "/Users/tom/projects/fun/macbook-mount"
EV = ROOT + "/dfm/evidence"
TMP = os.environ.get("DFM_TMP", "/tmp/deskmount_dfm")
d = App.openDocument(ROOT + "/DeskMount.FCStd")
mount = d.getObject("Mount_Rounded")
cart = d.getObject("USBC_Cartridge_Rounded")

# ---- STEP export, verified by reading back ----
steps = {"Mount_Rounded": ROOT + "/export/DeskMount_mount.step", "USBC_Cartridge_Rounded": ROOT + "/export/DeskMount_usbc_cartridge.step"}
for name, path in steps.items():
    Import.export([d.getObject(name)], path)
    back = Part.read(path)
    print("step", name, round(back.Volume / 1000, 2), "model", round(d.getObject(name).Shape.Volume / 1000, 2), flush=True)

# ---- checks 1-3: build volume, solids ----
bv = {}
for o in (mount, cart):
    s = o.Shape
    b = s.optimalBoundingBox()          # BoundBox is loose on curved (rounded) faces
    dims = sorted([b.XLength, b.YLength, b.ZLength])
    bv[o.Name] = {"bbox_xyz_mm": [round(b.XLength, 2), round(b.YLength, 2), round(b.ZLength, 2)],
                  "volume_cm3": round(s.Volume / 1000, 2), "area_cm2": round(s.Area / 100, 1),
                  "solids": len(s.Solids), "shells_per_solid": [len(x.Shells) for x in s.Solids],
                  "closed": all(sh.isClosed() for x in s.Solids for sh in x.Shells), "valid": s.isValid(),
                  "fits_580x580x380": dims[0] <= 380 and dims[1] <= 580 and dims[2] <= 580,
                  "fits_780x780x530": dims[0] <= 530 and dims[1] <= 780 and dims[2] <= 780,
                  "above_min_5x5x5": dims[0] >= 5}
json.dump(bv, open(EV + "/01_build_volume.json", "w"), indent=1)
print(json.dumps(bv), flush=True)

# ---- meshes: the parts as used (struts and ties left out) for the thickness scan, the mount as printed for the
# support scan ----
mount_use = mount.Shape.cut(d.getObject("Mount_Breakaway_Struts").Shape)
cart_use = cart.Shape.cut(d.getObject("Cart_Breakaway_Lid").Shape.fuse(d.getObject("Cart_Breakaway_Feet").Shape))
for name, s in (("mount", mount_use), ("cartridge", cart_use), ("mount_print", mount.Shape)):
    m = MeshPart.meshFromShape(Shape=s, LinearDeflection=0.02, AngularDeflection=0.15, Relative=False)
    m.write(TMP + "/%s.stl" % name)
    print("mesh", name, m.CountFacets, flush=True)

# ---- cartridge-zone clip for the TechDraw sheet (a boolean on the full mount has crashed the GUI) ----
mount.Shape.common(Part.makeBox(42, 30, 82, V(-22, 312, -2))).exportBrep(TMP + "/clip_cart_zone.brep")

# ---- checks 10-13: laptop fit from the laptop mesh points, detent preload ----
XL = d.getObject("Wall_Lid").Shape.BoundBox.XMax
XF = d.getObject("Wall_Feet").Shape.BoundBox.XMin
# Mesh.Points already include each mesh's Placement: do not add it again
pts = [(v.x, v.y) for o in d.getObject("Laptop").Group if hasattr(o, "Mesh") for v in o.Mesh.Points if 27 <= v.y <= 341.3]
case_x = max(v.x for v in d.getObject("L_geom_32").Mesh.Points)
feet_x = max(v.x for v in d.getObject("L_geom_30").Mesh.Points)
rs_y = d.getObject("RearStop").Shape.BoundBox.YMin
rows = [
    {"check": "Laptop lid face to Wall_Lid", "class": "fit", "design_mm": 2.0, "measured_mm": round(min(p[0] for p in pts) - XL, 3)},
    {"check": "Laptop bottom case to Wall_Feet", "class": "fit", "design_mm": 2.0, "measured_mm": round(XF - case_x, 3)},
    {"check": "Laptop rubber feet to Wall_Feet", "class": "fit", "design_mm": 1.1, "measured_mm": round(XF - feet_x, 3)},
    {"check": "Laptop end to RearStop (flush)", "class": "fit", "design_mm": 0.0, "measured_mm": round(rs_y - max(p[1] for p in pts), 3)},
]
for side in ("Lid", "Feet"):                          # the ball overlaps the hole edge by design
    ball = d.getObject("Cart_Detent_" + side).Shape
    rail = d.getObject("CartRail_" + side).Shape       # the detent holes are in the cartridge rails
    rows.append({"check": "Detent ball vs hole edge (%s side) - interference = preload" % side.lower(), "class": "preload",
                 "design_mm": 0.3, "measured_overlap_mm3": round(ball.common(rail).Volume, 4)})
# the whole print bodies: the cartridge may overlap the mount only by the detent preload, and no laptop point may sit
# inside the mount once the struts are off
rows.append({"check": "Cartridge print body vs mount print body - total overlap", "class": "preload",
             "measured_overlap_mm3": round(cart.Shape.common(mount.Shape).Volume, 4)})
lap = [p.Vector for o in d.getObject("Laptop").Group if hasattr(o, "Mesh") for p in o.Mesh.Points]
near = [p for p in lap if p.x < -9.0 or p.x > 7.0 or p.z < 4.5 or p.z > 224 or p.y > 313.5]
rows.append({"check": "Laptop mesh points inside the mount (struts removed)", "class": "fit",
             "measured_points": sum(1 for p in near if mount_use.isInside(p, 1e-6, False)), "of_points": len(near)})
json.dump(rows, open(EV + "/03_clearances.json", "w"), indent=1)
for r in rows:
    print(r)

# ---- facts for the tolerance stack ----
cb = cart.Shape.BoundBox
facts = {"floor_top_z": d.getObject("Floor").Shape.BoundBox.ZMax, "cart_base_z": cb.ZMin, "cart_top_z": cb.ZMax,
         "mount_bbox": bv["Mount_Rounded"]["bbox_xyz_mm"], "cart_bbox": bv["USBC_Cartridge_Rounded"]["bbox_xyz_mm"],
         "laptop_min_z": min(p.z for o in d.getObject("Laptop").Group if hasattr(o, "Mesh") for p in o.Mesh.Points)}
json.dump(facts, open(TMP + "/facts.json", "w"), indent=1)
print(json.dumps(facts), flush=True)
print("done", flush=True)
