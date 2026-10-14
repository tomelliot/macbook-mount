# Headless generators for parts that are made by script: GEN=floor|struts freecadcmd cad/generators.py
#   floor:  $BUILD_OUT/floor.brep (load into Floor) and $BUILD_OUT/cove_fill.brep (load into Floor_Cove_Fill)
#   struts: $BUILD_OUT/struts.brep (load into Mount_Breakaway_Struts)
#
# Floor: the wall grid (40 mm pitch, 2.4 mm ribs, R1.5 cell corners), centred in the slot; solid 2.4 mm rails along both
# walls (under the R2 coves), at the front and in front of RearStop; solid behind RearStop; three solid discs of the
# full slot width at Y 71, 171, 271 for felt sliding dots. Cove fill: the R2 cove profile copied into the gaps left by
# the old floor vents, so the coves run unbroken.
#
# Struts: self-supporting for a +Z build (DeskPlate up). Each strut is two 45° arms, 4 mm thick and 4 mm deep, rising
# from each wall to an apex over the slot centre. A 1.5 x 1.5 mm breakaway neck sits at the lowest point of each arm, so
# every layer grows from the one below. 5 struts at the front entry (Y 27-31) and 5 in line with them under the middle
# gusset (Y 169-173). At Y 171 the walls' inner face is solid only at rib nodes and the solid bands, so the strut heights
# are chosen for the necks to land there; every neck is checked against the walls.
import math
import os

import FreeCAD as App
import Part

V = App.Vector
ROOT = "/Users/tom/projects/fun/macbook-mount"
S = os.environ.get("BUILD_OUT", ROOT + "/cad/out") + "/"
XL, XF = -11.493, 9.248                        # wall inner faces
XC = (XL + XF) / 2


def floor(d):
    P, T = 40.0, 2.4
    H = (P - T * math.sqrt(2)) / 2             # half-diagonal of a cell
    Y0 = 171.0                                 # grid node on the slot centre, in line with the wall grid
    X0, X1, YA, YB = XL + T, XF - T, 27.0 + T, 316.225 - T
    ZA, ZB = -1.85, 2.15
    PADS_Y = (71.0, 171.0, 271.0)

    region = Part.makeBox(X1 - X0, YB - YA, 10, V(X0, YA, ZA - 5))
    centres = [(XC, Y0 + P / 2 + P * k) for k in range(-6, 6)] + [(XC + s * P / 2, Y0 + P * k) for s in (-1, 1) for k in range(-6, 6)]
    cells = []
    for cx, cy in centres:
        w = Part.makePolygon([V(cx + H, cy, ZA - 5), V(cx, cy + H, ZA - 5), V(cx - H, cy, ZA - 5), V(cx, cy - H, ZA - 5), V(cx + H, cy, ZA - 5)])
        c = Part.Face(w).extrude(V(0, 0, 10)).common(region)
        if c.Volume < 1e-6:
            continue
        c = c.removeSplitter()
        if [f for f in c.Faces if abs(f.normalAt(0, 0).z) > 0.99][0].Area < 12:     # drop slivers
            continue
        vert = [e for e in c.Edges if abs(e.tangentAt(e.FirstParameter).z) > 0.99]
        for r in (1.5, 1.0, 0.6):
            try:
                cf = c.makeFillet(r, vert)
                if cf.isValid():
                    c = cf
                    break
            except Exception:
                pass
        cells.append(c)
    b = Part.makeBox(28.741, 311.5, ZB - ZA, V(-15.493, 27.0, ZA))      # floor extent, 4 mm into each wall
    fl = b.cut(Part.makeCompound(cells)).removeSplitter()
    pads = [Part.makeCylinder((XF - XL) / 2, ZB - ZA, V(XC, y, ZA)) for y in PADS_Y]
    fl = fl.fuse(pads).removeSplitter()
    print("FLOOR cells %d valid %s solids %d vol %.1f mm3" % (len(cells), fl.isValid(), len(fl.Solids), fl.Volume), flush=True)
    fl.exportBrep(S + "floor.brep")

    gaps = [(37.479, 106.818), (129.318, 187.408), (209.908, 279.25)]
    fills = []
    for sol in d.getObject("Wall_Coves").Shape.Solids:
        bb = sol.BoundBox
        if bb.ZMax < 4.2 and abs(bb.YMin - 106.82) < 0.02:              # a floor cove piece on each wall
            prof = [f for f in sol.Faces if abs(f.BoundBox.YMin - bb.YMin) < 1e-6 and abs(f.BoundBox.YMax - bb.YMin) < 1e-6][0]
            for y0, y1 in gaps:
                fills.append(prof.translated(V(0, y0 - bb.YMin, 0)).extrude(V(0, y1 - y0, 0)))
    cf = Part.makeCompound(fills)
    print("COVE FILL pieces %d vol %.1f mm3" % (len(fills), cf.Volume), flush=True)
    cf.exportBrep(S + "cove_fill.brep")


def struts(d):
    GAP, T, DEPTH, NECK, EMB = 1.0, 4.0, 4.0, 1.5, 0.02
    xa, xb = XL + GAP, XF - GAP
    TV = T * 2 ** 0.5                   # vertical thickness of a 45° arm
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


if os.environ.get("GEN"):
    doc = App.openDocument(ROOT + "/DeskMount.FCStd")
    {"floor": floor, "struts": struts}[os.environ["GEN"]](doc)
