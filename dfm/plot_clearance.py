"""Zoomed section plots of cartridge-to-mount clearances, annotated with the measured gaps from 03_clearances.json."""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path as MPath
from matplotlib.patches import PathPatch

EV = Path(__file__).parent / "evidence"
data = json.loads((EV / "_sections_clearance.json").read_text())
measured = {r["check"]: r.get("measured_mm") for r in json.loads((EV / "03_clearances.json").read_text())}
RS_GAP = measured["Cartridge body to RearStop (Z 10)"]
XL, XF = data["XL"], data["XF"]
secs = {(s["axis"], s["val"]): s for s in data["sections"]}
IDX = {"z": (0, 1, "X (mm)", "Y (mm)"), "y": (0, 2, "X (mm)", "Z (mm)")}


def patch(loops, i, j, **kw):
    verts, codes = [], []
    for loop in loops:
        pts = [(p[i], p[j]) for p in loop]
        verts += pts + [pts[0]]
        codes += [MPath.MOVETO] + [MPath.LINETO] * (len(pts) - 1) + [MPath.CLOSEPOLY]
    return PathPatch(MPath(verts, codes), **kw)


def draw(ax, key, lims, title, notes):
    s = secs[key]
    i, j, xl, yl = IDX[s["axis"]]
    for f in s["mount"]:
        ax.add_patch(patch(f, i, j, facecolor="#c9d3e0", edgecolor="#4a5a70", lw=0.8))
    for f in s["cart"]:
        ax.add_patch(patch(f, i, j, facecolor="#e8833a", edgecolor="#7a3d10", lw=0.8, alpha=0.9))
    for (x, y), text, (dx, dy) in notes:
        ax.annotate(text, (x, y), xytext=(dx, dy), textcoords="offset points", fontsize=8,
                    arrowprops=dict(arrowstyle="->", lw=0.6), bbox=dict(boxstyle="round", fc="white", ec="0.5", lw=0.4))
    ax.set_xlim(*lims[:2]); ax.set_ylim(*lims[2:])
    ax.set_aspect("equal"); ax.grid(True, lw=0.3, alpha=0.4)
    ax.set_title(title, fontsize=10); ax.set_xlabel(xl, fontsize=8); ax.set_ylabel(yl, fontsize=8); ax.tick_params(labelsize=7)


fig, axs = plt.subplots(2, 3, figsize=(18, 11))
G_FRONT = measured["Tongue to groove, front face (feet side, Z 10)"]
G_REAR = measured["Tongue to groove, rear face (feet side, Z 10)"]
G_TIP = measured["Tongue tip to groove bottom (feet side, Z 10)"]
G_ARM = measured["Flex arm to groove bottom (feet side, Z 45)"]
G_FLEX = min(measured["Flex arm inner face to cartridge body (squeeze travel, Z 45)"])
G_PAD = measured["Squeeze pad to wall face (feet side, Y 328, Z 67)"]
HOLE_D = data.get("hole_d", 0)
draw(axs[0, 0], ("z", 10.0), (XF - 4, XF + 5, 327, 337), "Z = 10: rigid tongue in groove (feet side)",
     [((XF + 1.0, 330 + G_FRONT / 2), "%.2f front" % G_FRONT, (-70, -25)), ((XF + 1.0, 334 - G_REAR / 2), "%.2f rear" % G_REAR, (-70, 20)),
      ((XF + 2.0 - G_TIP / 2, 332), "%.2f tip" % G_TIP, (20, 25))])
draw(axs[0, 1], ("z", 10.0), (-2, 10, 316, 326), "Z = 10: cartridge body to RearStop",
     [((5, 320.225 + RS_GAP / 2), "%.2f gap" % RS_GAP, (20, 20))])
draw(axs[0, 2], ("z", 45.0), (XF - 5, XF + 5, 327, 337), "Z = 45: flex arm in groove (feet side)",
     [((XF + 2.0 - G_ARM / 2, 332), "%.2f to groove bottom" % G_ARM, (15, 30)), ((XF - 1.0, 332), "%.2f squeeze travel" % G_FLEX, (-90, 35))])
draw(axs[1, 0], ("z", 52.5), (XF - 3, XF + 5, 328, 336), "Z = 52.5: detent ball on Ø%.2f through-hole edge" % HOLE_D,
     [((XF + 2.0, 333.4), "0.3 preload (overlap)", (-110, 25)), ((XF + 3.3, 332), "through-hole to outside", (10, -45))])
draw(axs[1, 1], ("z", 67.0), (XF - 7, XF + 5, 325, 339), "Z = 67: squeeze pad (feet side)",
     [((XF - G_PAD / 2, 328), "%.2f pad to wall" % G_PAD, (-110, -25))])
draw(axs[1, 2], ("y", 332.0), (XF - 6, XF + 5, 0, 75), "Y = 332: arm, detent and entry notch (feet side)",
     [((XF + 1.0, 64), "entry notch Z 60.5-128.25", (15, 40)), ((XF + 2.6, 52.5), "detent", (25, -10)), ((XF + 1.0, 4), "rests on Floor (0.0)", (20, 25))])
fig.suptitle("Cartridge-to-mount clearances (orange = cartridge, blue-grey = mount). Values from 03_clearances.json", fontsize=12)
fig.tight_layout(rect=(0, 0, 1, 0.96))
fig.savefig(EV / "03_clearance_sections.png", dpi=120)
(EV / "_sections_clearance.json").unlink()
print("ok")
