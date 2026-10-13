# Run inside the FreeCAD GUI (freecad-mcp execute_code: exec(open(<this file>).read())), after fc_dfm_run.py.
# 1. Loads the cartridge-zone clip that fc_dfm_run.py cut headless (booleans on the full mount have crashed the GUI).
# 2. Re-runs fc_measures.py (live Measure objects for checks 10-12 and 18).
# 3. Re-anchors the sheet dimensions by geometry (fc_dims_anchor.py), saves the 01_* model views and exports the
#    TechDraw sheets DFM_Clearances and DFM_Mount_Structure as PDF and SVG.
# TechDraw views and dimensions must be visible (a 'hide everything' in the GUI hides them too).
import os
import time

import FreeCAD as App
import FreeCADGui as Gui
import Part
import TechDrawGui

ROOT = "/Users/tom/projects/fun/macbook-mount"
EV = ROOT + "/dfm/evidence/"
TMP = os.environ.get("DFM_TMP", "/tmp")
d = App.getDocument("DeskMount")

clip = d.getObject("DFM_Clip_Cartridge_Zone")
clip.Shape = Part.read(TMP + "/clip_cart_zone.brep")
exec(open(ROOT + "/dfm/fc_measures.py").read(), {"__name__": "measures"})
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
exec(open(ROOT + "/dfm/fc_dims_anchor.py").read(), {"__name__": "anchor"})   # dimensions reference edges by index
d.recompute()
for _ in range(10):                       # let the dimensions update on the finished views
    Gui.updateGui()
    time.sleep(0.5)

# ---- model views ----
v = Gui.getDocument("DeskMount").mdiViewsOfType("Gui::View3DInventor")[0]   # not ActiveView: a TechDraw page may be active
mount = [d.getObject("Mount_Rounded")]             # print bodies, with struts and ties as printed
cart = [d.getObject("USBC_Cartridge_Rounded")]
lap = list(d.getObject("Laptop").Group)
shown = [o for o in d.Objects if getattr(o, "ViewObject", None) and o.ViewObject.Visibility]
allo = [o for o in d.Objects if getattr(o, "ViewObject", None) and o.TypeId.startswith(("Part::", "Mesh::"))]


measures = [o for o in d.Objects if o.TypeId.startswith("Measure::")]


def shot(objs, views, prefix):
    for o in allo + measures:
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
for o in allo + measures:
    o.ViewObject.Visibility = o in shown

# ---- drawings ----
for page, name in (("DFM_Clearances", "03_clearance_sections"), ("DFM_Mount_Structure", "09_mount_structure")):
    d.getObject(page).ViewObject.doubleClicked()      # the export draws from the open page window
    for _ in range(6):
        Gui.updateGui()
        time.sleep(0.5)
    TechDrawGui.exportPageAsPdf(d.getObject(page), EV + name + ".pdf")
    TechDrawGui.exportPageAsSvg(d.getObject(page), EV + name + ".svg")
print("ok")
