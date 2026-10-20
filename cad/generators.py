# Headless generator for the breakaway struts: GEN=struts freecadcmd cad/generators.py
#   struts: $BUILD_OUT/struts.brep (load into Mount_Breakaway_Struts)
# The mount body itself is cad/mount_body.py.
#
# Struts: self-supporting for a +Z build (DeskPlate up). Each strut is two 45° arms, 4 mm thick and 4 mm deep, rising
# from each wall to an apex over the slot centre. A 1.5 x 1.5 mm breakaway neck sits at the lowest point of each arm, so
# every layer grows from the one below. 5 struts at the front entry (Y 27-31), and 5 in line with them at Y 91, 171
# (under the middle gusset) and 251, which halve the two 140 mm gaps between the entry and RearStop. Y 91, 171 and 251
# are the same column of wall-grid nodes (80 mm apart); there the walls' inner face is solid only at rib nodes and the
# solid bands, so the strut heights are chosen for the necks to land there; every neck is checked against the walls.
import os

import FreeCAD as App
import Part

V = App.Vector
ROOT = "/Users/tom/projects/fun/macbook-mount"
S = os.environ.get("BUILD_OUT", ROOT + "/cad/out") + "/"
XL, XF = -11.493, 9.248                        # wall inner faces
XC = (XL + XF) / 2


def struts(d):
    GAP, T, DEPTH, NECK, EMB = 1.0, 4.0, 4.0, 1.5, 0.02
    xa, xb = XL + GAP, XF - GAP
    TV = T * 2 ** 0.5                   # vertical thickness of a 45° arm
    ROWS_Y = (29.0, 91.0, 171.0, 251.0)
    Z0S = (25.0, 74.25, 114.25, 154.25, 200.0)
    WL = WF = d.getObject("MountBody").Shape

    def on_wall(w, x, ny, z0):
        return all(w.isInside(V(x, ny + dy, z0 + dz), 1e-6, True) for dy in (0.1, 0.75, 1.4) for dz in (0.1, 0.75, 1.4))

    out = []
    for yc in ROWS_Y:
        for z0 in Z0S:
            y0 = max(27.0, yc - DEPTH / 2)
            pts = [V(xa, 0, z0), V(XC, 0, z0 + (XC - xa)), V(xb, 0, z0), V(xb, 0, z0 + TV), V(XC, 0, z0 + (XC - xa) + TV), V(xa, 0, z0 + TV), V(xa, 0, z0)]
            arm = Part.Face(Part.makePolygon(pts)).extrude(V(0, DEPTH, 0)).translated(V(0, y0, 0))
            ny = y0 + DEPTH / 2 - NECK / 2
            necks = [Part.makeBox(GAP + 2 * EMB, NECK, NECK, V(x, ny, z0)) for x in (XL - EMB, xb - EMB)]
            st = arm.fuse(necks).removeSplitter()
            ok = on_wall(WL, XL - 0.3, ny, z0) and on_wall(WF, XF + 0.3, ny, z0)
            print("STRUT y %.1f z %.2f-%.2f valid %s vol %.1f necks on solid wall %s" % (yc, z0, st.BoundBox.ZMax, st.isValid(), st.Volume, ok), flush=True)
            out.append(st)
    Part.makeCompound(out).exportBrep(S + "struts.brep")


if os.environ.get("GEN"):
    doc = App.openDocument(ROOT + "/DeskMount.FCStd")
    {"struts": struts}[os.environ["GEN"]](doc)
