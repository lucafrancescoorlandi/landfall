# Changelog

All the versions released after 3.27.2, newest first. Every fix listed here was
found by measuring something, and the measurement is quoted where it explains
the change.

---

## 3.41.2

**E extruded at distance zero.** The move chained to the extrusion was
defined with `release_confirm`, so it confirmed the moment E was released:
a normal tap of the key produced the new faces exactly on top of the old
ones, and the mouse never got to set the distance. It only worked if E was
held down while dragging. Found while capturing the command guide, by
comparing the same gesture with G, which moved as expected. The option is
gone: press E, move the mouse, click or press Enter — the same as
Blender's own E. The adjust panel and its six parameters are unchanged.

---

## 3.41.1

**The snap pie moves to Shift+Alt+X.** On Shift+Alt+S it covered *To Sphere*
in Edit Mode — the shortcut tutorials use to turn a square of vertices into
a circle before cutting a round hole — and Landfall's rule is to add on top
of Blender rather than take its keys away. The self check of 3.41.0 is what
found it. X is Maya's snap-to-grid key, and Shift+Alt+X is free in every
keymap the pie is registered in, checked against Blender 5.2's own
configuration. On a stock 5.2 the self check now reports no NOTE at all.

---

## 3.41.0

Less code, same behaviour, a stricter self check. Eighty-three lines fewer
than 3.40.0 before the new checks, about fifty more for them.

**Removed or folded.** `landfall.grid_shade`, an operator no button had
called since the slider moved to a scene property. Three globals and six
functions for the overlay draw handlers, which differed only by name, are
one table and one function. Four keymap disable functions repeating the
same removal loop share one helper. A parameter of `_wake_user_kmi` that
nobody passed, a subdivision level set twice, and a `__main__` block that
means nothing in an extension.

**A keymap that did not exist.** Maya navigation was registered into
"Grease Pencil Stroke Edit Mode", a name Blender 5.2 no longer has;
`keymaps.new()` created it silently and the entries never fired. The
keymap is "Grease Pencil Edit Mode" and the navigation now works there.

**The self check looks at the keymaps too.** Every keymap name we write
into must exist in Blender's own configuration, or it is reported. And
every shortcut of ours that sits on top of one of Blender's in the same
keymap is listed as a NOTE, except the replacements made on purpose — E,
Ctrl+O, Ctrl+Shift+S and Alt plus a mouse button. On a stock 5.2 that
leaves exactly one: the snap pie on Shift+Alt+S hides *To Sphere* in Edit
Mode. Whether to move one of them is a decision, not a bug, so the check
only says it.

Verified: the panels of the sidebar and the Scene tab drawn in six modes
with stderr captured and empty; every dynamic tooltip answered for every
value; 194 operator calls across five modes without an exception; the
extrusion reference values; nothing left behind on disable.

---

## 3.40.0

Reactivity of the border edge overlay, and a stability pass over the rest.
Measured on macOS with Blender 5.2.1 on meshes of 840, 20,200 and 289,560
edges.

**The refresh in Edit Mode follows the mesh and the mouse.** The border
used to refresh on a fixed clock of a quarter of a second, whether or not
anything had changed — and our own sync of the edit cage produced a
depsgraph update that invalidated the result just computed, so the cycle
fed itself at every redraw. Now the depsgraph says when the mesh actually
changed, our own update is recognised and ignored, and the interval is
derived from the measured cost of the refresh: 30 ms on a mesh that reads
in a fraction of a millisecond, 80 ms on 290,000 edges, never more than a
quarter of a second. Sitting still in Edit Mode costs 0.01 ms per frame.
A refresh deferred by the interval schedules its own redraw, so the border
catches up even when the mouse stops before it was due.

**One scan and one set of GPU batches per viewport.** `visible_get()`
answers for the viewport in the context, so a viewport in Local View sees
a different set of objects than its neighbour; a single shared scan
flipped between the two on every frame and rebuilt both batches each time.
Checked with two viewports and with Quad View, whose four regions share
one space and therefore one store.

**Overlays saved on come back on.** The draw handlers were added only by
the buttons' update callbacks. A file saved with border edges or the cage
on — or the add-on re-enabled over such a scene — showed the button lit
and drew nothing until it was switched off and on again. The three
handlers now live as long as the add-on; the scene flags decide what is
drawn, and a flag that is off costs one comparison per redraw.

**A new file closes what the old one left floating.** The shortcut sheet
and the marking menu are modal operators, which die with the file they
were started in; their draw handlers did not, and a new file could open
with a sheet nobody could close. Both are closed on load.

Verified in this pass, and unchanged: undo and redo with the overlays on,
deleting objects while they draw, topology changes, mirror and other
modifiers that open or close borders, linked duplicates, Local View;
disabling the add-on leaves no handler, no timer, no keymap entry and no
draw handler behind, and puts Blender's own E and Alt+click back.

---

## 3.39.0

Measured on a scene of 1,203 mesh objects, 401 of them subdivided, plus a
290,000-edge mesh for Edit Mode. Every figure below is from that scene, on
macOS with Blender 5.2.1, before and after.

**The overlays no longer walk the scene on every redraw.** Border edges and
cage each visited every object of the view layer on every frame of every
viewport — visibility, selection, the modifier stack — and concatenated
twelve hundred arrays, only to find that the GPU batch from the previous
frame was still good. 3.8 ms and 3.2 ms per frame with nothing moving. The
walk is now done once and kept until the depsgraph reports something that
can change its result: a visibility or selection change, a modifier added
or removed. Dragging an object is a transform update and triggers no walk.
A time limit of half a second is the safety net. A frame at rest now costs
0.12 ms and 0.04 ms; during a drag, the same.

**Edit Mode reads at attribute speed.** A mesh in Edit Mode exposes no
attribute layers at all — `mesh.attributes` is empty — so every read fell
back on the collection wrappers, which are the slow path the code had been
avoiding everywhere else: 50 ms on 290,000 edges, against 1.3 ms for the
same mesh in Object Mode. `to_mesh()` after the sync hands back the same
data with the attributes present; the whole read is now 4.4 ms, and it was
checked to follow a vertex being moved. The size check moved before the
sync, so a mesh above the limit is no longer synced four times a second for
nothing.

**The fresh-object budget is a time, not a count.** Four hundred fresh
objects in one frame took 236 ms; the budget is now six milliseconds of
computation per redraw, and the remaining objects arrive over the next
frames. The worst frame on that scene went from 236 ms to 7 ms.

---

## 3.38.0

A review pass over the whole file, with each fault confirmed either by a
static check or in a running Blender before it was touched.

**Loop select on double click was silently off.** After a keymap rebuild the
mutings are re-applied, and that step silenced every `mesh.loop_select` and
`mesh.edgering_select` entry in the Mesh keymap by name — including our own
double-click ones, which Blender mirrors into the same keymap. The user
keymap is saved with the preferences, so once muted they stayed muted across
sessions. Seen on a real macOS install: both entries inactive, double click
doing nothing. The muting now touches only Blender's Alt+click entries, and
the double-click ones are woken up whenever navigation is enabled.

**The shortcut sheet did not draw.** Two nested functions read a variable
named `size` that did not exist, so the draw handler raised on every redraw
and the card never appeared. A static check found it at once; no script in
the battery reaches the drawing, which is exactly where it had been hiding.

**Load PBR set failed with a height map.** The material output node was
fetched under one name and used under another, so wiring the Displacement
node raised a `NameError`. Sets without a height map were unaffected.

**Finite grid with an odd number of cells drew no axes.** The axis lines were
the grid lines that happened to pass through the origin, and with an odd
count none does. Blender's own axes are switched off by the finite grid, so
the viewport had none at all. The two axes are now drawn on their own.

**GPU batches are rebuilt only when geometry or a transform changed.** Every
depsgraph update — a click on an object counted for four — bumped the overlay
generation and threw away both overlays' batches. The two handlers are now
one, and it drops the batches only when an object it had cached was actually
invalidated.

**The Modeling panel scanned the keymap on every redraw.** Three full passes
over four thousand entries to build labels that are only shown when *Show
shortcuts on the buttons* is on. The scan now happens only in that case. The
shortcut sheet keeps its rows for two seconds instead of reading sixteen
bindings per redraw, which cost 6 ms a frame.

**Timers are registered once and removed on disable.** Opening several files
in a row stacked a copy of the gizmo and keymap timers per file; disabling the
add-on left pending ones to fire into an unregistered module. The keymap
repair also ran with no preferences to read, which is the disabled case.

**Update callbacks no longer depend on `context.window`.** Setting a
Landfall scene property from a timer, the console or a script raised before
the redraw. Redraws now go through the window manager.

Also: the marking menu's open-branch chip was built and painted twice; a
block of its constants was defined twice; a list of muted entries was filled
and never read; the native extrude muting was written out in two places that
had already started to differ. All folded into one.

---

## 3.37.1

**The transform gizmos are applied over several rounds, not once.** A single
pass 0.2 s after registering was enough on Windows and not on macOS, where nine
viewports out of ten still had them off with the preference on: whatever builds
the workspaces had not finished. Same fix, and same reason, as the keymap repair
in 3.29.0 — a wait chosen by intuition is a wait that is wrong on some machine.

---

## 3.37.0

**The overlay switch is an enum.** `landfall.toggle_scene_flag` took a free
string and reported `Unknown switch` after the fact. Blender now refuses a wrong
value at the call instead.

**Reverted an optimisation that gained nothing.** Face normals and areas were
cached once per step in the extrude, instead of being recomputed per vertex. The
measurement on ten thousand faces: 93.3 ms against 92.6 ms — inside the noise.
The cost sits inside Blender's own `extrude_face_region`, so the cache was
removed rather than kept for the look of it.

---

## 3.36.0

**Extrude: directions are computed from the source faces, before extruding.**
They used to be worked out afterwards, from the faces recognised as "made only
of new vertices". That looked right and was wrong: on the caps of a cylinder the
side walls are also made only of new vertices. A probe placed inside the running
code showed a vertex touching three faces — the cap and two radial walls — and a
direction tilted by forty-five degrees. The caps of a cylinder moved to z 1.903
instead of 1.5.

---

## 3.35.0

**Extrude: even-offset correction.** Moving each vertex by `thickness` along the
average of its normals does not leave the faces `thickness` apart: on an edge or
a corner the average is tilted. A cube with every face selected and a thickness
of 0.5 grew by 0.289, which is 0.5 over the square root of three — the corner
belongs to three faces. Dividing by the average cosine restores the requested
distance. On a flat face the cosine is one and nothing changes.

Also in 3.35.1: the displacement is computed for every vertex first and applied
afterwards. Reading normals while moving vertices meant the first vertex moved
changed the normals used by the next ones, and a cube came out asymmetric — 1.569
on one side, −1.500 on the other.

---

## 3.34.0

**Extrude: displacement is per vertex, along its own normal.** A single averaged
normal for the whole selection works on a flat region and breaks as soon as the
faces disagree. The two caps of a cylinder point opposite ways, the average
cancels, and both caps translated sideways together instead of one up and one
down. A cube with every face selected translated instead of inflating.

The averaged normal survives only as the twist axis, and the twist is skipped
when it cancels out: rotating around a vector that does not exist means nothing.

---

## 3.33.0

**Extrude: the source face is removed.** It used to stay where it was and become
an internal diaphragm. One extrusion gave eleven faces instead of ten and four
non-manifold edges; with four divisions, twenty-six faces instead of twenty-two
and sixteen non-manifold edges. A non-manifold mesh breaks booleans, sculpting
and export, so this was not cosmetic.

**Extrude: the parameters reset between runs.** Blender remembers the values of
the last run and offers them again, so a second extrusion started with the
divisions and taper of the first. Maya resets every time.

In 3.33.1 the deletion context became `FACES` rather than `FACES_ONLY`: the
first also takes away vertices and edges left without any face. Extruding the
whole closed surface of a sphere creates no side walls, so the original shell
stayed inside as forty-two loose vertices and a hundred and twenty loose edges.

---

## 3.32.0

**Keymap mutings are re-applied after a rebuild.** `restore_to_default` brings
back every stock entry, including the ones Landfall deliberately silences. `E`
ended up with both our extrude and Blender's own active at once, and loop select
came back on Alt+click where the orbit lives. Two of our own functions were
undoing each other.

---

## 3.31.0

**Maya extrude on `E`, chained to Blender's own move.** Blender's `E` is not a
single operator but a macro — extrude, then translate — which is why its adjust
panel shows Move X, Y and Z. Landfall now builds the same thing with our extrude
in front, so the panel lists our six parameters *and* the move together, at the
bottom left where it does not sit over the geometry. The drag that sets the
distance is Blender's own, and typing a number still works.

Blender's entry on `E` is muted, not removed: switching the preference off
brings it back.

**The toggle is next to the command** in the Modeling section, so it is visible
at a glance whether `E` is using our extrude.

**The popup of 3.30.0 was dropped.** Relying on `F9` had not worked either: an
operator run from a panel button is not registered as the last operation, so the
redo panel had nothing to show and the keystroke did nothing. The macro registers
properly, which fixes both.

---

## 3.29.0

**The keymap repair looks several times, not once.** A single check 0.4 s after
registering found nothing wrong, because Blender had not finished building the
user configuration yet, and the truncation appeared afterwards. It now looks six
times over the first few seconds and again whenever a file is opened.

Seen for real on a clean Windows configuration: the Mesh keymap held six entries
out of ninety-three, `E` and `I` were gone, and the repair had already run and
reported nothing.

In 3.29.1: with **Keep Faces Together** off, only one face stayed selected
instead of all of them. The caps are now collected and selected once at the end.

---

## 3.28.0

**Extrude with Maya's parameters.** Thickness along the normal, offset,
divisions, keep faces together, twist and taper — the six values of Maya's
`polyExtrudeFace` node. Declaring them as operator properties is what makes them
adjustable: the panel is drawn and re-run by Blender, which already knows how to
restore the mesh before each re-run.

In 3.28.1: **press Turn off before uninstalling.** Two of the things Landfall
changes cannot put themselves back once it is gone. The finite grid works by
switching off Blender's own floor and axis lines and drawing its own, so
uninstalling leaves a viewport with no grid at all — and that state lives in the
.blend file, so restarting does not help. The reminder is in the Setup panel, in
the README and in both guides.

---

## What has not changed, and will not

**There is no construction history.** The parameters are adjustable while the
extrusion is the last operation. Do anything else and they freeze. Maya keeps
`polyExtrudeFace1` in the Channel Box because it is a node; here it is a
finished operation, and no add-on can supply the difference.

**The toolbar Extrude tool is untouched.** Tools in the toolbar carry their own
operator and do not go through the keymap, so the icon still runs Blender's
extrude. Use the Tweak tool and `E`, or ask for a Landfall tool to be added
beside it — Blender does not allow replacing the existing one.

**Scattered selections still produce non-manifold edges.** Extruding every third
face of Suzanne gives ninety-one of them. Blender's own extrude gives exactly the
same ninety-one on the same selection: it is inherent to extruding a scattered
region as one, not a fault of ours.

---

## How this was tested

Every version above was checked with the same battery: all forty-five operators
in six modes, with and without a selection, on a scene carrying stacked
modifiers, shape keys, linked duplicates, negative scales and hidden objects —
one hundred and seventy-four calls, and the run has to end with no exceptions.

The extrusion is checked against values worked out by hand rather than by eye:
one face gives z −1 to 2 and ten faces; four divisions give twenty-two faces;
twenty divisions give eighty-six; a whole cube at thickness 0.5 gives z ±1.500
with a uniform radius of 2.598; the caps of a cylinder give ±1.500. Non-manifold
edges and loose vertices must be zero in every case.

What no script reaches is the drawing, the mouse and the feel of using it. Every
fault found in that area over these versions was found by hand.
