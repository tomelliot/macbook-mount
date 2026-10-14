#!/bin/sh
# Follow cad/out/build_rounding.log while cad/build_rounding.sh runs: prints each stage line, "STALLED" when the log has
# not grown for STALL_MIN minutes (default 15), and "EXITED" when the build process ends.
LOG=$(cd "$(dirname "$0")" && pwd)/out/build_rounding.log
STALL=$(( ${STALL_MIN:-15} * 60 ))
seen=0; warned=0
while :; do
    if [ -f "$LOG" ]; then
        n=$(wc -c < "$LOG")
        if [ "$n" -gt "$seen" ]; then
            tail -c +$((seen + 1)) "$LOG" | tr '\r' '\n' | grep -a -o -E "^[A-Za-z_]+: (concave|major)[^B]*|  [A-Z0-9]+[ :][^B]*\([0-9]+s\)|[A-Za-z_]+_Rounded: valid[^B]*|BUILD DONE|Traceback.*|[A-Za-z]*Error[^B]*"
            seen=$n; warned=0
        fi
        age=$(( $(date +%s) - $(stat -f %m "$LOG") ))
        if [ "$age" -gt "$STALL" ] && [ "$warned" = 0 ]; then
            echo "STALLED: no log output for $((age / 60)) min"
            warned=1
        fi
    fi
    if ! pgrep -f "rounding.py" > /dev/null; then
        echo "EXITED"
        exit 0
    fi
    sleep 20
done
