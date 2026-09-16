# Changelog

All the versions released after 3.27.2, newest first. Every fix listed here was
found by measuring something, and the measurement is quoted where it explains
the change.

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
