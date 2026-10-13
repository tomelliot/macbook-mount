"""Axis-aligned ray scan of wall thickness on STL meshes from fc_dfm_run.py.

Each ray records the solid segments it crosses. A segment that starts or ends on a face hit at a grazing angle
(surface within 30 deg of the ray) is a chord of a curved feature (hole, fillet, ball), not a wall, so it is left
out; a ray with no other segment is marked masked. Output: dfm/evidence/02_thickness_scan_<part>.json, rows of
[u, w, lengths, starts, masked] per axis, read by plot_thickness.py.

usage: uv run --with numpy ray_thickness.py <scratch dir with mount.stl and cartridge.stl>
"""
import json
import struct
import sys
from pathlib import Path

import numpy as np

EV = Path(__file__).parent / "evidence"
GRAZE = 0.5          # |cos| between face normal and ray below this = grazing
OFF = 0.0137         # grid offset so rays miss mesh edges


def load_stl(path):
    raw = Path(path).read_bytes()
    n = struct.unpack("<I", raw[80:84])[0]
    if len(raw) == 84 + 50 * n:
        rec = np.frombuffer(raw[84:], dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]))
        return rec["v"].astype(float)
    pts = [list(map(float, l.split()[1:4])) for l in raw.decode().splitlines() if l.strip().startswith("vertex")]
    return np.array(pts).reshape(-1, 3, 3)


def scan(tri, axis, du, dw):
    a = "xyz".index(axis)
    iu, iw = [i for i in range(3) if i != a]
    lo, hi = tri.reshape(-1, 3).min(0), tri.reshape(-1, 3).max(0)
    us = np.arange(lo[iu] + OFF, hi[iu], du)
    ws = np.arange(lo[iw] + OFF, hi[iw], dw)
    nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    nlen = np.linalg.norm(nrm, axis=1)
    keep = (nlen > 1e-12) & (np.abs(nrm[:, a]) > 1e-9 * nlen)
    tri, nrm, nlen = tri[keep], nrm[keep], nlen[keep]
    graze = np.abs(nrm[:, a]) / nlen < GRAZE
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


if __name__ == "__main__":
    tmp = Path(sys.argv[1])
    grids = {"mount": {"x": (1.0, 1.0), "y": (0.5, 1.0), "z": (0.5, 1.0)},
             "cartridge": {"x": (0.25, 0.5), "y": (0.25, 0.5), "z": (0.25, 0.25)}}
    for part, g in grids.items():
        tri = load_stl(tmp / ("%s.stl" % part))
        out = {ax: scan(tri, ax, *g[ax]) for ax in "xyz"}
        (EV / ("02_thickness_scan_%s.json" % part)).write_text(json.dumps(out))
        print(part, {ax: (len(r), sum(x[4] for x in r)) for ax, r in out.items()})
