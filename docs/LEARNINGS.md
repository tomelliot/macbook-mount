# Learnings

What we learned using an agent (Claude Code + FreeCAD MCP) to design and DFM-check the MacBook mount.

## 3D CAD best practices

- Check every DFM rule against the part as it is made, not as it is used. Fabrication state (orientation, supports, no laptop in the mount) differs from use state.
- Decide the print orientation early and check every feature layer by layer in it. A feature joined to the part only above its lowest point starts as a floating island (the first breakaway struts did).
- Round each part before fusing. Filleting the fused body is slow and fragile; per-part fillets with a self-intersection check (`shape.check(True)`) are fast and reliable.
- Round corners that span several parts after the fuse, with one cutter along the whole corner, so the radius is the same on every part.
- Check the volume change of every fillet, not only its validity. On the walls an OpenCascade fillet returned a valid, self-intersection-free shape that had filled two whole grid cells (+411 mm³ each). A round of radius r on an edge whose faces meet at angle θ removes or adds r²(cot(θ/2) − (π − θ)/2) per mm.
- Turn off Refine on `Part::Cut` features that follow fillets. FreeCAD's default refine left invalid curve-on-surface edges that the same cut without refine does not.
- Run booleans and fillets on a `copy()` of a document object's shape. OpenCascade can raise the tolerances of the input shape's vertices in place, and saving the document then stores a shape that fails the self-intersection check. `limitTolerance` on a copy repairs it.
- FreeCAD 1.1 loads a Python feature's code on open only from FreeCAD's own or the user Mod folders, after resolving symlinks, so a linked project folder is blocked. A blocked feature keeps its last shape, but its code reference is lost when the file is saved. Put a real shim file in the Mod folder that runs the project code.
- Check the vertex tolerances of every fillet result, not only validity and the self-intersection check. A valid R0.4 round on a rail left a 0.38 mm vertex tolerance, and one fuse of all parts then returned an empty shape. A part-by-part fuse still worked.
- Expect OpenCascade fillets to crash the process (segfault) on some short edges, mostly where a small radius meets earlier rounds. Run long builds headless, save after each part, and drop a fallback radius that crashes instead of trying to catch the crash.

## Agent limitations

- **Weak DFM knowledge.** The agent does not know DFM well. Give it feedback, ask it for solutions and best practices, then select the right option yourself.
- **Mistakes of physical reasoning.** Example: it proposed a temporary manufacturing support between the two walls of the mount "because the laptop is there". The laptop is not in the mount during fabrication. Review its proposals for this class of error.
- **Print direction not considered.** It designed breakaway struts whose bodies started below their necks, so they float in a bottom-up build. Ask it to check designs in the print orientation.
- **Rule shortcuts give inconsistent results.** It picked fillet radii from each part's bounding box, so one continuous corner got R0.4 on the wall and R1.5 on the riser. Inspect corners where parts meet.

## Make the agent more effective

- **Tell it to use the native tools.** It does not use native FreeCAD options by default (for example, the measurement and drawing tools to check the design for DFM issues). Ask for them explicitly.
