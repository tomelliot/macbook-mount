# Recreate Mount_Rounded headless after its parts change, save, and check the saved feature reopens with its code.
# usage: freecadcmd cad/recompute_mount.py    (close the model in the GUI first, or reload it after)
# Prints MOUNT lines: the feature's report (fuse, fills, cutters, result), a strict shape check, and the reopen check.
import time

import FreeCAD as App

ROOT = "/Users/tom/projects/fun/macbook-mount"
PATH = ROOT + "/DeskMount.FCStd"

d = App.openDocument(PATH)
import mount_fuse          # noqa: E402  after the open: the copy FreeCAD loaded from its Mod folder (cad/install.sh)
old = d.getObject("Mount_Rounded").Shape.Volume if d.getObject("Mount_Rounded") else 0.0
print("MOUNT module", mount_fuse.__file__, flush=True)
t = time.time()
d.recompute()                                            # parts and rounding chains first
obj = mount_fuse.create(d)
print("MOUNT recompute %.0fs" % (time.time() - t), flush=True)
for line in obj.Report:
    print("MOUNT", line, flush=True)
s = obj.Shape
try:
    s.check(True)
    strict = s.isValid()
except Exception as e:                                   # check(True) raises on any BOP-level fault
    print("MOUNT check:", str(e)[:300], flush=True)
    strict = False
print("MOUNT strict", strict, flush=True)
print("MOUNT old %.3f cm3, diff %.1f mm3" % (old / 1000, s.Volume - old), flush=True)
d.save()
App.closeDocument(d.Name)
d = App.openDocument(PATH)
print("MOUNT reopened proxy", d.getObject("Mount_Rounded").Proxy, flush=True)
print("MOUNT saved", flush=True)
