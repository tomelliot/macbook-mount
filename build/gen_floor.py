# Headless: generate the grid floor and the cove fill. Output: $BUILD_OUT/floor.brep (load into Floor) and
# $BUILD_OUT/cove_fill.brep (load into Floor_Cove_Fill).
# Floor: the wall grid (40 mm pitch, 2.4 mm ribs, R1.5 cell corners), centred in the slot; solid 2.4 mm rails along both
# walls (under the R2 coves), at the front and in front of RearStop; solid behind RearStop; three solid discs of the
# full slot width at Y 71, 171, 271 for felt sliding dots.
# Cove fill: the R2 cove profile copied into the gaps left by the old floor vents, so the coves run unbroken.
import math, os
import FreeCAD as App, Part

V = App.Vector
ROOT = "/Users/tom/projects/fun/macbook-mount"
S = os.environ.get("BUILD_OUT", ROOT + "/build/out") + "/"
d = App.openDocument(ROOT + "/DeskMount.FCStd")
P, T = 40.0, 2.4
H = (P - T * math.sqrt(2)) / 2                 # half-diagonal of a cell
XL, XF = -11.493, 9.248                        # wall inner faces
XC, Y0 = (XL + XF) / 2, 171.0                  # grid node on the slot centre, in line with the wall grid
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
floor = b.cut(Part.makeCompound(cells)).removeSplitter()
pads = [Part.makeCylinder((XF - XL) / 2, ZB - ZA, V(XC, y, ZA)) for y in PADS_Y]
floor = floor.fuse(pads).removeSplitter()
print("FLOOR cells %d valid %s solids %d vol %.1f mm3" % (len(cells), floor.isValid(), len(floor.Solids), floor.Volume), flush=True)
floor.exportBrep(S + "floor.brep")

gaps = [(37.479, 106.818), (129.318, 187.408), (209.908, 279.25)]
fills = []
for sol in d.getObject("Mount_Fillets").Shape.Solids:
    bb = sol.BoundBox
    if bb.ZMax < 4.2 and abs(bb.YMin - 106.82) < 0.02:              # a floor cove piece on each wall
        prof = [f for f in sol.Faces if abs(f.BoundBox.YMin - bb.YMin) < 1e-6 and abs(f.BoundBox.YMax - bb.YMin) < 1e-6][0]
        for y0, y1 in gaps:
            fills.append(prof.translated(V(0, y0 - bb.YMin, 0)).extrude(V(0, y1 - y0, 0)))
cf = Part.makeCompound(fills)
print("COVE FILL pieces %d vol %.1f mm3" % (len(fills), cf.Volume), flush=True)
cf.exportBrep(S + "cove_fill.brep")
