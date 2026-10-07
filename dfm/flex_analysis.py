"""Cantilever check of the cartridge flex arms vs root height.

The arm is a 1.5 x 3.5 mm beam fixed at the root (Z = ROOT). Strain and deflection depend only on geometry, so they
do not depend on the resin's modulus. Forces do, and use E_GPA below.

Two load cases:
  release   - user squeezes the pad (load at pad centre Z 67.5); the ball (Z 52.5) must retract 1.2 mm from its
              free position (1.1 mm proud of the groove bottom + 0.1 mm margin). The arm must not hit the body
              top corner (Z 60) first: flex gap 2.5 mm.
  insertion - ball rides 1.1 mm deflected along the groove bottom (load at the ball).
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

EV = Path(__file__).parent / "evidence"
T, B = 1.5, 3.2            # arm thickness (bending) and width, mm
Z_BALL, Z_BODY, Z_PAD = 52.5, 60.0, 67.5
FLEX_GAP = 2.5
D_RELEASE, D_RIDE = 1.2, 1.1
E_GPA = 2.5                # assumed; SLA resins and PETG are roughly 2-3 GPa
EI = E_GPA * 1e3 * B * T ** 3 / 12  # N mm^2


def defl(x, a, f_over_ei):
    """Deflection at x of a cantilever with point load at a (x measured from the root)."""
    if x <= a:
        return f_over_ei * x * x * (3 * a - x) / 6
    return f_over_ei * a * a * (3 * x - a) / 6


def case(root):
    xd, xb, a = Z_BALL - root, Z_BODY - root, Z_PAD - root
    k = D_RELEASE / defl(xd, a, 1.0)           # F/EI giving the release deflection at the ball
    rel = {"root_strain_pct": 100 * k * a * T / 2, "body_top_deflection_mm": defl(xb, a, k),
           "pad_deflection_mm": defl(a, a, k), "pad_force_N": k * EI}
    k2 = D_RIDE / defl(xd, xd, 1.0)
    ins = {"root_strain_pct": 100 * k2 * xd * T / 2, "body_top_deflection_mm": defl(xb, xd, k2),
           "ball_force_N": k2 * EI}
    return {"root_z": root, "free_length_to_ball_mm": xd, "release": rel, "insertion": ins,
            "release_clears_body": rel["body_top_deflection_mm"] < FLEX_GAP}


roots = [r / 2 for r in range(30, 99)]  # Z 15 .. 49
res = [case(r) for r in roots]
pick = {str(r): case(r) for r in (20.0, 30.0, 35.0, 40.0)}
limit = next(r["root_z"] for r in res if not r["release_clears_body"])
out = {"assumptions": {"arm_mm": [T, B], "release_deflection_at_ball_mm": D_RELEASE, "flex_gap_mm": FLEX_GAP,
                       "E_GPa_for_forces": E_GPA},
       "highest_root_that_releases_before_hitting_body": round(limit - 0.5, 1), "cases": pick}
(EV / "05_flex_analysis.json").write_text(json.dumps(out, indent=1))

fig, axs = plt.subplots(1, 3, figsize=(18, 5.5))
z = [r["root_z"] for r in res]
ax = axs[0]
ax.plot(z, [r["release"]["root_strain_pct"] for r in res], label="release (squeeze pad)")
ax.plot(z, [r["insertion"]["root_strain_pct"] for r in res], label="insertion (ball riding groove)")
ax.axhspan(0, 1.0, color="#7fb069", alpha=0.15)
ax.axhspan(1.0, 2.0, color="#f9c80e", alpha=0.15)
ax.axhspan(2.0, 6, color="#d7263d", alpha=0.10)
ax.text(16, 0.5, "< 1%: OK for brittle resin", fontsize=8)
ax.text(16, 1.5, "1-2%: tough resin / PETG only", fontsize=8)
ax.text(16, 3.0, "> 2%: fatigue / cracking risk", fontsize=8)
ax.set_ylim(0, 4); ax.set_xlabel("Arm root height Z (mm)"); ax.set_ylabel("Peak strain at root (%)")
ax.set_title("Root strain"); ax.legend(fontsize=8, loc="upper center")
ax = axs[1]
ax.plot(z, [r["release"]["body_top_deflection_mm"] for r in res], label="arm at body top (Z 60) during release")
ax.axhline(FLEX_GAP, color="k", ls="--", lw=1); ax.text(16, FLEX_GAP + 0.08, "flex gap 2.5 mm: arm hits body", fontsize=8)
ax.axvspan(limit, max(z), color="#d7263d", alpha=0.1)
ax.text(limit + 0.3, 6.0, "release blocked\nroot Z >= %.1f" % limit, fontsize=8, color="#a01020")
ax.set_xlabel("Arm root height Z (mm)"); ax.set_ylabel("Deflection (mm)"); ax.set_title("Can the ball retract before the arm hits the body?")
ax.legend(fontsize=8, loc="upper left")
ax = axs[2]
ax.plot(z, [r["release"]["pad_force_N"] for r in res], label="squeeze force per pad (release)")
ax.plot(z, [r["insertion"]["ball_force_N"] for r in res], label="ball contact force (insertion drag source)")
ax.set_yscale("log"); ax.set_xlabel("Arm root height Z (mm)"); ax.set_ylabel("Force (N), E = %.1f GPa assumed" % E_GPA)
ax.set_title("Forces"); ax.legend(fontsize=8); ax.grid(True, which="both", lw=0.3, alpha=0.4)
for ax in axs:
    for r, ls in ((20, ":"), (40, "-")):
        ax.axvline(r, color="0.3", ls=ls, lw=0.8)
    ax.grid(True, lw=0.3, alpha=0.4)
axs[0].text(20.3, 3.7, "rev 1 (Z 20)", fontsize=8); axs[0].text(40.3, 3.7, "now (Z 40)", fontsize=8)
fig.suptitle("Cartridge flex arm (rev 4): 1.5 x 3.2 mm cantilever, ball at Z 52.5, pad at Z 67.5", fontsize=12)
fig.tight_layout(rect=(0, 0, 1, 0.94))
fig.savefig(EV / "05_flex_analysis.png", dpi=120)
print(json.dumps(out, indent=1))
