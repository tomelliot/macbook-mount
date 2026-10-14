# Run inside the FreeCAD GUI after fc_headless.py: exec(open("dfm/fc_gui.py").read()) (freecad-mcp execute_code).
# 1. Rebuilds the live Measure objects for checks 10-12 and 18 (group DFM_Measures) and writes 03_measures.json.
# 2. Loads the cartridge-zone clip cut by fc_headless.py (booleans on the full mount have crashed the GUI).
# 3. Re-anchors the DFM_Clearances dimensions by geometry, because TechDraw stores dimension references as edge
#    indices and the indices change whenever the model changes.
# 4. Saves the 01_* model views and exports the TechDraw sheets DFM_Clearances and DFM_Mount_Structure as PDF.
# TechDraw views and dimensions must stay visible (a 'hide everything' in the GUI hides them too).
import json
import os
import time

import FreeCAD as App
import FreeCADGui as Gui
import Part
import TechDrawGui

V = App.Vector
ROOT = "/Users/tom/projects/fun/macbook-mount"
EV = ROOT + "/dfm/evidence/"
TMP = os.environ.get("DFM_TMP", "/tmp/deskmount_dfm")
d = App.getDocument("DeskMount")


# ---------------------------------------------------------------- 1. measures
def measures():
    """Live Measure::MeasureDistance objects linked to the source parts' faces. The group is rebuilt each run, because
    face numbers change when a part's shape is replaced."""
    MOUNT = [d.getObject(n) for n in ("Wall_Lid", "Wall_Feet", "CartRail_Lid", "CartRail_Feet", "Floor", "RearStop")]
    CART = [d.getObject(n) for n in ("Cart_Body_Cut", "Cart_Tongue_Lid", "Cart_Tongue_Feet", "Cart_Detent_Lid", "Cart_Detent_Feet")]
    XL = d.getObject("Wall_Lid").Shape.BoundBox.XMax
    XF = d.getObject("Wall_Feet").Shape.BoundBox.XMin
    PORT_X = -0.919

    def hits(objs, a, b):
        """Solid segments along a->b for a group of parts, as sorted (s0, s1) distances from a."""
        edge = Part.LineSegment(a, b).toShape()
        axis = (b - a).normalize()
        segs = []
        for o in objs:
            for e in o.Shape.common(edge).Edges:
                segs.append(tuple(sorted(((e.Vertexes[0].Point - a).dot(axis), (e.Vertexes[-1].Point - a).dot(axis)))))
        return sorted(segs), axis

    def face_at(objs, p, axis):
        for o in objs:
            for i, f in enumerate(o.Shape.Faces):
                if f.Surface.__class__.__name__ == "Plane" and abs(f.normalAt(0, 0).dot(axis)) > 0.999 \
                        and f.distToShape(Part.Vertex(p))[0] < 1e-4:
                    return o, "Face%d" % (i + 1)
        raise RuntimeError("no face at %s" % p)

    def pair(first, second, a, b):
        """Faces bounding the first gap on a->b that runs from a `first` segment to a `second` segment."""
        s1, axis = hits(first, a, b)
        s2, _ = hits(second, a, b)
        tagged = sorted([(s, 1) for s in s1] + [(s, 2) for s in s2])
        for ((x0, x1), t1), ((y0, y1), t2) in zip(tagged, tagged[1:]):
            if t1 == 1 and t2 == 2:
                return face_at(first, a + axis * x1, axis), face_at(second, a + axis * y0, axis)
        raise RuntimeError("no gap on probe")

    PROBES = [
        # label, check, first group, second group, ray start, ray end, design value
        # (the flex arm's outer face is the same plane face as the tongue tip, so the tip measures cover the arm too)
        ("Tongue to groove, front face (feet, Z 10)", 10, MOUNT, CART, V(XF + 1, 320, 10), V(XF + 1, 340, 10), 0.4),
        ("Tongue to groove, rear face (feet, Z 10)", 10, CART, MOUNT, V(XF + 1, 320, 10), V(XF + 1, 340, 10), 0.4),
        ("Tongue to groove, front face (lid, Z 10)", 10, MOUNT, CART, V(XL - 1, 320, 10), V(XL - 1, 340, 10), 0.4),
        ("Tongue to groove, rear face (lid, Z 10)", 10, CART, MOUNT, V(XL - 1, 320, 10), V(XL - 1, 340, 10), 0.4),
        ("Tongue tip and arm to groove bottom (feet, Z 10)", 10, CART, MOUNT, V(0, 332, 10), V(XF + 6, 332, 10), 0.4),
        ("Tongue tip and arm to groove bottom (lid, Z 10)", 10, CART, MOUNT, V(0, 332, 10), V(XL - 6, 332, 10), 0.4),
        ("Cartridge front to RearStop (Z 10)", 11, MOUNT, CART, V(5, 315, 10), V(5, 330, 10), 0.5),
        # the pads sit above the rails and behind the walls' rear end (walls end at Y 320.2 above Z 60.5)
        ("Squeeze pad to rail top (feet, X 12.5)", 12, CART, MOUNT, V(12.5, 328, 67), V(12.5, 328, 50), None),
        ("Squeeze pad to rail top (lid, X -14.7)", 12, CART, MOUNT, V(-14.7, 328, 67), V(-14.7, 328, 50), None),
        ("Squeeze pad to wall rear end (feet, Z 67)", 12, CART, MOUNT, V(14, 336, 67), V(14, 310, 67), None),
        ("Squeeze pad to wall rear end (lid, Z 67)", 12, CART, MOUNT, V(-16.5, 336, 67), V(-16.5, 310, 67), None),
        ("Cartridge base on Floor (Z 2.15)", 18, MOUNT, CART, V(5, 325, -1), V(5, 325, 10), 0.0),
    ]

    old = d.getObject("DFM_Measures")
    if old:
        for o in list(old.Group):
            d.removeObject(o.Name)
        d.removeObject(old.Name)
    grp = d.addObject("App::DocumentObjectGroup", "DFM_Measures")
    d.getObject("DFM").addObject(grp)
    rows = []

    def add(label, check, design, o1, f1, o2, f2):
        m = d.addObject("Measure::MeasureDistance", "M_%02d" % (len(rows) + 1))
        m.Label2 = "Check %d: %s" % (check, label)      # Label is overwritten with the value by FreeCAD
        m.Element1 = (o1, [f1])
        m.Element2 = (o2, [f2])
        m.ViewObject.Visibility = False
        grp.addObject(m)
        rows.append((m, label, check, design, o1.Name + "." + f1, o2.Name + "." + f2))

    for label, check, first, second, a, b, design in PROBES:
        (o1, f1), (o2, f2) = pair(first, second, a, b)
        add(label, check, design, o1, f1, o2, f2)
    # check 18: port centre height above the floor datum, from the pocket floor and roof faces
    PX = PORT_X + 2.8          # beside the 5 mm cable slot, which opens the roof over the port centre
    seg, axis = hits(CART, V(PX, 324, 0), V(PX, 324, 75))
    fo, ff = face_at(MOUNT, V(5, 325, 2.15), V(0, 0, 1))
    for name, z in (("pocket floor", seg[0][1]), ("pocket roof", seg[1][0])):
        co, cf = face_at(CART, V(PX, 324, z), V(0, 0, 1))
        add("Floor top to %s" % name, 18, None, fo, ff, co, cf)
    d.recompute()

    out = [{"object": m.Name, "check": c, "measure": l, "design_mm": dz, "measured_mm": round(m.Distance.Value, 3),
            "between": [e1, e2]} for m, l, c, dz, e1, e2 in rows]
    lo, hi = out[-2]["measured_mm"], out[-1]["measured_mm"]
    out.append({"check": 18, "measure": "Pocket centre above floor top (derived)", "measured_mm": round((lo + hi) / 2, 3),
                "port_centre_above_floor_mm": round(50.44 - 2.15, 3)})
    json.dump(out, open(EV + "03_measures.json", "w"), indent=1)
    for r in out:
        print(r)


# ---------------------------------------------------------------- 3. dimension anchors
TOL = 0.03                                     # view units (scaled mm)


def ends(e):
    return [(p.x, p.y) for p in (e.Vertexes[0].Point, e.Vertexes[-1].Point)]


def visible(view):
    return {"Edge%d" % i: e for i, e in enumerate(view.getVisibleEdges())}


def mirror(bad, good):
    """Point dimension `bad` at the X-mirror (view X -> -X) of the edges `good` references, in the same view."""
    g = d.getObject(good)
    view, names = g.References2D[0][0], g.References2D[0][1]
    edges = visible(view)
    refs = []
    for n in names:
        want = sorted((-x, y) for x, y in ends(edges[n]))
        hit = [m for m, e in edges.items() if all(abs(a[0] - b[0]) < TOL and abs(a[1] - b[1]) < TOL for a, b in zip(sorted(ends(e)), want))]
        if not hit:
            raise RuntimeError("no mirror of %s.%s for %s" % (view.Name, n, bad))
        refs.append(hit[0])
    b = d.getObject(bad)
    b.Type = g.Type
    b.References2D = [(view, tuple(refs))]


def spacing(dim, view_name, mm, xwin, horizontal=True):
    """Point `dim` at the two parallel edges (horizontal or vertical in the view) `mm` apart, overlapping inside xwin."""
    view = d.getObject(view_name)
    target = mm * view.Scale
    lines = []
    for n, e in visible(view).items():
        (x0, y0), (x1, y1) = ends(e)
        if horizontal and abs(y0 - y1) < 1e-6 and abs(x1 - x0) > 0.5:
            lo, hi = sorted((x0, x1))
            if hi > xwin[0] and lo < xwin[1]:
                lines.append((n, y0, lo, hi))
        if not horizontal and abs(x0 - x1) < 1e-6 and abs(y1 - y0) > 0.5:
            lo, hi = sorted((y0, y1))
            lines.append((n, x0, lo, hi))
    best = None
    for i, a in enumerate(lines):
        for b in lines[i + 1:]:
            if abs(abs(a[1] - b[1]) - target) < TOL * 3:
                ov = min(a[3], b[3]) - max(a[2], b[2])
                if best is None or ov > best[0]:
                    best = (ov, a[0], b[0])
    if best is None:
        raise RuntimeError("no edge pair %.2f mm apart in %s for %s" % (mm, view_name, dim))
    o = d.getObject(dim)
    o.Type = "DistanceY" if horizontal else "DistanceX"
    o.References2D = [(view, (best[1], best[2]))]


def anchor_dims():
    for bad, good in {"DFM_Dim003": "DFM_Dim002", "DFM_Dim006": "DFM_Dim005", "DFM_Dim008": "DFM_Dim007", "DFM_Dim013": "DFM_Dim012"}.items():
        mirror(bad, good)
    spacing("DFM_Dim009", "DFM_Sec_Z67", 6.775, (10, 70))       # D-D (Z 67): squeeze pad front face to the wall's rear end
    spacing("DFM_Dim010", "DFM_Sec_Z67", 6.775, (-70, -10))
    spacing("DFM_Dim011", "DFM_Sec_Y332", 58.35, (25, 50))      # E-E (Y 332): tongue bottom (Z 2.15) to groove top (Z 60.5)
    for o in d.getObject("DFM_Clearances").Views:
        if o.TypeId == "TechDraw::DrawViewDimension":
            o.FormatSpec = "%.2f"
            o.FormatSpecOverTolerance = o.FormatSpecUnderTolerance = "%.2f"
    d.recompute()
    for o in d.getObject("DFM_Clearances").Views:
        if o.TypeId == "TechDraw::DrawViewDimension":
            print(o.Name, o.References2D[0][0].Name, o.References2D[0][1], round(o.getRawValue(), 3))


# ---------------------------------------------------------------- 4. model views and drawings
def pump(n, dt=0.5):
    for _ in range(n):
        Gui.updateGui()
        time.sleep(dt)


def shots():
    v = Gui.getDocument("DeskMount").mdiViewsOfType("Gui::View3DInventor")[0]   # not ActiveView: a page may be active
    mount = [d.getObject("Mount_Rounded")]             # print bodies, with struts and ties as printed
    cart = [d.getObject("USBC_Cartridge_Rounded")]
    lap = list(d.getObject("Laptop").Group)
    allo = [o for o in d.Objects if getattr(o, "ViewObject", None) and o.TypeId.startswith(("Part::", "Mesh::", "Measure::"))]
    shown = [o for o in allo if o.ViewObject.Visibility]

    def shot(objs, views, prefix):
        for o in allo:
            o.ViewObject.Visibility = o in objs
        Gui.updateGui()
        for name, fn in views:
            getattr(v, fn)()
            Gui.updateGui()
            v.fitAll()
            Gui.updateGui()
            v.saveImage(EV + prefix + name + ".png", 1400, 1000, "White")

    shot(mount, [("iso", "viewIsometric"), ("right", "viewRight"), ("back", "viewRear"), ("bottom", "viewBottom")], "01_mount_")
    shot(cart, [("iso", "viewIsometric"), ("front", "viewFront"), ("right", "viewRight")], "01_cartridge_")
    shot(mount + cart + lap, [("iso", "viewIsometric")], "01_assembly_")
    for o in allo:
        o.ViewObject.Visibility = o in shown


def drawings():
    for page, name in (("DFM_Clearances", "03_clearance_sections"), ("DFM_Mount_Structure", "09_mount_structure")):
        d.getObject(page).ViewObject.doubleClicked()      # the export draws from the open page window
        pump(6)
        TechDrawGui.exportPageAsPdf(d.getObject(page), EV + name + ".pdf")


measures()
d.getObject("DFM_Clip_Cartridge_Zone").Shape = Part.read(TMP + "/clip_cart_zone.brep")
for page in ("DFM_Clearances", "DFM_Mount_Structure"):
    for vw in d.getObject(page).Views:
        vw.touch()
d.recompute()
views = [vw for page in ("DFM_Clearances", "DFM_Mount_Structure") for vw in d.getObject(page).Views
         if vw.TypeId in ("TechDraw::DrawViewPart", "TechDraw::DrawViewSection")]
for _ in range(240):                      # TechDraw hidden-line removal runs in the background: wait for every view
    Gui.updateGui()
    if all(vw.getVisibleEdges() for vw in views):
        break
    time.sleep(0.5)
else:
    raise RuntimeError("TechDraw views still empty after 120 s")
anchor_dims()
pump(10)                                  # let the dimensions update on the finished views
shots()
drawings()
d.save()
print("ok")
