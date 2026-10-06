# Landfall — tutorial video script

Text to read, one paragraph per frame; the time on the left is when that frame appears in the video.

## 01 Installation

- `00:00:00` **Installing Landfall** — Downloading the zip and installing it in Blender 5.2
- `00:00:03` Landfall lives on GitHub: github.com/lucafrancescoorlandi/landfall. The README is the full documentation; the PDF guides are in the docs folder.
- `00:00:08` On the right, under Releases, open the latest version: under Assets download landfall-x.x.x.zip. Do not unzip it: Blender takes the zip as it is.
- `00:00:14` In Blender open Edit › Preferences and pick the Add-ons tab.
- `00:00:19` The arrow at the top right opens a menu: choose Install from Disk… and pick the zip you just downloaded.
- `00:00:25` Landfall appears in the list. Check that the box is ticked and that the version number is the one of the file.
- `00:00:30` Open the arrow next to the name and you see the preferences: they are all on already. Landfall on is Maya; off or uninstalled is factory Blender.
- `00:00:36` Close the preferences: the viewport already has Maya's colors, the finite grid and the Alt + mouse navigation.
- `00:00:41` From an empty scene press Setup › Save as startup: preferences and layout come back the same at every launch.
- `00:00:46` **Done** — The PDF guides are in the repository's docs folder

## 02 Updating

- `00:00:00` **Updating Landfall** — Uninstall the old version first, then install the new one
- `00:00:03` Installing a new zip over an old one is not reliable: Blender can keep running the old code while showing the new number.
- `00:00:08` So: Preferences › Get Extensions, search for landfall.
- `00:00:14` From the arrow next to the extension choose Uninstall. Theme, grid and navigation go back to Blender's own by themselves.
- `00:00:19` Close Blender and open it again: no compiled copy of the old code stays in memory that way.
- `00:00:25` Then Preferences › Add-ons › Install from Disk… with the new zip, as at the first installation.
- `00:00:30` Check the version number in the preferences: it must be the one of the zip. The Maya set-up comes back on by itself.
- `00:00:36` Setup › Self check verifies menus, shortcuts and keymaps; two NOTEs about Alt+Q and Alt+W are normal.
- `00:00:41` **Done** — What changed in each version is in the CHANGELOG

## 03 The panel on the left

- `00:00:00` **The panel on the left** — Where Landfall is and how to put it where Maya's shelf lives
- `00:00:03` Landfall appears in two places. The first is the viewport sidebar: N key, Landfall tab.
- `00:00:08` The second is the Properties editor, Scene tab. Same commands. Blender allows no panels in the toolbar on the left, so a Properties editor is opened on the left side.
- `00:00:14` Step 1: in the viewport, View › Area › Vertical Split. Bring the line close to the left edge and click.
- `00:00:19` Step 2: in the narrow area just made, the button at the top left picks the editor type: Properties.
- `00:00:25` Step 3: in the icon column pick Scene, the one with the cone and the sphere, and open the Landfall panel.
- `00:00:30` Close the Blender panels you do not need: Blender remembers what you leave open.
- `00:00:36` At the top is the reminder: G move, R rotate, S scale. Switch it off in the preferences once you no longer need it.
- `00:00:41` Step 4: from an empty scene, Setup › Save as startup. The layout comes back like this at every launch.
- `00:00:46` **Done**

## 04 Gizmos tab

- `00:00:00` **Gizmos** — Manipulators, orientation and pivot
- `00:00:03` The Gizmos section: the master switch, the three manipulators, the G R S button and the two orientation and pivot menus.
- `00:00:08` Move, Rotate and Scale choose which manipulators to show. With the preference 'Same transform gizmos in every workspace' the choice holds in every workspace, as in Maya.
- `00:00:14` Press G and only the move manipulator stays on…
- `00:00:19` …R the rotation one…
- `00:00:25` …S the scale one. Like W, E and R in Maya. The three panel buttons follow.
- `00:00:30` The button 'G R S: gizmo only, like Maya', on by default: the key only shows the manipulator and you transform with its handles, which stay visible.
- `00:00:36` Off, the key also starts Blender's modal transform: X Y Z axes, numbers, Enter. Blender hides the gizmos while a modal transform runs.
- `00:00:41` Below: orientation (Global, Local, Normal…) and pivot (Median Point, 3D Cursor…). The comma and period keys open their pies.
- `00:00:46` Alt+W hides and shows the manipulators without reaching for the panel; the navigation gizmo in the corner stays.
- `00:00:52` **Gizmos** — In the preferences: Same transform gizmos · G, R and S pick the gizmo

## 05 Display tab

- `00:00:00` **Display** — X-ray, wire, hide and show, isolate, border edges, color
- `00:00:03` The Display section holds what Maya keeps in the Display menu and in the shelf.
- `00:00:08` X-ray makes only the selected objects see-through; the slider next to it sets the opacity.
- `00:00:14` Wire on shaded: the wireframe over the solid shading, like Maya's Wireframe on Shaded.
- `00:00:19` Hide hides the selection. Show sel shows the hidden objects selected in the Outliner, Show last the last hidden group, Show all everything.
- `00:00:25` In Edit Mode the same buttons work on components: they hide and show faces.
- `00:00:30` Isolate is Blender's Local View: only the selection. Again to return. In Edit Mode it hides the rest of the mesh.
- `00:00:36` Border edges draws the open edges in orange: the mesh's borders and holes. Underneath, width and color; Select border edges selects them in Edit Mode.
- `00:00:41` Object color: eight colors and a free one for the selected objects, X goes back to white. It switches the viewport shading to Object.
- `00:00:46` **Display**

## 06 Modeling tab

- `00:00:00` **Modeling** — Pivot, freeze, Maya's extrude, merge, smooth preview
- `00:00:03` The Modeling section. In Object Mode the Edit Mode commands are greyed out; here we are in Edit Mode with a face selected.
- `00:00:08` Center pivot puts the origin at the centre of the geometry. Edit pivot: hold it down, then G and R move the origin instead of the object; press again to leave.
- `00:00:14` Freeze applies location, rotation and scale, like Freeze Transformations. Hierarchy selects the children; Inverse inverts the selection.
- `00:00:19` Extrude with options is Maya's polyExtrudeFace: thickness, offset, divisions, keep faces together, twist and taper. It is on the E key too.
- `00:00:25` Press E, move the mouse, confirm: the panel at the bottom left shows the six parameters and the move, editable while the extrusion is the last operation.
- `00:00:30` Thickness 0 keeps the mouse distance; any other value replaces it. With only edges or vertices selected, E hands over to Blender's extrude.
- `00:00:36` Merge by distance joins vertices within a threshold; Merge at center collapses them into one point. Spin rotates the edge, Detach separates the faces, Grid fill fills a closed loop.
- `00:00:41` Smooth preview: Alt+1 shows the cage alone…
- `00:00:46` …Alt+2 the smooth surface with the cage on top…
- `00:00:52` …Alt+3 the surface alone. It is Blender's Subdivision Surface, so it stays in the stack: Subdivisions sets the level, Apply smooth makes it permanent.
- `00:00:57` **Modeling**

## 07 Texturing tab

- `00:00:00` **Texturing** — UVs and PBR sets
- `00:00:03` The Texturing section, in Edit Mode.
- `00:00:08` Unwrap + scale + pack does in one step what Maya does in three: unwrap, average island scale, pack.
- `00:00:14` Pla, Cyl, Sph, Auto: planar, cylindrical, spherical and automatic projections.
- `00:00:19` Load PBR set: pick the images of a set and Landfall builds the Principled BSDF, wiring every map by name: basecolor, roughness, metallic, normal, height, emission, opacity…
- `00:00:25` Reload textures reloads every image of the file from disk, after painting them outside.
- `00:00:30` **Texturing**

## 08 Editors and output tab

- `00:00:00` **Editors and output** — Workspaces, playblast, quad view, regions
- `00:00:03` The Editors and output section.
- `00:00:08` UV and Shading switch to Blender's UV Editing and Shading workspaces, like Maya's UV Editor and Hypershade windows.
- `00:00:14` Playblast: the OpenGL render of the animation from the viewport, as in Maya. The result follows the render output settings.
- `00:00:19` Quad view, or Ctrl+Alt+Q: four views in the viewport, top, front, side and perspective. Again to return.
- `00:00:25` Toolbar, Sidebar and Header show or hide those regions in every viewport at once.
- `00:00:30` **Editors and output**

## 09 Project tab

- `00:00:00` **Project** — The panel section
- `00:00:03` The Project section. At the top, the name of the current project, or 'No project set'.
- `00:00:08` Create builds the folders of a new project and makes it current; Set makes an existing project folder current.
- `00:00:14` Open scene and Save as work inside scenes/: they are Ctrl+O and Ctrl+Shift+S too. Ctrl+S stays Blender's own.
- `00:00:19` Make paths relative makes every external path relative, to do before moving the project. Write workspace.mel writes Maya's project file.
- `00:00:25` **Project** — Video 13 shows the whole workflow

## 10 Setup tab

- `00:00:00` **Setup** — The Maya set-up in one go
- `00:00:03` The Setup section, at the bottom of the panel: it switches the five Maya-style settings on and off together. The line above says how many are on.
- `00:00:08` Turn on switches navigation, marking menu, contextual wire, colors and grid on. Turn off switches them off: it is for working the Blender way with the add-on still installed.
- `00:00:14` Save as startup saves the preferences and the startup file: layout and settings come back at every launch.
- `00:00:19` Self check verifies menus, shortcuts and keymaps and writes the result in the landfall_self_check text block.
- `00:00:25` Navigation and Marking menu are the same switches as in the preferences, within reach.
- `00:00:30` Maya colors applies Maya's theme; the arrow restores your previous theme, the other icon the factory one.
- `00:00:36` Finite grid: a grid that ends, like Maya's: 22 cells of 1 metre a side, adjustable next to it. Follow theme gives it the theme's color.
- `00:00:41` Off, Blender's infinite floor comes back, with its axis lines. Up close the two look alike; the difference shows when you zoom out.
- `00:00:46` Shortcuts opens the card with every shortcut: it stays over the viewport, moves when dragged and reads the keys from the keymap.
- `00:00:52` **Setup** — Landfall on is Maya, off is Blender

## 11 Shortcuts and marking menu

- `00:00:00` **Shortcuts and marking menu** — Ctrl+Tab, Shift+Q, Alt+Q, E, F, Shift+F
- `00:00:03` Ctrl+Tab opens the marking menu, in place of Blender's mode pie. In Object Mode: the modes on the left, Edit and Sculpt on the right, Display and Edit above.
- `00:00:08` A click on a branch opens its list, anchored under the entry. The entries show no keys, as in Maya.
- `00:00:14` In Edit Mode: vertex, edge and face on the left, like the 1, 2, 3 keys; Modeling on the right with the modelling commands.
- `00:00:19` The Modeling branch: the modelling commands in two columns, Make face included.
- `00:00:25` Shift+Q: Landfall's pie with the eight most-used commands, in every mode.
- `00:00:30` Shift+Alt+Q: the modelling pie in Edit Mode. Shift+Alt+X: the snap pie, like Maya's X.
- `00:00:36` Alt+Q: the hotbox, every panel section in columns under the mouse.
- `00:00:41` E extrudes with Maya's parameters. F frames the selection, in Edit Mode too. Shift+F makes the face (Blender's Make Edge/Face).
- `00:00:46` G, R, S show the matching manipulator. Alt+1 2 3 the smooth preview, Alt+W the gizmos, Backspace deletes like X and Delete.
- `00:00:52` The Shortcuts card lists them all. To change one: Preferences › Keymap, search landfall, and change every copy, one per mode.
- `00:00:57` **Shortcuts**

## 12 Maya navigation

- `00:00:00` **Maya navigation** — Alt + mouse, F, Home, double click
- `00:00:03` With Navigation on, in the Setup panel or in the preferences, the viewport handles like Maya's.
- `00:00:08` Alt + left button orbits around the selection…
- `00:00:14` …Alt + middle button pans, Alt + right button zooms in and out towards the pointer.
- `00:00:19` F frames the selection, in Object Mode and in Edit Mode on the components. Home frames everything: Maya's A (on a laptop Fn + Left Arrow).
- `00:00:25` Double click selects an edge loop, Ctrl + double click a ring: in Blender they were Alt+click, which now orbits.
- `00:00:30` The switch also sets Orbit Around Selection, Auto Depth and Zoom to Mouse Position. Blender's own middle-button navigation keeps working.
- `00:00:36` Off, or with Landfall uninstalled, everything goes back to Blender's factory preferences.
- `00:00:41` **Maya navigation**

## 13 Maya-style project

- `00:00:00` **Maya-style project** — Create, Set, Open scene, Save as, workspace.mel
- `00:00:03` The project system mirrors Maya's Set Project: a folder holding scenes, sourceimages, images and the rest, and a workspace.mel that Maya recognises.
- `00:00:08` Create: pick where and what to call it. Landfall builds the folders, writes the workspace.mel and makes the project current.
- `00:00:14` The current project's name appears at the top of the section. Set makes an existing project current, one made by Maya too.
- `00:00:19` Open scene, or Ctrl+O, opens the browser straight inside scenes/. With no project it is Blender's Open.
- `00:00:25` Save as, or Ctrl+Shift+S, saves into scenes/ with relative paths. A file already in the project stays where it is. Ctrl+S overwrites the current file, as in Blender.
- `00:00:30` Before moving or copying the project, Make paths relative. Write workspace.mel adds Maya's file to a project made without one.
- `00:00:36` In the preferences: the projects' root folder, renders in images/, the assets/ folder as an asset library.
- `00:00:41` **Project**
