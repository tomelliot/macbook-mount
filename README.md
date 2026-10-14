# DeskMount: vertical under-desk mount for a closed MacBook Pro 14

Two printed parts:
- a mount body taped under the desk;
- a removable cartridge that holds the USB-C plug.

The laptop slides in end-first and plugs itself in. The design is complete in CAD. Open DFM items before ordering in SLA are listed at the end.

**Files**
- `DeskMount.FCStd`: FreeCAD model, in five groups. Everything from the source parts to the print bodies is a chain of features, so the print bodies recompute with the model.
  - `Source`: the editable, unrounded parts, under the two assemblies `Mount_Fused` and `USBC_Cartridge`.
  - `Rounding`: one `<part>_Rounded` feature per printed part, each the end of a short chain of fillets and cuts that rounds that part's edges, plus `Corner_Cutters` for the corners that span several parts. The chains hold fixed edge lists: after editing a part, rebuild its chain with `cad/build_rounding.sh <part>`.
  - `Print_Bodies`: `Mount_Rounded`, a custom feature that fuses the rounded mount parts and rounds the corners that span several parts, and `USBC_Cartridge_Rounded`. Only these are shown on open.
  - `DFM`: live clearance measurements (`DFM_Measures`) and the dimensioned TechDraw sheets `DFM_Clearances` (cartridge-zone sections) and `DFM_Mount_Structure` (wall grid).
  - `Laptop`: the reference laptop mesh, not a printed part.
- `export/DeskMount_mount.step`: mount body (Mount_Rounded), 71.7 × 314.2 × 283.9 mm, 599.9 cm³.
- `export/DeskMount_usbc_cartridge.step`: cartridge (USBC_Cartridge_Rounded), 36.7 × 20.5 × 68.9 mm, 18.7 cm³.
- `cad/`: the scripts behind the model's rounding and print bodies. Output and logs go to `cad/out/` (not in git).
  - `install.sh`: run once per machine. It puts a shim for `mount_fuse.py` in FreeCAD's user Mod folder, so FreeCAD can load it when it opens the model. Without it, `Mount_Rounded` loses its code on open; if the file is then saved, recreate the feature with `mount_fuse.create(doc)`.
  - `rounding.py`: the edge rules and the chain builder. Each chain fillets the inside corners, cuts the cell mouths with rounded-lip cutters, fillets the remaining edges, and cuts any edge a fillet cannot round with a small edge cutter. Every step is tested for validity, self-intersections and the expected volume change.
  - `build_rounding.sh`: builds chains headless and saves the model (close it in the GUI first, or reload it after). A wall takes about 30 minutes, the other parts seconds. `watch_build.sh` follows its log and reports stalls.
  - `mount_fuse.py`: the `Mount_Rounded` feature (a fuse with a fuzzy tolerance, which FreeCAD's own fuse feature lacks) and its corner cutters.
  - `generators.py`: the grid floor and the breakaway struts.
- `dfm/`: the JLC3DP SLA checklist `DFM_JLC3DP_SLA.md`, its `evidence/`, and the scripts that regenerate it. `run_dfm.sh` runs them (see the report's last section).
- `docs/`: `LEARNINGS.md` (using an agent with FreeCAD for this design) and `journal/journal.db` (decisions and rationale; read it with the journal skill).
- `reference/`: the original third-party desk mount STL.
- `freecad-mcp/` (not in git): local clone of the FreeCAD MCP server used to drive the model; the Claude Code MCP config points here.

**Workflow after a design change**
1. Edit the source parts in `DeskMount.FCStd`, save, and close the model in the GUI.
2. `cad/build_rounding.sh <changed parts>`. Reopen the model: the print bodies recompute.
3. `dfm/run_dfm.sh headless`, then `dfm/fc_gui.py` in the GUI, then `dfm/run_dfm.sh plots`. Update the report.

**How it holds the laptop**
- The laptop stands on its hinge edge in a 20.74 mm slot, with 2 mm to each wall for felt pads.
- The laptop sits on felt dots on three solid floor discs, 2 mm above the floor top.
- The laptop's port end sits flush against RearStop, which sets insertion depth. The plug can sit up to 0.2 mm short of fully home.
- RearStop's laptop-side face meets the walls, floor and slot ceiling with R0.5 inside rounds, so the laptop bears on the flat face even when pushed against one wall.
- A 50 mm riser (Z 228–278) lifts the slot's entry clear of the desk's 50 mm under-support.
  - DeskPlate (Z 278–282, X −19.49 to 52.25) bonds to the desk with double-sided tape. It covers both walls and overhangs 35 mm past Wall_Feet.
  - Three 35 mm, 2.4 mm thick 45° gussets (the riser rib thickness) brace the overhang, at Y 27–29.4, 169.8–172.2 and 317.8–320.2. The outer two are flush with the front and back faces.

**Structure**
- **Walls:** a ±45° diamond grid. The ribs are 2.4 mm wide and 8 mm deep, with nodes 40 mm apart. The grid stiffens the walls against bowing and diagonal warp in SLA, and every section is 2.4 mm.
- **Solid rails and band:** Z 19–44 and Z 186–228. They carry the rubber feet and the felt so nothing snags a cell. Each is a 2.4 mm plate with the grid continued as ribs behind it.
- **Front frame:** 4 mm at the entry edge. A 2.4 mm cap closes the top of the rib layer.
- **Riser (Riser_Grid):** the wall grid continues up to DeskPlate, and across the gap between the walls, growing from each wall to meet in the middle. It replaces the former honeycomb riser and TopPlate.
- **Rear:** the grid continues to the back of both walls and is solid only where the cartridge needs it. Above Z 60.5 the walls, riser and DeskPlate end at RearStop's rear face (Y 320.22). Below Z 60.5 the walls, the cartridge rails and the floor run to Y 341.2, flush with the cartridge's back.
- **Cartridge rails:** `CartRail_Lid` and `CartRail_Feet` (Y 316.2–341.2, Z −1.85 to 60.5) are separate objects from the walls, so they can be viewed and edited on their own. Their front lines up with RearStop's laptop-side face, so the wall grid ends on a solid face there.
- **Floor:** the same diamond grid (40 mm pitch, 2.4 mm ribs, R1.5 cell corners). It is centred in the slot and lined up with the wall grid.
  - Solid 2.4 mm rails run along both walls, at the front edge and in front of RearStop. The R2 coves at the wall bases run unbroken on the side rails.
  - The floor is solid behind RearStop, under the cartridge.
  - Three solid Ø20.74 mm discs (the full slot width) at Y 71, 171 and 271 take the felt dots. They are spaced evenly about the laptop's centre.
- **Edges:**
  - R1.5 on the outer extents: plate and wall corners, wall edges, DeskPlate corners, the full-height front and back corners, the floor's front edges, and the gussets' sloped edges.
  - R0.4 on the remaining rib ridges.
  - R1.5 on internal cell corners, or R0.4 where R1.5 does not fit.
  - The ends of the rounds are rounded R0.4 where it fits.
  - Each part is rounded before fusing. An edge that another part touches only at an end is rounded with its part; one that another part touches along its length is a join and stays sharp. Corners that span several parts are rounded after the fuse: outside corners with cutters (including DeskPlate's feet-side bottom edge, which also trims the gusset tips) and inside corners with fills (the R1.5 between the rail tops and the wall ends at Y 320.2).
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
- The pocket fits a plug whose overmold is 23 mm long, 12 mm wide and 6 mm thick, plus the standard 6.65 mm metal tip. It is 6.4 × 12.4 mm (0.2 mm clearance per side, so the plug floats ±0.2 mm), and its rear wall is 23.2 mm behind RearStop's face (Y 339.4): the overmold plus a 0.2 mm buffer. The rear wall is 1.8 mm thick; the cartridge ends at Y 341.2. The overmold bears on it over 16.2 mm², about 1.2 MPa at 20 N.
- The cable (Ø5.0) drops in through a 5.2 mm top cutout over the pocket. The strain relief (Ø5.5) leaves through a 7.5 mm exit in the rear wall with an R3.75 bottom on the plug axis: 1.0 mm clear all round.
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
