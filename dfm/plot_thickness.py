"""Plot ray-scan wall-thickness maps from FreeCAD scan JSON (dfm/evidence/02_thickness_scan_*.json).

Each ray records the solid segment lengths it crosses; the map colour is the thinnest segment on that ray.
Rays that graze curved features (detent balls, detent holes, gusset tips) give short chords that are not
walls, so they are masked and drawn grey.
"""
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap

EV = Path(__file__).parent / "evidence"
BANDS = [0, 1.0, 1.5, 2.0, 4.0, 100]
COLOURS = ["#d7263d", "#f46036", "#f9c80e", "#7fb069", "#2e933c"]
LABELS = ["< 1.0", "1.0 - 1.5", "1.5 - 2.0", "2.0 - 4.0", ">= 4.0"]
AXES = {"x": ("Y (mm)", "Z (mm)"), "y": ("X (mm)", "Z (mm)"), "z": ("X (mm)", "Y (mm)")}


def plot(part_file, title, masks, step, out_name):
    data = json.loads((EV / part_file).read_text())
    fig, axs = plt.subplots(1, 3, figsize=(18, 7))
    cmap = ListedColormap(COLOURS)
    norm = BoundaryNorm(BANDS, cmap.N)
    minima = {}
    for ax, axis in zip(axs, "xyz"):
        rows = data[axis]
        us, ws, vals, masked_u, masked_w = [], [], [], [], []
        best = None
        for u, w, lengths, starts in rows:
            if any(m(axis, u, w) for m in masks):
                masked_u.append(u)
                masked_w.append(w)
                continue
            t = min(lengths)
            us.append(u)
            ws.append(w)
            vals.append(t)
            if best is None or t < best[0]:
                best = (t, u, w, starts[lengths.index(t)])
        su, sw = step[axis]
        ax.scatter(masked_u, masked_w, c="#bbbbbb", marker="s", s=4, linewidths=0)
        sc = ax.scatter(us, ws, c=vals, cmap=cmap, norm=norm, marker="s", s=4, linewidths=0)
        if best:
            ax.plot(best[1], best[2], "kx", ms=10, mew=2)
            ax.annotate("min %.2f mm" % best[0], (best[1], best[2]), xytext=(8, 8), textcoords="offset points", fontsize=9,
                        bbox=dict(boxstyle="round", fc="white", ec="black", lw=0.5))
            minima[axis] = {"thickness_mm": best[0], "ray_u": best[1], "ray_w": best[2], "segment_start": best[3]}
        ax.set_aspect("equal")
        ax.set_xlabel(AXES[axis][0])
        ax.set_ylabel(AXES[axis][1])
        ax.set_title("Rays along %s (thinnest wall crossed)" % axis.upper(), fontsize=10)
        ax.grid(True, lw=0.3, alpha=0.4)
    handles = [plt.Line2D([], [], marker="s", ls="", color=c, label=l) for c, l in zip(COLOURS, LABELS)]
    handles.append(plt.Line2D([], [], marker="s", ls="", color="#bbbbbb", label="masked: curved-feature graze"))
    fig.legend(handles=handles, loc="lower center", ncol=6, fontsize=9, title="Wall thickness (mm)")
    fig.suptitle(title, fontsize=12)
    fig.tight_layout(rect=(0, 0.08, 1, 0.95))
    fig.savefig(EV / out_name, dpi=120)
    return minima


def ball_mask(xs, centre_w_by_axis, r=1.7):
    """Mask rays passing within r of a detent ball / hole, for Y and Z rays (X rays run along their axis)."""
    def m(axis, u, w):
        if axis == "x":
            return False
        return any(lo <= u <= hi for lo, hi in xs) and abs(w - centre_w_by_axis[axis]) < r
    return m


if __name__ == "__main__":
    xl, xf = float(sys.argv[1]), float(sys.argv[2])  # wall inner faces (lid, feet)
    lo_wall = xl - 4.0  # lid wall outer face (gusset root)
    # detent balls on the cartridge and holes in the mount, both at Y 332, Z 52.5
    balls = ball_mask([(xl - 3.3, xl - 1.7), (xf + 1.7, xf + 3.3)], {"y": 52.5, "z": 332.0})
    holes = ball_mask([(xl - 4.1, xl - 1.9), (xf + 1.9, xf + 4.1)], {"y": 52.5, "z": 332.0}, r=1.6)

    def gusset_tip(axis, u, w):
        # X rays through the 45 deg gussets near their bottom tip see the taper, not a wall
        return axis == "x" and 193.0 <= w <= 197.0

    cart = plot("02_thickness_scan_cartridge.json", "USBC_Cartridge wall thickness, ray scan 0.25-0.5 mm grid",
                [balls], {"x": (0.25, 0.5), "y": (0.25, 0.5), "z": (0.25, 0.25)}, "02_thickness_map_cartridge.png")
    mount = plot("02_thickness_scan_mount.json", "Mount_Fused wall thickness, ray scan 0.5-2 mm grid",
                 [holes, gusset_tip], {"x": (1.5, 1.5), "y": (0.5, 2.0), "z": (0.5, 2.0)}, "02_thickness_map_mount.png")
    (EV / "02_thickness_minima.json").write_text(json.dumps({"USBC_Cartridge": cart, "Mount_Fused": mount}, indent=1))
    print(json.dumps({"USBC_Cartridge": cart, "Mount_Fused": mount}, indent=1))
