# Load the built shapes into Print_Bodies (Mount_Rounded, USBC_Cartridge_Rounded) and save DeskMount.FCStd.
# In the GUI: exec(open("build/load_print_bodies.py").read()). Headless: freecadcmd build/load_print_bodies.py (close
# the document in the GUI first, or reload it after).
import os
import FreeCAD as App, Part

ROOT = "/Users/tom/projects/fun/macbook-mount"
S = os.environ.get("BUILD_OUT", ROOT + "/build/out") + "/"
d = App.getDocument("DeskMount") if "DeskMount" in App.listDocuments() else App.openDocument(ROOT + "/DeskMount.FCStd")
for name, f in (("Mount_Rounded", "mount_rounded.brep"), ("USBC_Cartridge_Rounded", "cart_rounded.brep")):
    s = Part.read(S + f)
    d.getObject(name).Shape = s
    print("%s valid %s solids %d vol %.3f cm3" % (name, s.isValid(), len(s.Solids), s.Volume / 1000))
d.recompute()
d.save()
