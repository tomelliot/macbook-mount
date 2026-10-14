"""Mesh scans on the STL meshes from fc_headless.py. usage: uv run --with numpy --with scipy --with matplotlib dfm/mesh_scans.py $DFM_TMP

Thickness (check 4/5): axis-aligned rays record the solid segments they cross. A segment that starts or ends on a face
hit at a grazing angle (surface within 30 deg of the ray) is a chord of a curved feature (hole, fillet, ball), not a
wall, so it is left out; a ray with no other segment is marked masked. Output: 02_thickness_scan_<part>.json, rows of
[u, w, lengths, starts, masked] per axis, read by plots.py.

Supports (check 23): layer-by-layer scan of the mount as printed (struts in), for a +Z build: floor first, DeskPlate
last. Voxelises the mesh from Z-ray intervals at RES mm, then per layer:
  island   = a connected region with no solid directly below it in the previous layer. It needs a support.
  overhang = new solid more than OVH mm sideways from any solid in the previous layer (the SLA rule of thumb for an
             unsupported overhang is 1 mm). max_reach_mm is how far it reaches; a bridge of span L reaches L / 2.
Rays that cross a mesh seam can return an odd hit count; the scan drops them, which leaves an empty column. Those
columns take their state from their four neighbours in each layer, and regions one voxel wide are dropped too: both
come from the mesh, not the geometry. Output: 08_support_scan.json and 08_support_map.png.
"""
import json
import struct
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage

EV = Path(__file__).parent / "evidence"
GRAZE = 0.5          # thickness scan: |cos| between face normal and ray below this = grazing
OFF = 0.0137         # thickness scan: grid offset so rays miss mesh edges


def load_stl(path):
    raw = Path(path).read_bytes()
    n = struct.unpack("<I", raw[80:84])[0]
    if len(raw) == 84 + 50 * n:
        rec = np.frombuffer(raw[84:], dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]))
        return rec["v"].astype(float)
    pts = [list(map(float, l.split()[1:4])) for l in raw.decode().splitlines() if l.strip().startswith("vertex")]
    return np.array(pts).reshape(-1, 3, 3)


def scan(tri, axis, du, dw, off=OFF, graze_cos=GRAZE):
    a = "xyz".index(axis)
    iu, iw = [i for i in range(3) if i != a]
    lo, hi = tri.reshape(-1, 3).min(0), tri.reshape(-1, 3).max(0)
    us = np.arange(lo[iu] + off, hi[iu], du)
    ws = np.arange(lo[iw] + off, hi[iw], dw)
    nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    nlen = np.linalg.norm(nrm, axis=1)
    keep = (nlen > 1e-12) & (np.abs(nrm[:, a]) > 1e-9 * nlen)
    tri, nrm, nlen = tri[keep], nrm[keep], nlen[keep]
    graze = np.abs(nrm[:, a]) / nlen < graze_cos
    P = tri[:, :, [iu, iw]]
    i0 = np.ceil((P[:, :, 0].min(1) - us[0]) / du).astype(int).clip(0, len(us))
    i1 = np.floor((P[:, :, 0].max(1) - us[0]) / du).astype(int).clip(-1, len(us) - 1)
    j0 = np.ceil((P[:, :, 1].min(1) - ws[0]) / dw).astype(int).clip(0, len(ws))
    j1 = np.floor((P[:, :, 1].max(1) - ws[0]) / dw).astype(int).clip(-1, len(ws) - 1)
    rid, ts, gz = [], [], []
    for k in np.nonzero((i1 >= i0) & (j1 >= j0))[0]:
        I, J = np.meshgrid(np.arange(i0[k], i1[k] + 1), np.arange(j0[k], j1[k] + 1), indexing="ij")
        I, J = I.ravel(), J.ravel()
        u, w = us[I], ws[J]
        (au, aw), (bu, bw), (cu, cw) = P[k]
        e0 = (bu - au) * (w - aw) - (bw - aw) * (u - au)
        e1 = (cu - bu) * (w - bw) - (cw - bw) * (u - bu)
        e2 = (au - cu) * (w - cw) - (aw - cw) * (u - cu)
        inside = ((e0 >= 0) & (e1 >= 0) & (e2 >= 0)) | ((e0 <= 0) & (e1 <= 0) & (e2 <= 0))
        if not inside.any():
            continue
        u, w, I, J = u[inside], w[inside], I[inside], J[inside]
        v0, n = tri[k, 0], nrm[k]
        t = v0[a] - (n[iu] * (u - v0[iu]) + n[iw] * (w - v0[iw])) / n[a]
        rid.append(I * len(ws) + J)
        ts.append(t)
        gz.append(np.full(len(t), graze[k]))
    rid, ts, gz = np.concatenate(rid), np.concatenate(ts), np.concatenate(gz)
    order = np.lexsort((ts, rid))
    rid, ts, gz = rid[order], ts[order], gz[order]
    rows = []
    bounds = np.flatnonzero(np.diff(rid)) + 1
    for r, t, g in zip(np.split(rid, bounds), np.split(ts, bounds), np.split(gz, bounds)):
        keep = np.concatenate([[True], np.diff(t) > 1e-6])      # same hit on two triangles sharing an edge
        t, g = t[keep], g[keep]
        u, w = us[r[0] // len(ws)], ws[r[0] % len(ws)]
        if len(t) % 2:
            rows.append([round(u, 3), round(w, 3), [], [], True])
            continue
        L, S = [], []
        for s0, s1, g0, g1 in zip(t[0::2], t[1::2], g[0::2], g[1::2]):
            if not (g0 or g1):
                L.append(round(s1 - s0, 3))
                S.append(round(s0, 3))
        rows.append([round(u, 3), round(w, 3), L, S, not L])
    return rows


SUPPORT_OFF = 0.0731               # support scan: ray grid offset away from the mesh's regular seams
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


def support(stl):
    tri = load_stl(stl)
    lo, hi = tri.reshape(-1, 3).min(0), tri.reshape(-1, 3).max(0)
    rows = scan(tri, "z", RES, RES, off=SUPPORT_OFF, graze_cos=0.0)   # keep every segment: occupancy, not thickness
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
    tmp = Path(sys.argv[1])
    grids = {"mount": {"x": (1.0, 1.0), "y": (0.5, 1.0), "z": (0.5, 1.0)},
             "cartridge": {"x": (0.25, 0.5), "y": (0.25, 0.5), "z": (0.25, 0.25)}}
    for part, g in grids.items():
        tri = load_stl(tmp / ("%s.stl" % part))
        out = {ax: scan(tri, ax, *g[ax]) for ax in "xyz"}
        (EV / ("02_thickness_scan_%s.json" % part)).write_text(json.dumps(out))
        print(part, {ax: (len(r), sum(x[4] for x in r)) for ax, r in out.items()})
    regions = support(tmp / "mount_print.stl")
    summary = summarise(regions)
    (EV / "08_support_scan.json").write_text(json.dumps({"build": "+Z, floor first, DeskPlate last", "layer_mm": RES,
                                                         "overhang_limit_mm": OVH, "summary": summary, "regions": regions}, indent=1))
    plot(regions, EV / "08_support_map.png")
    print(json.dumps(summary, indent=1))
