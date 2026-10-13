# Headless: fuzzy-fuse the rounded mount parts, then round the outer corners that span several parts with edge-round
# cutters (box minus cylinder, R1.5). Takes the walls, Floor and Riser_Grid from rp_*.brep (round_part.py), the simple
# parts from their Part::Fillet features in the model (model_fillets.py), and the cartridge from round_cartridge.py for
# the overlap check. Output: $BUILD_OUT/mount_rounded.brep.
# The fuse and the cutters stay here: FreeCAD's boolean features have no fuzzy tolerance, and a plain fuse of the rounded
# parts returns a valid solid of 0.25 cm3.
# A plain fuse fails on the coplanar joins; a fuzzy fuse (1e-5) in Mount_Fused order, without removeSplitter, is valid
# and passes shape.check(True). A cutter coaxial with an existing round needs a fuzzy cut (1e-4).
import os
import FreeCAD as App, Part

V = App.Vector
ROOT = "/Users/tom/projects/fun/macbook-mount"
S = os.environ.get("BUILD_OUT", ROOT + "/build/out") + "/"
d = App.openDocument(ROOT + "/DeskMount.FCStd")
SCRIPTED = ["Wall_Lid", "Wall_Feet", "Floor", "Riser_Grid"]
IN_MODEL = ["RearStop", "DeskPlate", "Gusset_Lid", "CartRail_Lid", "CartRail_Feet"]
RAD = 1.5


def strict(s):
    try:
        s.check(True)
        return 0
    except Exception as e:
        return max(1, str(e).count("Error"))


# struts, coves and cove fill go in unrounded
d.recompute()


def part(o):
    if o.Name in SCRIPTED:
        return Part.read(S + "rp_" + o.Name + ".brep")
    if o.Name in IN_MODEL:
        return d.getObject(o.Name + "_Rounded").Shape
    return o.Shape


ps = [part(o) for o in d.getObject("Mount_Fused").Shapes]
m = ps[0].fuse(ps[1:], 1e-5)
print("FUSED valid %s solids %d strict %d vol %.3f cm3" % (m.isValid(), len(m.Solids), strict(m), m.Volume / 1000), flush=True)


def vcut(x, y, sx, sy, z0, z1):
    """Cutter for a vertical corner at (x, y); (sx, sy) point into the material."""
    b = Part.makeBox(1 + RAD, 1 + RAD, z1 - z0, V(min(x - sx, x + sx * RAD), min(y - sy, y + sy * RAD), z0))
    return b.cut(Part.makeCylinder(RAD, z1 - z0 + 2, V(x + sx * RAD, y + sy * RAD, z0 - 1)))


def xcut(y, z, sy, sz, x0, x1):
    """Cutter for an edge along X at (y, z); (sy, sz) point into the material."""
    b = Part.makeBox(x1 - x0, 1 + RAD, 1 + RAD, V(x0, min(y - sy, y + sy * RAD), min(z - sz, z + sz * RAD)))
    return b.cut(Part.makeCylinder(RAD, x1 - x0 + 2, V(x0 - 1, y + sy * RAD, z + sz * RAD), V(1, 0, 0)))


XL, XR, XG, YF, YB = -19.493, 17.248, 52.248, 27.0, 320.225   # lid wall outer, feet wall outer, plate edge, front, back
cutters = {
    "plate+wall lid front vertical": vcut(XL, YF, 1, 1, -3, 284),
    "plate feet front vertical": vcut(XG, YF, -1, 1, 240, 284),
    "plate feet back vertical": vcut(XG, YB, -1, -1, 240, 284),
    "plate lid back vertical": vcut(XL, YB, 1, -1, 228, 284),
    "wall feet front vertical": vcut(XR, YF, -1, 1, -3, 243),
    "front bottom edge": xcut(YF, -1.85, 1, 1, -21, 19),
    "floor front lip": xcut(YF, 2.15, 1, -1, -11.493, 9.248),
    "wall+riser lid back vertical": vcut(XL, YB, 1, -1, 60.5, 278),
    "wall feet back vertical": vcut(XR, YB, -1, -1, 60.5, 243),
}
for k, c in cutters.items():
    for tol in (0, 1e-4):
        t = m.cut(c, tol) if tol else m.cut(c)
        ok = t.isValid() and len(t.Solids) == 1 and strict(t) == 0 and m.Volume - t.Volume < 500
        if ok:
            break
    print("CUT %-30s removed %.2f mm3 -> %s" % (k, m.Volume - t.Volume, "kept" if ok else "SKIPPED"), flush=True)
    if ok:
        m = t
m.exportBrep(S + "mount_rounded.brep")
print("MOUNT RESULT valid %s solids %d strict %d vol %.3f cm3" % (m.isValid(), len(m.Solids), strict(m), m.Volume / 1000), flush=True)

# checks: cartridge overlap is the detent preload only; no laptop point inside the mount with the struts removed
if os.path.exists(S + "cart_rounded.brep"):
    print("CHECK cartridge overlap with mount %.4f mm3" % Part.read(S + "cart_rounded.brep").common(m).Volume, flush=True)
nost = m.cut(d.getObject("Mount_Breakaway_Struts").Shape)
pts = [o.Placement.multVec(p.Vector) for o in d.getObject("Laptop").Group if hasattr(o, "Mesh") for p in o.Mesh.Points]
near = [p for p in pts if p.x < -9.0 or p.x > 7.0 or p.z < 4.5 or p.z > 224 or p.y > 313.5]
print("CHECK laptop points inside mount (struts removed): %d of %d" % (sum(1 for p in near if nost.isInside(p, 1e-6, False)), len(near)), flush=True)
