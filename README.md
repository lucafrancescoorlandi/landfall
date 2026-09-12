# Landfall 3.27.1

A Blender add-on for artists coming from Maya.

Landfall brings a familiar set of commands into Blender: a shelf-style panel,
a hotbox, a pie menu, Maya-style smooth preview levels, and a project system
modelled on Maya's *Set Project*.

Most of it is added on top of stock Blender, so tutorials and other add-ons
keep working. Seven things are replaced rather than added — the navigation on
Alt plus a mouse button, `F`, double click, `Ctrl+Tab`, `Ctrl+O` and
`Ctrl+Shift+S` — and each is listed under *Maya navigation* below. Everything
replaced can be switched off from the preferences.

---

## Requirements

- Blender 4.2 or newer. Developed and tested on Blender 5.2 LTS.
- Windows, macOS and Linux. No external dependencies.

---

## Installation

1. Download `landfall.zip`.
2. In Blender: `Edit → Preferences → Add-ons`.
3. Click the arrow at the top right of the panel → `Install from Disk…`.
4. Pick the zip file.
5. Find **Landfall** in the list and tick its checkbox.

**Installing a newer zip over an older one is not reliable.** In practice the
files are sometimes left as they were, and the compiled copy in the
`__pycache__` folder makes Blender keep running the old code, so the add-on
looks updated while behaving exactly as before. It happened repeatedly during
development, and the version number in the panel was the only way to notice.

Uninstall first, close Blender, then install the new zip. The steps are below.

### Where it gets installed

Landfall is an extension, so `Install from Disk` places it in Blender's
per-version extensions folder. Replace `5.2` with your own Blender version.

**Windows**

```
C:\Users\<user>\AppData\Roaming\Blender Foundation\Blender\5.2\extensions\user_default\landfall
```

`AppData` is hidden. Paste the path into the address bar of File Explorer, or
type `%APPDATA%` to jump straight to the `Roaming` folder.

**macOS**

```
~/Library/Application Support/Blender/5.2/extensions/user_default/landfall
```

`~/Library` is hidden. In Finder use `Go → Go to Folder` (`Cmd+Shift+G`) and
paste the path, or hold `Option` while opening the `Go` menu to reveal the
Library entry.

**Linux**

```
~/.config/blender/5.2/extensions/user_default/landfall
```

Legacy-format add-ons live in `scripts/addons/` instead of
`extensions/user_default/`, in the same per-version folder.

To see the exact path on your own machine, expand the Landfall entry in
`Preferences → Add-ons` and read the **File** field. That is authoritative and
accounts for Store, portable and Steam installs, whose paths differ.

### Uninstalling

Landfall is an extension, and for extensions the **Uninstall** command lives in
`Preferences → Get Extensions`, at the right end of the row. It is **not** in
`Preferences → Add-ons`, where it was installed: that panel only offers it for
legacy add-ons, so looking there is wasted time.

The manual route is more reliable and works whatever Blender decides to show:

1. Close Blender.
2. Delete the `landfall` folder shown in the **File** field above,
   `__pycache__` included.
3. Reopen Blender and install the new zip.

Deleting the folder is what actually matters. Leaving `__pycache__` behind is
enough for Blender to keep running the previous version.

### Surviving Blender upgrades

Add-ons install into a folder tied to the Blender version, so a major upgrade
can leave them behind. To avoid reinstalling every time:

1. Create a folder outside Blender's own directories, for example
   `Documents/blender_scripts`.
2. Inside it create a subfolder named `addons`.
3. In `Preferences → File Paths → Script Directories`, add the parent folder.
4. Unzip `landfall` into `blender_scripts/addons/`.

Every Blender version will then read the add-on from the same place.

If you work on more than one machine, put that folder on a synced or shared
drive: the add-on follows you across Windows and macOS without reinstalling,
and the path stops mattering.

---

## Where to find it

| Location | How to open |
|---|---|
| 3D viewport sidebar | Press `N`, then the **Landfall** tab |
| Properties editor | `Scene` tab, the cone and sphere icon |
| Hotbox | `Alt+Q` — a popup at the mouse cursor |
| Pie menu | `Shift+Q` — a radial menu at the mouse cursor |

The sidebar sections are collapsible and Blender remembers which ones you
leave closed. At the top of the panel, above Display, sit the **Maya
navigation** toggle and a `G` `R` `S` reminder; both can be hidden from the
add-on preferences.

---

## Shortcuts

| Key | Action |
|---|---|
| `Shift+Q` | Pie menu with the eight most-used commands |
| `Alt+Q` | Hotbox with every command, in columns |
| `Alt+W` | Show or hide the transform gizmos |
| `Backspace` | Deletes, if turned on in the preferences |
| `Ctrl+Tab` | Marking menu |
| `Shift+Alt+Q` | Modeling pie, in Edit Mode |
| `Shift+Alt+S` | Snap pie |
| `Alt+1` | Smooth preview: cage only |
| `Alt+2` | Smooth preview: smooth surface with cage on top |
| `Alt+3` | Smooth preview: smooth surface only |
| `Ctrl+O` | Open, starting inside the project's `scenes/` |
| `Ctrl+Shift+S` | Save As, starting inside the project's `scenes/` |

With **Maya navigation** on, these are added as well:

| Key | Action |
|---|---|
| `Alt` + Left / Middle / Right Mouse | Orbit, pan, zoom |
| `F` | Frame the selection, Object Mode only |
| Double click | Loop select |
| `Ctrl` + double click | Edge ring select |

Useful stock Blender keys worth knowing, which Landfall does not change:

| Key | Action |
|---|---|
| `G` `R` `S` | Move, rotate, scale — press, move, type an axis and a number |
| `Home` | Frame the whole scene (`Fn` + Left Arrow on a laptop) |
| `Numpad .` | Frame the selection, works in every mode |
| `A` / `Alt+A` | Select all / deselect all |
| `Ctrl+I` | Invert the selection |
| `Ctrl+Tab` | Marking menu: ring plus list |
| `,` | Transform orientation pie — global, local, normal, gimbal, view, cursor |
| `.` | Pivot point pie — median, individual origins, 3D cursor, active, bounding box |
| `1` `2` `3` | Vertex, edge, face mode, in Edit Mode |
| `Ctrl+1`…`5` | Add a Subdivision Surface at that level |
| `` ` `` | View pie — front, back, left, right, top, bottom, camera |
| `Numpad 1 3 7` | Front, right, top. Add `Ctrl` for the opposite view |
| `Numpad 5` | Perspective / orthographic |
| `Ctrl+Alt+Q` | Quad view on and off |
| `Ctrl+Space` | Maximise the area under the mouse, and back |
| `Alt+Z` | Global X-ray, and it makes hidden geometry selectable |

These work in every mode, including Sculpt, Vertex Paint, Weight Paint and
Pose. Blender checks a mode's own keymap before the general viewport one, so
each shortcut is registered in every mode rather than once globally. That is
also why the same entry appears several times in the keymap editor.

To change or remove any of these: `Preferences → Keymap`, then search
`landfall`. Remember to change every copy, one per mode.

Tooltips show the current binding of a button, read from the keymap itself. If
you rebind a key, the tooltip updates with it. To show the shortcut on the
button face as well, tick *Show shortcuts on the buttons* in
`Preferences → Add-ons → Landfall`.

---

## The marking menu

`Ctrl+Tab` opens a menu with the radial ring and a list showing at the same
time, the way Maya's marking menus work. Blender's own pies are radial only,
and opening a second one hides the first; this is drawn by Landfall instead.

Everything is reachable in two flicks. The ring holds what you press all day,
the list holds the rest, and three of the eight directions open a different
list without the ring going away.

**In Edit Mode** the left column is what you work on and the right is what you
do with it: vertex, edge and face top to bottom on the left, in the order of
the `1`, `2`, `3` keys; Modeling and Snap on the right; Display and Object mode
on the remaining directions.

**In Object Mode** the same shape: the three paint modes fill the left column,
Edit sits top right next to Display, Sculpt and Snap on the right, and Frame
selected alone at the bottom.

The direction top right therefore always means *go deeper into the work* —
Edit from Object Mode, Modeling from Edit Mode.

| Gesture | What happens |
|---|---|
| Click a command | Runs it and closes |
| Click a branch | Opens its list under that item, over the ring |
| Click the open branch again | Folds the list back |
| Right mouse | Back to the base list, then out |
| Click outside | The same, in two steps |
| `Esc` | Straight out |

Lists longer than seven entries split into two columns with a divider, so even
the twelve modelling commands stay short enough to read at a glance.

Choosing **Edit** brings the menu straight back once Blender has switched
mode, since entering Edit Mode is nearly always followed by picking a
component. Turn that off in the preferences if you tend to keep the component
mode you left.

**What it is not.** Maya lets you flick and release in one motion; here you
press, then click. And the commands are Blender's own, so their options appear
in the usual place afterwards rather than in the menu.

## Gizmos, orientation and pivot

Gizmos are a collapsible section at the top of the panel, above Display: a
master switch plus one toggle each for move, rotate and scale, and dropdowns for
the transform orientation and the pivot point. `Alt+W` toggles the gizmos
without reaching for the panel.

Blender ships with the move, rotate and scale gizmos on in the Layout
workspace and off in every other one, and each workspace keeps its own
setting — so they vanish the moment you switch to Modeling. The preference
**Transform gizmos on in every workspace** turns them on in all of them, the
way Maya always shows the manipulator, and reapplies it whenever you open a
file, since each file carries its own workspaces.

**Finite grid**, in Setup, replaces Blender's infinite floor with a bounded one
like Maya's, 22 cells by default. Blender's own `grid_lines` setting has no
effect in perspective view — the tooltip says otherwise, but it does not — so
the floor and the two axis lines are switched off and Landfall draws the grid
itself, axes included, stopping at the edge. Turning it off puts all three back
exactly as they were. Maya colors switches it on, the restore arrow switches it
off.

By default the color follows the theme's grid entry, taking the color but
drawing it opaque: the theme carries 50% alpha that Blender's own grid shader
handles differently, and a plain line at that alpha has almost no contrast left
against the background.

The **Grid shade** slider sets the brightness of the floor
grid, and defaults to 0.19.

Two of Landfall's colors deliberately differ from the values sampled in Maya,
because copying them exactly looks wrong in Blender. Maya's grid is `#404040`,
0.25 on the slider, but Blender fades the grid with distance and viewing angle,
so it is darkened to `#303030` to hold the same readability — with a darker grid
than the background, moving further down means more contrast, not less. And Maya's interface highlight is `#5285A6`, sampled from panels lighter than
Blender's. Landfall keeps that hue but sets the value for legibility: white
text on `#2A7A9C` reaches a 4.8:1 contrast ratio, where a brighter blue of the
same hue drops to 2.8:1 and the labels become hard to read.

Both are adjustable: the grid from the slider, the highlight by editing the
theme afterwards.

**Maya colors** matches Blender's theme to Maya's, using values sampled from a
real Maya viewport rather than guessed:

| Element | Color |
|---|---|
| Background | `#5C5C5C`, flat instead of Blender's gradient |
| Grid | `#303030` |
| Active selection, Object Mode | `#43FFA3` |
| Selected, not active | the same green at 55% |
| Selected components | `#00FF0F`, faces at 20% alpha |
| Edit-mode wireframe | `#64DCFF` |
| Selected items in the UI | `#2A7A9C` |

Maya uses two different greens: a soft `#43FFA3` for objects, and a pure
`#00FF0F` for components, together with a light cyan wireframe that tells you at
a glance that you are in component mode. Landfall reproduces both. The cyan
wireframe is a lot of color on a dense mesh, so it has its own switch in the
preferences.

The blue is applied to every widget class that has a selected state — toggles,
checkboxes, radio buttons, list rows, tabs, sliders and menu entries — with
white text on top. Both the selection green and the interface blue can be turned
off separately in the add-on preferences. Landfall changes nothing else in the
interface: recoloring the rest from a handful of sampled values gives an
inconsistent result, and a button is not what you look at all day.

Theme colors are written in gamma space, not linear. This is the opposite of
scene data such as an object's viewport color, and getting it backwards is why
a hand-matched theme usually comes out far too dark.

Before applying, it saves your current theme values, so the back arrow restores
exactly what you had, not a generic default. If there is nothing saved — or the
backup was written by a version older than 1.17, which did not record widget
colors — the arrow falls back to Blender's own factory reset, because those
defaults differ per widget and cannot be reconstructed reliably.

#### Where the snapshot is kept

In a file called `landfall_theme_backup.json`, next to Blender's own
preferences in the `config` folder. It used to live inside the add-on
preferences, which do not survive being disabled or reinstalled, and that
caused an awkward case: after a reinstall the snapshot was gone while the theme
was still Maya's, so turning the set-up off handed Maya's colors straight back
and looked like a restore that did not work.

Kept on disk it outlives disabling, re-enabling and reinstalling. You can
delete the file by hand; the next time the colors are applied a fresh snapshot
is written. If the folder is not writable the add-on says so in the console and
falls back to the preference, so nothing stops working.

As a second line of defence, the theme is checked before the snapshot is taken:
if it already carries Maya's background, Blender's own values are restored
first and those are recorded instead. That way a missing snapshot can never
turn into "off gives me Maya back", however old the install it came from.

The second button next to it triggers that factory reset directly. It is the
sure way back to stock Blender, at the cost of discarding any other theme tweaks
you have made. It edits the theme,
so it applies to every viewport on the machine and is saved to your preferences.
For a single viewport instead, use the Viewport Shading popover and set
*Background* to *Viewport*.

Hex values are converted from sRGB to linear before being written. Typing them
straight into Blender's RGB fields gives a noticeably lighter result, which is
the usual reason a hand-matched theme looks wrong.

Blender already has one-key access to the two dropdowns, which is faster than
either the header or this panel once you know it: `,` opens the orientation pie
and `.` opens the pivot point pie. Press the key, flick the mouse in the right
direction, release. The two keys sit next to each other on purpose.

## The panel

Sections are ordered by how often you touch them: what you press all day first,
what you set once last.

| Section | Holds |
|---|---|
| Display | X-ray, wireframe, hide and show, isolate, border edges, object color |
| Modeling | Pivots, freeze, selection, merges, spin, detach, grid fill, smooth preview and cage |
| Texturing | UV projections, unwrap and pack, PBR loading, texture reload |
| Gizmos | Gizmo toggles, transform orientation, pivot point |
| Editors and output | Workspaces, playblast, quad view, viewport regions |
| Project | Create, set, open, save, relative paths, workspace.mel |
| Setup | Maya setup, self check, navigation, marking menu, colors, finite grid |

**Modeling and Texturing hide themselves** outside Object and Edit Mode. In
Sculpt or a paint mode they have nothing to offer, so they disappear rather
than sit there greyed out, and the panel gets shorter on its own.

**Gizmos and Setup start closed.** Blender remembers what you leave open, so
after the first session the panel shows only what you actually use.

### Checking it over

**Self check**, under the Maya setup buttons, verifies that every command in
the menus points at an operator that exists, that both rings have eight
entries, that every branch names a real list, that no row of a list can fall
outside its panel, and that no keymap has lost its shortcuts. The result goes
to a text block called `landfall_self_check`.

It cannot check the drawing or the mouse. Those are the one part with no
safety net, so if something looks wrong on screen, that is where to look
first.

### When a shortcut stops working

A keymap in the user configuration replaces the stock one rather than merging
with it, so a keymap that has lost its entries silently removes every shortcut
it is missing — and Blender reports nothing. It was seen for real: `Tab`
stopped entering Edit Mode, and the Mesh keymap held two entries out of a
hundred and eight, taking `I`, `K`, `P` and `A` with it.

Landfall now rebuilds any keymap that has lost more than half of Blender's own
shortcuts, shortly after startup, and prints what it rebuilt to the console.
The threshold is deliberately severe, because no deliberate customisation
looks like that. If you keep a stripped-down keymap on purpose, turn off
**Rebuild truncated keymaps at startup**.

If a shortcut ever stops responding: restart Blender, then press Self check.

### Maya setup

At the top of Setup, a line reads *Maya setup: n of 5 on*, followed by **Turn
on** and **Turn off**. The five are navigation, the marking menu, the contextual wire
on shaded, Maya colors and the finite grid.

Turning it off also puts the viewport shading back to *Material*: applying an
object color switches it to *Object*, and the theme knows nothing about that,
so restoring the colors alone used to leave everything still painted with its
object color — which looks exactly like a restore that did not work.

It is what to point students at: five separate switches is five decisions
before they can start, and most people never make them.

It deliberately shows the count and offers two explicit buttons rather than one
that toggles. A single button has to guess which way to go, and when some of
the five are already on it can switch off things you meant to keep — which is
exactly what happened during testing.

## Shortcut sheet

The **Shortcuts** button at the bottom of the panel opens a floating card over
the viewport. It stays open while you work: clicks pass through to the scene,
you can drag it by its title bar to park it in a corner, and it closes on the
`X`. Press the button again to close it too.

Three blocks: Landfall's own shortcuts, the Maya navigation ones, and a cheat
sheet of stock Blender keys worth learning. Every key is read from your live
keymap, so if you rebind something the sheet follows. A command with no key
assigned shows *not set* rather than disappearing, so you know it exists and can
bind it. When Maya navigation is off, that block is greyed out and marked *off*.

Because it is drawn into the 3D viewport it is not an operating-system window:
you cannot move it to a second monitor, and it closes if you quit or reload the
file.

## Commands

### Display

- **X-ray** — makes only the selected objects transparent, leaving the rest
  solid. Unlike Blender's `Alt+Z`, this is per object. Solid shading only; it
  does not make hidden geometry selectable.
- **Wire** — toggles the wireframe overlay on top of solid shading.
- **Hide** — hides the selection and remembers what it hid.
- **Show sel** — unhides the objects that are currently selected. Hidden
  objects can only be selected in the Outliner, so select them there first.
- **Show last** — unhides and reselects only the group hidden most recently.
  It remembers one group at a time.
- **Show all** — unhides everything.
- **Isolate** — Blender's Local View. Shows only the selection; press again to
  return.
- **Border edges** — a real overlay, like Maya's *Toggle Border Edges*. Open
  border edges are drawn as thick colored lines on top of the mesh, and stay
  visible in Object Mode as well as Edit Mode. Width, color and whether it
  applies to the selection only are all adjustable under the toggle. The
  refresh button next to it forces a recompute if the display ever falls
  behind.
- **Select border edges** — selects those edges instead of just showing them.
  Edit Mode only.
- **Object color** — eight fixed swatches plus a free color picker. Colors
  the selected objects and switches the viewport shading to *Object* so the
  color actually shows. The `X` resets them to white.

  This is the closest thing Blender has to Maya's layer colors. Blender's own
  collection Color Tag only tints the row in the Outliner, never the viewport.
  Two caveats: with shading set to *Object* the color fills the surface in
  Solid mode rather than just the wireframe, and materials are no longer shown
  in Solid mode, since that needs shading set to *Material*. For a colored
  outline only, set *Display As* to *Wire* in Object Properties.

#### A note on the name

**Wire on shaded** draws the wire on top of the solid surface, which is what
Maya calls *Wireframe on Shaded*. It is not Blender's **Wireframe** shading
mode, which shows the edges instead of the surface. The two are easy to
confuse and do different things.

### Modeling

- **Center pivot** — sets the object origin to the center of its geometry.
- **Edit pivot** — toggles *Affect Only Origins*. While it is on, `G` and `R`
  move the origin instead of the object. Remember to turn it off.
- **Freeze transforms** — applies location, rotation and scale.
- **Select hierarchy** — selects all children recursively.
- **Select inverse** — inverts the selection. Works in Object Mode and in every
  edit mode (mesh, curve, armature, pose, lattice, metaball), picking the right
  operator for the context. Blender's own shortcut is `Ctrl+I`.
- **Merge by distance** — merges selected vertices within a threshold. Adjust
  the threshold in the operator panel (`F9`) after running it.
- **Merge at center** — collapses the selected vertices into a single point.
- **Spin** — rotates the selected edge.
- **Detach** — separates the selected faces into a new object.
- **Grid fill** — fills a closed edge loop with quads.

#### Smooth preview

Three levels matching Maya's `1` `2` `3`, applied to the selected meshes.
They use Blender's Subdivision Surface modifier, so the result stays in the
modifier stack and can be applied or removed at any time.

- **1** — turns the subdivision off in the viewport, keeping the modifier and
  its level intact.
- **2** — smooth surface with the control cage drawn on top.
- **3** — smooth surface only.
- **Apply smooth** — applies the subdivision permanently.

**2** also draws the original cage around the smooth surface, the way Maya
does. Blender's own wireframe follows the subdivided mesh, so the lines sit on
the smooth surface instead of around it; Landfall draws the base mesh before any
modifier. The cage is green on the selection and dark blue on everything else,
it is hidden where the surface occludes it, and it steps aside in Edit Mode
where Blender already draws its own with the proper selection colors. Width,
colors and the two toggles are under the buttons.

The **Subdivisions** field under the three buttons sets how many levels are
displayed. Changing it updates every selected mesh that already has a
subdivision, so you can drag the value and watch the result. It is stored per
scene, so each file keeps its own setting.

If an object has no Subdivision Surface modifier yet, one is created at the
current level with Optimal Display enabled.

For a scene-wide limit, use `Scene Properties → Simplify → Max Subdivision`.

### Texturing

- **Unwrap + scale + pack** — unwrap, average island scale and pack, in one
  step. Edit Mode only.
- **Pla / Cyl / Sph / Auto** — planar, cylindrical, spherical and automatic UV
  projection.
- **Load PBR set** — pick a folder of texture maps and Landfall builds the
  Principled BSDF for you: it creates the material if missing, assigns the
  correct color spaces, and wires Normal Map and Displacement nodes.
- **Reload textures** — reloads every image in the file from disk.

Maps are recognized from their file names. Recognised keywords:

| Channel | Keywords in the file name |
|---|---|
| Base color | `basecolor`, `base_color`, `albedo`, `diffuse`, `col`, `color` |
| Roughness | `roughness`, `rough`, `rgh` |
| Metallic | `metallic`, `metalness`, `metal`, `mtl` |
| Normal | `normalgl`, `normal`, `nrm`, `nor` |
| Height | `displacement`, `height`, `disp`, `hgt` |
| Emission | `emissive`, `emission`, `emit` |
| Opacity | `opacity`, `alpha` |

Everything except base color and emission is loaded as Non-Color data.

### Editors and output

- **UV editing** and **Shading** — switch to those workspaces.
- **Playblast** — an OpenGL viewport render of the animation, the equivalent of
  Maya's playblast.
- **Quad view** — toggles Blender's own Quad View in the viewport: top, front,
  right and perspective in one area. The Outliner, Properties and this panel
  stay exactly where they are, which is the reason for using the built-in one.

  Two things it does not do, by design of Blender rather than of Landfall: the
  three orthographic panes are locked and cannot be orbited, and `Ctrl+Space`
  maximises the whole block rather than a single pane. Landfall used to build
  four separate areas to work around this; closing them again handed their space
  to the wrong neighbours and wrecked the layout, so that approach was dropped.

  **Toolbar**, **Sidebar** and **Header** underneath toggle those regions in
  every 3D viewport at once.



### Project

Modelled on Maya's *Set Project*.

- **Create** — pick a location, give a project name, and Landfall builds the
  folder tree and sets it as current.
- **Set** — point at an existing project folder and make it current.
- **Open scene** — opens the file browser inside the project's `scenes/`.
- **Save as** — saves into `scenes/` and remaps paths to relative. If the file
  already lives inside the project, it stays where it is instead of being
  pulled back into `scenes/`.

`Ctrl+O` and `Ctrl+Shift+S` are rebound to these two, so ordinary opening and
saving respects the project without you having to use the panel. With no
project set they behave exactly like Blender's own Open and Save As, so nothing
is lost. Plain `Ctrl+S` is untouched: it overwrites the current file, as always.
- **Make paths relative** — converts every external path in the current file to
  a relative one. Run this before moving a project between machines.
- **Write workspace.mel** — writes a Maya project definition into the project
  root, for a folder that was made before this feature existed. New projects get
  one automatically unless you turn that off in the add-on preferences.

Setting a project also points the render output at `images/` and registers
`assets/` as an Asset Library named after the project. The current project is
stored in the add-on preferences and survives a restart.

The default folder tree follows Maya's:

```
scenes/          assets/          sourceimages/
  3dPaintTextures/               images/
movies/          cache/           renderData/
  alembic/         shaders/
  particles/     data/            clips/
sound/           scripts/         autosave/
workspace.mel
```

Edit the list in `Preferences → Add-ons → Landfall`, one folder per line.

### Maya compatibility

New projects also get a `workspace.mel`, which is what Maya's *Set Project*
looks for. Point Maya at a folder Landfall created and it resolves `scenes`,
`sourceimages`, `images`, `cache`, `data` and the rest through its own file
rules. The two applications then agree on where things live, which is the whole
point of having a project in the first place.

The file declares 21 rules. Maya fills in anything missing with its defaults, so
a partial list is safe. Edit it by hand if your studio uses a different layout.

### Moving work between Blender and Maya

There is no way to write a Maya `.ma` from Blender, and it is not worth chasing.
A `.ma` is a dump of Maya's node graph rather than a description of geometry, so
writing one means reimplementing Maya's dependency graph. Commercial add-ons
that claim `.ma` export require Maya to be installed and convert through FBX
using `mayapy` in the background; if Maya is on the same machine, importing the
FBX directly is the same thing with fewer moving parts.

Use the interchange formats instead:

| Format | Best for |
|---|---|
| **USD** | Assets and scenes: hierarchy, meshes, UVs, materials, cameras, lights |
| **FBX** | Rigs and skinning, especially towards game engines |
| **Alembic** | Baked animation and simulation caches |

USD is the strongest option for a Blender and Maya pipeline. Blender imports USD
skeletons as armatures and converts UsdPreviewSurface shaders into Principled
BSDF networks; on export it does the reverse, writing armatures and skinned
meshes as USD skeletons with their animation. On the Maya side this needs the
**MayaUSD** plug-in, which supports Maya 2023 through 2027 and adds a Layer
Editor, USD cameras and lights, and material editing through LookdevX.

One practical note on materials: **Standard Surface** round-trips best in Maya.
Lambert and Stingray PBS lose data in translation.

**Note.** Blender has no global "default save folder" setting, so a project can
only steer the file browser through the operators above. If you use
`File → Save As` from the menu you get Blender's own behavior, not the
project's.

**Known limitation.** Blender has no equivalent of Maya's `workspace.mel` file
path rules, so it will not automatically look inside `sourceimages/` when a
texture goes missing. You get the folder structure, the right default paths and
relative linking; automatic resolution is not possible without replacing
Blender's file loader. When links do break, use
`File → External Data → Find Missing Files` and point it at the project folder.

---

## Maya navigation

Off by default. The toggle sits at the top of the Landfall panel, above
Display, and also in `Preferences → Add-ons → Landfall`.

| Input | Action |
|---|---|
| `Alt` + Left Mouse | Orbit |
| `Alt` + Middle Mouse | Pan |
| `Alt` + Right Mouse | Zoom |
| `F` | Frame the selection, Object Mode only |
| Double click | Loop select, moved from `Alt` + click |
| `Ctrl` + double click | Edge ring select |

`Home` frames the whole scene, which is what `A` does in Maya. On a laptop or a
keyboard without a numeric block, `Home` is `Fn` + Left Arrow.

**What the toggle changes for you.** These four preferences matter more than
the keys themselves, and the toggle sets them so you do not have to hunt for
them:

| Preferences section | Setting | Value |
|---|---|---|
| Navigation | Orbit Around Selection | on |
| Navigation | Auto Depth | on |
| Navigation | Zoom to Mouse Position | on |
| Input | Emulate 3 Button Mouse | off |

**What it deliberately leaves alone.**

*Orbit Method* stays on Turntable. That is already Blender's default and the
right behavior, so there was nothing to change.

*Invert Zoom Direction* is left to you. Whether Blender's zoom feels inverted
compared to Maya depends on how you move your hand, and forcing it would annoy
half the people who try it. If dragging `Alt` + Right Mouse to the right pushes
you away instead of pulling you in, tick that box in
`Preferences → Navigation`.

**Conflicts, and how they are handled.**

`Alt` + click is loop select in stock Blender, so it is muted and loop select
moves to a double click. Turning the option off restores it.

`F` creates a face in Edit Mode, which is essential, so framing is bound to `F`
in the Object Mode keymap only. In Edit Mode use `Numpad .` to frame, or
the marking menu.

`A` is Select All in Blender, not frame-all as in Maya. It is left alone. Use
`Home` to frame the whole scene.

Blender's own middle-mouse navigation keeps working alongside, so you always
have a fallback. This matters on a laptop trackpad, where `Alt` + middle mouse
does not exist.

Everything is added to the add-on keymap, so it travels with Landfall between
machines and shows up in `Preferences → Keymap` under Add-ons if you want to
adjust it.

## Working across machines

1. Set a project before you start.
2. Keep the **Relative Path** checkbox on in the file browser. It is on by
   default; leave it alone.
3. Save scenes with **Save as** from the Project panel, which forces relative
   remapping.
4. Run **Make paths relative** before handing a project to someone else.
5. Move the whole project folder, never a `.blend` on its own.

---

## Platforms

Tested on macOS on Apple silicon and on Windows 11, both with Blender 5.2.1
LTS. Nothing in the add-on detects the operating system or builds a path by
hand: folders go through Python's own path handling, and the shortcuts use
Ctrl, which Blender maps to Control on macOS too rather than to Command.

Two things do differ between the two, and neither is Landfall's doing.

**Interface scale.** Windows commonly runs at 1.5; macOS reports 1.0 with a
larger pixel size. The marking menu reads the final scale at draw time and
sizes itself accordingly, verified at 0.5, 1.0, 1.5 and 2.0.

**The `workspace.mel` file** is written with forward slashes on both, because
that is what Maya expects everywhere. The project path itself stays in the
native format.

## Notes and limitations

- The X-ray toggle works in Solid shading only, and does not make occluded
  geometry selectable. For that, use Blender's own `Alt+Z`.
- Both overlays cache their geometry per object and their GPU batches per
  change, so an unchanged viewport redraws without rebuilding anything, and
  moving one object only recomputes that object.
- The border edge overlay is drawn by Landfall with Blender's GPU module, since
  Blender has no built-in option for it. It recomputes when the scene changes,
  so on very heavy meshes it can cost some viewport performance. Meshes above
  400,000 edges are skipped. Leaving *Selected only* on keeps it cheap.
- The hotbox is a column popup, not the four quadrants of Maya's. Blender does
  not expose a radial layout for panels; only pie menus are radial, and those
  are limited to eight entries.
- Add-on panels cannot be placed in the viewport's left toolbar. That region is
  reserved for tools and Blender rejects a panel category there. To keep the
  panel on the left, move the Properties editor to the left side of your
  workspace and save the startup file.
- The wireframe overlay follows the mode: off in Object Mode, on in component
  mode, and whatever you set by hand is restored on the way out. Switch it off
  in the preferences if you prefer to drive it yourself.
- Transform shortcuts are left alone on purpose. `G` move, `R` rotate and `S`
  scale are modal in Blender: press the key, move the mouse, type an axis and a
  number, press Enter. That is fewer mouse movements than dragging a gizmo, and
  remapping them to `W E R` means never learning it. The panel shows a reminder
  at the top; turn it off in the add-on preferences once you no longer need it.

---

## License

Landfall is released under the GNU General Public License, version 3 or later,
as required for Blender add-ons. See `LICENSE`.

You are free to use, study, modify and redistribute it. Derivative works must
carry the same licence.

---

## Credits

Written by Luca Orlandi for teaching and production use.

Bug reports and requests are welcome.
