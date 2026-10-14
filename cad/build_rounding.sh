#!/bin/sh
# Build the in-model rounding chains headless (cad/rounding.py) and save DeskMount.FCStd. Close the model in the FreeCAD
# GUI first, or reload it after. A wall takes 40-50 minutes; the other parts take seconds to a few minutes.
#   cad/build_rounding.sh                 every part
#   cad/build_rounding.sh Wall_Lid Floor  only these parts
# Progress goes to cad/out/build_rounding.log, one line per stage; the last line is "BUILD DONE" or a traceback.
FC=${FREECADCMD:-/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd}
HERE=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$HERE/out"
PARTS=${*:-"Wall_Lid Wall_Feet Floor Riser_Grid RearStop DeskPlate Gussets CartRail_Lid CartRail_Feet USBC_Cartridge"}
BUILD_PARTS="$PARTS" "$FC" "$HERE/rounding.py" > "$HERE/out/build_rounding.log" 2>&1
grep -a -o -E "[A-Za-z_]+_Rounded: valid[^B]*|BUILD DONE|[A-Za-z]*Error[^B]*" "$HERE/out/build_rounding.log"
