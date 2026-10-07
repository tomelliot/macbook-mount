# DeskMount: vertical under-desk mount for a closed MacBook Pro 14

Two printed parts: a mount body taped under the desk, and a removable cartridge that holds the USB-C plug. The laptop slides in end-first and plugs itself in. The design is complete in CAD. Two DFM items on the cartridge's flex arms are still open before ordering in SLA.

**Files**
- `DeskMount.FCStd`: FreeCAD model. The Laptop group is a reference mesh, not a printed part.
- `export/DeskMount_mount.step`: mount body (Mount_Fused), 63.7 x 311.5 x 233.9 mm, 452 cm3.
- `export/DeskMount_usbc_cartridge.step`: cartridge (USBC_Cartridge), 26.9 x 17.8 x 68.9 mm, 16.6 cm3.
- `dfm/DFM_JLC3DP_SLA.md`: JLC3DP SLA checklist with evidence and scripts (rev 4).
- `docs/journal/journal.db`: decisions and rationale; read with the journal skill.
- `reference/`: the original third-party desk mount STL.
- `freecad-mcp/`: FreeCAD MCP server used to drive the model. The project MCP config points here.

**How it holds the laptop**
- The laptop stands on its hinge edge in a 20.74 mm slot, with 2 mm clearance to each wall for felt pads.
- The floor sits 2 mm below the laptop, also for felt.
- RearStop is 2 mm behind the laptop's port end. The plug, not the stop, sets insertion depth.
- TopPlate (64 x 311.5 mm) bonds to the desk underside with double-sided tape. Three 45 deg gussets brace its 35 mm overhang.

**Airflow**
- Floor openings follow the hinge vent strip plus 2 mm, split by two 22.5 mm ribs.
- Wall_Feet repeats the same three openings at hinge height.
- Both walls are solid up to Z 96.75 (twice the port height), with large windows above.

**USB-C cartridge**
- The pocket is centred on the rear USB-C port at X -0.919, Z 50.44, behind a 9.5 x 15.5 mm RearStop opening.
- The cable drops in through a 5 mm roof slot. Pulling it back seats the plug against the pocket's rear wall.
- Tongues slide in vertical grooves in both walls with 0.4 mm clearance per face. The plug's push goes across the rails.
- Fitting: squeeze the two pads, push the cartridge through the rear notches, drop it 59 mm, release.
- Two 1.5 mm hemispherical detents click into dia 2.65 through-holes and centre the cartridge.
- Flex arms are rooted at Z 30. Breakaway ties hold them during printing; clip them off before fitting.

**Open before ordering**
- Flex arms are 1.5 mm thick; JLC asks for more than 1.5 mm on snaps.
- The rubber feet are 1.1 mm from Wall_Feet, so felt thicker than that will press on the feet.
- Nothing clamps the cable, so the plug relies on friction when the laptop is pulled out.
- The DFM evidence predates the Z 30 root, the lowered floor and the breakaway ties.

**Notes**

Port alignment assumes the laptop rests exactly 2.0 mm above the floor. That height now comes from the felt, so thinner or compressed felt lowers the port against the fixed cartridge pocket. The plug's lead-in tolerates about 0.75 mm, which makes the felt stack the main source of vertical misalignment.

The two parts print separately. The sliding fit is judged against JLC's 0.2 mm assembled-parts clearance, which holds in the worst case. JLC's 0.5 mm moving-parts rule reads as a print-in-place rule, but the guideline does not say so. Order the cartridge in a tough resin; the mount suits a standard resin.

Measure the felt stack under the laptop before printing: the cartridge pocket height depends on it.
