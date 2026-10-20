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

- `isValid()` misses self-intersections. A PartDesign fillet returned a valid body that the strict check (`check(True)`) found 82 self-intersections in, and every later fillet test on it failed. Strict-check a part before rounding it.
- The strict check on a whole 340 mm lattice body took over an hour. Checking overlapping 60 mm crops took under a minute.
- A fillet's result depends on the state of its input. The same 197-edge fillet failed on a shape read from a BREP file and passed on its topology copy (`copy(False)`), and `Part::Fillet` features recomputed differently from the `makeFillet` tests of the same edges. Store the shape that passed the tests rather than a feature that recomputes it.
- Run each OpenCascade fillet test of a large part in its own process. A segfault then ends one worker, not the build, and the parent can split the failing set and retry.
- When the geometry comes from a generator, build the rounds into the cutting tools (a cell prism with lips at its mouths) instead of searching the finished solid for edges to fillet. On this mount that took the edges left to search from about 2500 to about 1000, and the long sharp edges from 1.6 m to 0.4 m.
- A corner rounded against a line that is open air on one side (a cell clipped at an opening) meets the face tangentially and leaves a zero-angle knife edge. Clip and round only against solid.
- `Shape.isInside()` builds a classifier of the whole solid on every call: 6000 calls on the lattice body took 16 minutes. A local test from the two faces' normals took seconds.

## Agent limitations

- **Weak DFM knowledge.** The agent does not know DFM well. Give it feedback, ask it for solutions and best practices, then select the right option yourself.
- **Mistakes of physical reasoning.** Example: it proposed a temporary manufacturing support between the two walls of the mount "because the laptop is there". The laptop is not in the mount during fabrication. Review its proposals for this class of error.
- **Print direction not considered.** It designed breakaway struts whose bodies started below their necks, so they float in a bottom-up build. Ask it to check designs in the print orientation.
- **Rule shortcuts give inconsistent results.** It picked fillet radii from each part's bounding box, so one continuous corner got R0.4 on the wall and R1.5 on the riser. Inspect corners where parts meet.

## Make the agent more effective

- **Ask for progress logging before a long run.** A rounding run sat for 6.5 hours with no way to tell progress from a stall. Ask for a log line before and after every long step, and a watchdog that reports CPU, time since the last line and a stack sample. On a Mac, keep it awake with `caffeinate -i`: `caffeinate -s` holds only on mains power, and sleep pauses the job.
- **Tell it to use the native tools.** It does not use native FreeCAD options by default (for example, the measurement and drawing tools to check the design for DFM issues). Ask for them explicitly.
