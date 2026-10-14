#!/bin/sh
# Regenerate the DFM evidence from the print bodies in DeskMount.FCStd (save the model first). Two stages, because the
# measures, drawings and model views need the FreeCAD GUI:
#   dfm/run_dfm.sh headless   STEP export, build volume, laptop fit, meshes, thickness and support scans, calculations
#   then in the FreeCAD GUI:  exec(open("dfm/fc_gui.py").read())   (same DFM_TMP; default /tmp/deskmount_dfm)
#   dfm/run_dfm.sh plots      thickness maps and clearance bands
set -e
FC=${FREECADCMD:-/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd}
HERE=$(cd "$(dirname "$0")" && pwd)
export DFM_TMP=${DFM_TMP:-/tmp/deskmount_dfm}
mkdir -p "$DFM_TMP"
case ${1:-headless} in
    headless)
        "$FC" "$HERE/fc_headless.py" 2>&1 | grep -a -E "^(step|mesh|done|\{|\[)|Error|Traceback" || true
        uv run -q --with numpy --with scipy --with matplotlib python "$HERE/mesh_scans.py" "$DFM_TMP"
        uv run -q --with matplotlib python "$HERE/calcs.py" "$DFM_TMP/facts.json" > /dev/null
        echo "next: in the FreeCAD GUI, exec(open(\"$HERE/fc_gui.py\").read()), then dfm/run_dfm.sh plots"
        ;;
    plots)
        uv run -q --with matplotlib python "$HERE/plots.py"
        ;;
    *)
        echo "usage: dfm/run_dfm.sh [headless|plots]" >&2
        exit 1
        ;;
esac
