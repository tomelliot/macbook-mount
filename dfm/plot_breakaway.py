"""Y = 332 section of the cartridge with the breakaway print supports highlighted."""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path as MPath
from matplotlib.patches import PathPatch

EV = Path(__file__).parent / "evidence"
data = json.loads((EV / "_breakaway.json").read_text())


def patch(loops, **kw):
    verts, codes = [], []
    for loop in loops:
        verts += [tuple(p) for p in loop] + [tuple(loop[0])]
        codes += [MPath.MOVETO] + [MPath.LINETO] * (len(loop) - 1) + [MPath.CLOSEPOLY]
    return PathPatch(MPath(verts, codes), **kw)


fig, axs = plt.subplots(1, 2, figsize=(14, 9), gridspec_kw={"width_ratios": [1, 1.3]})
for ax, lims, title in ((axs[0], (-15, 13, 0, 74), "Y = 332 section: cartridge with breakaway supports"),
                        (axs[1], (3, 12, 34, 66), "Feet side close-up")):
    for f in data["cart"]:
        ax.add_patch(patch(f, facecolor="#e8833a", edgecolor="#7a3d10", lw=0.6, alpha=0.85))
    for f in data["breakaway"]:
        ax.add_patch(patch(f, facecolor="#3a86e8", edgecolor="#0b3d91", lw=0.8))
    ax.set_xlim(*lims[:2]); ax.set_ylim(*lims[2:]); ax.set_aspect("equal")
    ax.grid(True, lw=0.3, alpha=0.4); ax.set_xlabel("X (mm)"); ax.set_ylabel("Z (mm)"); ax.set_title(title, fontsize=10)
ax = axs[1]
for z in (38, 46, 58):
    ax.annotate("tie 1.6 x 1.6, neck 0.8 x 0.8\nbreaks at arm inner face", (9.1, z), xytext=(30, -4), textcoords="offset points", fontsize=8,
                arrowprops=dict(arrowstyle="->", lw=0.6)) if z == 46 else None
ax.annotate("post Ø1.5, neck Ø0.8\nbreaks at pad underside", (5.75, 63.7), xytext=(-150, -30), textcoords="offset points", fontsize=8,
            arrowprops=dict(arrowstyle="->", lw=0.6))
ax.annotate("flex arm (root Z 30)", (10.1, 42), xytext=(25, 40), textcoords="offset points", fontsize=8, arrowprops=dict(arrowstyle="->", lw=0.6))
fig.suptitle("Breakaway print supports (blue): print with the cartridge, clip off before fitting", fontsize=12)
fig.tight_layout(rect=(0, 0, 1, 0.95))
fig.savefig(EV / "07_breakaway_supports.png", dpi=120)
(EV / "_breakaway.json").unlink()
print("ok")
