"""Check 10 visual: per-face sliding clearance, nominal and JLC worst case, against the JLC moving-part rule."""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

EV = Path(__file__).parent / "evidence"
TOL = 0.2          # JLC SLA model tolerance within 100 mm, each part
RULE_MOVING, RULE_ASSEMBLY = 0.5, 0.2

measured = {r["measure"]: r["measured_mm"] for r in json.loads((EV / "03_measures.json").read_text()) if "object" in r}
# (label, measured per-face gap, faces sharing the tolerance, rule, proposed per-face gap)
# separate prints: JLC "assembled" rule (0.2) applies; the 0.5 "moving" rule is shown for reference (print-in-place)
rows = [
    ("Tongue Y faces (front/rear)", measured["Tongue to groove, front face (feet, Z 10)"], 2, RULE_ASSEMBLY, None),
    ("Tongue tip and arm to groove bottom (X)", measured["Tongue tip and arm to groove bottom (feet, Z 10)"], 2, RULE_ASSEMBLY, None),
    ("Squeeze pad to rail top (Z)", measured["Squeeze pad to rail top (feet, X 12.5)"], 1, RULE_ASSEMBLY, None),
    ("Cartridge to RearStop (Y)", measured["Cartridge front to RearStop (Z 10)"], 1, RULE_ASSEMBLY, None),
]
REV1 = 0.25  # rev 1-3 sliding clearance, shown faded for comparison



def band(gap, faces):
    # two parts at +/-0.2 each change the total gap by +/-0.4; a 2-face fit shares that over both faces when centred
    spread = 2 * TOL / faces
    return gap - spread, gap + spread


fig, ax = plt.subplots(figsize=(13, 6))
for i, (label, gap, faces, rule, proposed) in enumerate(rows):
    y = len(rows) - i
    lo, hi = band(gap, faces)
    colour = "#d7263d" if gap < rule else ("#f9c80e" if lo < rule else "#2e933c")
    ax.plot([lo, hi], [y + 0.12, y + 0.12], color=colour, lw=8, solid_capstyle="butt", alpha=0.6)
    ax.plot(gap, y + 0.12, "ko", ms=6)
    ax.text(hi + 0.02, y + 0.12, "now %.2f (worst %.2f-%.2f)" % (gap, lo, hi), va="center", fontsize=8)
    ax.plot([rule, rule], [y - 0.3, y + 0.42], color="k", ls="--", lw=1)
    ax.text(rule, y + 0.47, "JLC assembled %.1f" % rule, ha="center", fontsize=7)
    ax.plot([RULE_MOVING, RULE_MOVING], [y - 0.3, y + 0.42], color="0.6", ls=":", lw=1)
    if i < 2:
        olo, ohi = band(REV1, faces)
        ax.plot([olo, ohi], [y - 0.15, y - 0.15], color="#d7263d", lw=8, solid_capstyle="butt", alpha=0.2)
        ax.plot(REV1, y - 0.15, "o", mfc="white", mec="0.5", ms=5)
        ax.text(ohi + 0.02, y - 0.15, "rev 3 was %.2f (worst %.2f-%.2f)" % (REV1, olo, ohi), va="center", fontsize=8, color="0.5")
    if proposed:
        plo, phi = band(proposed, faces)
        pc = "#d7263d" if proposed < rule else ("#f9c80e" if plo < rule else "#2e933c")
        ax.plot([plo, phi], [y - 0.15, y - 0.15], color=pc, lw=8, solid_capstyle="butt", alpha=0.35)
        ax.plot(proposed, y - 0.15, "o", mfc="white", mec="k", ms=6)
        ax.text(phi + 0.02, y - 0.15, "proposed %.2f (worst %.2f-%.2f)" % (proposed, plo, phi), va="center", fontsize=8, color="0.3")
ax.axvline(0, color="#a01020", lw=1.5)
ax.text(0.005, 0.45, "interference", color="#a01020", fontsize=8)
ax.set_yticks(range(len(rows), 0, -1))
ax.set_yticklabels([r[0] for r in rows], fontsize=9)
ax.set_xlim(-0.1, 1.45)
ax.set_ylim(0.3, len(rows) + 0.8)
ax.set_xlabel("Clearance per face (mm)")
ax.grid(True, axis="x", lw=0.3, alpha=0.5)
ax.set_title("Check 10 (rev 5, values from FreeCAD Measure objects): clearance per face vs JLC SLA 'assembled parts' rule (0.2 mm, dashed); "
             "dotted grey = 0.5 mm 'moving parts' rule (print-in-place)\nbar = worst-case range (±0.2 mm on each part), dot = nominal, "
             "faded bar = rev 3\nred: nominal below rule · yellow: nominal meets rule, worst case below it · green: worst case meets rule", fontsize=10)
fig.tight_layout()
fig.savefig(EV / "06_clearance_bands.png", dpi=120)
print("ok")
