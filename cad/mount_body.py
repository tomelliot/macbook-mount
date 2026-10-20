# The mount body (walls, riser, floor, RearStop, DeskPlate, gussets): MountSolid, a PartDesign Body of the plain features,
# less MountCellTools, one rounded tool per lattice cell, as the Part::Cut MountBody. It is a part of Mount_Fused with
# the cartridge rails and the breakaway struts.
#   BUILD_BODY=1 freecadcmd cad/mount_body.py   rebuilds MountBody in DeskMount.FCStd and saves it (close the model in
#                                               the GUI first, or reload it after); then cad/build_rounding.sh MountBody
#                                               and cad/recompute_mount.py
# MountSolid: the side profile padded across the full width, the laptop cavity (its R2 bottom corners are the floor
# coves), the riser's end openings and the cartridge zone as pockets, DeskPlate and the gussets as pads. The cells are
# known from the lattice (cell_loops), so their rounds are built into their tools, not searched for: each tool is the
# cell's R1.5 prism with an R0.4 lip at every face it opens on (walls' outer and cavity faces, the floor's faces,
# RearStop's faces). The skins and the riser band are left out of the prisms. cad/rounding.py rounds the edges left.
import math
import os
import time

import FreeCAD as App
import Part

V = App.Vector
ROOT = "/Users/tom/projects/fun/macbook-mount"
MODEL = ROOT + "/DeskMount.FCStd"
SUBS = ("CellsAY", "CellsAZ", "CellsBY", "CellsBZ")    # the MultiTransforms' sub-transformations (not in the Body)

XL, XR, XG = -19.493, 17.248, 52.248            # lid wall outer face, feet wall outer face, DeskPlate edge
XI0, XI1 = -11.493, 9.248                        # the slot (walls' inner faces)
YF, YR, YB, YT = 27.0, 316.225, 320.225, 341.225  # front, RearStop's laptop face, back, cartridge tail end
Z0, ZF, ZTAIL, ZTOP, ZP = -1.85, 2.15, 60.5, 278.0, 282.0
T, P, R_CELL = 2.4, 40.0, 1.5
ZGUS = 235.0             # the gussets' lowest corner: a rib crossing of the feet wall's lattice under the middle gusset
                         # (Y 171), so the corner is supported; the lattice crossings in that column are Z 35 + 40k
H = (P - T * math.sqrt(2)) / 2                   # cell half-diagonal, 18.30


def rot(x, y, z):
    return App.Rotation(V(*x), V(*y), V(*z), "ZXY")


YZ = rot((0, 1, 0), (0, 0, 1), (1, 0, 0))        # sketch u = Y, v = Z, normal +X
XZ = rot((1, 0, 0), (0, 0, 1), (0, -1, 0))       # sketch u = X, v = Z, normal -Y
XY = App.Rotation()                              # sketch u = X, v = Y, normal +Z


def rounded(pts, r):
    """Closed polygon (2D points) as sketch geometry, its corners rounded to r: one radius, or one per corner (0: sharp)."""
    n = len(pts)
    rs = list(r) if isinstance(r, (list, tuple)) else [r] * n
    P2 = [V(p[0], p[1], 0) for p in pts]
    if not any(rs):
        return [Part.LineSegment(P2[i], P2[(i + 1) % n]) for i in range(n)]
    ends, arcs = [], []
    for i in range(n):
        p, a, b = P2[i], P2[i - 1], P2[(i + 1) % n]
        if rs[i] <= 0:
            ends.append((p, p))
            arcs.append(None)
            continue
        u, w = (a - p).normalize(), (b - p).normalize()
        th = math.acos(max(-1.0, min(1.0, u.dot(w))))
        t = rs[i] / math.tan(th / 2)
        bis = (u + w).normalize()
        c = p + bis * (rs[i] / math.sin(th / 2))
        t1, t2 = p + u * t, p + w * t
        arcs.append(Part.Arc(t1, c - bis * rs[i], t2))
        ends.append((t1, t2))
    out = []
    for i in range(n):
        if arcs[i] is not None:
            out.append(arcs[i])
        out.append(Part.LineSegment(ends[i][1], ends[(i + 1) % n][0]))
    return out


def clip(poly, y0, y1, z0, z1):
    """Convex polygon clipped to a rectangle (Sutherland-Hodgman)."""
    def cut(pts, inside, cross):
        out = []
        for i in range(len(pts)):
            p, q = pts[i - 1], pts[i]
            if inside(q):
                if not inside(p):
                    out.append(cross(p, q))
                out.append(q)
            elif inside(p):
                out.append(cross(p, q))
        return out

    def at_u(u):
        return lambda p, q: (u, p[1] + (q[1] - p[1]) * (u - p[0]) / (q[0] - p[0]))

    def at_v(v):
        return lambda p, q: (p[0] + (q[0] - p[0]) * (v - p[1]) / (q[1] - p[1]), v)
    for inside, cross in ((lambda p: p[0] >= y0, at_u(y0)), (lambda p: p[0] <= y1, at_u(y1)),
                          (lambda p: p[1] >= z0, at_v(z0)), (lambda p: p[1] <= z1, at_v(z1))):
        poly = cut(poly, inside, cross) if poly else poly
    out = []
    for p in poly:                               # drop repeated points
        if not out or abs(p[0] - out[-1][0]) > 1e-6 or abs(p[1] - out[-1][1]) > 1e-6:
            out.append(p)
    if len(out) > 1 and abs(out[0][0] - out[-1][0]) < 1e-6 and abs(out[0][1] - out[-1][1]) < 1e-6:
        out.pop()
    return out if len(out) >= 3 else []


def clip_cell(c, h, y0, y1, z0, z1, snap=1.0):
    """A diamond (centre c, half-diagonal h) clipped to a rectangle. A side closer than snap to the cell's widest line
    moves onto that line, so the clipped cell has no sliver of side that would force its corner rounds small."""
    if 0 < c[0] - y0 < snap: y0 = c[0]
    if 0 < y1 - c[0] < snap: y1 = c[0]
    if 0 < c[1] - z0 < snap: z0 = c[1]
    if 0 < z1 - c[1] < snap: z1 = c[1]
    return clip([(c[0] + h, c[1]), (c[0], c[1] + h), (c[0] - h, c[1]), (c[0], c[1] - h)], y0, y1, z0, z1)


def area(poly):
    return abs(sum(poly[i - 1][0] * poly[i][1] - poly[i][0] * poly[i - 1][1] for i in range(len(poly)))) / 2


def rounded_fit(pts, r):
    """rounded(), with r reduced where two corners' rounds would overlap on a short side."""
    n = len(pts)
    P2 = [V(p[0], p[1], 0) for p in pts]
    k = []
    for i in range(n):
        u, w = (P2[i - 1] - P2[i]).normalize(), (P2[(i + 1) % n] - P2[i]).normalize()
        k.append(1 / math.tan(math.acos(max(-1.0, min(1.0, u.dot(w)))) / 2))     # tangent length per unit radius
    for i in range(n):
        side = (P2[(i + 1) % n] - P2[i]).Length
        r = min(r, 0.95 * side / (k[i] + k[(i + 1) % n]))
    return rounded(pts, r)


def sketch(body, name, placement, loops):
    sk = body.newObject("Sketcher::SketchObject", name)
    sk.MapMode = "Deactivated"
    sk.Placement = placement
    for g in loops:
        sk.addGeometry(g, False)
    return sk


def diamond(cu, cv, h=H, r=R_CELL):
    return rounded([(cu + h, cv), (cu, cv + h), (cu - h, cv), (cu, cv - h)], r)


def report(doc, f, t0):
    doc.recompute()
    s = f.Shape
    print("STEP %-14s %-8s valid %s solids %d vol %.1f cm3 (%.0fs)" % (
        f.Name, "OK" if "Invalid" not in f.State and not s.isNull() else "FAILED", s.isValid() if not s.isNull() else None,
        len(s.Solids) if not s.isNull() else 0, (s.Volume / 1000) if not s.isNull() else 0, time.time() - t0), flush=True)


def strict_fails(shape, step=60.0, margin=8.0):
    """Y blocks where the strict (BOP self-intersection) check fails. isValid() misses these: a PartDesign fillet can
    return a valid shape that intersects itself, and every fillet test in cad/rounding.py then fails on it.
    Checked in crops: the whole-shape check takes over an hour on this body."""
    bb, out, a = shape.BoundBox, [], shape.BoundBox.YMin
    while a < bb.YMax:
        c = shape.common(Part.makeBox(bb.XLength + 2, step + 2 * margin, bb.ZLength + 2,
                                      App.Vector(bb.XMin - 1, a - margin, bb.ZMin - 1)))
        try:
            c.check(True)
        except Exception:
            out.append((round(a), round(a + step)))
        a += step
    return out


def remove(doc, name="MountBody"):
    """Remove an earlier MountBody (a Part::Cut, or the older PartDesign Body) with its tools, body and features."""
    o = doc.getObject(name)
    if o and o.TypeId == "Part::Cut":
        doc.removeObject(name)
        for n in ("MountCellTools", name.replace("Body", "Filled"), "MountFills"):
            if doc.getObject(n):
                doc.removeObject(n)
        name = name.replace("Body", "Solid")
    body = doc.getObject(name)
    if body:
        for o in list(body.Group):
            if o.Name in [x.Name for x in doc.Objects]:
                doc.removeObject(o.Name)
        doc.removeObject(body.Name)
    for n in SUBS:
        if doc.getObject(n):
            doc.removeObject(n)


# ---------------------------------------------------------------- the cells
RB = (169.8, 172.2, 228.0, ZTOP)                 # the riser band under the middle gusset: Y0, Y1, Z0, Z1, solid across
SKINS = [(YF + 4, YR, 19.0, 44.0), (YF + 4, YR, 186.0, 228.0)]   # the laptop-side skins: Y0, Y1, Z0, Z1, 2.4 mm deep
INNER = (YF, YR, ZF + 2.0, 228.0)                # the walls' cavity faces (above the floor coves): Y0, Y1, Z0, Z1
R_LIP = 0.4                                      # the cells' mouth rounds
RW = XI1 - XI0
RH = RW / 2 - T / math.sqrt(2)                   # RearStop's cell half-diagonal
XC = (XI0 + XI1) / 2


def cell_loops():
    """The cell outlines, as sketch geometry (one list per closed loop): wall cells in YZ, floor cells in XY (X, Y),
    RearStop cells in XZ. The lattice: diamonds on a 40 mm pitch (grid A at Y 31+40i, Z -5+40j; grid B offset half a
    pitch), clipped to the window between the frames with their corners R1.5."""
    wy0, wy1, wz0, wz1 = YF + 4, YR, ZF + 2 + 0.5, ZTOP - T   # 0.5 mm above the floor coves' top (ZF + 2): room
                                                               # for the bottom row's lips on the cavity faces
    TAIL_Y, TAIL_Z = 334.5, ZTAIL - 4.0            # the tail's rear frame and top frame (below Z 60.5)
    wall, cav = [], []
    for cy0, cz0 in ((31.0, -5.0), (11.0, 15.0)):
        for i in range(-1, 10):
            for j in range(-1, 9):
                c = (cy0 + P * i, cz0 + P * j)
                if c[0] > YR or c[1] + H <= ZTAIL:       # in the walls' tail behind RearStop: no rear column there,
                    poly = clip_cell(c, H, wy0, TAIL_Y, wz0, TAIL_Z)  # the cells run to the tail's own frames
                else:
                    poly = clip_cell(c, H, wy0, wy1, wz0, wz1)
                if poly and area(poly) > 12.0:
                    wall.append(rounded_fit(poly, R_CELL))
                    # between the walls the front and back openings and the cavity are open: there the cell is cut
                    # unclipped along Y (a corner rounded against an open line leaves a knife edge on the face)
                    cav.append(rounded_fit(clip_cell(c, H, -1e3, 1e3, wz0, wz1), R_CELL))
    # floor: the wall grid's diamonds in plan, clipped to the floor between its rails (along the walls, at the front
    # and in front of RearStop); the three cells under the felt dots are left out, so the floor is solid there
    fx0, fx1, fy0, fy1 = XI0 + T, XI1 - T, YF + T, YR - T
    floor = []
    for cx0, cy0 in ((XC, 31.0), (XC - P / 2, 11.0), (XC + P / 2, 11.0)):
        for k in range(-1, 9):
            c = (cx0, cy0 + P * k)
            if abs(c[0] - XC) < 1e-6 and c[1] in (71.0, 271.0):    # felt dots at Y 71 and 271: cells left out
                continue
            y0, y1 = fy0, fy1
            if abs(c[1] - 171.0) < 1e-6:                             # the felt dot at Y 171 falls between rows:
                continue                                             # a solid band Y 160.6-181.4 instead
            if abs(c[1] - 151.0) < 1e-6:
                y1 = 171.0 - RW / 2
            if abs(c[1] - 191.0) < 1e-6:
                y0 = 171.0 + RW / 2
            poly = clip_cell(c, H, fx0, fx1, y0, y1)
            if poly and area(poly) > 12.0:
                floor.append(rounded_fit(poly, R_CELL))
    # RearStop: a centre diamond and the two half-diamonds beside it, 7 times down the plate from its 2.4 mm border
    # under Z 228, then the bottom diamond and the plug window
    rtop = 228.0 - T - RH

    def half(xw, s, cz):                         # half-diamond against a wall, clipped by the 2.4 mm border
        xb = xw + s * T
        return rounded([(xb, cz + RH - T), (xw + s * RH, cz), (xb, cz - RH + T)][::(1 if s > 0 else -1)], R_CELL)
    rear = []
    for k in range(7):
        z = rtop - k * RW
        rear += [diamond(XC, z, RH), half(XI0, 1, z - RW / 2), half(XI1, -1, z - RW / 2)]
    rear.append(diamond(XC, rtop - 7 * RW, RH))
    rear.append(rounded([(-0.9195 - 4.75, 50.43875 - 7.75), (-0.9195 + 4.75, 50.43875 - 7.75),
                         (-0.9195 + 4.75, 50.43875 + 7.75), (-0.9195 - 4.75, 50.43875 + 7.75)], 1.0))
    return wall, floor, rear, cav


def loop_face(geom, rotation):
    """A flat face from one loop of sketch geometry, turned into a model plane through the origin."""
    f = Part.Face(Part.Wire(Part.__sortEdges__([g.toShape() for g in geom])))
    f.transformShape(App.Placement(V(0, 0, 0), rotation).toMatrix())
    return f


def rect_face(u0, u1, v0, v1, rotation):
    return loop_face(rounded([(u0, v0), (u1, v0), (u1, v1), (u0, v1)], 0), rotation)


def less(face, rects, rotation):
    """face less the rectangles (u0, u1, v0, v1) in its plane: the pieces, as faces."""
    out = face
    for r in rects:
        out = out.cut(rect_face(*r, rotation))
    return [f for f in out.Faces if f.Area > 1.0]


def lip(face, A, c, s, r=R_LIP):
    """The cutter that rounds a mouth: face (in the plane through the origin normal to the unit axis A) at A = c, the
    material on the side s (+1: beyond c along A). A slab of the face grown by r, from 1 mm in the air to r deep,
    less a circle swept r deep along the grown outline: what is left is the lip that an R0.4 round takes off.
    Sharp joins first (an arc of radius r at a sharp corner, such as a skin's edge, sweeps a self-crossing torus),
    then arc joins; None if neither gives a valid solid."""
    for join in (2, 0):
        try:
            ring = face.translated(A * c).makeOffset2D(r, join=join)
            slab = ring.translated(A * (-s * 1.0)).extrude(A * (s * (1.0 + r)))
            C = ring.OuterWire.translated(A * (s * r))
            e0 = C.Edges[0]
            ps = Part.BRepOffsetAPI.MakePipeShell(C)
            ps.setTransitionMode(2)
            ps.add(Part.Wire(Part.makeCircle(r, e0.valueAt(e0.FirstParameter), e0.tangentAt(e0.FirstParameter))))
            ps.build()
            ps.makeSolid()
            out = slab.cut(ps.shape())
            if out.isValid() and len(out.Solids) == 1:
                return out
        except Exception:
            pass
    return lip_by_fillet(face, A, c, s, r)


def lip_by_fillet(face, A, c, s, r=R_LIP):
    """The lip as what a fillet takes off a small plate with the same hole: the sweep fails on some outlines that mix
    arcs and sharp corners, but a fillet on a plate this simple holds. None if that fails too."""
    try:
        F = face.translated(A * c)
        plate = F.makeOffset2D(1.5, join=2).extrude(A * (s * 1.5)).cut(F.translated(A * (-s * 1.0)).extrude(A * (s * 4.0)))
        k = (0 if abs(A.x) > 0.5 else 1 if abs(A.y) > 0.5 else 2)
        es = [e for e in plate.Edges if abs((e.BoundBox.XMin, e.BoundBox.YMin, e.BoundBox.ZMin)[k] - c) < 1e-6
              and abs((e.BoundBox.XMax, e.BoundBox.YMax, e.BoundBox.ZMax)[k] - c) < 1e-6
              and F.OuterWire.distToShape(Part.Vertex(e.valueAt((e.FirstParameter + e.LastParameter) / 2)))[0] < 1e-6]
        out = plate.cut(plate.makeFillet(r, es))
        if out.isValid() and len(out.Solids) >= 1 and out.Volume > 0:
            return out
    except Exception:
        pass
    return None


def prism(face, A, a0, a1):
    return face.translated(A * a0).extrude(A * (a1 - a0))


def opened(faces, r=R_CELL):
    """The faces with their sharp convex corners rounded to r (an inward then outward offset): where a skin or the
    riser band clips a cell, the corner left in the band's solid becomes an R1.5 inside round. Corners already
    rounded to r or more stay as they are."""
    out = []
    for f in faces:
        try:
            g = f.makeOffset2D(-r, join=0)
            g = g.makeOffset2D(r, join=0) if g.Faces else g
            out += [x for x in g.Faces if x.Area > 1.0]
        except Exception:
            out.append(f)
    return out


def edge_cut(a, b, n1, n2, r):
    """Cutter that rounds the straight convex edge a-b to r: n1, n2 are the unit outward normals of its two faces."""
    d = b - a
    L = d.Length
    d.normalize()
    q = [a + n1 * u + n2 * v - d * 1.0 for u, v in ((-r, -r), (0.5, -r), (0.5, 0.5), (-r, 0.5), (-r, -r))]
    slab = Part.Face(Part.makePolygon(q)).extrude(d * (L + 2.0))
    return slab.cut(Part.makeCylinder(r, L + 4.0, a - (n1 + n2) * r - d * 2.0, d))


def edge_cut_g(a, b, n1, n2, r):
    """Cutter that rounds the straight convex edge a-b to r for faces at any angle (n1, n2: unit outward normals,
    both at right angles to the edge). No extension past a and b: the edge ends against solid."""
    d = b - a
    L = d.Length
    d.normalize()
    c = a - (n1 + n2) * (r / (1.0 + n1.dot(n2)))   # the round's centre, r from both faces, in the material
    t1, t2 = c + n1 * r, c + n2 * r
    q = [c, t1 + n1 * 0.3, a + (n1 + n2) * 0.3, t2 + n2 * 0.3, c]
    slab = Part.Face(Part.makePolygon(q)).extrude(d * L)
    return slab.cut(Part.makeCylinder(r, L + 2.0, c - d * 1.0, d))


def cross_round(piece, p, n1, r=R_LIP):
    """Cutter that rounds the edge along X (XI0 to XI1) where the cell piece's side crosses a face between the walls
    at p (YZ point), n1 the face's outward normal: what a fillet takes off a small block of that corner. A fillet
    follows a curved side (a cell corner's R1.5 on the face), which a straight quarter round does not.
    Used where the side is curved: on straight sides the quarter round (edge_cut_g) holds the strict check."""
    lo = [p.y - 2.5, p.z - 2.5]
    hi = [p.y + 2.5, p.z + 2.5]
    k = 0 if abs(n1.y) > 0.5 else 1                # the block lies on the material side of the face
    if (n1.y if k == 0 else n1.z) < 0:
        lo[k] = (p.y, p.z)[k]
    else:
        hi[k] = (p.y, p.z)[k]
    block = Part.makeBox(XI1 - XI0, hi[0] - lo[0], hi[1] - lo[1], V(XI0, lo[0], lo[1])).cut(
        prism(piece, V(1, 0, 0), XI0 - 1.0, XI1 + 1.0))
    es = [e for e in block.Edges if e.BoundBox.YLength < 1e-6 and e.BoundBox.ZLength < 1e-6
          and e.BoundBox.XLength > (XI1 - XI0) - 1e-3 and abs(e.BoundBox.YMin - p.y) < 1e-4 and abs(e.BoundBox.ZMin - p.z) < 1e-4]
    if len(es) != 1:
        return None
    out = block.cut(block.makeFillet(r, es))
    return out if out.isValid() and out.Volume > 0 else None


def crossings(face, line_pts, keep):
    """Where the outline of face (in the YZ plane) crosses the line through line_pts: [(point, unit normal of the
    outline into the face, True if the outline is curved there)], for points that keep(point) accepts."""
    out = []
    w = face.OuterWire
    for v in w.section(Part.makeLine(*line_pts)).Vertexes:
        p = v.Point
        if not keep(p):
            continue
        e = min(w.Edges, key=lambda e: e.distToShape(v)[0])
        t = e.tangentAt(e.Curve.parameter(p))
        n = V(0, -t.z, t.y)
        n.normalize()
        if face.distToShape(Part.Vertex(p + n * 0.05))[0] > 1e-6:
            n = -n
        out.append((p, n, not isinstance(e.Curve, Part.Line)))
    return out


def fill(a, b, n1, n2, r):
    """Fill that rounds the straight concave edge a-b to r: n1, n2 are the unit directions from the edge into the air
    along each face (the inside corner's two legs)."""
    d = b - a
    L = d.Length
    d.normalize()
    q = [a + n1 * u + n2 * v for u, v in ((0, 0), (r, 0), (r, r), (0, r), (0, 0))]
    sq = Part.Face(Part.makePolygon(q)).extrude(d * L)
    return sq.cut(Part.makeCylinder(r, L + 2.0, a + (n1 + n2) * r - d * 1.0, d))


def outer_rounds():
    """Cutters for the body's straight outer edges: R1.5 on the bottom edges, DeskPlate's top edges and the tail's end
    verticals (the bounding-box edges), R0.4 on the tail's top edges. The front and back verticals are rounded after
    the fuse (cad/mount_fuse.py)."""
    x, y, z = V(1, 0, 0), V(0, 1, 0), V(0, 0, 1)
    R = 1.5
    out = [edge_cut(V(XL, YF, Z0), V(XL, YT, Z0), -x, -z, R), edge_cut(V(XR, YF, Z0), V(XR, YT, Z0), x, -z, R),
           edge_cut(V(XL, YF, ZP), V(XL, YB, ZP), -x, z, R), edge_cut(V(XG, YF, ZP), V(XG, YB, ZP), x, z, R),
           edge_cut(V(XL, YF, ZP), V(XG, YF, ZP), -y, z, R), edge_cut(V(XL, YB, ZP), V(XG, YB, ZP), y, z, R),
           edge_cut(V(XL, YT, Z0), V(XL, YT, ZTAIL), -x, y, R), edge_cut(V(XR, YT, Z0), V(XR, YT, ZTAIL), x, y, R),
           edge_cut(V(XL, YB, ZTAIL), V(XL, YT, ZTAIL), -x, z, R_LIP), edge_cut(V(XR, YB, ZTAIL), V(XR, YT, ZTAIL), x, z, R_LIP),
           edge_cut(V(XL, YT, ZTAIL), V(XI0, YT, ZTAIL), y, z, R_LIP), edge_cut(V(XI1, YT, ZTAIL), V(XR, YT, ZTAIL), y, z, R_LIP),
           edge_cut(V(XL, YT, Z0), V(XR, YT, Z0), y, -z, R)]
    return out


def inside_fills():
    """Fills for straight inside corners: R1.5 under DeskPlate on the feet side, R0.5 at RearStop's inside corners
    (walls and floor, as the old RearStopRounds), R0.5 at the gussets' roots (where a cell opens beside the middle
    gusset, the cell's hole takes the fill away), R0.4 in the cavity's top corners and the openings' inside corners."""
    x, y, z = V(1, 0, 0), V(0, 1, 0), V(0, 0, 1)
    rs = 0.5
    out = [fill(V(XR, YF, ZTOP), V(XR, YB, ZTOP), x, -z, 1.5),
           fill(V(XI0, YR, ZF), V(XI0, YR, 228.0), x, -y, rs), fill(V(XI1, YR, ZF), V(XI1, YR, 228.0), -x, -y, rs),
           fill(V(XI0, YR, ZF), V(XI1, YR, ZF), -y, z, rs)]
    for xw, sx in ((XI0, 1), (XI1, -1)):         # R0.4 (clear of the laptop): the cavity's top corners and the
        out.append(fill(V(xw, YF, 228.0), V(xw, YR, 228.0), x * sx, -z, R_LIP))          # openings' inside corners
        out.append(fill(V(xw, YF + 4, 228.0), V(xw, YF + 4, ZTOP - T), x * sx, -y, R_LIP))
        out.append(fill(V(xw, YR, 228.0), V(xw, YR, ZTOP - T), x * sx, y, R_LIP))
    out.append(fill(V(XI0, YF + 4, ZTOP - T), V(XI1, YF + 4, ZTOP - T), -y, -z, R_LIP))   # the openings' top
    out.append(fill(V(XI0, YR, ZTOP - T), V(XI1, YR, ZTOP - T), y, -z, R_LIP))           # inside corners
    for y0 in (YF, RB[0], YB - T):               # the gussets' sides that are not on the outer faces
        for yf, sy in ((y0, -1), (y0 + T, 1)):
            if abs(yf - YF) < 1e-6 or abs(yf - YB) < 1e-6:
                continue
            out.append(fill(V(XR, yf, ZTOP), V(XG - 3.0, yf, ZTOP), y * sy, -z, rs))       # under DeskPlate
            out.append(fill(V(XR, yf, ZGUS + 1.2), V(XR, yf, ZTOP), x, y * sy, rs))         # on the feet wall, above the slope at the tip
    return out


def cell_tools():
    """One tool per cell: its R1.5 prism and an R0.4 lip at each face it opens on, so the cut leaves the cells' mouths
    rounded and no search is needed for them. The riser band and the skins are left out of the prisms (the hole edges
    at them are real edges, and the lips round them too). Returns (tools, lips left out)."""
    X, Y, Z = V(1, 0, 0), V(0, 1, 0), V(0, 0, 1)
    wall, floor, rear, cav = cell_loops()
    tools, failed = [], 0

    def add(parts, ls):
        """Fuse a cell's prisms, then its lips one by one: a lip that fails or would make the tool invalid is left
        out (its mouth edges go to cad/rounding.py)."""
        nonlocal failed
        t = parts[0]
        for q in parts[1:]:
            t = t.fuse(q)
        for q in ls:
            n = t.fuse(q) if q is not None else None
            if n is not None and n.isValid() and len(n.Solids) == len(t.Solids):   # 2 where the riser band splits a cell
                t = n
            else:
                failed += 1
        t = t.removeSplitter()
        for so in t.Solids:
            if so.Volume < 0:                    # a prism from a face whose normal points against the extrusion
                so.reverse()
        tools.append(t)

    def lips(faces, A, c, s):
        return [lip(f, A, c, s) for f in faces]

    rb = [(RB[0], RB[1], RB[2], RB[3])]
    gus = Part.makeBox(XG - XR + 3.0, RB[1] - RB[0], ZTOP - ZGUS + 1.0, V(XR - 1.0, RB[0], ZGUS))   # middle gusset
    for geom, gcav in zip(wall, cav):            # through the walls along X; YZ faces: u = Y, v = Z
        P0 = loop_face(geom, YZ)
        outer = opened(less(P0, rb, YZ))         # through the riser band's solid
        middle = opened(less(P0, rb + SKINS, YZ))   # through the skins' solid as well
        between = opened(less(loop_face(gcav, YZ), rb + [(YR, YB, -50.0, 228.0)], YZ))   # between the walls: not
        parts = [prism(f, X, XL - 1.0, XI0 - T) for f in outer] + [prism(f, X, XI0 - T, XI0) for f in middle] + \
                [prism(f, X, XI0, XI1) for f in between] + [prism(f, X, XI1, XI1 + T) for f in middle] + \
                [prism(f, X, XI1 + T, XR + 1.0) for f in outer]                          # through RearStop
        ls = lips(outer, X, XL, 1) + [q.cut(gus) if q is not None else None for q in lips(outer, X, XR, -1)]
        for f in between:                        # the cell's sides across the cavity's ceiling and the openings' faces
            for (p, n, curved), n1 in [(x, V(0, 0, -1)) for x in crossings(f, (V(0, -1e3, 228.0), V(0, 1e3, 228.0)),
                                                                    lambda p: YF + 4 < p.y < YR and not
                                                                    RB[0] - 0.01 <= p.y <= RB[1] + 0.01)] + \
                               [(x, V(0, -1, 0)) for x in crossings(f, (V(0, YF + 4, 0), V(0, YF + 4, 400)),
                                                                    lambda p: 228.0 < p.z < ZTOP - T)] + \
                               [(x, V(0, 1, 0)) for x in crossings(f, (V(0, YR, 0), V(0, YR, 400)),
                                                                   lambda p: 228.0 < p.z < ZTOP - T)]:
                try:                             # a fillet on a block where the side is curved; else a quarter round
                    ls.append(cross_round(f, p, n1) if curved else edge_cut_g(V(XI0, p.y, p.z), V(XI1, p.y, p.z), n1, n, R_LIP))
                except Exception:
                    ls.append(None)
        if abs(sum(f.Area for f in outer) - sum(f.Area for f in middle)) > 1.0:   # a skin in the cell: round the
            hole = Part.makeCompound([prism(f, X, XL - 1.0, XR + 1.0) for f in outer])  # skin's edges in the cell
            for q in lips(middle, X, XI0 - T, 1) + lips(middle, X, XI1 + T, -1):
                if q is not None:
                    q = q.common(hole)           # not the cell's own walls, where the hole runs on
                    ls.append(q if q.Solids else None)
        b = P0.BoundBox
        if INNER[0] <= b.YMin and b.YMax <= INNER[1] and INNER[2] <= b.ZMin and b.ZMax <= INNER[3]:
            inner = opened(less(P0, SKINS, YZ))  # a mouth on the cavity faces (where no skin closes it)
            cav = Part.makeBox(XR - XL + 4, INNER[1] - INNER[0], ZTOP + 10, V(XL - 2, INNER[0], Z0 - 5))
            for q in lips(inner, X, XI0, -1) + lips(inner, X, XI1, 1):
                ls.append(q.common(cav) if q is not None else None)   # not past RearStop's face (Y 316.2)
        add(parts, ls)
    for geom in floor:                           # through the floor along Z; XY faces
        f = loop_face(geom, XY)
        add([prism(f, Z, Z0 - 1.0, ZF + 1.0)], lips([f], Z, Z0, 1) + lips([f], Z, ZF, -1))
    for geom in rear:                            # through RearStop along Y; XZ faces lie in the plane Y = 0
        f = loop_face(geom, XZ)
        add([prism(f, Y, YR - 1.0, YB + 1.0)], lips([f], Y, YR, 1) + lips([f], Y, YB, -1))
    tools += outer_rounds()
    return tools, failed


def build(doc, name="MountBody"):
    """MountSolid (a PartDesign Body: the plain features) less MountCellTools (one rounded tool per cell) as the
    Part::Cut MountBody."""
    t0 = time.time()
    body = doc.addObject("PartDesign::Body", name.replace("Body", "Solid"))
    wid_pos, wid_neg = XR, -XL                     # pad from the X = 0 plane both ways

    # 1. side profile, padded across the full width
    outline = [(YF, Z0), (YT, Z0), (YT, ZTAIL), (YB, ZTAIL), (YB, ZTOP), (YF, ZTOP)]
    sk = sketch(body, "ProfileSketch", App.Placement(V(0, 0, 0), YZ), rounded(outline, 0))
    pad = body.newObject("PartDesign::Pad", "Profile")
    pad.Profile = sk
    pad.SideType = "Two sides"
    pad.Length, pad.Length2 = wid_pos, wid_neg
    report(doc, pad, t0)

    # 2. the laptop cavity: floor top to Z 228, front to RearStop; its bottom corners R2 are the floor coves (no
    # coves at the top: above Z 228 the riser is open over the slot)
    cav = rounded([(XI0, ZF), (XI1, ZF), (XI1, 228.0), (XI0, 228.0)], [2.0, 2.0, 0, 0])
    sk = sketch(body, "CavitySketch", App.Placement(V(0, YF, 0), XZ), cav)
    pk = body.newObject("PartDesign::Pocket", "Cavity")
    pk.Profile = sk
    pk.Type = "Length"
    pk.Length = YR - YF
    report(doc, pk, t0)

    # 3. the riser's end openings over the slot, Z 228 to its top plate
    for nm, y0, ln in (("FrontOpening", YF, 4.0), ("BackOpening", YR, YB - YR)):
        sk = sketch(body, nm + "Sketch", App.Placement(V(0, y0, 0), XZ),
                    rounded([(XI0, 228.0), (XI1, 228.0), (XI1, ZTOP - T), (XI0, ZTOP - T)], 0))
        pk = body.newObject("PartDesign::Pocket", nm)
        pk.Profile = sk
        pk.Type = "Length"
        pk.Length = ln
        report(doc, pk, t0)

    # 4. the cartridge's space behind RearStop: between the walls, floor top up, open at the back and the top. The
    # rails are separate parts; their grooves are opened after the fuse (mount_fuse: the rails' space less the rails)
    sk = sketch(body, "CartridgeSketch", App.Placement(V(0, 0, ZTAIL), XY),
                rounded([(XI0, YB), (XI1, YB), (XI1, YT + 1), (XI0, YT + 1)], 0))
    pk = body.newObject("PartDesign::Pocket", "CartridgeZone")
    pk.Profile = sk
    pk.Type = "Length"
    pk.Length = ZTAIL - ZF
    report(doc, pk, t0)

    # 5. DeskPlate and the three gussets under its overhang, down to ZGUS (a rib crossing, so the lowest corner is on
    # solid)
    sk = sketch(body, "DeskPlateSketch", App.Placement(V(0, 0, ZTOP), XY), rounded([(XL, YF), (XG, YF), (XG, YB), (XL, YB)], 0))
    dp = body.newObject("PartDesign::Pad", "DeskPlate")
    dp.Profile = sk
    dp.Length = ZP - ZTOP
    report(doc, dp, t0)
    for i, y0 in enumerate((YF, RB[0], YB - T)):
        sk = sketch(body, "GussetSketch%d" % i, App.Placement(V(0, y0, 0), XZ), rounded([(XR, ZTOP), (XG, ZTOP), (XR, ZGUS)], 0))
        gp = body.newObject("PartDesign::Pad", "Gusset%d" % i)
        gp.Profile = sk
        gp.Length = T
        gp.Reversed = True
        report(doc, gp, t0)

    # 6. the inside fills, then the cells and the outer edges: one cut with a rounded tool per cell and per edge
    t = time.time()
    tools, failed = cell_tools()
    tl = doc.addObject("Part::Feature", "MountCellTools")
    tl.Shape = tools[0].multiFuse(tools[1:])      # one shape: some tools overlap (a compound of them cuts nothing)
    print("TOOLS %d tools, %d lips left out (%.0fs)" % (len(tools), failed, time.time() - t), flush=True)
    wall, floor, rear, cav = cell_loops()
    holes = [prism(loop_face(g, YZ), V(1, 0, 0), XL - 5.0, XG + 5.0) for g in wall]
    fl = doc.addObject("Part::Feature", "MountFills")
    fs = inside_fills()
    fl.Shape = fs[0].multiFuse(fs[1:]).cut(holes[0].multiFuse(holes[1:]))   # no fill across a cell's opening
    base = doc.addObject("Part::MultiFuse", name.replace("Body", "Filled"))
    base.Shapes = [body, fl]
    base.Refine = False
    cut = doc.addObject("Part::Cut", name)
    cut.Base = base
    cut.Tool = tl
    cut.Refine = False
    for o in (body, tl, fl, base):
        if o.ViewObject:
            o.ViewObject.Visibility = False
    report(doc, cut, t0)
    return cut


if __name__ == "__main__" or os.environ.get("BUILD_BODY"):     # freecadcmd does not run a script as __main__
    d = App.openDocument(MODEL)
    remove(d)
    b = build(d)
    bad = strict_fails(b.Shape)
    print("STRICT MountBody %s" % ("ok" if not bad else "FAILS in Y blocks %s: the rounding cannot work on it" % bad), flush=True)
    if d.getObject("Source"):
        d.getObject("Source").addObject(b)
    if d.getObject("Mount_Fused"):
        d.getObject("Mount_Fused").Shapes = [b] + [o for o in d.getObject("Mount_Fused").Shapes if o.Name != b.Name]
    if d.getObject("DFM_View_WallFeet"):         # the TechDraw view of the feet wall lost its source with the old body
        d.getObject("DFM_View_WallFeet").Source = [b]
    d.save()                                     # the body is recomputed; its rounding chain and Mount_Rounded follow
                                                 # with build_rounding.sh MountBody and recompute_mount.py
    print("SAVED", MODEL, flush=True)
