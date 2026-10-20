#!/bin/sh
# Build the in-model rounding chains headless (cad/rounding.py) and save DeskMount.FCStd. Close the model in the FreeCAD
# GUI first, or reload it after. MountBody is the long one; the other parts take seconds to a few minutes.
#   cad/build_rounding.sh                 every part
#   cad/build_rounding.sh MountBody       only these parts
# Progress goes to cad/out/build_rounding.log, one line per stage; the last line is "BUILD DONE" or a traceback.
# A watchdog adds "WATCH" lines every 5 minutes (CPU, minutes since the build last wrote a line). With no new line for 20 minutes
# it adds the top OpenCascade/FreeCAD frames of a stack sample, so a long or stuck step shows what it is doing.
# Near 0% CPU for 15 minutes adds "WATCH STALLED" (check pmset -g log first: a sleeping Mac pauses the job).
FC=${FREECADCMD:-/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd}
HERE=$(cd "$(dirname "$0")" && pwd)
LOG="$HERE/out/build_rounding.log"
mkdir -p "$HERE/out"
PARTS=${*:-"MountBody CartRail_Lid CartRail_Feet USBC_Cartridge"}
: > "$LOG"
BUILD_PARTS="$PARTS" "$FC" "$HERE/rounding.py" >> "$LOG" 2>&1 &   # append mode: the watchdog writes to the same log
PID=$!
caffeinate -i -w $PID &                                # no idle sleep while it runs, on battery too (caffeinate -s
                                                       # holds only on mains power, and sleep pauses the build)

idle=0
tick=0
wsize=0                                                # log size after the watchdog's own last write
seen=$(date +%s)                                       # time of the last line the build wrote
while kill -0 $PID 2>/dev/null; do
  sleep 60
  kill -0 $PID 2>/dev/null || break
  tick=$((tick + 1))
  cpu=$(ps -A -o pid=,ppid=,%cpu= | awk -v p=$PID '$1 == p || $2 == p { s += $3 } END { printf "%d", s }')   # with the block workers
  [ "${cpu:-0}" -lt 5 ] && idle=$((idle + 1)) || idle=0
  size=$(stat -f %z "$LOG")
  if [ "$size" != "$wsize" ]; then seen=$(date +%s); wsize=$size; fi
  age=$(( ($(date +%s) - seen) / 60 ))
  if [ $idle -ge 15 ]; then
    echo "WATCH STALLED $(date +%H:%M): cpu ${cpu}% for $idle min" >> "$LOG"
    idle=0
  fi
  if [ $((tick % 5)) -eq 0 ]; then
    echo "WATCH $(date +%H:%M) cpu ${cpu}% cputime $(ps -o time= -p $PID | tr -d ' ') last line ${age} min ago" >> "$LOG"
    if [ $age -ge 20 ] && [ $((tick % 20)) -eq 0 ]; then
      sample $PID 3 2>/dev/null | grep -oE "(TopoShapePy|TopoShape|BRep[A-Za-z_]+|ChFi[A-Za-z0-9_]+|BOP[A-Za-z_]+|IntTools[A-Za-z_]*)::[A-Za-z_]+" \
        | sort | uniq -c | sort -rn | head -6 | sed 's/^/WATCH   /' >> "$LOG"
    fi
  fi
  wsize=$(stat -f %z "$LOG")
done
wait $PID
grep -a -o -E "[A-Za-z_]+_Rounded: valid[^B]*|BUILD DONE|[A-Za-z]*Error[^B]*|WATCH STALLED[^W]*" "$LOG"
