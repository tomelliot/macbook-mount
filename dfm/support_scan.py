"""Layer-by-layer printability scan of the mount as printed (struts in), for a +Z build: floor first, DeskPlate last.

usage: uv run --with numpy --with scipy --with matplotlib dfm/support_scan.py $DFM_TMP
Reads $DFM_TMP/mount_print.stl (fc_dfm_run.py). Voxelises the mesh from Z-ray intervals at RES mm, then per layer:
  island   = a connected region with no solid directly below it in the previous layer. It needs a support.
  overhang = new solid more than OVH mm sideways from any solid in the previous layer (the SLA rule of thumb for an
             unsupported overhang is 1 mm). max_reach_mm is how far it reaches; a bridge of span L reaches L / 2.
Rays that cross a mesh seam can return an odd hit count; the scan drops them, which leaves an empty column. Those
columns take their state from their four neighbours in each layer, and regions one voxel wide are dropped too: both
come from the mesh, not the geometry.
Writes dfm/evidence/08_support_scan.json and 08_support_map.png.
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage

import ray_thickness as rt

rt.OFF = 0.0731                    # ray grid offset away from the mesh's regular seams
rt.GRAZE = 0.0                     # keep every solid segment: this is occupancy, not wall thickness
EV = Path(__file__).parent / "evidence"
RES, OVH = 0.25, 1.0
ZONES = [  # (name, test on region centre x, y, z)
    ("Breakaway struts", lambda x, y, z: -11 < x < 9 and 20 < z < 220 and y < 316),
    ("DeskPlate overhang", lambda x, y, z: x > 17.3 and z > 270),
    ("Riser top-row cell ceilings", lambda x, y, z: 270 < z < 278),
    ("Slot ceiling under the riser", lambda x, y, z: -11.5 < x < 9.3 and 226.5 < z < 230),
    ("Wall top-row cell ceilings", lambda x, y, z: 220 < z < 228),
    ("Cartridge zone", lambda x, y, z: y > 314 and z < 70),
    ("Wall inner-face window tops", lambda x, y, z: -14 < x < -11 or 9 < x < 12),
]


def zone(x, y, z):
    return next((n for n, f in ZONES if f(x, y, z)), "Other")


def run(stl):
    tri = rt.load_stl(stl)
    lo, hi = tri.reshape(-1, 3).min(0), tri.reshape(-1, 3).max(0)
    rows = rt.scan(tri, "z", RES, RES)
    xs = np.array(sorted({r[0] for r in rows}))
    ys = np.array(sorted({r[1] for r in rows}))
    xi = {v: i for i, v in enumerate(xs)}
    yi = {v: i for i, v in enumerate(ys)}
    C, S, E = [], [], []
    bad = np.zeros((len(xs), len(ys)), bool)
    for u, w, L, St, odd in rows:
        bad[xi[u], yi[w]] = odd and not L
        for length, s in zip(L, St):
            C.append(xi[u] * len(ys) + yi[w])
            S.append(s)
            E.append(s + length)
    C, S, E = np.array(C), np.array(S), np.array(E)
    prev = np.zeros((len(xs), len(ys)), bool)
    found = []
    for k in range(int((hi[2] - lo[2]) / RES) + 1):
        z = lo[2] + (k + 0.537) * RES
        m = np.zeros(len(xs) * len(ys), bool)
        m[C[(S <= z) & (E > z)]] = True
        m = m.reshape(len(xs), len(ys))
        if bad.any():
            nb = ndimage.convolve(m.astype(int), np.array([[0, 1, 0], [1, 0, 1], [0, 1, 0]]), mode="constant")
            m[bad] = nb[bad] >= 2
        if k and m.any():
            lab, n = ndimage.label(m, structure=np.ones((3, 3)))
            supp = ndimage.maximum(prev, lab, index=np.arange(1, n + 1)) if n else []
            for i in np.nonzero(~np.asarray(supp, bool))[0]:
                sl = ndimage.find_objects((lab == i + 1).astype(int))[0]
                found.append(("island", z, sl, int((lab == i + 1).sum()), None))
            new = m & ~prev
            if new.any() and prev.any():
                dist = ndimage.distance_transform_edt(~prev) * RES
                bad = new & (dist > OVH)
                if bad.any():
                    bl, _ = ndimage.label(bad, structure=np.ones((3, 3)))
                    for i, sl in enumerate(ndimage.find_objects(bl)):
                        reg = bl[sl] == i + 1
                        found.append(("overhang", z, sl, int(reg.sum()), float(dist[sl][reg].max())))
        prev = m
    out = []
    for kind, z, sl, px, reach in found:
        if sl[0].stop - sl[0].start < 2 or sl[1].stop - sl[1].start < 2:      # one voxel wide: scan artifact
            continue
        x0, x1, y0, y1 = xs[sl[0].start], xs[sl[0].stop - 1], ys[sl[1].start], ys[sl[1].stop - 1]
        out.append({"kind": kind, "zone": zone((x0 + x1) / 2, (y0 + y1) / 2, z), "z": round(z, 2),
                    "x": [round(x0, 2), round(x1, 2)], "y": [round(y0, 2), round(y1, 2)],
                    "area_mm2": round(px * RES * RES, 1), "max_reach_mm": None if reach is None else round(reach, 2)})
    return out


def summarise(regions):
    s = {}
    for r in regions:
        z = s.setdefault(r["zone"], {"islands": 0, "overhang_regions": 0, "overhang_area_mm2": 0.0, "max_reach_mm": 0.0,
                                     "z_range": [r["z"], r["z"]]})
        if r["kind"] == "island":
            z["islands"] += 1
        else:
            z["overhang_regions"] += 1
            z["overhang_area_mm2"] = round(z["overhang_area_mm2"] + r["area_mm2"], 1)
            z["max_reach_mm"] = max(z["max_reach_mm"], r["max_reach_mm"])
        z["z_range"] = [min(z["z_range"][0], r["z"]), max(z["z_range"][1], r["z"])]
    return s


def plot(regions, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(14, 10))
    ov = [r for r in regions if r["kind"] == "overhang"]
    sc = ax.scatter([(r["y"][0] + r["y"][1]) / 2 for r in ov], [r["z"] for r in ov], s=[min(400, 4 + r["area_mm2"] / 4) for r in ov],
                    c=[r["max_reach_mm"] for r in ov], cmap="plasma", vmin=1, vmax=20, alpha=0.8, edgecolors="k", linewidths=0.3)
    isl = [r for r in regions if r["kind"] == "island"]
    ax.scatter([(r["y"][0] + r["y"][1]) / 2 for r in isl], [r["z"] for r in isl], marker="x", s=60, c="red", label="island")
    fig.colorbar(sc, ax=ax, label="overhang reach from the layer below (mm); a bridge of span L reaches L/2")
    ax.set_xlabel("Y (mm), front at left")
    ax.set_ylabel("Z (mm), build direction")
    ax.set_title("Mount as printed, +Z build (DeskPlate last): unsupported overhangs > %.0f mm and islands, %.2f mm layers" % (OVH, RES))
    ax.legend(loc="upper left")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=110)


if __name__ == "__main__":
    regions = run(Path(sys.argv[1]) / "mount_print.stl")
    summary = summarise(regions)
    (EV / "08_support_scan.json").write_text(json.dumps({"build": "+Z, floor first, DeskPlate last", "layer_mm": RES,
                                                         "overhang_limit_mm": OVH, "summary": summary, "regions": regions}, indent=1))
    plot(regions, EV / "08_support_map.png")
    print(json.dumps(summary, indent=1))
