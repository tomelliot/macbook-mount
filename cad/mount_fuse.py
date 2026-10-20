# Mount print body as a model feature: fuzzy fuse of the rounded mount parts, then round fills on the inside corners and
# edge-round cutters on the outside corners that span several parts. FreeCAD's own boolean features have no fuzzy
# tolerance, and a plain fuse of the rounded parts returns a broken solid, so this is a Part::FeaturePython whose code
# lives here.
# FreeCAD must be able to import this module when it opens DeskMount.FCStd: cad/install.sh links cad/ into FreeCAD's
# user Mod folder. Without it the model still shows the last result but cannot recompute Mount_Rounded.
# Create or recreate the feature (in the GUI): import mount_fuse; mount_fuse.create(App.getDocument("DeskMount"))
import math

import FreeCAD as App
import Part

V = App.Vector
RAD = 1.5
XL, XR, XG, YF, YB = -19.493, 17.248, 52.248, 27.0, 320.225   # lid wall outer, feet wall outer, plate edge, front, back


def vcut(x, y, sx, sy, z0, z1):
    """Cutter for a vertical corner at (x, y); (sx, sy) point into the material."""
    b = Part.makeBox(1 + RAD, 1 + RAD, z1 - z0, V(min(x - sx, x + sx * RAD), min(y - sy, y + sy * RAD), z0))
    return b.cut(Part.makeCylinder(RAD, z1 - z0 + 2, V(x + sx * RAD, y + sy * RAD, z0 - 1)))


def xcut(y, z, sy, sz, x0, x1):
    """Cutter for an edge along X at (y, z); (sy, sz) point into the material."""
    b = Part.makeBox(x1 - x0, 1 + RAD, 1 + RAD, V(x0, min(y - sy, y + sy * RAD), min(z - sz, z + sz * RAD)))
    return b.cut(Part.makeCylinder(RAD, x1 - x0 + 2, V(x0 - 1, y + sy * RAD, z + sz * RAD), V(1, 0, 0)))


def ycut(x, z, sx, sz, y0, y1):
    """Cutter for an edge along Y at (x, z); (sx, sz) point into the material."""
    b = Part.makeBox(1 + RAD, y1 - y0, 1 + RAD, V(min(x - sx, x + sx * RAD), y0, min(z - sz, z + sz * RAD)))
    return b.cut(Part.makeCylinder(RAD, y1 - y0 + 2, V(x + sx * RAD, y0 - 1, z + sz * RAD), V(0, 1, 0)))


def xfill(y, z, sy, sz, x0, x1):
    """Fill for an inside corner along X at (y, z); (sy, sz) point into the empty quadrant."""
    b = Part.makeBox(x1 - x0, RAD, RAD, V(x0, min(y, y + sy * RAD), min(z, z + sz * RAD)))
    return b.cut(Part.makeCylinder(RAD, x1 - x0 + 2, V(x0 - 1, y + sy * RAD, z + sz * RAD), V(1, 0, 0)))


# Inside corners that span several parts, rounded by adding material after the fuse
FILLS = [
    ("rail lid top to wall end", lambda: xfill(YB, 60.5, 1, 1, -15.493, -11.493)),    # continues Wall_Lid's own R1.5
    ("rail feet top to wall end", lambda: xfill(YB, 60.5, 1, 1, 9.248, 13.248)),
    ("entry top corner lid", lambda: yfill(EX0, EZ1, 1, -1, YF, YF + 4, ER)),       # in the riser's 4 mm front posts
    ("entry top corner feet", lambda: yfill(EX1, EZ1, -1, -1, YF, YF + 4, ER)),
    ("back top corner lid", lambda: yfill(EX0, EZ1, 1, -1, RS0, YB, ER)),           # in the riser's 4 mm back posts
    ("back top corner feet", lambda: yfill(EX1, EZ1, -1, -1, RS0, YB, ER)),
    ("back bottom corner lid", lambda: yfill(EX0, BZ0, 1, 1, RS0, YB, ER)),         # on RearStop's top, by the posts
    ("back bottom corner feet", lambda: yfill(EX1, BZ0, -1, 1, RS0, YB, ER)),
]

# The slot's openings: the entry on the front face (YF) runs from the floor top (Z 2.15), the back opening on the back
# face (YB) from RearStop's top (Z 228); both to the riser's top plate (Z 275.6), between the walls' inner faces
# (X -11.493 to 9.248). Their corners are R2: the floor coves at the entry's bottom, fills (FILLS) at the others.
EX0, EX1, EZ0, EZ1, ER = -11.493, 9.248, 2.15, 275.6, 2.0
BZ0 = 228.0
RS0 = 316.225                                       # RearStop's and the riser posts' laptop-side face


def yfill(x, z, sx, sz, y0, y1, r):
    """Fill of radius r for an inside corner along Y at (x, z); (sx, sz) point into the empty quadrant."""
    b = Part.makeBox(r, y1 - y0, r, V(min(x, x + sx * r), y0, min(z, z + sz * r)))
    return b.cut(Part.makeCylinder(r, y1 - y0 + 2, V(x + sx * r, y0 - 1, z + sz * r), V(0, 1, 0)))


def rail_space(name, x0):
    """The space a cartridge rail occupies (its 4 mm band, Y 316.225-341.225, Z -1.85-60.5) less the rail itself:
    cut after the fuse, it opens the rail's tongue groove and detent holes in the body, which is solid there."""
    rail = App.ActiveDocument.getObject(name + "_Rounded") or App.ActiveDocument.getObject(name)
    box = Part.makeBox(4.0, 341.225 - 316.225, 60.5 + 1.85, V(x0, 316.225, -1.85))
    return box.cut(rail.Shape).removeSplitter()


def opening_outline(yf, sy, z0, z1):
    """An R1.5 edge-round cutter swept round an opening's outline on the face Y = yf (sy points into the part), so the
    sides, bottom, top and the four R2 corners blend. The section is the cutters' own (1 mm out, RAD in, less the
    round), held square to the face. At the entry it runs unbroken past the front struts: they are fused after the
    cutters (MountFuse.AfterCutters)."""
    def arc(cx, cz, a0):
        pts = [V(cx + ER * math.cos(math.radians(a)), yf, cz + ER * math.sin(math.radians(a))) for a in (a0, a0 + 45, a0 + 90)]
        return Part.Arc(*pts).toShape()
    xc = (EX0 + EX1) / 2
    edges = [Part.LineSegment(V(xc, yf, z0), V(EX1 - ER, yf, z0)).toShape(),
             arc(EX1 - ER, z0 + ER, 270), Part.LineSegment(V(EX1, yf, z0 + ER), V(EX1, yf, z1 - ER)).toShape(),
             arc(EX1 - ER, z1 - ER, 0), Part.LineSegment(V(EX1 - ER, yf, z1), V(EX0 + ER, yf, z1)).toShape(),
             arc(EX0 + ER, z1 - ER, 90), Part.LineSegment(V(EX0, yf, z1 - ER), V(EX0, yf, z0 + ER)).toShape(),
             arc(EX0 + ER, z0 + ER, 180), Part.LineSegment(V(EX0 + ER, yf, z0), V(xc, yf, z0)).toShape()]
    spine = Part.Wire(Part.__sortEdges__(edges))
    # section in the plane X = xc at the start: out of the opening is +Z here, into the material -Z, into the part sy
    yo, yi = yf - sy, yf + sy * RAD
    sq = Part.makePolygon([V(xc, yo, z0 + 1), V(xc, yi, z0 + 1), V(xc, yi, z0 - RAD), V(xc, yo, z0 - RAD), V(xc, yo, z0 + 1)])
    disk = Part.Face(Part.Wire(Part.makeCircle(RAD, V(xc, yi, z0 - RAD), V(1, 0, 0))))
    sec = Part.Face(sq).cut(disk).Faces[0].OuterWire
    ps = Part.BRepOffsetAPI.MakePipeShell(spine)
    ps.setBiNormalMode(V(0, 1, 0))
    ps.add(sec, False, False)
    ps.build()
    ps.makeSolid()
    c = ps.shape()
    return Part.Solid(c.Shells[0]) if not c.Solids else c.Solids[0]


CUTTERS = [
    # the plate's bottom edge goes before the verticals that cross it: cut after them, its end at the feet-side back
    # corner leaves two self-intersecting vertices (strict check fails)
    ("plate feet bottom edge", lambda: ycut(XG, 278, -1, 1, YF - 2, YB + 2)),     # also trims the three gusset tips
    ("plate+wall lid front vertical", lambda: vcut(XL, YF, 1, 1, -3, 284)),
    ("plate feet front vertical", lambda: vcut(XG, YF, -1, 1, 240, 284)),
    ("plate feet back vertical", lambda: vcut(XG, YB, -1, -1, 240, 284)),
    ("wall feet front vertical", lambda: vcut(XR, YF, -1, 1, -3, 243)),
    ("front bottom edge", lambda: xcut(YF, -1.85, 1, 1, -21, 19)),
    ("entry outline", lambda: opening_outline(YF, 1, EZ0, EZ1)),     # R1.5 all round the slot entry, corners blended
    ("back opening outline", lambda: opening_outline(YB, -1, BZ0, EZ1)),   # the same round the riser's back opening
    ("rail lid grooves", lambda: rail_space("CartRail_Lid", -15.493)),       # the body is solid where the rails go
    ("rail feet grooves", lambda: rail_space("CartRail_Feet", 9.248)),
    ("wall lid back vertical", lambda: vcut(XL, YB, 1, -1, 60.5, 284)),   # up through the riser to DeskPlate's round
    ("wall feet back vertical", lambda: vcut(XR, YB, -1, -1, 60.5, 243)),
]


class MountFuse:
    def __init__(self, obj):
        obj.addProperty("App::PropertyLinkList", "Shapes", "Fuse", "Parts in fuse order")
        obj.addProperty("App::PropertyFloat", "Fuzzy", "Fuse", "Fuzzy tolerance of the fuse").Fuzzy = 1e-5
        obj.addProperty("App::PropertyLink", "Fills", "Fuse", "Compound of inside-corner fills, added before the cutters")
        obj.addProperty("App::PropertyLink", "Cutters", "Fuse", "Compound of edge-round cutters, applied in order")
        obj.addProperty("App::PropertyLinkList", "AfterCutters", "Fuse", "Parts fused last, after the cutters (the struts)")
        obj.addProperty("App::PropertyFloat", "CutterFuzzy", "Fuse", "Fuzzy tolerance for a cutter that the plain cut rejects").CutterFuzzy = 1e-4
        obj.addProperty("App::PropertyStringList", "Report", "Fuse", "Result of the last recompute")
        obj.setEditorMode("Report", 1)
        obj.Proxy = self

    def execute(self, obj):
        ps = [o.Shape for o in obj.Shapes]
        m = ps[0].fuse(ps[1:], obj.Fuzzy)
        if not m.Solids or not m.isValid():            # one fuse of all parts can fail where part-by-part works
            m = ps[0]
            for s in ps[1:]:
                m = m.fuse(s, obj.Fuzzy)
        report = ["fused: valid %s, %d solids, %.3f cm3" % (m.isValid(), len(m.Solids), m.Volume / 1000)]
        slivers = [x for x in m.Solids if x.Volume < 1.0]      # zero-volume pieces where two parts' faces touch
        if slivers and len(m.Solids) - len(slivers) == 1:
            m = [x for x in m.Solids if x.Volume >= 1.0][0]
            report.append("dropped %d zero-volume sliver solid(s)" % len(slivers))
        if getattr(obj, "Fills", None):
            for k, f in enumerate(obj.Fills.Shape.Solids):
                gap = f.Volume - m.common(f).Volume            # the fill's volume outside the body
                t = m.fuse(f, obj.Fuzzy)
                ok = t.isValid() and len(t.Solids) == 1 and abs(t.Volume - m.Volume - gap) < 0.5
                label = FILLS[k][0] if k < len(FILLS) else "fill %d" % k
                report.append("%s: added %.2f mm3%s" % (label, t.Volume - m.Volume, "" if ok else ", SKIPPED"))
                if ok:
                    m = t
        if obj.Cutters:
            for k, c in enumerate(obj.Cutters.Shape.Solids):
                inside = m.common(c).Volume                      # a broken cut can remove material outside the cutter
                for tol in (0, obj.CutterFuzzy):
                    t = m.cut(c, tol) if tol else m.cut(c)
                    ok = t.isValid() and len(t.Solids) == 1 and abs(m.Volume - t.Volume - inside) < 0.5
                    if ok:
                        break
                label = CUTTERS[k][0] if k < len(CUTTERS) else "cutter %d" % k
                report.append("%s: removed %.2f mm3%s" % (label, m.Volume - t.Volume, "" if ok else ", SKIPPED"))
                if ok:
                    m = t
        for o in getattr(obj, "AfterCutters", None) or []:       # the struts go on last, so no round is cut into them
            t = m.fuse(o.Shape, obj.Fuzzy)
            report.append("%s fused after the cutters: %d solids, added %.2f mm3" % (o.Label, len(t.Solids), t.Volume - m.Volume))
            m = t
        report.append("result: valid %s, %d solids, %.3f cm3" % (m.isValid(), len(m.Solids), m.Volume / 1000))
        obj.Report = report
        obj.Shape = m

    def dumps(self):
        return None

    def loads(self, state):
        return None


def create(d):
    """(Re)create Corner_Cutters and the Mount_Rounded feature in Print_Bodies."""
    for n in ("Mount_Rounded", "Corner_Cutters", "Corner_Fills"):
        if d.getObject(n):
            d.removeObject(n)
    cut = d.addObject("Part::Feature", "Corner_Cutters")
    cut.Shape = Part.makeCompound([f() for _, f in CUTTERS])
    fill = d.addObject("Part::Feature", "Corner_Fills")
    fill.Shape = Part.makeCompound([f() for _, f in FILLS])
    rounded = {o.Name for o in d.Objects if o.Name.endswith("_Rounded")}
    parts = [d.getObject(o.Name + "_Rounded") if o.Name + "_Rounded" in rounded else o for o in d.getObject("Mount_Fused").Shapes]
    after = [o for o in parts if o.Name == "Mount_Breakaway_Struts"]
    parts = [o for o in parts if o not in after]
    obj = d.addObject("Part::FeaturePython", "Mount_Rounded")
    MountFuse(obj)
    obj.Shapes = parts
    obj.Fills = fill
    obj.Cutters = cut
    obj.AfterCutters = after
    if App.GuiUp:
        obj.ViewObject.Proxy = 0
        cut.ViewObject.Visibility = False
        fill.ViewObject.Visibility = False
    d.getObject("Print_Bodies").addObject(obj)
    d.getObject("Rounding").addObject(cut)
    d.getObject("Rounding").addObject(fill)
    d.recompute()
    return obj
