# In the GUI: exec(open("build/model_fillets.py").read()). Creates or updates a Part::Fillet "<part>_Rounded" for each
# simple mount part, with the edges and radii of edge_rules.py (gussets: R1.5 on the sloped-face edges). The fillets
# recompute with the model. Edge numbers are fixed in each fillet, so run this again after any edit to these parts.
import os, sys
import FreeCAD as App, Part

ROOT = "/Users/tom/projects/fun/macbook-mount"
sys.path.insert(0, ROOT + "/build")
from edge_rules import R_MAJOR, R_RIDGE, classify, key, mid

SIMPLE = ["DeskPlate", "RearStop", "CartRail_Lid", "CartRail_Feet", "Gusset_Lid"]
d = App.getDocument("DeskMount")


def gusset_edges(shape):
    """R1.5 on the free edges of each gusset (sloped face to front and back faces)."""
    pts = []
    for s in shape.Solids:
        slope = [f for f in s.Faces if abs(abs(f.normalAt(0, 0).x) - 0.7071) < 0.01 and abs(abs(f.normalAt(0, 0).z) - 0.7071) < 0.01]
        pts += [mid(e) for e in slope[0].Edges if abs(e.tangentAt(e.FirstParameter).y) < 0.01]
    return [(p, R_MAJOR) for p in pts]


def wanted(name):
    shape = d.getObject(name).Shape
    if name == "Gusset_Lid":
        return gusset_edges(shape)
    concave, major, ridge = classify(d, name)
    return [(p, R_MAJOR) for p in concave + major] + [(p, R_RIDGE) for p in ridge]


def edge_list(shape, want):
    index = {key(mid(e)): i + 1 for i, e in enumerate(shape.Edges)}
    missing = [p for p, r in want if key(p) not in index]
    return [(index[key(p)], r, r) for p, r in want if key(p) in index], missing


def ok(o):
    return "Invalid" not in o.State and not o.Shape.isNull() and o.Shape.isValid()


group = d.getObject("Model_Rounded_Parts") or d.addObject("App::DocumentObjectGroup", "Model_Rounded_Parts")


def feature(fname, base, edges):
    f = d.getObject(fname) or d.addObject("Part::Fillet", fname)
    f.Base = base
    f.Edges = edges
    if f not in group.Group:
        group.addObject(f)
    if f.ViewObject:
        f.ViewObject.Visibility = False
    d.recompute()
    return f


for name in SIMPLE:
    src = d.getObject(name)
    want = wanted(name)
    edges, _ = edge_list(src.Shape, want)
    f = feature(name + "_Rounded", src, edges)
    stages = 1
    if not ok(f):
        # one operation fails: R1.5 first on the source, then R0.4 on that result, as round_part.py does
        f1 = feature(name + "_R15", src, edge_list(src.Shape, [w for w in want if w[1] == R_MAJOR])[0])
        edges2, missing = edge_list(f1.Shape, [w for w in want if w[1] == R_RIDGE])
        f = feature(name + "_Rounded", f1, edges2)
        stages = 2
        if missing:
            print("%s: %d R0.4 edges not found after the R1.5 stage" % (name, len(missing)))
    elif d.getObject(name + "_R15"):
        d.removeObject(name + "_R15")
    print("%s_Rounded stages %d edges %d valid %s vol %.1f" % (name, stages, len(edges), ok(f), f.Shape.Volume))
