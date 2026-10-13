"""Update 04_tolerance_stack.json for the current mount size and the felt-supported laptop (rev 5).

usage: python3 tolerance_stack.py <facts.json from fc_dfm_run.py>
"""
import json
import math
import sys
from pathlib import Path

EV = Path(__file__).parent / "evidence"
facts = json.loads(Path(sys.argv[1]).read_text())
ts = json.loads((EV / "04_tolerance_stack.json").read_text())
x, y, z = facts["mount_bbox"]
ts["long_dimension_tolerance_mm"] = {"Mount length Y (%.1f mm)" % y: round(0.003 * y, 2), "Mount height Z (%.1f mm)" % z: round(0.003 * z, 2),
                                     "Mount width X (%.1f mm)" % x: 0.2}
ts["post_print_drift_mm"] = {"1-3 days 0.15%": {"mount %.1f mm" % y: round(0.0015 * y, 2), "cartridge %.1f mm" % facts["cart_bbox"][2]: 0.15},
                             "3-7 days 0.20%": {"mount %.1f mm" % y: round(0.002 * y, 2), "cartridge %.1f mm" % facts["cart_bbox"][2]: 0.2}}
port_z = 50.44
parts = {"cartridge base->pocket centre +/-0.2": 0.2, "floor flatness, laptop seat to cartridge seat (common datum Z %.2f) +/-0.2" % facts["floor_top_z"]: 0.2}
wc = sum(parts.values())
float_mm, bias = 0.75, -0.15
ts["usb_port_alignment_z"] = {
    "port_centre_z": port_z, "pocket centre above cartridge base": round(port_z - facts["cart_base_z"], 2),
    "laptop_rests_on": "felt, %.2f mm above floor top" % (facts["laptop_min_z"] - facts["floor_top_z"]),
    "contributors": parts, "worst_case_mm": round(wc, 2), "rss_mm": round(math.sqrt(sum(v * v for v in parts.values())), 2),
    "laptop_seating_bias_mm": bias, "usb_c_plug_float_mm": float_mm,
    "felt_allowance_mm": round(float_mm - wc - abs(bias), 2),
    "note": "The printed parts use 0.55 of the 0.75 mm plug float in the worst case; the felt under the laptop must hold 2.0 mm within the remaining +/-0.2 mm."}
(EV / "04_tolerance_stack.json").write_text(json.dumps(ts, indent=1))
print(json.dumps({k: ts[k] for k in ("long_dimension_tolerance_mm", "post_print_drift_mm", "usb_port_alignment_z")}, indent=1))
