#!/bin/sh
# Put a mount_fuse shim in FreeCAD's user Mod folder, so FreeCAD can import mount_fuse.py when it opens DeskMount.FCStd
# (the Mount_Rounded feature's code). FreeCAD 1.1 resolves symlinks and blocks modules whose real path is outside its
# Mod folders, so a linked cad/ does not work: the shim is a real file that runs cad/mount_fuse.py. Run once per machine.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
MOD="$HOME/Library/Application Support/FreeCAD/v1-1/Mod/DeskMount"
[ -L "$MOD" ] && rm "$MOD"
mkdir -p "$MOD"
cat > "$MOD/mount_fuse.py" <<EOF
# Shim made by $HERE/install.sh: runs the project's mount_fuse.py in this module.
exec(compile(open("$HERE/mount_fuse.py").read(), "$HERE/mount_fuse.py", "exec"))
EOF
echo "installed $MOD/mount_fuse.py -> $HERE/mount_fuse.py (restart FreeCAD)"
