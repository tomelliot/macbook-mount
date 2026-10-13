# Headless: generate the breakaway print struts. Output: $BUILD_OUT/struts.brep (load into Mount_Breakaway_Struts).
# Self-supporting for a +Z build (DeskPlate up): each strut is two 45° arms, 4 mm thick and 4 mm deep, rising from each
# wall to an apex over the slot centre. A 1.5 x 1.5 mm breakaway neck sits at the lowest point of each arm, so every
# layer grows from the one below. 5 struts at the front entry (Y 27-31) and 5 in line with them under the middle
# gusset (Y 169-173). At Y 171 the walls' inner face is solid only at rib nodes and the solid bands, so the strut
# heights are chosen for the necks to land there; the script checks every neck against the walls.
import os
import FreeCAD as App, Part

V = App.Vector
ROOT = "/Users/tom/projects/fun/macbook-mount"
S = os.environ.get("BUILD_OUT", ROOT + "/build/out") + "/"
d = App.openDocument(ROOT + "/DeskMount.FCStd")
XL, XF, GAP, T, DEPTH, NECK, EMB = -11.493, 9.248, 1.0, 4.0, 4.0, 1.5, 0.02
XC = (XL + XF) / 2
xa, xb = XL + GAP, XF - GAP
TV = T * 2 ** 0.5                       # vertical thickness of a 45° arm
ROWS_Y = (29.0, 171.0)
Z0S = (25.0, 74.25, 114.25, 154.25, 200.0)
WL, WF = d.getObject("Wall_Lid").Shape, d.getObject("Wall_Feet").Shape


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
