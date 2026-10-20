"""Warp screen (check 17), geometry only, no FEA. usage: uv run --with numpy --with scipy --with matplotlib dfm/warp_screen.py $DFM_TMP

Voxelises mount_print.stl (struts in) and mount.stl (struts out) at RES mm from Z-ray intervals, then looks for the
features JLC names as warp risks:
  ties     the walls are joined only where solid crosses the slot (floor, riser, RearStop, struts). For each point of
           the wall plane (Y, Z), the distance to the nearest tie is the span over which the walls can pull in or bow.
  lumps    3D distance transform; medial points with an inscribed diameter over LUMP mm are thick spots that cure and
           shrink later than the 2.4 mm ribs around them.
  profile  solid area of each Y slice and each Z slice: a step means bulk next to light structure.
  panels   per panel (walls along X, DeskPlate along Z), the solid thickness through the panel. Skin with no rib
           behind it (thickness <= SKIN mm) is flat panel; the largest inscribed circle in it is its free span.
Output: 10_warp_screen.json and 10_warp_*.png.
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage

from mesh_scans import EV, load_stl, scan

RES = 0.5
OFF = 0.0731
LUMP = 4.5               # mm inscribed diameter; a rib crossing node is about 2.4 * sqrt(2) = 3.4
SKIN = 3.0               # mm solid through a panel: skin only, no rib behind
SLOT = (-11.49, 9.25)    # slot inner faces (X)
WALLS = {"Wall_Lid": (-19.6, -11.49), "Wall_Feet": (9.25, 17.4)}


def voxels(stl):
    tri = load_stl(stl)
    rows = scan(tri, "z", RES, RES, off=OFF, graze_cos=0.0)
    xs = np.array(sorted({r[0] for r in rows}))
    ys = np.array(sorted({r[1] for r in rows}))
    lo, hi = tri.reshape(-1, 3).min(0), tri.reshape(-1, 3).max(0)
    zs = np.arange(lo[2] + OFF, hi[2], RES)
    V = np.zeros((len(xs), len(ys), len(zs)), bool)
    bad = np.zeros((len(xs), len(ys)), bool)
    xi = {v: i for i, v in enumerate(xs)}
    yi = {v: i for i, v in enumerate(ys)}
    for u, w, L, S, odd in rows:
        i, j = xi[u], yi[w]
        bad[i, j] = odd and not L
        for length, s in zip(L, S):
            V[i, j, (zs >= s) & (zs < s + length)] = True
    # columns lost to mesh seams take the majority of their four neighbours
    nb = ndimage.convolve(V.astype(np.uint8), np.array([[[0], [1], [0]], [[1], [0], [1]], [[0], [1], [0]]], np.uint8), mode="constant")
    V[bad] = nb[bad] >= 2
    return V, xs, ys, zs


def ties(V, xs, ys, zs):
    """Wall-plane (Y, Z) map: solid anywhere across the slot interior, and the distance from each point to it."""
    inner = (xs > SLOT[0] + 0.5) & (xs < SLOT[1] - 0.5)
    tie = V[inner].any(0)
    d = ndimage.distance_transform_edt(~tie) * RES
    return tie, d


def lumps(V, xs, ys, zs):
    D = ndimage.distance_transform_edt(np.pad(V, 1))[1:-1, 1:-1, 1:-1] * RES      # pad: the grid edge is not solid
    peak = (D == ndimage.maximum_filter(D, size=3)) & (2 * D > LUMP)
    lab, n = ndimage.label(peak, structure=np.ones((3, 3, 3)))
    out = []
    for k, sl in enumerate(ndimage.find_objects(lab)):
        m = lab[sl] == k + 1
        dia = 2 * D[sl][m].max()
        c = [float(np.mean(a[s])) for a, s in zip((xs, ys, zs), sl)]
        out.append({"x": round(c[0], 1), "y": round(c[1], 1), "z": round(c[2], 1), "dia_mm": round(float(dia), 2),
                    "extent_mm": [round((s.stop - s.start) * RES, 1) for s in sl]})
    out.sort(key=lambda r: -r["dia_mm"])
    return out, D


def panel(V, axis, sel, skin_mm=SKIN):
    """Solid thickness through a panel along axis, inside the slab sel, and the free span of skin-only areas."""
    T = V[sel].sum(axis) * RES if axis == 0 else V[:, :, sel].sum(axis) * RES
    skin = (T > 0) & (T <= skin_mm)
    span = 2 * ndimage.distance_transform_edt(np.pad(skin, 1))[1:-1, 1:-1] * RES
    return T, skin, span


def plot_maps(ys, zs, d_in, d_out, walls, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(2, 2, figsize=(15, 11), layout="constrained")
    ext = [ys[0], ys[-1], zs[0], zs[-1]]
    vmax = max(d_in.max(), d_out.max())
    for ax, d, t in ((axs[0, 0], d_in, "struts in (as printed and cured)"), (axs[0, 1], d_out, "struts removed")):
        im = ax.imshow(d.T, origin="lower", extent=ext, cmap="magma_r", vmin=0, vmax=vmax, aspect="equal")
        ax.contour(ys, zs, d.T, levels=[20, 40, 60], colors="w", linewidths=0.6)
        ax.set_title("Distance from each point of the slot to the nearest cross-tie (mm), " + t, fontsize=10)
        ax.set_xlabel("Y (mm), front at left"); ax.set_ylabel("Z (mm), build direction")
    fig.colorbar(im, ax=axs[0, :], shrink=0.8, label="mm to nearest tie (floor, riser, RearStop, strut); contours 20/40/60")
    for ax, (name, (T, skin, span)) in zip(axs[1], walls.items()):
        im2 = ax.imshow(np.where(skin, span, np.nan).T, origin="lower", extent=ext, cmap="viridis", aspect="equal")
        ax.imshow(np.where(T == 0, 1.0, np.nan).T, origin="lower", extent=ext, cmap="Greys", vmin=0, vmax=2, aspect="equal")
        ax.set_title(name + ": skin with no rib behind it, coloured by free span (mm); grey = open", fontsize=10)
        ax.set_xlabel("Y (mm)"); ax.set_ylabel("Z (mm)")
        fig.colorbar(im2, ax=ax, shrink=0.8)
    fig.savefig(path, dpi=110)


def plot_profiles(xs, ys, zs, V, lumps_, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, (a1, a2, a3) = plt.subplots(3, 1, figsize=(14, 12), layout="constrained")
    a1.plot(ys, V.sum((0, 2)) * RES * RES, lw=0.8)
    a1.set_title("Solid area of each Y slice (mm²)"); a1.set_xlabel("Y (mm)"); a1.grid(alpha=0.3)
    a2.plot(zs, V.sum((0, 1)) * RES * RES, lw=0.8)
    a2.set_title("Solid area of each Z slice (mm²), build direction"); a2.set_xlabel("Z (mm)"); a2.grid(alpha=0.3)
    top = lumps_[:400]
    sc = a3.scatter([r["y"] for r in top], [r["z"] for r in top], c=[r["dia_mm"] for r in top], s=[6 * r["dia_mm"] ** 1.5 for r in top],
                    cmap="plasma", edgecolors="k", linewidths=0.3)
    a3.set_title("Thick spots: inscribed diameter over %.1f mm (ribs are 2.4)" % LUMP)
    a3.set_xlabel("Y (mm)"); a3.set_ylabel("Z (mm)"); a3.set_xlim(ys[0], ys[-1]); a3.set_ylim(zs[0], zs[-1]); a3.grid(alpha=0.3)
    fig.colorbar(sc, ax=a3, label="inscribed diameter (mm)")
    fig.savefig(path, dpi=110)


def runs(mask, coords):
    """[start, end] of each True run along a 1-D mask."""
    e = np.flatnonzero(np.diff(np.concatenate([[0], mask.astype(int), [0]])))
    return [[round(float(coords[a]), 1), round(float(coords[b - 1]), 1)] for a, b in zip(e[0::2], e[1::2])]


if __name__ == "__main__":
    tmp = Path(sys.argv[1])
    Vp, xs, ys, zs = voxels(tmp / "mount_print.stl")
    Vm, xm, ym, zm = voxels(tmp / "mount.stl")
    assert len(xs) == len(xm) and len(ys) == len(ym) and len(zs) == len(zm)
    tie_in, d_in = ties(Vp, xs, ys, zs)
    tie_out, d_out = ties(Vm, xs, ys, zs)
    slot = (zs > 2.2) & (zs < 228)
    out = {"res_mm": RES}
    for name, d in (("struts_in", d_in), ("struts_out", d_out)):
        dd = d[:, slot]
        j, k = np.unravel_index(dd.argmax(), dd.shape)
        out["tie_" + name] = {"max_mm": round(float(dd.max()), 1), "at_y": round(float(ys[j]), 1), "at_z": round(float(zs[slot][k]), 1),
                              "tie_y_runs_at_mid_z": runs(tie_in[:, np.searchsorted(zs, 115)] if name == "struts_in" else tie_out[:, np.searchsorted(zs, 115)], ys)}
    lumps_, _ = lumps(Vm, xs, ys, zs)
    out["lumps"] = {"count": len(lumps_), "largest": lumps_[:40]}
    walls = {}
    for name, (a, b) in WALLS.items():
        T, skin, span = panel(Vm, 0, (xs > a) & (xs < b))
        walls[name] = (T, skin, span)
        j, k = np.unravel_index(span.argmax(), span.shape)
        out[name] = {"skin_area_mm2": round(float(skin.sum()) * RES * RES, 0), "open_area_mm2": round(float((T == 0).sum()) * RES * RES, 0),
                     "max_free_span_mm": round(float(span.max()), 1), "at_y": round(float(ys[j]), 1), "at_z": round(float(zs[k]), 1)}
    T, skin, span = panel(Vm, 2, zs > 270, skin_mm=4.5)     # DeskPlate is 4 mm
    i, j = np.unravel_index(span.argmax(), span.shape)
    out["DeskPlate"] = {"skin_area_mm2": round(float(skin.sum()) * RES * RES, 0), "max_free_span_mm": round(float(span.max()), 1),
                        "at_x": round(float(xs[i]), 1), "at_y": round(float(ys[j]), 1)}
    out["y_area_mm2"] = [[round(float(y), 1), round(float(a), 1)] for y, a in zip(ys[::4], (Vm.sum((0, 2)) * RES * RES)[::4])]
    out["z_area_mm2"] = [[round(float(z), 1), round(float(a), 1)] for z, a in zip(zs[::4], (Vm.sum((0, 1)) * RES * RES)[::4])]
    (EV / "10_warp_screen.json").write_text(json.dumps(out, indent=1))
    plot_maps(ys, zs, d_in, d_out, walls, EV / "10_warp_ties_panels.png")
    plot_profiles(xs, ys, zs, Vm, lumps_, EV / "10_warp_profiles.png")
    print(json.dumps({k: v for k, v in out.items() if k not in ("y_area_mm2", "z_area_mm2", "lumps")}, indent=1))
    print("lumps", len(lumps_), lumps_[:15])
