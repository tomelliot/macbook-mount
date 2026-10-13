# Run headless: freecadcmd dfm/fc_dfm_run.py  (env DFM_TMP = scratch dir for meshes)
# Exports the STEP files and writes the model-derived DFM evidence: build volume, clearance probe (laptop fit, detent
# overlap), STL meshes for the ray thickness scan (ray_thickness.py) and the support scan (support_scan.py), and the clip
# that fc_evidence_export.py loads. Works on the print bodies (Print_Bodies: Mount_Rounded, USBC_Cartridge_Rounded).
import json
import os

import FreeCAD as App
import Import
import MeshPart
import Part

V = App.Vector
ROOT = "/Users/tom/projects/fun/macbook-mount"
EV = ROOT + "/dfm/evidence"
TMP = os.environ.get("DFM_TMP", "/tmp")
d = App.openDocument(ROOT + "/DeskMount.FCStd")
mount = d.getObject("Mount_Rounded")
cart = d.getObject("USBC_Cartridge_Rounded")

# ---- STEP export of the print bodies (rounded, static shapes in Print_Bodies), verified by reading back ----
steps = {"Mount_Rounded": ROOT + "/export/DeskMount_mount.step", "USBC_Cartridge_Rounded": ROOT + "/export/DeskMount_usbc_cartridge.step"}
for name, path in steps.items():
    Import.export([d.getObject(name)], path)
    back = Part.read(path)
    print("step", name, round(back.Volume / 1000, 2), "model", round(d.getObject(name).Shape.Volume / 1000, 2), flush=True)

# ---- check 1-3: build volume, solids ----
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

# ---- meshes: printed parts as used (breakaway struts and ties left out) for the thickness scan, and the mount as
# printed (struts in) for the support scan ----
mount_use = mount.Shape.cut(d.getObject("Mount_Breakaway_Struts").Shape)
cart_use = cart.Shape.cut(d.getObject("Cart_Breakaway_Lid").Shape.fuse(d.getObject("Cart_Breakaway_Feet").Shape))
for name, s in (("mount", mount_use), ("cartridge", cart_use), ("mount_print", mount.Shape)):
    m = MeshPart.meshFromShape(Shape=s, LinearDeflection=0.02, AngularDeflection=0.15, Relative=False)
    m.write(TMP + "/%s.stl" % name)
    print("mesh", name, m.CountFacets, flush=True)


# ---- cartridge-zone clip for the TechDraw sheet (a boolean on the full mount has crashed the GUI) ----
mount.Shape.common(Part.makeBox(42, 30, 82, V(-22, 312, -2))).exportBrep(TMP + "/clip_cart_zone.brep")

# ---- clearances (check 10-13) ----
exec(open(ROOT + "/dfm/fc_clearance_probe.py").read(), {"__name__": "probe"})

# ---- facts for the tolerance stack and flex check ----
cb = cart.Shape.BoundBox
facts = {"floor_top_z": d.getObject("Floor").Shape.BoundBox.ZMax, "cart_base_z": cb.ZMin, "cart_top_z": cb.ZMax,
         "mount_bbox": bv["Mount_Rounded"]["bbox_xyz_mm"], "cart_bbox": bv["USBC_Cartridge_Rounded"]["bbox_xyz_mm"],
         "laptop_min_z": min(o.Placement.multVec(p.Vector).z for o in d.getObject("Laptop").Group if hasattr(o, "Mesh") for p in o.Mesh.Points)}
json.dump(facts, open(TMP + "/facts.json", "w"), indent=1)
print(json.dumps(facts), flush=True)
print("done", flush=True)
