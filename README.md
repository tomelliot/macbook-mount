# DeskMount: vertical under-desk mount for a closed MacBook Pro 14

Two printed parts:
- a mount body taped under the desk;
- a removable cartridge that holds the USB-C plug.

The laptop slides in end-first and plugs itself in. The design is complete in CAD. Open DFM items before ordering in SLA are listed at the end.

**Files**
- `DeskMount.FCStd`: FreeCAD model, in five groups.
  - `Source`: the unrounded parts, under the two assemblies `Mount_Fused` and `USBC_Cartridge`. In `Mount_Fused`:
    - `MountBody` (walls, riser, floor, RearStop, DeskPlate, gussets), built by `cad/mount_body.py`. It is `MountSolid` (a PartDesign Body of the plain features) with `MountFills` (inside rounds) fused on, less `MountCellTools` (one rounded tool per lattice cell, plus the outer edge rounds).
    - `CartRail_Lid`, `CartRail_Feet` and `Mount_Breakaway_Struts`.
  - `Rounding`: one `<part>_Rounded` per printed part, a compound of the last of a short chain of stored shapes (fillets and cuts) that rounds the edges the part's tools did not. The chain does not recompute with the model: after a change, rebuild it with `cad/build_rounding.sh <part>`.
  - `Print_Bodies`: `Mount_Rounded`, a custom feature that fuses the rounded mount parts and rounds the corners that span several parts, and `USBC_Cartridge_Rounded`. Only these are shown on open.
  - `DFM`: live clearance measurements (`DFM_Measures`) and the dimensioned TechDraw sheets `DFM_Clearances` (cartridge-zone sections) and `DFM_Mount_Structure` (wall grid).
  - `Laptop`: the reference laptop mesh, not a printed part.
- `export/DeskMount_mount.step`: mount body (Mount_Rounded), 71.7 × 314.2 × 283.9 mm, 567.9 cm³.
- `export/DeskMount_usbc_cartridge.step`: cartridge (USBC_Cartridge_Rounded), 36.7 × 20.5 × 68.9 mm, 18.7 cm³.
- `cad/`: the scripts behind the model's rounding and print bodies. Output and logs go to `cad/out/` (not in git).
  - `install.sh`: run once per machine. It puts a shim for `mount_fuse.py` in FreeCAD's user Mod folder, so FreeCAD can load it when it opens the model. Without it, `Mount_Rounded` loses its code on open; if the file is then saved, recreate the feature with `mount_fuse.create(doc)`.
  - `mount_body.py`: builds `MountBody` (`BUILD_BODY=1 freecadcmd cad/mount_body.py`, about 2 minutes) and saves the model. The cells and their rounds come from the lattice definition, so no search is needed for them:
    - each cell tool is the R1.5 cell prism with an R0.4 lip at every face the cell opens on (walls, floor, RearStop);
    - where a skin or the riser band clips a cell, the corner is R1.5 and the band's edge in the cell gets a lip;
    - between the walls the cells are cut unclipped where the cavity and the riser openings are open, and their sides get R0.4 cutters where they cross the cavity ceiling and the openings' faces;
    - fixed cutters round the straight outer edges (R1.5 bottom, DeskPlate top and tail-end edges, R0.4 tail top), and fills round the inside corners (R1.5 under DeskPlate, R0.5 at RearStop and the gusset roots, R0.4 at the cavity's top corners and the openings).
  - `rounding.py`: rounds the edges the tools leave (about 1000 short edges on `MountBody`), and the other parts. The stages are: R1.5 concave and major edges, rounded-lip cutters on closed mouth loops, R0.4 on the rest, edge cutters, and a last R0.4 pass. Each stage tests its edges in 60 mm blocks in parallel `freecadcmd` workers (`round_check.py`), then checks the stage's own shape: validity, self-intersections (in crops), vertex tolerances and the expected volume change. A fillet that crashes OpenCascade ends only its worker. `cad/out/rounding_cache.json` keeps each stage's results, so a rebuild tests only edges that changed (`ROUND_NOCACHE=1` for a full search).
  - `build_rounding.sh`: builds chains headless and saves the model (close it in the GUI first, or reload it after). `MountBody` takes about 20 minutes. It keeps the Mac awake while it runs, and a watchdog adds `WATCH` lines to the log every 5 minutes (CPU, minutes since the last line, and a stack sample when a step runs long).
  - `mount_fuse.py`: the `Mount_Rounded` feature (a fuse with a fuzzy tolerance, which FreeCAD's own fuse feature lacks) and its corner cutters.
  - `generators.py`: the breakaway struts.
  - `recompute_mount.py`: recreates `Mount_Rounded` headless after a part changes, saves, and checks the feature reopens with its code.
- `dfm/`: the JLC3DP SLA checklist `DFM_JLC3DP_SLA.md`, its `evidence/`, and the scripts that regenerate it. `run_dfm.sh` runs them (see the report's last section).
- `docs/`: `LEARNINGS.md` (using an agent with FreeCAD for this design) and `journal/journal.db` (decisions and rationale; read it with the journal skill).
- `reference/`: the original third-party desk mount STL.
- `freecad-mcp/` (not in git): local clone of the FreeCAD MCP server used to drive the model; the Claude Code MCP config points here.

**Workflow after a design change**
1. Close the model in the GUI. For the mount body, edit `cad/mount_body.py` and run `BUILD_BODY=1 freecadcmd cad/mount_body.py`; for the other parts, edit them in the model and save.
2. `cad/build_rounding.sh <changed parts>`, then `freecadcmd cad/recompute_mount.py` (rebuilds `Mount_Rounded`).
3. `dfm/run_dfm.sh headless`, then `dfm/fc_gui.py` in the GUI, then `dfm/run_dfm.sh plots`. Update the report.

**How it holds the laptop**
- The laptop stands on its hinge edge in a 20.74 mm slot, with 2 mm to each wall for felt pads.
- The laptop sits on felt dots on three solid floor discs, 2 mm above the floor top.
- The laptop's port end sits flush against RearStop, which sets insertion depth. The plug can sit up to 0.2 mm short of fully home.
- RearStop's laptop-side face meets the walls and floor with R0.5 inside rounds, so the laptop bears on the flat face even when pushed against one wall.
- RearStop is a ±45° grid like the walls (2.4 mm ribs, R1.5 cell corners), one diamond wide: 8 diamonds up the centre and 7 half-diamonds against each wall. It is solid below Z 63 (the plug window and the zone in front of the cartridge) and in a 2.4 mm border along the walls and the slot ceiling. Every cell top is a 45° peak. The laptop's end bears on the ribs.
- A 50 mm riser (Z 228–278) lifts the slot's entry clear of the desk's 50 mm under-support.
  - DeskPlate (Z 278–282, X −19.49 to 52.25) bonds to the desk with double-sided tape. It covers both walls and overhangs 35 mm past Wall_Feet.
  - Three 35 mm, 2.4 mm thick 45° gussets (the riser rib thickness) brace the overhang, at Y 27–29.4, 169.8–172.2 and 317.8–320.2. The outer two are flush with the front and back faces.

**Structure**
- **Walls:** a ±45° diamond grid. The ribs are 2.4 mm wide and 8 mm deep, with nodes 40 mm apart. The grid stiffens the walls against bowing and diagonal warp in SLA, and every section is 2.4 mm.
- **Solid rails and band:** Z 19–44 and Z 186–228. They carry the rubber feet and the felt so nothing snags a cell. Each is a 2.4 mm plate with the grid continued as ribs behind it.
- **Front frame:** 4 mm at the entry edge. A 2.4 mm cap closes the top of the rib layer.
- **Riser:** the wall grid continues up to DeskPlate and across the gap between the walls. Over the slot it is open at the front and back (4 mm openings), and a 2.4 mm band across it (Y 169.8–172.2) carries the middle gusset.
- **Rear:** the grid continues to the back of both walls and is solid only where the cartridge needs it. Above Z 60.5 the walls, riser and DeskPlate end at RearStop's rear face (Y 320.22). Below Z 60.5 the walls, the cartridge rails and the floor run to Y 341.2, flush with the cartridge's back.
- **Cartridge rails:** `CartRail_Lid` and `CartRail_Feet` (Y 316.2–341.2, Z −1.85 to 60.5) are separate objects from the walls, so they can be viewed and edited on their own. Their front lines up with RearStop's laptop-side face, so the wall grid ends on a solid face there.
- **Floor:** the same diamond grid (40 mm pitch, 2.4 mm ribs, R1.5 cell corners). It is centred in the slot and lined up with the wall grid.
  - Solid 2.4 mm rails run along both walls, at the front edge and in front of RearStop. The R2 coves at the wall bases run unbroken on the side rails.
  - The floor is solid behind RearStop, under the cartridge.
  - Three solid Ø20.74 mm discs (the full slot width) at Y 71, 171 and 271 take the felt dots. They are spaced evenly about the laptop's centre.
- **Edges:**
  - R1.5 on the outer extents: the bottom edges, DeskPlate's top edges, the tail's end edges, the full-height front and back corners, and the gussets' sloped edges.
  - R0.4 on the cell mouths and the remaining rib ridges.
  - R1.5 on cell corners, including where a skin or the riser band clips a cell. In the walls only the cell corners along X are inside rounds; the corners where the cells meet the skins' faces stay sharp.
  - R0.5 at RearStop's inside corners and the gusset roots; R1.5 under DeskPlate on the feet side; R0.4 at the cavity's top corners and the openings' inside corners.
  - Each part is rounded before fusing. An edge that another part touches along its length is a join and stays sharp. Corners that span several parts are rounded after the fuse: outside corners with cutters (including DeskPlate's feet-side bottom edge, which also trims the gusset tips) and inside corners with fills (the R1.5 between the rail tops and the wall ends at Y 320.2).
  - About 390 mm of edge longer than 3 mm stays sharp. Most of it (about 300 mm) is at the rail grooves and the tail end, which the rail parts' rounding has not been rebuilt for yet.
- **Print struts:** 20 breakaway struts tie the walls together during printing and curing.
  - 4 rows of 5: at the front entry (Y 27–31), to hold the slot width there, and at Y 91, 171 (under the middle gusset) and 251. The rows at Y 91 and 251 halve the two 140 mm gaps between the entry and RearStop.
  - All rows sit at Z 25, 74.25, 114.25, 154.25 and 200. Y 91, 171 and 251 are the same column of wall-grid nodes, so the necks land on rib nodes and solid bands.
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
- Thin sections on the new mount body (DFM check 4, to re-check): the thickness scan finds sub-millimetre segments where a skin's top, a cell and the cavity ceiling meet (X −11.5 and 9.5, Z 228.2–228.7) and at the front gusset's tip (0.66 mm). The 0.03 mm skin at Y 316.2, Z 55 (rev 6) has not been re-checked.
- Rebuild the rail parts' rounding on the new body, for the sharp edges at the rail grooves and the tail end.
- Order notes: keep the 20 wall struts through post-cure, and list the support-free sliding faces.
- The felt under the laptop must measure 1.8–2.2 mm after compression (port alignment).
- The rubber feet are 1.1 mm from Wall_Feet, so felt thicker than that will press on the feet.
- Nothing clamps the cable, so the plug relies on friction when the laptop is pulled out.

**Notes**

The laptop rests on felt and the cartridge on the bare floor, so both share the floor top as a datum. The printed parts use ±0.4 mm of the plug's ±0.75 mm lead-in, and the laptop settles a further 0.15 mm, which leaves ±0.2 mm for the felt.

The two parts print separately. The sliding fit is judged against JLC's 0.2 mm assembled-parts clearance, which holds in the worst case. JLC's 0.5 mm moving-parts rule reads as a print-in-place rule, but the guideline does not say so. Order the cartridge in a tough resin; the mount suits a standard resin.
