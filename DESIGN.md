# DeskMount: vertical under-desk mount for a closed MacBook Pro 14

Two printed parts:
- a mount body taped under the desk;
- a removable cartridge that holds the USB-C plug.

The laptop slides in end-first and plugs itself in. The design is complete in CAD. Open DFM items before ordering in SLA are listed at the end.

**Files**
- `DeskMount.FCStd`: FreeCAD model.
  - The Laptop group is a reference mesh, not a printed part.
  - `Mount_Fused` and `USBC_Cartridge` are the editable, unrounded assemblies.
  - `Model_Rounded_Parts` holds `Part::Fillet` features that round RearStop, DeskPlate, Gusset_Lid and both CartRails in the model. Their edge lists are fixed: after an edit to one of these parts, run `build/model_fillets.py` in the GUI.
  - `Print_Bodies` holds the print shapes, `Mount_Rounded` and `USBC_Cartridge_Rounded`. They are static shapes: after any edit to the source parts, rebuild them with `build/rebuild_print_bodies.sh` and load them with `build/load_print_bodies.py`. The walls, Floor, Riser_Grid and cartridge are rounded by script, and the fuse and the corner cutters run in the script too, because FreeCAD's boolean features have no fuzzy tolerance.
  - `DFM_Measures` holds live clearance measurements.
  - TechDraw sheets `DFM_Clearances` (cartridge-zone sections) and `DFM_Mount_Structure` (wall grid) are the dimensioned drawings.
  - Backups of replaced geometry are hidden: `Wall_*_plate_v1`, `*_pre_access`, `*_pre_outboard`, `*_pre_shorten`, `DeskPlate_pre_flip`, `Gusset_Lid_pre_flip`, `Cart_Tongue_Lid_pre_mirror`, `Floor_pre_grid`, `Mount_Breakaway_Struts_pre_lambda`, `Wall_*_pre_skin`, `Wall_*_pre_notch`.
- `export/DeskMount_mount.step`: mount body (Mount_Rounded), 71.7 × 311.5 × 283.9 mm, 598.7 cm³.
- `export/DeskMount_usbc_cartridge.step`: cartridge (USBC_Cartridge_Rounded), 36.7 × 17.8 × 68.9 mm, 16.5 cm³.
- `build/`: scripts that make the print bodies (round the walls, Floor, Riser_Grid and cartridge, fuse the mount, round the corners that span several parts), the in-model fillet script, the shared edge rules (`edge_rules.py`), and the generators for the grid floor and the struts. Output goes to `build/out/` (not in git).
- `dfm/DFM_JLC3DP_SLA.md`: JLC3DP SLA checklist, with evidence and the scripts that regenerate it (rev 6).
- `docs/journal/journal.db`: decisions and rationale. Read it with the journal skill.
- `reference/`: the original third-party desk mount STL.
- `freecad-mcp/`: the FreeCAD MCP server used to drive the model. The project MCP config points here.

**How it holds the laptop**
- The laptop stands on its hinge edge in a 20.74 mm slot, with 2 mm to each wall for felt pads.
- The laptop sits on felt dots on three solid floor discs, 2 mm above the floor top.
- RearStop is 2 mm behind the laptop's port end. The plug, not the stop, sets insertion depth.
- A 50 mm riser (Z 228–278) lifts the slot's entry clear of the desk's 50 mm under-support.
  - DeskPlate (Z 278–282, X −19.49 to 52.25) bonds to the desk with double-sided tape. It covers both walls and overhangs 35 mm past Wall_Feet.
  - Three 35 mm, 4 mm thick 45° gussets brace the overhang, at Y 27, 169 and 316.2.

**Structure**
- **Walls:** a ±45° diamond grid. The ribs are 2.4 mm wide and 8 mm deep, with nodes 40 mm apart. The grid stiffens the walls against bowing and diagonal warp in SLA, and every section is 2.4 mm.
- **Solid rails and band:** Z 19–44 and Z 186–228. They carry the rubber feet and the felt so nothing snags a cell. Each is a 2.4 mm plate with the grid continued as ribs behind it.
- **Front frame:** 4 mm at the entry edge. A 2.4 mm cap closes the top of the rib layer.
- **Riser (Riser_Grid):** the wall grid continues up to DeskPlate, and across the gap between the walls, growing from each wall to meet in the middle. It replaces the former honeycomb riser and TopPlate.
- **Rear:** the grid continues to the back of both walls and is solid only where the cartridge needs it. Above Z 60.5 the walls, riser and DeskPlate end at RearStop's rear face (Y 320.22). Only the cartridge rails and the floor run to Y 338.5.
- **Cartridge rails:** `CartRail_Lid` and `CartRail_Feet` (Y 322.6–338.5, Z −1.85 to 60.5) are separate objects from the walls, so they can be viewed and edited on their own.
- **Floor:** the same diamond grid (40 mm pitch, 2.4 mm ribs, R1.5 cell corners). It is centred in the slot and lined up with the wall grid.
  - Solid 2.4 mm rails run along both walls, at the front edge and in front of RearStop. The R2 coves at the wall bases run unbroken on the side rails.
  - The floor is solid behind RearStop, under the cartridge.
  - Three solid Ø20.74 mm discs (the full slot width) at Y 71, 171 and 271 take the felt dots. They are spaced evenly about the laptop's centre.
- **Edges:**
  - R1.5 on the outer extents: plate and wall corners, wall edges, DeskPlate corners, the full-height front and back corners, the floor's front edges, and the gussets' sloped edges.
  - R0.4 on the remaining rib ridges.
  - R1.5 on internal cell corners, or R0.4 where R1.5 does not fit.
  - Each part is rounded before fusing. Corners that span several parts are rounded after the fuse.
- **Print struts:** 10 breakaway struts tie the walls together during printing and curing.
  - 5 are at the front entry (Y 27–31), to hold the slot width there. 5 are in line with them under the middle gusset (Y 169–173).
  - Both rows sit at Z 25, 74.25, 114.25, 154.25 and 200. At Y 171 the necks land on rib nodes and solid bands.
  - Each strut is a Λ: two 45° arms, 4 mm thick, rising from each wall to an apex over the slot centre. A 1.5 × 1.5 mm breakaway neck sits at the lowest point of each arm, so the strut never starts as a floating island.
  - Keep the struts through post-cure, then clip them off.

**Airflow**
- The open floor cells sit under the hinge vent strip.
- The open grid cells (Z 4–19 and Z 44–186) ventilate both walls.

**USB-C cartridge**
- The pocket is centred on the rear USB-C port at X −0.919, Z 50.44, behind a 9.5 × 15.5 mm opening in RearStop.
- The cable drops in through a 5 mm roof slot. Pulling it back seats the plug against the pocket's rear wall.
- Tongues slide in vertical grooves in both rails, with 0.4 mm clearance per face. The plug's push acts across the rails.
- Fitting: lower the cartridge from above, behind RearStop, until the tongues enter the grooves. Squeeze the pads so the detent balls pass the groove tops, and push it down until the detents click.
- Squeeze pads: one pad on the outer side of each flex arm (Z 64–71). Each pad sits above the rails and behind the shortened walls, flush with the wall's outer face, so a finger pushes it inward from outside the mount.
- Removal: squeeze the two pads and lift the cartridge straight up. The tongues leave the grooves after 58.4 mm.
- Groove tops (Z 60.5): a 1 mm 45° lead-in guides the tongue and the detent ball into the groove.
- Two 1.5 mm hemispherical detents click into Ø2.65 through-holes and centre the cartridge.
- The flex arms are rooted at Z 30. Breakaway ties hold them during printing; clip them off before fitting.
- The lid-side tongue is a mirror of the feet-side tongue; the original lid tongue was an invalid shape.

**Print orientation and supports**

Print the mount with DeskPlate at the top (+Z build, floor first). The layer-by-layer support scan (DFM check 23) finds no islands, and these overhangs:

| Area | Status |
|---|---|
| Wall, riser and floor grid, gussets, struts | Self-supporting (45°) |
| DeskPlate overhang | Needs supports: 35 mm cantilever between the gussets |
| Riser top-row cells (Z 275.8) | Flat ceilings, up to 17.8 mm reach |
| Slot ceiling under the riser (Z 228) | 18.5 mm bridge between the walls |
| Inner-face window tops (Z 19, Z 186) | Flat bridges, up to 14.5 mm reach (29 mm span) |
| Wall top-row cells (Z 226) | Flat ceilings, up to 5.8 mm reach |
| Cartridge zone (Z 56–58) | Small groove and rail ceilings, up to 4.3 mm reach |

Print the cartridge upright, pad end to the platform.

**Open before ordering**
- The flat ceilings in the table above: make them 45° peaks, or accept JLC's supports there.
- Specify the orientation on the JLC order. JLC chooses orientation and supports itself unless told.
- The flex arms are 1.5 mm thick, and JLC asks for more than 1.5 mm on snaps (DFM check 6, FAIL).
- A 0.03 mm skin through both walls at Y 316.2, Z 55, at the bottom of the rear access frame (DFM check 4, FAIL).
- The gusset tips meet the riser at a sharp 45° edge.
- Order notes: keep the 10 wall struts through post-cure, and list the support-free sliding faces.
- The felt under the laptop must measure 1.8–2.2 mm after compression (port alignment).
- The rubber feet are 1.1 mm from Wall_Feet, so felt thicker than that will press on the feet.
- Nothing clamps the cable, so the plug relies on friction when the laptop is pulled out.

**Notes**

The laptop rests on felt and the cartridge on the bare floor, so both share the floor top as a datum. The printed parts use ±0.4 mm of the plug's ±0.75 mm lead-in, and the laptop settles a further 0.15 mm, which leaves ±0.2 mm for the felt.

The two parts print separately. The sliding fit is judged against JLC's 0.2 mm assembled-parts clearance, which holds in the worst case. JLC's 0.5 mm moving-parts rule reads as a print-in-place rule, but the guideline does not say so. Order the cartridge in a tough resin; the mount suits a standard resin.
