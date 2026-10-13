# DFM checklist: DeskMount for JLC3DP SLA (resin)

- **Parts:** `Mount_Rounded` (mount body) and `USBC_Cartridge_Rounded` (removable USB-C cartridge), the print bodies in `Print_Bodies` of `DeskMount.FCStd`. They are rebuilt from the editable parts by `build/rebuild_print_bodies.sh`.
- **Process:** JLC3DP SLA resin.
- **Print orientation:** mount with DeskPlate at the top (+Z build: floor first, DeskPlate last); cartridge upright, pad end to the platform.
- **Rules source:** [JLC3DP 3D Printing Design Guideline](https://jlc3dp.com/help/article/3D-Printing-Design-Guideline), fetched 2026-10-07.
- **Evidence:** generated from the saved `DeskMount.FCStd`. Clearances, sections and model views come from FreeCAD itself: Measure objects (group `DFM_Measures`) and two TechDraw sheets (`DFM_Clearances`, `DFM_Mount_Structure`). Python handles the thickness scan, the support scan and the calculated charts. All files are in [`evidence/`](evidence/).

## Result

**2 FAIL, 7 WARN, 13 PASS, 1 N/A.**
- **Check 4 (FAIL):** a 0.03 mm skin through both walls at Y 316.2, Z 55, at the bottom of the rear access frame.
- **Check 6 (FAIL):** the cartridge's 1.5 mm flex arms against JLC's "more than 1.5 mm" snap rule.
- **Check 23 (WARN, new):** no islands in the print orientation, but the DeskPlate overhang and several flat ceilings need supports.

Revision 6 (2026-10-13): re-run on the print bodies.
- **Mount changes since rev 5:**
  - The riser is the wall grid continued up to DeskPlate, across the gap between the walls; the honeycomb riser and TopPlate are gone.
  - The grid runs to the back of the walls, solid only where the cartridge needs it. Above Z 60.5 the walls end at Y 320.2.
  - The cartridge rails are separate parts (`CartRail_Lid`, `CartRail_Feet`).
  - DeskPlate overhangs 35 mm on the feet side, with three 45° gussets.
  - The floor is a diamond grid with solid rails and three Ø20.74 mm felt discs.
  - Edges are rounded: R1.5 on outer extents, R0.4 on rib ridges, R1.5 on cell corners.
  - 10 self-supporting Λ breakaway struts replace the 13 box struts.
- **Cartridge changes since rev 5:**
  - The lid-side tongue is a mirror of the feet-side tongue (the old one was an invalid shape).
  - The cartridge is rounded like the mount.
  - The squeeze pads now reach the walls' outer faces, above the rails and behind the walls' rear end.
- **Checks 4, 8, 12, 15 and 21** are rewritten for the new geometry, and **check 23** (supports in the print orientation) is new.
- **Evidence regenerated:** all except 07 (breakaway ties), which is unchanged. The STEP files are exported from the print bodies.

Earlier revisions:
- **Rev 5 (2026-10-09):** diamond-grid walls; Measure objects and TechDraw sheets as evidence.
- **Rev 4 (2026-10-07):** sliding clearance went to 0.4 mm per face.
- **Rev 3:** arm root moved to Z 40, which blocked release. Rev 5 uses Z 30.
- **Rev 2:** RearStop gap went to 0.5 mm.

| # | Check | Part | Result |
|---|---|---|---|
| 1 | Build volume | both | PASS |
| 2 | Minimum part size | both | PASS |
| 3 | Closed, valid, single solid | both | PASS |
| 4 | Wall thickness vs part size | Mount | **FAIL** (was PASS) |
| 5 | Wall thickness vs part size | Cartridge | PASS |
| 6 | Snaps / protrusions thicker than 1.5 mm | Cartridge flex arms | **FAIL** |
| 7 | Small columns / pins aspect ratio | Cartridge flex arms | WARN |
| 8 | Hole diameter vs depth | Detent holes | PASS |
| 9 | Hole tolerance effect on detent | Detent holes | WARN |
| 10 | Sliding clearance, separate prints (≥ 0.2 mm worst case) | Tongues in grooves | PASS |
| 11 | Clearance, assembly (≥ 0.2 mm) | Cartridge to RearStop | PASS |
| 12 | Clearance, moving parts | Squeeze pads | PASS |
| 13 | Laptop fit | Mount | PASS |
| 14 | Embossed / engraved detail (≥ 0.8 × 0.8 mm) | both | PASS |
| 15 | Escape holes | Mount | PASS |
| 16 | Long-dimension tolerance and post-print drift | Mount | WARN |
| 17 | Large flat panels and open frames (warp) | Mount | PASS |
| 18 | USB-C port alignment stack | Cartridge + mount + felt | PASS |
| 19 | Support marks on sliding faces | Cartridge + grooves | WARN |
| 20 | Resin choice for flexing features | Cartridge | WARN |
| 21 | Resin volume / cost | Mount | WARN |
| 22 | Threads / text | both | N/A |
| 23 | Supports and islands in the print orientation | Mount | WARN (new) |

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

The guideline gives no overhang or bridge limits. Check 23 uses the common SLA rules of thumb: unsupported overhangs up to about 1 mm, and islands always supported.

## Checks

### 1. Build volume: PASS

- **Mount:** 71.7 × 311.5 × 283.9 mm. Fits the smaller 580 × 580 × 380 mm envelope, so any resin can be used.
- **Cartridge:** 36.7 × 17.8 × 68.9 mm.
- **Evidence:** [`01_build_volume.json`](evidence/01_build_volume.json), [`01_mount_iso.png`](evidence/01_mount_iso.png), [`01_cartridge_iso.png`](evidence/01_cartridge_iso.png), [`01_assembly_iso.png`](evidence/01_assembly_iso.png).

### 2. Minimum part size: PASS

- The smallest part dimension is 17.8 mm (cartridge Y), above the 5 mm minimum.
- **Evidence:** [`01_build_volume.json`](evidence/01_build_volume.json).

### 3. Closed, valid, single solid: PASS

- Each part is 1 valid solid with 1 closed shell. Both also pass FreeCAD's strict self-intersection check (`shape.check(True)`).
- The STEP exports read back with the same volumes: mount 598.70 cm³, cartridge 16.53 cm³.
- **Evidence:** [`01_build_volume.json`](evidence/01_build_volume.json).

### 4. Mount wall thickness: FAIL (was PASS)

- **Rule:** the mount is larger than 200 × 200 mm, so 2.0 mm minimum.
- **Problem:** a 0.033 mm skin of solid through both walls, at Y 316.20–316.23 and Z ≈ 55, on RearStop's front-face plane (Y 316.225). It runs the full wall thickness (lid X −19.5 to −15.5, feet X 9.3 to 17.2), at the bottom of the rear access frame. It will print as a flake or not at all, and a flake can break away.
- **Action:** remove the skin, or thicken it to at least 2 mm, at the bottom of the access frame in both walls.
- **Everywhere else:** at least 2.0 mm. The thinnest sections are the walls behind the cartridge grooves (2.0 mm, Y 330–334) and the grid ribs (2.4 mm).
- **Breakaway struts:** left out of the scan. Their 1.5 mm necks are meant to snap, and they are clipped off after post-cure.
- **Method:** about 102,000 axis-aligned rays through a fine STL mesh of the mount. Each ray records the thinnest solid segment it crosses. A segment that ends on a face within 30° of the ray is a chord of a curved feature (fillet, rounded edge), not a wall, so it is dropped.
- **Since rev 5:** the 0.02 mm floor flake at the old floor vents is gone with the grid floor.
- **Evidence:** [`02_thickness_map_mount.png`](evidence/02_thickness_map_mount.png), [`02_thickness_minima.json`](evidence/02_thickness_minima.json), [`02_thickness_scan_mount.json`](evidence/02_thickness_scan_mount.json).

### 5. Cartridge wall thickness: PASS

- **Rule:** the cartridge sits between the 50 × 50 and 100 × 100 rows, so 1.0–1.5 mm minimum.
- **Measured minimum:** 1.5 mm, the flex arms along X. The 1.35–1.38 mm readings at Y 330.5 and 333.5 are rays skimming the R0.4 rounds on the arm edges, so they are chords, not walls.
- **Breakaway ties:** left out of the scan. Their 0.8 mm necks are meant to snap.
- **Evidence:** [`02_thickness_map_cartridge.png`](evidence/02_thickness_map_cartridge.png), [`02_thickness_minima.json`](evidence/02_thickness_minima.json).

### 6. Snaps / protrusions thicker than 1.5 mm: FAIL

- **Problem:** the flex arms are snap features, and they are exactly 1.5 mm thick. The rule asks for more than 1.5 mm.
- **Constraint:** each arm sits inside a 2.0 mm deep groove, with 0.4 mm clearance to the groove bottom. It can't get thicker without changing the rails.
- **Action:** deepen the grooves to 2.5 mm and thicken the arms to 2.0 mm.
  - The rail behind the groove would then be 1.5 mm, below check 4's 2.0 mm. Add a 0.5 mm boss on the outside of the rail at the groove (Y 328–336) to keep 2.0 mm.
  - Re-run `flex_analysis.py`: a 2.0 mm arm raises root strain by a third.
  - Or ask JLC to accept 1.5 mm for a tough resin.
- **Evidence:** [`02_thickness_map_cartridge.png`](evidence/02_thickness_map_cartridge.png), [`03_clearance_sections.pdf`](evidence/03_clearance_sections.pdf) (section B-B).

### 7. Small columns / pins aspect ratio: WARN

- **Rule:** the guideline allows about a 2:1 height-to-diameter ratio (D3: H ≤ 6 mm).
- **Measured:** each flex arm is a 1.5 × 3.2 mm beam, free from its root at Z 30 to the pad top at Z 71. That's 41 mm, about 27:1 against its thickness, so the rule is not met.
- **Mitigation, printing:** three breakaway ties per arm (Z 38, 46 and 58) and a post under each pad hold the arm to the body during printing and post-cure. Clip them off before fitting. See [`07_breakaway_supports.png`](evidence/07_breakaway_supports.png).
- **Function at Z 30** (cantilever analysis):
  - **Release:** squeezing the pad to retract the ball 1.2 mm bends the arm 1.96 mm at the body top. That's under the 2.5 mm flex gap, so the ball clears first. Release stops working above a root of Z 38.
  - **Root strain:** 0.44% on release and 0.49% on insertion, below 1%.
  - **Forces:** 0.36 N per pad and 0.65 N at the ball, at E = 2.5 GPa.
- **Evidence:** [`05_flex_analysis.png`](evidence/05_flex_analysis.png), [`05_flex_analysis.json`](evidence/05_flex_analysis.json), [`07_breakaway_supports.png`](evidence/07_breakaway_supports.png).

### 8. Hole diameter vs depth: PASS

- **Detent holes:** Ø2.65 mm through 2.0 mm of rail. The Φ2.0 row allows h 2–6 mm.
- **Other openings:** grid cells in the walls, riser and floor, the cable slot (5 mm) and the RearStop opening (9.5 × 15.5 mm) are all large. The riser drain holes are gone with the honeycomb.
- **Evidence:** [`03_clearance_sections.pdf`](evidence/03_clearance_sections.pdf) (section C-C, 2.65 dimensions).

### 9. Hole tolerance effect on detent: WARN

- **Rule:** hole tolerance is ±0.3 mm, so the hole can print anywhere from Ø2.35 to Ø2.95 (nominal Ø2.65).
- **Effect on preload:** 0.53 mm at Ø2.35, 0.30 mm at nominal, and none at Ø2.95. At Ø2.95 the ball floats about ±0.03 mm and no longer centres the cartridge.
- **Measured overlap:** 0.17 mm³ per side between ball and hole edge, which is the designed preload.
- **Action:** after the first print, check the hole with a Ø2.65 mm pin gauge or drill shank. If it is oversize, reduce the nominal diameter.
- **Evidence:** [`04_tolerance_stack.json`](evidence/04_tolerance_stack.json) (`detent_hole`), [`03_clearances.json`](evidence/03_clearances.json).

### 10. Sliding clearance, separate prints: PASS

- **Rule applied:** JLC's 0.2 mm minimum for "Modules... printed to be assembled", met in the worst case. JLC's 0.5 mm "moving or connecting parts" rule most plausibly targets print-in-place parts; ask JLC support to confirm.
- **Measured:** 0.40 mm per face on the tongue front and rear faces, the tongue tips and the flex arms, on both sides.
- **Worst case:** with ±0.2 mm on each part, 0.20–0.60 mm per face.
- **Evidence:** Measure objects M_01–M_06 in `DFM_Measures` ([`03_measures.json`](evidence/03_measures.json)), [`03_clearance_sections.pdf`](evidence/03_clearance_sections.pdf) (sections A-A and B-B), [`06_clearance_bands.png`](evidence/06_clearance_bands.png).

### 11. Clearance, assembly: PASS

- **Measured:** 0.50 mm between the cartridge's front face and RearStop's back face.
- **Worst case:** 0.1–0.9 mm, so it never interferes. A 0.6 mm nominal gap would also meet 0.2 mm in the worst case.
- **Evidence:** Measure object M_07 ([`03_measures.json`](evidence/03_measures.json)), [`03_clearance_sections.pdf`](evidence/03_clearance_sections.pdf) (section A-A).

### 12. Clearance, squeeze pads: PASS

- **Measured:** the pads sit outside the mount, above the rails and behind the walls' rear end. They clear the rail tops by 3.50 mm and the walls' rear end by 6.78 mm, on both sides. No mount face runs alongside them.
- **Squeeze travel:** the arms have 2.50 mm before they meet the cartridge body.
- **Evidence:** Measure objects M_08–M_11 ([`03_measures.json`](evidence/03_measures.json)), [`03_clearance_sections.pdf`](evidence/03_clearance_sections.pdf) (section D-D for the 6.78 gaps, B-B for the 2.50 squeeze travel).

### 13. Laptop fit: PASS

- **Measured:**
  - Lid face to Wall_Lid: 2.00 mm.
  - Bottom case to Wall_Feet: 2.00 mm.
  - Rubber feet to Wall_Feet: 1.10 mm.
  - Laptop end to RearStop: 2.00 mm.
  - Laptop above the floor top: 2.00 mm, for the felt dots on the three floor discs.
- **No clash:** no point of the laptop mesh is inside the mount with the breakaway struts removed (0 of 4,352).
- **Rails:** the rubber feet run along solid rails (Z 19–44 and Z 186–228), so they can't drop into a grid cell during insertion.
- **Evidence:** [`03_clearances.json`](evidence/03_clearances.json) (Python probe: the laptop is a mesh, which FreeCAD Measure can't link to), [`09_mount_structure.svg`](evidence/09_mount_structure.svg).

### 14. Embossed / engraved detail: PASS

- There is no text or logo. The smallest recessed feature is the groove (2.0 × 4.0 mm), and the smallest raised feature is the detent ball (1.5 mm high on a 3.0 mm base).

### 15. Escape holes: PASS

- **No enclosed volumes:** each part is one solid with one shell, so there is no internal cavity to drain.
- **Open structure:** the walls, riser and floor are open grids. Resin drains through the cells and air vents through them during each peel.
- **Evidence:** [`01_build_volume.json`](evidence/01_build_volume.json) (`shells_per_solid`).

### 16. Long-dimension tolerance and post-print drift: WARN

- **Tolerance:** ±0.93 mm over the 311.5 mm length and ±0.85 mm over the 283.9 mm height.
- **Drift:** 0.47 mm (1–3 days) to 0.62 mm (3–7 days) over the length.
- **Impact:** the laptop has 2 mm of clearance at the ends and sides. The cartridge's interfaces are within 20 mm of each other, so they see ±0.2 mm.
- **Action:** let the mount settle for several days before checking critical dimensions.
- **Evidence:** [`04_tolerance_stack.json`](evidence/04_tolerance_stack.json).

### 17. Large flat panels and open frames (warp): PASS

- **JLC feedback (2026-10-09):** long, flat and frame parts with large unoccupied areas can shrink toward the centre or warp along the diagonals.
- **Design response,** following published SLA practice (ribs about 60% of wall thickness, uniform sections, filleted corners, no large open frames):
  - **Diamond grid throughout:** ±45° ribs, 2.4 mm wide, nodes every 40 mm, in the walls, the riser (including across the gap between the walls) and the floor. The triangulated grid resists bowing and diagonal racking.
  - **Solid rails and band:** Z 19–44 and Z 186–228 carry the felt and the rubber feet. They are 2.4 mm plates with the grid continued as ribs behind them.
  - **DeskPlate:** the one large flat panel (71.7 × 293 × 4 mm). The riser grid backs it across its full width, and three gussets brace the 35 mm overhang.
  - **Fillets:** R2 on the bay's inside corners, R1.5 on cell corners and outer edges.
  - **Struts:** 10 breakaway struts hold the slot width through printing and curing, 5 at the front entry and 5 under the middle gusset.
- **Order note:** ask JLC to leave the 10 wall struts in place through post-cure and to remove only their own supports. Clip the struts after curing.
- **Evidence:** [`09_mount_structure.svg`](evidence/09_mount_structure.svg) (Wall_Feet grid), [`02_thickness_map_mount.png`](evidence/02_thickness_map_mount.png), [`01_mount_iso.png`](evidence/01_mount_iso.png).

### 18. USB-C port alignment stack (Z): PASS

- **Datum:** the laptop rests on 2.0 mm of felt and the cartridge on the bare floor, both on the same floor top (Z 2.15). The port centre is at Z 50.44, which is 48.29 mm above the cartridge base.
- **Printed parts:** cartridge base to pocket ±0.2 mm, plus floor flatness between the laptop seat and the cartridge seat ±0.2 mm. That gives ±0.4 mm worst case (±0.28 RSS), plus a −0.15 mm bias from how the laptop settles.
- **Margin:** the plug floats about ±0.75 mm, which leaves ±0.2 mm for the felt. The felt under the laptop must stay within 1.8–2.2 mm after compression.
- **Measured:** Measure objects M_13 and M_14 put the pocket floor 41.84 mm and its roof 54.74 mm above the floor top. That gives a centre 48.29 mm up, matching the port. M_12 shows the cartridge base sits on the floor (0.00).
- **Evidence:** [`03_measures.json`](evidence/03_measures.json), [`04_tolerance_stack.json`](evidence/04_tolerance_stack.json) (`usb_port_alignment_z`).

### 19. Support marks on sliding faces: WARN

- Each SLA support leaves a small bump. A bump on a sliding face eats into the 0.4 mm clearance.
- **Faces to keep support-free:**
  - Cartridge: tongue faces, arm faces and detent balls.
  - Mount: groove faces, the RearStop back face, the felt rails' inside faces and the tops of the three floor discs.
- **Action:** list these as no-support faces in the order notes, or plan to sand them.

### 20. Resin choice for flexing features: WARN

- The arms flex on every insert and removal, with 0.44–0.49% strain at the root. Standard SLA resins are brittle at thin cantilevers.
- **Action:** order the cartridge in a tough resin, or print it in PETG on FDM. The mount can use a standard resin.

### 21. Resin volume / cost: WARN

- **Measured:** the mount is 598.7 cm³ (792 cm³ in rev 5), including 4.3 cm³ of struts.
- **By part,** rounded, before the fuse:
  - each wall: 156.8 cm³;
  - riser grid: 149.7 cm³;
  - DeskPlate: 83.8 cm³;
  - floor: 24.0 cm³;
  - RearStop: 18.5 cm³;
  - gussets: 7.2 cm³;
  - cartridge rails: 7.0 cm³.
  The overlaps at the joins account for the difference to the fused total.
- **Cartridge:** 16.5 cm³.
- **Action:** compare quotes across resins.
- **Evidence:** [`01_build_volume.json`](evidence/01_build_volume.json).

### 22. Threads / text: N/A

- No threads or text. DeskPlate mounts with double-sided tape.

### 23. Supports and islands in the print orientation: WARN (new)

- **Orientation:** +Z build, floor first, DeskPlate last.
- **Method:** the mount as printed (struts in) is voxelised at 0.25 mm and checked layer by layer:
  - an **island** is a region with no solid directly below it;
  - an **overhang** is new solid more than 1 mm sideways from the layer below. Its reach is how far it gets from that support; a bridge of span L reaches L / 2.
- **Islands:** none. The breakaway struts grow from both walls on 45° arms, and each neck is at the lowest point of its arm.
- **Self-supporting:** the 45° grids in the walls, riser and floor, the gussets, and the struts.
- **Needs supports, or a design change:**

| Area | Z | Reach | Area |
|---|---|---|---|
| DeskPlate overhang (feet side, between the gussets) | 278 | 35.0 mm | 9,429 mm² |
| Riser top-row cell ceilings | 275.8 | 17.8 mm | 8,591 mm² |
| Wall inner-face window tops | 19 and 186 | 14.5 mm | 1,444 mm² |
| Slot ceiling under the riser | 228 | 9.3 mm | 4,740 mm² |
| Wall top-row cell ceilings | 225.8 | 5.8 mm | 1,472 mm² |
| Cartridge zone (groove and rail ceilings) | 56–58 | 4.3 mm | 122 mm² |

- **Actions:**
  - Make the flat cell and window ceilings 45° peaks. That leaves only the DeskPlate overhang to support.
  - Accept supports under the DeskPlate overhang. They sit on its outer underside, which is easy to reach and not a cosmetic face.
  - Put the orientation on the order. JLC picks orientation and supports itself unless told.
- **Evidence:** [`08_support_map.png`](evidence/08_support_map.png), [`08_support_scan.json`](evidence/08_support_scan.json).

## Actions before ordering

1. **Check 4:** remove or thicken the 0.03 mm skin at Y 316.2, Z 55 in both walls.
2. **Check 6:** thicken the flex arms to 2.0 mm with 2.5 mm grooves and an outside boss, or get JLC to accept 1.5 mm in a tough resin.
3. **Check 23:** peak the flat ceilings at 45°, and state the orientation (DeskPlate up) on the order.
4. **Check 20:** specify a tough resin for the cartridge, or print it in FDM PETG.
5. **Checks 17 and 19, order notes:** keep the 10 wall struts through post-cure, and list the support-free faces.
6. **Check 18:** measure the felt under the laptop after compression. It must be 1.8–2.2 mm.
7. **Check 9:** after the first print, gauge the detent holes.
8. **Check 11 (optional):** open the RearStop gap to 0.6 mm.

## Evidence index

| File | Content | Made by |
|---|---|---|
| [`01_build_volume.json`](evidence/01_build_volume.json) | Bounding boxes, volumes, solid/shell checks, envelope fit | FreeCAD (headless) |
| [`01_mount_iso.png`](evidence/01_mount_iso.png), [`01_mount_back.png`](evidence/01_mount_back.png), [`01_mount_right.png`](evidence/01_mount_right.png), [`01_mount_bottom.png`](evidence/01_mount_bottom.png) | Mount print body views, with struts | FreeCAD GUI |
| [`01_cartridge_iso.png`](evidence/01_cartridge_iso.png), [`01_cartridge_front.png`](evidence/01_cartridge_front.png), [`01_cartridge_right.png`](evidence/01_cartridge_right.png) | Cartridge print body views, with print ties | FreeCAD GUI |
| [`01_assembly_iso.png`](evidence/01_assembly_iso.png) | Mount, cartridge and laptop together | FreeCAD GUI |
| [`02_thickness_map_mount.png`](evidence/02_thickness_map_mount.png), [`02_thickness_map_cartridge.png`](evidence/02_thickness_map_cartridge.png) | Ray-scan wall-thickness maps, colour-banded | Python |
| [`02_thickness_minima.json`](evidence/02_thickness_minima.json), [`02_thickness_scan_mount.json`](evidence/02_thickness_scan_mount.json), [`02_thickness_scan_cartridge.json`](evidence/02_thickness_scan_cartridge.json) | Thinnest wall per part and axis; raw scan data | Python |
| [`03_measures.json`](evidence/03_measures.json) | Values of the 14 Measure objects in `DFM_Measures`, with the faces they link | FreeCAD GUI |
| [`03_clearance_sections.pdf`](evidence/03_clearance_sections.pdf), [`.svg`](evidence/03_clearance_sections.svg) | TechDraw sheet `DFM_Clearances`: sections A-A to E-E of the cartridge zone, 14 dimensions on model edges | FreeCAD GUI |
| [`03_clearances.json`](evidence/03_clearances.json) | Laptop fit (mesh) and detent overlap volume | FreeCAD (headless) |
| [`04_tolerance_stack.json`](evidence/04_tolerance_stack.json) | Worst-case clearances, detent preload range, long-dimension and drift tolerances, port alignment with felt allowance | Python |
| [`05_flex_analysis.png`](evidence/05_flex_analysis.png), [`05_flex_analysis.json`](evidence/05_flex_analysis.json) | Flex arm root strain, release travel vs flex gap, forces vs root height | Python |
| [`06_clearance_bands.png`](evidence/06_clearance_bands.png) | Per-face clearance from the Measure values, nominal and worst case vs JLC rule | Python |
| [`07_breakaway_supports.png`](evidence/07_breakaway_supports.png) | Cartridge print ties on the flex arms (rev 4) | Python |
| [`08_support_map.png`](evidence/08_support_map.png), [`08_support_scan.json`](evidence/08_support_scan.json) | Islands and unsupported overhangs for the +Z build, by region | Python |
| [`09_mount_structure.pdf`](evidence/09_mount_structure.pdf), [`.svg`](evidence/09_mount_structure.svg) | TechDraw sheet `DFM_Mount_Structure`: Wall_Feet grid | FreeCAD GUI |

## How the evidence was made

0. If the editable parts changed, rebuild the print bodies: `build/rebuild_print_bodies.sh`, then `build/load_print_bodies.py`.
1. `freecadcmd dfm/fc_dfm_run.py` (env `DFM_TMP` = scratch dir) opens the saved model. It:
   - exports both STEP files from the print bodies;
   - writes `01_build_volume.json` and `03_clearances.json` (through [`fc_clearance_probe.py`](fc_clearance_probe.py));
   - writes the STL meshes for the scans (as used, and the mount as printed);
   - cuts the cartridge-zone clip for the clearance sheet.
2. In the FreeCAD GUI, `exec(open("dfm/fc_evidence_export.py").read())` ([`fc_evidence_export.py`](fc_evidence_export.py)):
   - loads the clip;
   - rebuilds the Measure objects through [`fc_measures.py`](fc_measures.py);
   - re-anchors the sheet dimensions by geometry through [`fc_dims_anchor.py`](fc_dims_anchor.py) (TechDraw stores them as edge indices, which change with the model);
   - saves the `01_*.png` views;
   - exports both TechDraw sheets as PDF and SVG.
3. `uv run --with numpy ray_thickness.py $DFM_TMP` runs the thickness scan ([`ray_thickness.py`](ray_thickness.py)).
4. `uv run --with numpy --with scipy --with matplotlib support_scan.py $DFM_TMP` runs the support scan ([`support_scan.py`](support_scan.py)).
5. Plots run with `uv run --with matplotlib`:
   - [`plot_thickness.py`](plot_thickness.py)
   - [`flex_analysis.py`](flex_analysis.py)
   - [`plot_clearance_bands.py`](plot_clearance_bands.py)
6. `python3 tolerance_stack.py $DFM_TMP/facts.json` ([`tolerance_stack.py`](tolerance_stack.py)) updates `04_tolerance_stack.json`.

Run heavy geometry headless: booleans on the full mount have crashed the GUI. [`plot_breakaway.py`](plot_breakaway.py) made `07` in rev 4 and needs inline section data to re-run.
