# DFM checklist: DeskMount for JLC3DP SLA (resin)

- **Parts:** `Mount_Fused` (mount body) and `USBC_Cartridge` (removable USB-C cartridge), from `DeskMount.FCStd`.
- **Process:** JLC3DP SLA resin.
- **Rules source:** [JLC3DP 3D Printing Design Guideline](https://jlc3dp.com/help/article/3D-Printing-Design-Guideline), fetched 2026-10-07.
- **Evidence:** generated from the live FreeCAD model through freecad-mcp. All files are in [`evidence/`](evidence/).

## Result

**2 FAIL, 6 WARN, 12 PASS, 2 N/A.** Fix the FAIL items before ordering in SLA. Both FAIL items are the cartridge's flex arms. The mount body passes every rule.

Revision 4 (2026-10-07): the sliding clearance is now 0.4 mm per face, so the worst case is 0.2 mm (check 10).
- Tongues and arms narrowed from 3.5 to 3.2 mm, and their outer faces moved 0.15 mm inward.
- The body is 0.15 mm narrower per side, so the arms keep 2.5 mm of squeeze travel.
- The detent holes shrank from Ø2.79 to Ø2.65 mm to keep the 0.3 mm preload.
- Check 10 is now judged against JLC's 0.2 mm "assembled parts" rule, since the cartridge and mount are printed separately.
- Evidence regenerated for checks 1, 5, 7–12 and 18. The mount was not re-scanned: only its detent holes changed, inside the 2.0 mm wall.

Revision 3 (2026-10-07): the arm root moved to Z 40 (check 7). The flex analysis shows that this blocks release; see check 7. A clearance-band chart was added for check 10.

Revision 2 (2026-10-07): check 11 is fixed. The gap between the cartridge and RearStop went from 0.25 mm to 0.5 mm, and the evidence for checks 1, 2, 5, 10–12 and 18 was regenerated.

| # | Check | Part | Result |
|---|---|---|---|
| 1 | Build volume | both | PASS |
| 2 | Minimum part size | both | PASS |
| 3 | Closed, valid, single solid | both | PASS |
| 4 | Wall thickness vs part size | Mount | PASS |
| 5 | Wall thickness vs part size | Cartridge | PASS |
| 6 | Snaps / protrusions thicker than 1.5 mm | Cartridge flex arms | **FAIL** |
| 7 | Small columns / pins aspect ratio | Cartridge flex arms | **FAIL** |
| 8 | Hole diameter vs depth | Detent holes | PASS |
| 9 | Hole tolerance effect on detent | Detent holes | WARN |
| 10 | Sliding clearance, separate prints (≥ 0.2 mm worst case) | Tongues in grooves | PASS (rev 4) |
| 11 | Clearance, assembly (≥ 0.2 mm) | Cartridge to RearStop | PASS (fixed in rev 2) |
| 12 | Clearance, moving parts | Squeeze pads | PASS |
| 13 | Laptop fit | Mount | PASS |
| 14 | Embossed / engraved detail (≥ 0.8 × 0.8 mm) | both | PASS |
| 15 | Escape holes | both | N/A (solid parts) |
| 16 | Long-dimension tolerance and post-print drift | Mount | WARN |
| 17 | Large flat panels (warp) | Mount | WARN |
| 18 | USB-C port alignment stack | Cartridge + mount | PASS |
| 19 | Support marks on sliding faces | Cartridge + grooves | WARN |
| 20 | Resin choice for flexing features | Cartridge | WARN |
| 21 | Resin volume / cost | Mount | WARN |
| 22 | Threads / text | both | N/A |

## JLC3DP SLA rules used

| Rule | Value |
|---|---|
| Max build size | 780 × 780 × 530 mm (most resins); 580 × 580 × 380 mm (Grey, 8228, Imagine Black, JLC Temp, 9000HE) |
| Min part size | 5 × 5 × 5 mm or 10 × 2 × 2 mm |
| Min wall by part size | 5 × 5: 0.5 · 10 × 10: 0.8 · 50 × 50: 1.0 · 100 × 100: 1.5 · 200 × 200: 2.0 mm |
| Protrusions, snaps, fasteners | more than 1.5 mm |
| Embossed / engraved | 0.8 mm deep and 0.8 mm wide |
| Hole Φ vs depth h | Φ1.0: h 1–3 · Φ1.5: h 1.5–4.5 · Φ2.0: h 2–6 mm |
| Small columns D vs height H | D1: H 1 · D2: H 2–4 · D3: H 3–6 mm |
| Clearance | assembly 0.2 mm · moving / connecting 0.5 mm |
| Escape holes | Ø ≥ 2.5 mm; two holes if Ø < 3 mm |
| Model tolerance | ±0.2 mm within 100 mm; ±0.3% above 100 mm |
| Hole tolerance | ±0.3 mm |
| Drift over time | 1–3 days: 0.15 mm or 0.15% · 3–7 days: 0.2 mm or 0.20% |

## Checks

### 1. Build volume: PASS

- **Mount:** 63.7 × 311.5 × 232.0 mm. Fits the smaller 580 × 580 × 380 mm envelope, so any resin can be used.
- **Cartridge:** 27.2 × 17.8 × 67.0 mm.
- **Evidence:** [`01_build_volume.json`](evidence/01_build_volume.json), [`01_mount_iso.png`](evidence/01_mount_iso.png), [`01_cartridge_iso.png`](evidence/01_cartridge_iso.png), [`01_assembly_iso.png`](evidence/01_assembly_iso.png).

### 2. Minimum part size: PASS

- The smallest part dimension is 17.8 mm (cartridge Y), above the 5 mm minimum.
- **Evidence:** [`01_build_volume.json`](evidence/01_build_volume.json).

### 3. Closed, valid, single solid: PASS

- Each part is 1 solid with 1 closed shell, and the shape is valid.
- The parts are not hollow, so no resin is trapped.
- **Evidence:** [`01_build_volume.json`](evidence/01_build_volume.json).

### 4. Mount wall thickness: PASS

- **Rule:** the mount is larger than 200 × 200 mm, so the table's top value applies: 2.0 mm minimum.
- **Measured minimum:** 2.0 mm, at the side walls behind the cartridge grooves and entry notches (Y 330–338.5, Z 4–128). This equals the limit.
- **Everywhere else:** 4.0 mm or more (walls, floor, TopPlate, RearStop, gussets).
- **Method:** about 47,000 ray probes along X, Y and Z. Each ray records the thinnest solid it crosses. Rays that graze the round detent holes are masked, since they measure chords of the hole, not walls.
- **Evidence:** [`02_thickness_map_mount.png`](evidence/02_thickness_map_mount.png), [`02_thickness_minima.json`](evidence/02_thickness_minima.json), [`02_thickness_scan_mount.json`](evidence/02_thickness_scan_mount.json).

### 5. Cartridge wall thickness: PASS

- **Rule:** the cartridge sits between the 50 × 50 and 100 × 100 rows, so 1.0–1.5 mm minimum.
- **Measured minimum:** 1.5 mm (flex arms, along X). Next thinnest: 3.1 mm (pocket roof, along Z) and 3.2 mm (tongue width, along Y).
- **Method:** about 24,000 ray probes. Rays grazing the detent balls are masked.
- **Evidence:** [`02_thickness_map_cartridge.png`](evidence/02_thickness_map_cartridge.png), [`02_thickness_minima.json`](evidence/02_thickness_minima.json).

### 6. Snaps / protrusions thicker than 1.5 mm: FAIL

- **Problem:** the flex arms are snap features, and they are exactly 1.5 mm thick. The rule asks for more than 1.5 mm.
- **Constraint:** each arm sits inside a 2.0 mm deep groove, with 0.4 mm clearance to the groove bottom and 0.1 mm outward of the wall face. It can't get thicker without changing the walls.
- **Action:** deepen the grooves to 2.5 mm and thicken the arms to 2.0 mm. The wall behind the groove would then be 1.5 mm, below check 4's 2.0 mm minimum. To keep 2.0 mm, add a 0.5 mm boss on the outside of the wall at the groove (Y 328–336).
- **Evidence:** [`02_thickness_map_cartridge.png`](evidence/02_thickness_map_cartridge.png) (yellow band), [`03_clearance_sections.png`](evidence/03_clearance_sections.png) (Z = 45 panel).

### 7. Small columns / pins aspect ratio: FAIL

- **Rule:** the guideline allows about a 2:1 height-to-diameter ratio (D3: H ≤ 6 mm).
- **Measured (rev 4):**
  - Arm root raised from Z 20 to Z 40 in rev 3.
  - Each flex arm is a free 1.5 × 3.2 mm beam, 31 mm long (Z 40–71), about 21:1 against its thickness. It was 51 mm (34:1).
  - Each squeeze pad still hangs off the top of its arm.
- **Risk:** slender resin beams warp during printing and post-cure, and break when the part is handled or the supports are removed.
- **New problem at Z 40: the cartridge can't be released.** From cantilever analysis ([`05_flex_analysis.png`](evidence/05_flex_analysis.png), [`05_flex_analysis.json`](evidence/05_flex_analysis.json)):
  - To release, the ball must retract 1.2 mm in rev 4 (1.1 mm proud of the groove bottom plus 0.1 mm margin). With the root at Z 40, squeezing the pad that far bends the arm 2.74 mm at the body top (Z 60). The flex gap is only 2.5 mm, so the arm hits the body before the ball clears.
  - Release still works with the root at Z 38 or lower.
  - Root strain at Z 40 is 1.4% on release and 1.6% on insertion. That suits tough resin or PETG only, not a brittle standard resin.
- **Action:** choose one:
  1. Root at Z 30: 0.44% strain on release and 0.49% on insertion. Release clears the body by 0.54 mm, with about 0.65 N ball force.
  2. Root at Z 40 with the flex gap widened to 3.5 mm by narrowing the body 1 mm per side. The pocket walls stay at least 3.3 mm thick. Strain stays at 1.4–1.6%.

  Either way, the arm still exceeds the 2:1 guideline. Ask JLC to support the arm along its length, or accept the risk for a functional prototype.
- **Evidence:** [`05_flex_analysis.png`](evidence/05_flex_analysis.png), [`03_clearance_sections.png`](evidence/03_clearance_sections.png) (Y = 332 panel), [`01_cartridge_iso.png`](evidence/01_cartridge_iso.png).

### 8. Hole diameter vs depth: PASS

- **Detent holes:** Ø2.65 mm through 2.0 mm of wall (rev 4; was Ø2.79). The Φ2.0 row allows h 2–6 mm, so this passes.
- **Other openings:** vents, windows, the cable slot (5 mm) and the RearStop opening (9.5 × 15.5 mm) are all large.
- **Evidence:** [`03_clearance_sections.png`](evidence/03_clearance_sections.png) (Z = 52.5 panel).

### 9. Hole tolerance effect on detent: WARN

- **Rule:** hole tolerance is ±0.3 mm, so the hole can print anywhere from Ø2.35 to Ø2.95 (rev 4 nominal Ø2.65).
- **Effect on preload:**
  - Ø2.35: 0.53 mm preload (firm).
  - Ø2.65 nominal: 0.30 mm.
  - Ø2.95: 0. The ball no longer seats on the hole edge. It floats about ±0.03 mm in the hole, and the cartridge no longer self-centres.
- **Action:** after the first print, check the hole with a Ø2.65 mm pin gauge or drill shank. If it is oversize, ream it or reduce the nominal hole diameter.
- **Evidence:** [`04_tolerance_stack.json`](evidence/04_tolerance_stack.json) (`detent_hole`).

### 10. Sliding clearance, separate prints: PASS (rev 4)

- **Rule applied:** JLC's 0.2 mm minimum for "Modules... printed to be assembled", met in the worst case.
- **Why not the 0.5 mm rule:** JLC's 0.5 mm "moving or connecting parts" rule most plausibly targets print-in-place parts. The guideline doesn't say whether either rule applies to parts printed together or separately, so ask JLC support to confirm.
- **Measured:** 0.40 mm per face on the tongue front and rear faces, the tongue tips and the flex arms (Z 45), on both sides.
- **Worst case:** with ±0.2 mm on each part, the clearance is 0.20–0.60 mm per face, so it meets the 0.2 mm rule. In rev 3 it was 0.25 nominal and 0.05–0.45 worst case.
- **Side effect:** the cartridge has ±0.4 mm of play in X and Y. The detent balls centre it.
- **Visual:** [`06_clearance_bands.png`](evidence/06_clearance_bands.png) shows each interface's nominal gap and worst-case range against the 0.2 mm rule (dashed) and the 0.5 mm rule (dotted), with rev 3 faded for comparison.
- **Evidence:** [`03_clearances.json`](evidence/03_clearances.json), [`03_clearance_sections.png`](evidence/03_clearance_sections.png) (Z = 10 and Z = 45 panels), [`04_tolerance_stack.json`](evidence/04_tolerance_stack.json).

### 11. Clearance, assembly: PASS (fixed in rev 2)

- **Rule:** 0.2 mm minimum for assembled parts.
- **Measured:** 0.50 mm between the cartridge's front face and RearStop's back face.
- **Worst case:** with ±0.2 mm on each part, the gap ranges from 0.1 to 0.9 mm, so it never interferes. It doesn't meet the 0.2 mm worst-case standard applied to check 10, though. A 0.6 mm nominal gap would.
- **Before the fix (rev 1):** the gap was 0.25 mm, which could reach −0.15 mm worst case, enough for the cartridge not to seat on the Floor.
- **Fix:** Cart_Body's front face moved 0.25 mm rearward, to Y 320.725. The pocket is now 13.8 mm deep. Its rear wall, and so the plug position, are unchanged.
- **Evidence:** [`03_clearances.json`](evidence/03_clearances.json), [`03_clearance_sections.png`](evidence/03_clearance_sections.png) (Z = 10 RearStop panel), [`04_tolerance_stack.json`](evidence/04_tolerance_stack.json).

### 12. Clearance, squeeze pads: PASS

- **Measured:** 0.75 mm from pad to wall face, 0.35 mm worst case. The arms have 2.5 mm of squeeze travel before they meet the body.
- **Evidence:** [`03_clearances.json`](evidence/03_clearances.json), [`03_clearance_sections.png`](evidence/03_clearance_sections.png) (Z = 67 panel).

### 13. Laptop fit: PASS

- **Measured:**
  - Lid face to Wall_Lid: 2.00 mm.
  - Bottom case to Wall_Feet: 2.00 mm.
  - Rubber feet to Wall_Feet: 1.10 mm.
  - Laptop end to RearStop: 2.00 mm.
- All are well above the ±0.2 mm wall tolerance.
- **Evidence:** [`03_clearances.json`](evidence/03_clearances.json).

### 14. Embossed / engraved detail: PASS

- There is no text or logo.
- **Smallest recessed feature:** the groove, 2.0 mm deep × 4.0 mm wide.
- **Smallest raised feature:** the detent ball, 1.5 mm high on a 3.0 mm base.
- Both exceed 0.8 × 0.8 mm.
- **Evidence:** [`03_clearance_sections.png`](evidence/03_clearance_sections.png).

### 15. Escape holes: N/A

- Both parts are solid (check 3), so no escape holes are needed.
- If the mount is hollowed to cut cost (check 21), add at least two Ø2.5–3 mm escape holes per cavity, or one of Ø3 mm or more.

### 16. Long-dimension tolerance and post-print drift: WARN

- **Tolerance:** ±0.3% above 100 mm gives ±0.93 mm over the mount's 311.5 mm length and ±0.70 mm over its 232 mm height.
- **Drift:** after printing, resin parts change by 0.47 mm (1–3 days) to 0.62 mm (3–7 days) over the mount's length.
- **Impact:** the laptop has 2 mm of clearance at the ends and sides, so this is fine. The cartridge's interfaces are local, under 20 mm apart, so they see ±0.2 mm, not the long-dimension value.
- **Action:** none for fit. Allow the mount to settle for several days before checking critical dimensions.
- **Evidence:** [`04_tolerance_stack.json`](evidence/04_tolerance_stack.json).

### 17. Large flat panels (warp): WARN

- **Measured:** each side wall is a 311.5 × 228 mm panel only 4 mm thick, and TopPlate is a 64 × 311.5 × 4 mm plate. JLC gives no flatness figure. Large thin resin panels are prone to curl during printing and post-cure.
- **Impact:**
  - TopPlate flatness matters for the double-sided tape bond to the desk.
  - Wall bow changes the 2 mm laptop gap.
- **Action:** ask JLC for an orientation that keeps the side walls vertical in the build. Consider adding stiffening ribs along the outside of TopPlate between the gussets, or thickening TopPlate to 5–6 mm.
- **Evidence:** [`01_mount_iso.png`](evidence/01_mount_iso.png), [`01_mount_right.png`](evidence/01_mount_right.png).

### 18. USB-C port alignment stack (Z): PASS

- **Stack:** cartridge base to pocket centre is 40.44 mm (±0.2), and the floor top is at Z 4 (±0.2). That gives ±0.4 mm worst case and ±0.28 mm RSS, plus a −0.15 mm bias from how the laptop settles.
- **Margin:** about ±0.75 mm of plug float is available, so this is within the plug's lead-in.
- **Evidence:** [`04_tolerance_stack.json`](evidence/04_tolerance_stack.json) (`usb_port_alignment_z`).

### 19. Support marks on sliding faces: WARN

- SLA needs supports, and each support leaves a small bump. A bump on a sliding face eats into the 0.4 mm clearance. In the worst case only 0.2 mm is left.
- **Faces to keep support-free:**
  - Cartridge: tongue faces, arm faces and detent balls.
  - Mount: groove faces and the RearStop back face.
- **Action:** in the order notes, list these faces as no-support / cosmetic faces, or plan to sand them. The fix in check 10 also leaves more room for support marks.

### 20. Resin choice for flexing features: WARN

- The cartridge arms flex every time it is inserted or removed. Bending strain is about 0.3–0.4% at full squeeze. Standard SLA resins are brittle and chip at thin cantilevers.
- **Action:** order the cartridge in a tough or flexible resin, or print it in PETG on FDM. The mount body can use a standard resin.

### 21. Resin volume / cost: WARN

- **Measured:** the mount body is 447.6 cm³ of solid resin. Most of it is in the 4 mm walls, the solid floor ends and the lower wall bands below the windows. The cartridge is 16.1 cm³, mostly its solid base under the pocket.
- **Action:** get quotes solid and hollowed. For a hollow version, the shell must stay at least 2.0 mm (check 4) and needs escape holes (check 15).
- **Evidence:** [`01_build_volume.json`](evidence/01_build_volume.json).

### 22. Threads / text: N/A

- No threads or text. The TopPlate mounts with double-sided tape.

## Actions before ordering

1. **Check 11 (optional):** open the RearStop gap to 0.6 mm so its worst case also meets 0.2 mm. Check 10 is done in rev 4.
2. **Checks 6 and 7:** thicken the flex arms to 2.0 mm with 2.5 mm grooves plus an outside boss. Then either lower the arm root to Z 30, or keep it at Z 40 and widen the flex gap to 3.5 mm. Re-run `flex_analysis.py`, because a thicker arm raises strain.
3. **Check 20:** specify a tough resin for the cartridge, or print the cartridge in FDM PETG.
4. **Check 19:** list the support-free faces in the order notes.
5. **Check 17:** decide on TopPlate stiffening.
6. **Check 9:** after the first print, gauge the detent holes.
7. Re-run this checklist and re-export the STEP files.

## Evidence index

| File | Content |
|---|---|
| [`01_build_volume.json`](evidence/01_build_volume.json) | Bounding boxes, volumes, solid/shell checks, envelope fit |
| [`01_mount_iso.png`](evidence/01_mount_iso.png), [`01_mount_back.png`](evidence/01_mount_back.png), [`01_mount_right.png`](evidence/01_mount_right.png), [`01_mount_bottom.png`](evidence/01_mount_bottom.png) | Mount body views |
| [`01_cartridge_iso.png`](evidence/01_cartridge_iso.png), [`01_cartridge_front.png`](evidence/01_cartridge_front.png), [`01_cartridge_right.png`](evidence/01_cartridge_right.png) | Cartridge views |
| [`01_assembly_iso.png`](evidence/01_assembly_iso.png) | Mount, cartridge and laptop together |
| [`02_thickness_map_mount.png`](evidence/02_thickness_map_mount.png), [`02_thickness_map_cartridge.png`](evidence/02_thickness_map_cartridge.png) | Ray-scan wall-thickness maps, colour-banded |
| [`02_thickness_minima.json`](evidence/02_thickness_minima.json) | Thinnest wall per part and axis, with location |
| [`02_thickness_scan_mount.json`](evidence/02_thickness_scan_mount.json), [`02_thickness_scan_cartridge.json`](evidence/02_thickness_scan_cartridge.json) | Raw ray-scan data |
| [`03_clearances.json`](evidence/03_clearances.json) | Measured gaps: cartridge to mount, laptop to mount, detent preload |
| [`03_clearance_sections.png`](evidence/03_clearance_sections.png) | Zoomed sections of each clearance, annotated |
| [`04_tolerance_stack.json`](evidence/04_tolerance_stack.json) | Worst-case clearances, detent preload range, long-dimension and drift tolerances, port alignment |
| [`05_flex_analysis.png`](evidence/05_flex_analysis.png), [`05_flex_analysis.json`](evidence/05_flex_analysis.json) | Flex arm root strain, release travel vs flex gap, forces vs root height ([`flex_analysis.py`](flex_analysis.py)) |
| [`06_clearance_bands.png`](evidence/06_clearance_bands.png) | Check 10: per-face clearance, nominal and worst case vs JLC rule, now and proposed ([`plot_clearance_bands.py`](plot_clearance_bands.py)) |

## How the evidence was made

- **Probe script:** [`fc_clearance_probe.py`](fc_clearance_probe.py) runs inside FreeCAD. The thickness scans ran inline through freecad-mcp `execute_code`.
- **Plot scripts:** [`plot_thickness.py`](plot_thickness.py) and [`plot_clearance.py`](plot_clearance.py) run with matplotlib from the JSON files.
- **Model state:** the evidence reflects the model as it was in FreeCAD at the time of the checks, before it was saved. Save `DeskMount.FCStd` to keep the model and this checklist in sync.
