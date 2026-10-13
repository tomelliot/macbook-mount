#!/bin/sh
# Rebuild the print bodies from the editable parts in DeskMount.FCStd (save the model first).
# RearStop, DeskPlate, Gusset_Lid and the CartRails are rounded in the model (Part::Fillet "<part>_Rounded"); after an
# edit to one of them, run build/model_fillets.py in the GUI and save.
# 1. round the walls, Floor, Riser_Grid and the cartridge, in parallel (the walls take longest: about 50 minutes each with the strict check);
# 2. fuse the mount and cut the corners that span several parts (about 15 minutes);
# 3. load the result: build/load_print_bodies.py (in the GUI, or headless with the document closed in the GUI).
# Output and logs go to build/out (BUILD_OUT).
set -e
FC=${FREECADCMD:-/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd}
HERE=$(cd "$(dirname "$0")" && pwd)
export BUILD_OUT=${BUILD_OUT:-$HERE/out}
mkdir -p "$BUILD_OUT"
run() { "$FC" "$HERE/$1" > "$BUILD_OUT/$2.log" 2>&1 || echo "FAILED $2"; }
for p in Wall_Lid Wall_Feet Floor; do (PART=$p STRICT=1 run round_part.py "rp_$p") & done
(PART=Riser_Grid run round_part.py rp_Riser_Grid) &
(run round_cartridge.py cart) &
wait
run fuse_mount.py fuse
# FreeCAD writes warnings without newlines; pull out the result lines
python3 - "$BUILD_OUT" <<'PY'
import glob, os, re, sys
for f in sorted(glob.glob(os.path.join(sys.argv[1], "*.log"))):
    t = re.sub(r"Base shape is not valid.*?(?=RESULT|STRICT|CUT|FUSED|CHECK|MOUNT|CART|Gusset|\n|$)", "", open(f, errors="ignore").read())
    for m in re.finditer(r"(\S+ RESULT|\S+ STRICT check|CUT|FUSED|CHECK|MOUNT RESULT|CART RESULT|Gusset_Lid Y|FAILED)[^\n]*", t):
        print(os.path.basename(f)[:-4] + ": " + m.group(0)[:160])
PY
