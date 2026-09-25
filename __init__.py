# Landfall — a Blender add-on for artists coming from Maya.
# Copyright (C) 2026  Luca Orlandi
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import json
import os
import time

import bpy
import blf
import bmesh
import mathutils
import numpy as np
import gpu
from gpu_extras.batch import batch_for_shader

bl_info = {
    "name": "Landfall",
    "author": "Luca Orlandi",
    "version": (3, 41, 2),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar (N) > Landfall | Properties > Object | Shift+Q | Alt+Q",
    "description": "Maya-style shelf for Blender",
    "category": "3D View",
}


VERSION_TEXT = "vers. %d.%d.%d - by %s" % (
    bl_info["version"][0],
    bl_info["version"][1],
    bl_info["version"][2],
    bl_info["author"],
)


def _grid_update(self, context):
    try:
        v3d = context.preferences.themes[0].view_3d
    except Exception:
        return
    v = self.landfall_grid_shade
    v3d.grid = (v, v, v, 1.0)


def draw_gizmos(layout, context):
    spaces = _view3d_spaces(context)
    scene = context.scene
    box = layout.column(align=True)

    row = box.row(align=True)
    if spaces:
        space = spaces[0]
        row.prop(space, "show_gizmo", text="Gizmos", toggle=True, icon="GIZMO")
        sub = row.row(align=True)
        sub.enabled = space.show_gizmo
        sub.prop(space, "show_gizmo_object_translate", text="Move", toggle=True)
        sub.prop(space, "show_gizmo_object_rotate", text="Rotate", toggle=True)
        sub.prop(space, "show_gizmo_object_scale", text="Scale", toggle=True)
    else:
        row.operator("landfall.toggle_gizmos", text="Gizmos", icon="GIZMO")

    col = box.column(align=True)
    row = col.row(align=True)
    slot = scene.transform_orientation_slots[0]
    row.prop(slot, "type", text="")
    row.prop(scene.tool_settings, "transform_pivot_point", text="")
    row = col.row(align=True)
    row.enabled = False
    row.label(text="Pie menus: , orientation   . pivot")


def draw_nav_toggle(layout, context):
    p = prefs(context)
    if p is None:
        return
    scene = context.scene

    row = layout.row(align=True)
    row.prop(p, "maya_navigation", text="Navigation", toggle=True,
             icon="ORIENTATION_GIMBAL")
    row.prop(p, "marking_menu", text="Marking menu", toggle=True,
             icon="MESH_DATA")

    row = layout.row(align=True)
    row.operator("landfall.maya_theme", text="Maya colors",
                 icon="SHADING_SOLID").restore = False
    row.operator("landfall.maya_theme", text="", icon="LOOP_BACK").restore = True
    row.operator("landfall.reset_theme", text="", icon="FILE_REFRESH")

    col = layout.column(align=True)
    row = col.row(align=True)
    row.prop(scene, "landfall_grid_finite", text="Finite grid", toggle=True,
             icon="GRID")
    if scene.landfall_grid_finite:
        row.prop(scene, "landfall_grid_size", text="")
        row.prop(scene, "landfall_grid_cell", text="")
        row = col.row(align=True)
        row.prop(scene, "landfall_grid_follow_theme", text="Follow theme",
                 toggle=True)
        sub = row.row(align=True)
        sub.enabled = not scene.landfall_grid_follow_theme
        sub.scale_x = 0.5
        sub.prop(scene, "landfall_grid_color", text="")
    else:
        row.prop(scene, "landfall_grid_shade", text="Shade", slider=True)


def draw_transform_hint(layout, context):
    p = prefs(context)
    if p is not None and not p.show_transform_hint:
        return
    box = layout.box()

    row = box.row(align=True)
    for key, label in (("G", "Move"), ("R", "Rotate"), ("S", "Scale")):
        sub = row.column(align=True)
        sub.alignment = "CENTER"
        sub.label(text="%s = %s" % (key, label))

    col = box.column(align=True)
    col.enabled = False
    col.label(text="Views   Numpad 1 3 7   `  pie")
    col.label(text="Ctrl Alt Q  quad     Ctrl Space  max")


def draw_footer(layout):
    layout.operator("landfall.cheatsheet", text="Shortcuts", icon="KEYINGSET")
    row = layout.row()
    row.alignment = "CENTER"
    row.enabled = False
    row.label(text=VERSION_TEXT)


def _view3d_spaces(context):
    """Every 3D viewport on the current screen, whatever editor we are called from."""
    space = getattr(context, "space_data", None)
    if space is not None and getattr(space, "type", "") == "VIEW_3D":
        return [space]
    out = []
    win = getattr(context, "window", None)
    if win is None or win.screen is None:
        return out
    for area in win.screen.areas:
        if area.type == "VIEW_3D":
            for sp in area.spaces:
                if sp.type == "VIEW_3D":
                    out.append(sp)
                    break
    return out


def _view3d_area(context):
    win = getattr(context, "window", None)
    if win is None or win.screen is None:
        return None, None
    for area in win.screen.areas:
        if area.type != "VIEW_3D":
            continue
        for region in area.regions:
            if region.type == "WINDOW":
                return area, region
    return None, None


def _redraw_view3d(context=None):
    """Tag every 3D viewport in every window for redraw.

    The update callbacks used to read context.window.screen, which is None
    when the property is set from a timer, the Python console or a script,
    and the whole callback died on an AttributeError before it got there.
    """
    try:
        wm = (context or bpy.context).window_manager
        windows = wm.windows
    except Exception:
        return
    for window in windows:
        screen = window.screen
        if screen is None:
            continue
        for area in screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()


def _start_timer(fn, first_interval):
    """Register a timer once. Opening several files in a row used to stack a
    copy of the same timer per file, each resetting the other's counter."""
    try:
        if bpy.app.timers.is_registered(fn):
            return
    except Exception:
        pass
    bpy.app.timers.register(fn, first_interval=first_interval)


def _stop_timer(fn):
    try:
        if bpy.app.timers.is_registered(fn):
            bpy.app.timers.unregister(fn)
    except Exception:
        pass


def _shortcut(idname, props=None):
    """Return the live keymap binding for an operator, or an empty string."""
    try:
        kc = bpy.context.window_manager.keyconfigs.user
    except Exception:
        return ""
    if kc is None:
        return ""
    for km in kc.keymaps:
        for kmi in km.keymap_items:
            if kmi.idname != idname:
                continue
            if props:
                match = True
                for key, value in props.items():
                    if getattr(kmi.properties, key, None) != value:
                        match = False
                        break
                if not match:
                    continue
            try:
                return kmi.to_string()
            except Exception:
                return ""
    return ""


def _with_shortcut(text, idname, props=None):
    key = _shortcut(idname, props)
    return text + "\nShortcut: " + key if key else text


# --------------------------------------------------------------- operators


class LANDFALL_OT_toggle_xray_object(bpy.types.Operator):
    bl_idname = "landfall.toggle_xray_object"
    bl_label = "Object X-ray"
    bl_description = "Make only the selected objects transparent"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        alpha = context.scene.landfall_xray_alpha
        objs = list(context.selected_objects)
        active = context.view_layer.objects.active
        if not objs and active is not None:
            objs = [active]
        if not objs:
            self.report({"WARNING"}, "No object selected")
            return {"CANCELLED"}

        for space in _view3d_spaces(context):
            if space.shading.type == "SOLID":
                space.shading.color_type = "OBJECT"

        turning_on = any(o.color[3] >= 0.999 for o in objs)
        for o in objs:
            o.color[3] = alpha if turning_on else 1.0
        return {"FINISHED"}


class LANDFALL_OT_toggle_wireframe(bpy.types.Operator):
    bl_idname = "landfall.toggle_wireframe"
    bl_label = "Wire on shaded"
    bl_description = (
        "Draw the wire on top of the solid shading, as Maya's Wireframe on "
        "Shaded does. This is not Blender's Wireframe shading mode, which "
        "shows the edges instead of the surface"
    )

    def execute(self, context):
        spaces = _view3d_spaces(context)
        if not spaces:
            self.report({"WARNING"}, "No 3D viewport on this screen")
            return {"CANCELLED"}
        new_state = not spaces[0].overlay.show_wireframes
        for space in spaces:
            space.overlay.show_wireframes = new_state
        return {"FINISHED"}


class LANDFALL_OT_hide_selected(bpy.types.Operator):
    bl_idname = "landfall.hide_selected"
    bl_label = "Hide selection"
    bl_description = "Hide the selected objects and remember which"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        objs = [o for o in context.selected_objects if not o.hide_get()]
        if not objs:
            self.report({"WARNING"}, "No object selected")
            return {"CANCELLED"}
        context.scene["landfall_last_hidden"] = "\n".join(o.name for o in objs)
        for o in objs:
            o.hide_set(True)
        return {"FINISHED"}


class LANDFALL_OT_show_selected(bpy.types.Operator):
    bl_idname = "landfall.show_selected"
    bl_label = "Show selection"
    bl_description = "Unhide the selected objects (select them in the Outliner)"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        shown = 0
        targets = [o for o in context.view_layer.objects if o.select_get()]
        active = context.view_layer.objects.active
        if active is not None and active not in targets:
            targets.append(active)

        for o in targets:
            if o.hide_get():
                o.hide_set(False)
                o.select_set(True)
                shown += 1
        if shown == 0:
            self.report({"WARNING"}, "No selected object is hidden")
            return {"CANCELLED"}
        self.report({"INFO"}, "Unhid %d objects" % shown)
        return {"FINISHED"}


class LANDFALL_OT_show_all(bpy.types.Operator):
    bl_idname = "landfall.show_all"
    bl_label = "Show all"
    bl_description = "Unhide every object in the view layer"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        n = 0
        for o in context.view_layer.objects:
            if o.hide_get():
                o.hide_set(False)
                n += 1
        context.scene["landfall_last_hidden"] = ""
        self.report({"INFO"}, "Unhid %d objects" % n)
        return {"FINISHED"}


class LANDFALL_OT_isolate(bpy.types.Operator):
    bl_idname = "landfall.isolate"
    bl_label = "Isolate"
    bl_description = "Toggle Local View on the 3D viewport"

    def execute(self, context):
        area, region = _view3d_area(context)
        if area is None:
            self.report({"WARNING"}, "No 3D viewport on this screen")
            return {"CANCELLED"}
        with context.temp_override(area=area, region=region):
            _safe(bpy.ops.view3d.localview)
        return {"FINISHED"}


class LANDFALL_OT_show_last_hidden(bpy.types.Operator):
    bl_idname = "landfall.show_last_hidden"
    bl_label = "Show last hidden"
    bl_description = "Unhide and reselect only the objects hidden last"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        raw = context.scene.get("landfall_last_hidden", "")
        names = [n for n in raw.split("\n") if n]
        if not names:
            self.report({"WARNING"}, "Nothing to unhide")
            return {"CANCELLED"}

        _safe(bpy.ops.object.select_all, action="DESELECT")
        restored = 0
        for name in names:
            o = context.scene.objects.get(name)
            if o is not None and o.hide_get():
                o.hide_set(False)
                o.select_set(True)
                context.view_layer.objects.active = o
                restored += 1

        context.scene["landfall_last_hidden"] = ""
        if restored == 0:
            self.report({"WARNING"}, "Those objects are no longer hidden")
            return {"CANCELLED"}
        self.report({"INFO"}, "Unhid %d objects" % restored)
        return {"FINISHED"}


# --------------------------------------------------- border edge overlay

EMPTY_COORDS = np.empty((0, 3), dtype=np.float32)


def _join(parts):
    """One array out of many, without going through Python lists."""
    parts = [p for p in parts if len(p)]
    if not parts:
        return EMPTY_COORDS
    return parts[0] if len(parts) == 1 else np.concatenate(parts)

# Seconds of fresh border computation allowed per redraw. A count of objects
# was the earlier measure, and four hundred fresh objects took 236 ms in one
# frame on a scene of twelve hundred: time is what the eye notices.
BORDER_BUDGET_S = 0.006

# While a mesh is being edited its border is refreshed on its own clock, not
# on every redraw: every vertex you drag invalidates the cache, so on a dense
# mesh the recompute would land on every single frame.
#
# The interval follows the cost of the mesh. A refresh that takes 0.1 ms can
# run thirty times a second and the border follows the mouse; one that takes
# 5 ms runs ten times a second and the viewport stays free. The interval is
# the measured cost times EDIT_REFRESH_RATIO, clamped between the two limits.
# And it only runs when the mesh has actually changed since the last refresh:
# the depsgraph says so, and sitting still costs nothing at all.
EDIT_REFRESH_MIN_S = 0.03
EDIT_REFRESH_MAX_S = 0.25
EDIT_REFRESH_RATIO = 20.0

MAX_EDGES = 400000

_border_cache = {}
# Per object in Edit Mode: (time of the last refresh, its coordinates, the
# interval to wait before the next one).
_border_recent = {}
# Objects in Edit Mode whose geometry changed since their last refresh.
_edit_dirty = set()
# The one object whose depsgraph update was caused by our own sync, which
# would otherwise count as an edit and start the cycle again.
_self_sync = set()


def _cache_key(obj):
    """Pointer rather than name: survives a rename, unique across scenes.

    After an undo the Python reference can point at an object Blender has
    already freed, and every attribute on it raises. The fallback used to read
    obj.name, which raises just the same, so the error escaped instead of
    being handled. None means "no usable key" and the caller skips the object.
    """
    try:
        return obj.as_pointer()
    except ReferenceError:
        return None
    except Exception:
        try:
            return obj.name
        except Exception:
            return None


# Bumped on every invalidation. The drawing keeps its GPU batches until this
# changes, instead of rebuilding them on every redraw of every viewport.
_generation = [0]


def _changed_keys(depsgraph):
    """Pointers of the objects whose geometry or transform just changed.

    None means "everything": no depsgraph to ask, or an update we could not
    read, and then the caller drops the whole cache rather than guess.
    """
    if depsgraph is None:
        return None, True
    try:
        keys = set()
        geometry = False
        for update in depsgraph.updates:
            # Only objects: the caches are keyed by object, and the mesh
            # datablock's own entry — which every edit also carries — would
            # count as a second, unrelated geometry change.
            if not isinstance(update.id, bpy.types.Object):
                continue
            if update.is_updated_geometry:
                key = update.id.original.as_pointer()
                if key in _self_sync:
                    # Our own update_from_editmode, not an edit: it must
                    # neither invalidate what it just produced nor mark the
                    # object as changed, or the refresh would feed itself.
                    _self_sync.discard(key)
                    continue
                geometry = True
                if key in _border_recent:
                    _edit_dirty.add(key)
            elif not update.is_updated_transform:
                continue
            keys.add(update.id.original.as_pointer())
        return keys, geometry
    except Exception:
        return None, True


def _invalidate(cache, keys):
    """Drop only what actually changed, and say whether anything was dropped.

    Clearing everything meant that moving one object recomputed the border
    edges of every object in the scene, which is what made heavy files crawl.
    """
    if keys is None:
        had = bool(cache)
        cache.clear()
        return had
    dropped = False
    for key in keys:
        if cache.pop(key, None) is not None:
            dropped = True
    return dropped


def _clear_all_caches(*args):
    """Undo and redo rebuild the datablocks, so every address we hold may now
    belong to something else. Nothing survives that."""
    _cage_cache.clear()
    _border_cache.clear()
    _border_recent.clear()
    _edit_dirty.clear()
    _self_sync.clear()
    _cage_batches.clear()
    _border_batches.clear()
    _scans.clear()
    _generation[0] += 1
    _scan_gen[0] += 1


# ------------------------------------------------ which objects to draw
#
# Both overlays used to walk every object of the view layer on every redraw
# of every viewport — visible_get, select_get, the modifier stack — and then
# concatenate twelve hundred arrays, only to find that the GPU batch built on
# the previous frame was still good. On 1200 objects that was 3.8 ms for the
# borders and 3.2 ms for the cage, per frame, with nothing changing.
#
# The walk is done once and kept until the depsgraph reports something that
# could change its outcome (see _on_depsgraph), with a time limit as a safety
# net for whatever Blender does not report. A frame where nothing changed
# then costs a few dictionary lookups and one batch.draw.

_scan_gen = [0]
# One scan per 3D viewport: visible_get() answers for the viewport in the
# context, so a viewport in Local View sees a different set of objects than
# its neighbour, and a shared scan flipped between the two on every frame.
_scans = {}
SCAN_REFRESH_S = 0.5


def _space_key(context):
    space = getattr(context, "space_data", None)
    try:
        return space.as_pointer() if space is not None else 0
    except Exception:
        return 0


def _per_space(stores, context):
    """The store of this viewport, created on first use."""
    key = _space_key(context)
    store = stores.get(key)
    if store is None:
        store = stores[key] = {}
    return store


def _scan_objects(context):
    now = time.monotonic()
    _scan = _per_space(_scans, context)
    if (_scan.get("gen") == _scan_gen[0]
            and now - _scan.get("at", 0.0) < SCAN_REFRESH_S):
        return _scan
    view_layer = context.view_layer
    every, selected, cage = [], [], []
    for o in view_layer.objects:
        if o.type != "MESH" or not o.visible_get():
            continue
        key = _cache_key(o)
        if key is None:
            continue
        chosen = o.select_get()
        every.append((o, key))
        if chosen:
            selected.append((o, key))
        # In Edit Mode Blender already draws the cage, with its own vertex,
        # edge and face selection colors. Drawing ours on top hides them.
        if o.mode != "EDIT" and any(
                m.type == "SUBSURF" and m.show_viewport for m in o.modifiers):
            cage.append((o, key, chosen))
    active = view_layer.objects.active
    if (active is not None and active.type == "MESH"
            and not active.select_get() and active.visible_get()):
        key = _cache_key(active)
        if key is not None:
            selected.append((active, key))
    _scan.update(gen=_scan_gen[0], at=now, all=tuple(every),
                 selected=tuple(selected), cage=tuple(cage))
    return _scan


def _on_depsgraph(scene=None, depsgraph=None):
    """One handler for both overlays instead of two reading the same updates.

    The GPU batches are only dropped when a cached object was actually
    invalidated. Every depsgraph update used to bump the generation and
    throw the batches away — four times for a single click on an object,
    measured — so selecting anything rebuilt the whole overlay for nothing.
    """
    keys, geometry = _changed_keys(depsgraph)
    # Which objects the overlays look at depends on visibility, selection
    # and modifiers. Those arrive as updates carrying no transform and no
    # geometry — or as geometry updates, when a modifier is added — and a
    # pure transform update, the drag of one object, is neither. So the
    # object scan is only marked stale in the first two cases, and dragging
    # never triggers a pass over the whole scene.
    if keys is None or not keys or geometry:
        _scan_gen[0] += 1
    if keys is not None and not keys:
        return
    border = _invalidate(_border_cache, keys)
    cage = _invalidate(_cage_cache, keys)
    if border or cage:
        _generation[0] += 1
        _border_batches.clear()
        _cage_batches.clear()
    if len(_border_recent) > 64:
        _border_recent.clear()
        _edit_dirty.clear()


def _clear_border_cache(*args):
    _border_cache.clear()
    _border_batches.clear()
    _border_recent.clear()
    _edit_dirty.clear()
    _generation[0] += 1


def _border_edges(mesh):
    """Indices of the edges that belong to exactly one face."""
    ne = len(mesh.edges)
    if ne == 0 or ne > MAX_EDGES:
        return None
    loops = _attr(mesh, ".corner_edge", "value", 1, np.int32)
    if loops is None:
        loops = np.empty(len(mesh.loops), dtype=np.int32)
        mesh.loops.foreach_get("edge_index", loops)
    counts = np.bincount(loops, minlength=ne)
    return np.nonzero(counts == 1)[0]


def _border_coords(obj, context):
    """World-space coordinates of the open border edges of one object."""
    key = _cache_key(obj)
    if key is None:
        return EMPTY_COORDS
    cached = _border_cache.get(key)
    if cached is not None:
        return cached

    coords = EMPTY_COORDS
    fresh_at = None
    temp = False
    try:
        if obj.mode == "EDIT" and obj.type == "MESH":
            # While editing, the geometry lives in the BMesh and the evaluated
            # mesh comes back empty — reading it there drew nothing at all.
            # Syncing writes the edit cage into the mesh; but a mesh in Edit
            # Mode exposes no attribute layers at all (mesh.attributes is
            # empty), so every read fell back on the collection wrappers:
            # 50 ms on 290k edges, against 1.3 ms for the same mesh in Object
            # Mode. to_mesh() after the sync hands back the same data as a
            # plain mesh, attributes included, and the whole read is 3.6 ms.
            now = time.monotonic()
            last, stale, wait = _border_recent.get(key, (0.0, None, 0.0))
            if stale is not None:
                if key not in _edit_dirty:
                    # Nothing changed since the last refresh: sitting still
                    # in Edit Mode costs nothing.
                    _border_cache[key] = stale
                    return stale
                if now - last < wait:
                    # Changed, but too soon: keep the last result and come
                    # back when the interval is over, even if the mouse has
                    # stopped by then and nothing else asks for a redraw.
                    _border_cache[key] = stale
                    _redraw_later(wait - (now - last))
                    return stale
            fresh_at = now
            _edit_dirty.discard(key)
            # The size check comes before the sync: syncing a mesh too big
            # to draw, several times a second, was the one cost left on it.
            if len(obj.data.edges) > MAX_EDGES:
                mesh = None
            else:
                _self_sync.add(key)
                obj.update_from_editmode()
                mesh = obj.to_mesh()
                temp = True
                if mesh is None or len(mesh.edges) != len(obj.data.edges):
                    obj.to_mesh_clear()
                    temp = False
                    mesh = obj.data
        else:
            # The evaluated object already carries its mesh; to_mesh() would
            # hand back a copy of it, which costs time and memory for nothing.
            dg = context.evaluated_depsgraph_get()
            mesh = obj.evaluated_get(dg).data
        if mesh is not None and isinstance(mesh, bpy.types.Mesh):
            border = _border_edges(mesh)
            if border is not None and len(border):
                co, ed, ne = _mesh_arrays(mesh)
                pairs = ed.reshape(ne, 2)[border].ravel()
                coords = _to_world(co, pairs, obj.matrix_world)
    except Exception:
        coords = EMPTY_COORDS
    finally:
        if temp:
            try:
                obj.to_mesh_clear()
            except Exception:
                pass

    _border_cache[key] = coords
    if fresh_at is not None:
        cost = time.monotonic() - fresh_at
        wait = min(EDIT_REFRESH_MAX_S, max(EDIT_REFRESH_MIN_S,
                                           cost * EDIT_REFRESH_RATIO))
        _border_recent[key] = (fresh_at, coords, wait)
    return coords


_redraw_timer = {"at": 0.0}


def _redraw_later(delay):
    """One redraw of every 3D viewport after the delay, coalesced.

    A refresh deferred by the interval needs a redraw to be picked up; if
    the mouse stops before then, nothing else would ask for one and the
    border would stay behind until the next event.
    """
    due = time.monotonic() + delay
    if _redraw_timer["at"] > time.monotonic() and _redraw_timer["at"] <= due:
        return
    _redraw_timer["at"] = due

    def fire():
        _redraw_timer["at"] = 0.0
        _redraw_view3d()
        return None
    try:
        bpy.app.timers.register(fire, first_interval=max(0.005, delay))
    except Exception:
        pass


def _draw_borders():
    context = bpy.context
    scene = getattr(context, "scene", None)
    if scene is None or not getattr(scene, "landfall_border_show", False):
        return

    region = getattr(context, "region", None)
    if region is None:
        return

    scan = _scan_objects(context)
    objs = scan["selected"] if scene.landfall_border_selected_only else scan["all"]

    shader = gpu.shader.from_builtin("POLYLINE_UNIFORM_COLOR")
    store = _per_space(_border_batches, context)

    # An object being edited refreshes on its own clock. Its part of the
    # signature is the time of its last refresh, so the batch is rebuilt
    # when a refresh happened and not otherwise. The refresh itself is
    # asked for first, because it is what moves that stamp.
    edit_keys = [k for o, k in objs if o.mode == "EDIT"]
    for o, key in objs:
        if o.mode == "EDIT" and key not in _border_cache:
            _border_coords(o, context)
    stamps = tuple(_border_recent.get(k, (0.0,))[0] for k in edit_keys)
    signature = (_generation[0], tuple(k for _o, k in objs), stamps)
    if store.get("signature") != signature:
        # Finding the open edges of an object that is not cached yet costs
        # a couple of milliseconds. Six hundred of them at once would freeze
        # the viewport for a second, so fresh objects are done within a time
        # budget per redraw and the rest arrive over the next few frames.
        parts = []
        done = []
        deadline = time.monotonic() + BORDER_BUDGET_S
        for o, key in objs:
            if key not in _border_cache and time.monotonic() > deadline:
                if context.area:
                    context.area.tag_redraw()
                continue
            parts.append(_border_coords(o, context))
            done.append(key)
        coords = _join(parts)
        stamps = tuple(_border_recent.get(k, (0.0,))[0] for k in edit_keys)
        signature = (_generation[0], tuple(done), stamps)
        batch = _batches(store, shader, signature, coords)[0]
    else:
        batch = store["batches"][0]
    if batch is None:
        return

    gpu.state.blend_set("ALPHA")
    gpu.state.depth_test_set("LESS_EQUAL")

    shader.bind()
    shader.uniform_float("viewportSize", (region.width, region.height))
    shader.uniform_float("lineWidth", scene.landfall_border_width)
    shader.uniform_float("color", scene.landfall_border_color)
    batch.draw(shader)

    gpu.state.depth_test_set("NONE")
    gpu.state.blend_set("NONE")


def _border_show_update(self, context):
    _clear_border_cache()
    _redraw_view3d(context)


def _grid_sync(*args):
    """Bring the drawing in line with the saved property.

    The update callback only fires when the value changes, so on start-up and
    on opening a file a scene saved with the finite grid on would have the
    native floor off and nothing of ours drawn: no grid at all.
    """
    try:
        scene = bpy.context.scene
    except Exception:
        return
    on = getattr(scene, "landfall_grid_finite", False)
    _set_native_grid(not on)


# --------------------------------------------------------- cheat sheet

SHEET_LANDFALL = (
    ("Pie menu", "wm.call_menu_pie", {"name": "VIEW3D_MT_landfall_pie"}, {}),
    ("Hotbox", "landfall.hotbox", None, {}),
    ("Gizmos on/off", "landfall.toggle_gizmos", None, {}),
    ("Marking menu", "landfall.marking_menu", None, {}),
    ("Modeling pie", "wm.call_menu_pie",
     {"name": "VIEW3D_MT_landfall_model_pie"}, {}),
    ("Snap pie", "wm.call_menu_pie",
     {"name": "VIEW3D_MT_landfall_snap_pie"}, {}),
    ("Smooth: cage", "landfall.smooth_preview", {"mode": "CAGE"}, {}),
    ("Smooth: cage + surface", "landfall.smooth_preview", {"mode": "BOTH"}, {}),
    ("Smooth: surface only", "landfall.smooth_preview", {"mode": "SMOOTH"}, {}),
    ("Open in project", "landfall.project_open", None, {}),
    ("Save in project", "landfall.project_save_as", None, {}),
)

SHEET_NAV = (
    ("Orbit", "view3d.rotate", None, {"alt": True}),
    ("Pan", "view3d.move", None, {"alt": True}),
    ("Zoom", "view3d.zoom", None, {"alt": True}),
    ("Frame selection", "view3d.view_selected", None, {"type": "F"}),
    ("Loop select", "mesh.loop_select", None, {"value": "DOUBLE_CLICK"}),
)

# Panel commands with no key of their own, listed so they are discoverable.
SHEET_PANEL = (
    ("Cage overlay", "Modeling, or Smooth 2"),
    ("Border edges", "Display"),
    ("Object color", "Display"),
    ("Finite grid", "Setup"),
    ("Maya colors", "Setup"),
    ("Maya setup, all at once", "Setup"),
    ("Quad view", "Editors, or Ctrl Alt Q"),
    ("Toolbar / sidebar / header", "Editors"),
    ("Load PBR set", "Texturing"),
    ("Create or set project", "Project"),
)

SHEET_BLENDER = (
    ("Move / rotate / scale", "G  R  S"),
    ("Constrain to axis", "X  Y  Z"),
    ("Numeric input", "type a number"),
    ("Frame all", "Home"),
    ("Frame selection", "Numpad ."),
    ("Marking menu", "Ctrl Tab"),
    ("Vertex / edge / face", "1  2  3"),
    ("Select all / none", "A / Alt A"),
    ("Invert selection", "Ctrl I"),
    ("Global x-ray", "Alt Z"),
    ("Loop cut", "Ctrl R"),
    ("Knife", "K"),
    ("Make face", "F"),
    ("Subdivision level", "Ctrl 1-5"),
    ("Orientation pie", ","),
    ("Pivot point pie", "."),
    ("View pie", "`"),
    ("Front / right / top", "Numpad 1 3 7"),
    ("Quad view", "Ctrl Alt Q"),
    ("Maximise area", "Ctrl Space"),
)

_sheet = {"handle": None, "x": 60.0, "y": 120.0, "close": None,
          "drag": None, "running": False, "w": 0.0, "h": 0.0,
          "rows": None, "rows_at": 0.0, "rows_nav": None}

# The sheet reads every key from the live keymap, which is the point of it,
# but a full scan of the user configuration is four thousand entries and
# sixteen of them per redraw cost 6 ms, measured. Keymaps do not change while
# you drag a card around, so the rows are kept this long before being read
# again.
SHEET_REFRESH_S = 2.0


def _find_kmi(idname, props=None, attrs=None):
    try:
        kc = bpy.context.window_manager.keyconfigs.user
    except Exception:
        return ""
    if kc is None:
        return ""
    for km in kc.keymaps:
        for kmi in km.keymap_items:
            if kmi.idname != idname or not kmi.active:
                continue
            ok = True
            for key, value in (attrs or {}).items():
                if getattr(kmi, key, None) != value:
                    ok = False
                    break
            if ok:
                for key, value in (props or {}).items():
                    if getattr(kmi.properties, key, None) != value:
                        ok = False
                        break
            if ok:
                try:
                    return kmi.to_string()
                except Exception:
                    return ""
    return ""


def _rect(x, y, w, h, color):
    verts = ((x, y), (x + w, y), (x + w, y + h), (x, y + h))
    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    batch = batch_for_shader(shader, "TRIS", {"pos": verts},
                             indices=((0, 1, 2), (0, 2, 3)))
    shader.bind()
    shader.uniform_float("color", color)
    batch.draw(shader)


def _sheet_theme(context):
    back = (0.11, 0.11, 0.11, 0.96)
    text = (0.88, 0.88, 0.88, 1.0)
    try:
        ui = context.preferences.themes[0].user_interface
        b = tuple(ui.wcol_menu_back.inner)
        back = (b[0], b[1], b[2], max(b[3], 0.94)) if len(b) == 4 else back
        t = tuple(ui.wcol_menu_back.text)
        text = (t[0], t[1], t[2], 1.0)
    except Exception:
        pass
    return back, text


# blf.dimensions is not free and the sheet measures every label on every
# redraw while it is open. The widths only depend on the text and the size.
_text_cache = {}


def _text_w(font, size, text):
    if len(_text_cache) > 400:
        _text_cache.clear()
    key = (round(size, 2), text)
    w = _text_cache.get(key)
    if w is None:
        blf.size(font, size)
        w = blf.dimensions(font, text)[0]
        _text_cache[key] = w
    return w


def _draw_sheet():
    context = bpy.context
    if not _sheet["running"]:
        return

    font = 0
    scale = context.preferences.system.ui_scale
    s_title, s_head, s_row = 13 * scale, 11 * scale, 12 * scale
    pad, row_h, gap = 14 * scale, 19 * scale, 20 * scale

    back, text_col = _sheet_theme(context)
    muted = (text_col[0], text_col[1], text_col[2], 0.5)
    dim = (text_col[0], text_col[1], text_col[2], 0.35)

    nav_on = False
    p = prefs(context)
    if p is not None:
        nav_on = p.maya_navigation

    now = time.monotonic()
    if (_sheet["rows"] is None or _sheet["rows_nav"] != nav_on
            or now - _sheet["rows_at"] > SHEET_REFRESH_S):
        left = [("Landfall", [(lbl, _find_kmi(op, pr, at) or "not set")
                              for lbl, op, pr, at in SHEET_LANDFALL])]
        nav_rows = [(lbl, (_find_kmi(op, pr, at) or "not set")
                     if nav_on else "off")
                    for lbl, op, pr, at in SHEET_NAV]
        left.append(("Maya navigation", nav_rows))
        left.append(("In the panel", list(SHEET_PANEL)))
        right = [("Blender essentials", list(SHEET_BLENDER))]
        _sheet["rows"] = (left, right)
        _sheet["rows_at"] = now
        _sheet["rows_nav"] = nav_on
    left, right = _sheet["rows"]

    def measure(cols):
        lbl_w = key_w = 0.0
        rows = 0
        for title, items in cols:
            lbl_w = max(lbl_w, _text_w(font, s_head, title))
            rows += 1
            for lbl, key in items:
                lbl_w = max(lbl_w, _text_w(font, s_row, lbl))
                key_w = max(key_w, _text_w(font, s_row, key))
                rows += 1
        return lbl_w, key_w, rows

    l_lbl, l_key, l_rows = measure(left)
    r_lbl, r_key, r_rows = measure(right)
    col_l = l_lbl + l_key + 26 * scale
    col_r = r_lbl + r_key + 26 * scale
    body_rows = max(l_rows + len(left) - 1, r_rows)

    width = pad * 2 + col_l + gap + col_r
    height = pad * 2 + 26 * scale + body_rows * row_h
    x, y = _sheet["x"], _sheet["y"]
    _sheet["w"], _sheet["h"] = width, height

    gpu.state.blend_set("ALPHA")
    _rect(x, y, width, height, back)
    _rect(x, y + height - 26 * scale, width, 26 * scale,
          (back[0] + 0.06, back[1] + 0.06, back[2] + 0.06, back[3]))

    blf.size(font, s_title)
    blf.color(font, *text_col)
    blf.position(font, x + pad, y + height - 19 * scale, 0)
    blf.draw(font, "Landfall shortcuts")

    close_size = 16 * scale
    cx = x + width - pad - close_size
    cy = y + height - 21 * scale
    _sheet["close"] = (cx, cy, close_size, close_size)
    blf.size(font, s_row)
    blf.color(font, *muted)
    blf.position(font, cx + 4 * scale, cy + 3 * scale, 0)
    blf.draw(font, "X")

    def draw_column(cols, cx0, lbl_w, col_w):
        yy = y + height - 26 * scale - pad
        for title, items in cols:
            greyed = title == "Maya navigation" and not nav_on
            blf.size(font, s_head)
            blf.color(font, *muted)
            blf.position(font, cx0, yy, 0)
            blf.draw(font, title + ("  (off)" if greyed else ""))
            yy -= row_h
            for lbl, key in items:
                blf.size(font, s_row)
                blf.color(font, *(dim if greyed else text_col))
                blf.position(font, cx0, yy, 0)
                blf.draw(font, lbl)
                blf.color(font, *(dim if (greyed or key in ("not set", "off")) else muted))
                kw = _text_w(font, s_row, key)
                blf.position(font, cx0 + col_w - kw, yy, 0)
                blf.draw(font, key)
                yy -= row_h
            yy -= row_h * 0.4

    draw_column(left, x + pad, l_lbl, col_l)
    draw_column(right, x + pad + col_l + gap, r_lbl, col_r)

    gpu.state.blend_set("NONE")


def _sheet_stop():
    if _sheet["handle"] is not None:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(_sheet["handle"], "WINDOW")
        except Exception:
            pass
    _sheet["handle"] = None
    _sheet["running"] = False
    _sheet["drag"] = None
    _sheet["rows"] = None


# Sampled from a Maya screenshot: background #5C5C5C, selection #43FFA3,
# grid #404040. Stored as sRGB and converted to linear when applied.
MAYA_BACKGROUND = "5C5C5C"
MAYA_SELECT = "43FFA3"
# Component mode uses different colors: a pure green for the selected
# components and a light cyan for the whole wireframe of the edited object.
MAYA_COMPONENT = "00FF0F"
MAYA_EDIT_WIRE = "64DCFF"
# Maya draws #404040 at full strength; Blender fades the grid with distance
# and angle, so it is darkened to keep the same readability.
MAYA_GRID = "303030"
# Maya samples at #5285A6, but its panels are lighter than Blender's, so the
# hue is kept and the value tuned for legibility instead: white text on this
# reaches 4.8:1, where #37A5CC only manages 2.8:1.
MAYA_HIGHLIGHT = "2A7A9C"


# theme attribute -> number of components
# Every widget class that has a selected state. Toggles were the ones missing:
# a prop(toggle=True) button uses wcol_toggle, not wcol_regular.
HIGHLIGHT_WIDGETS = (
    "wcol_regular",
    "wcol_tool",
    "wcol_toolbar_item",
    "wcol_radio",
    "wcol_option",
    "wcol_toggle",
    "wcol_num",
    "wcol_numslider",
    "wcol_menu",
    "wcol_pulldown",
    "wcol_menu_item",
    "wcol_box",
    "wcol_list_item",
    "wcol_tab",
    "wcol_text",
)

THEME_FIELDS = (
    ("object_active", 3),
    ("object_selected", 3),
    ("vertex_select", 3),
    ("edge_select", 3),
    ("face_select", 4),
    ("wire_edit", 3),
    ("editmesh_active", 4),
    ("grid", 4),
)


def _srgb_to_linear(c):
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def _hex_to_linear(value, size=3, alpha=1.0, factor=1.0):
    """For scene data such as object.color, which Blender stores linear."""
    r = _srgb_to_linear(int(value[0:2], 16) / 255.0) * factor
    g = _srgb_to_linear(int(value[2:4], 16) / 255.0) * factor
    b = _srgb_to_linear(int(value[4:6], 16) / 255.0) * factor
    return (r, g, b, alpha) if size == 4 else (r, g, b)


def _hex_to_theme(value, size=3, alpha=1.0, factor=1.0):
    """Theme colors are gamma space: the float matches the hex directly.

    Converting these to linear is what made every themed color come out far
    too dark.
    """
    r = (int(value[0:2], 16) / 255.0) * factor
    g = (int(value[2:4], 16) / 255.0) * factor
    b = (int(value[4:6], 16) / 255.0) * factor
    return (r, g, b, alpha) if size == 4 else (r, g, b)


def _theme_is_maya(v3d):
    """Is the theme already wearing Maya's colors?

    If it is, the current values are not a "previous theme" worth keeping.
    Saving them would mean that turning the set-up off hands Maya's colors
    straight back, which looks exactly like a restore that does not work.
    It happens after a reinstall: the preferences are new, so the snapshot is
    gone, while the theme in the user preferences is still the Maya one.
    """
    try:
        want = _hex_to_theme(MAYA_BACKGROUND)
        have = tuple(v3d.space.gradients.high_gradient)
        return all(abs(a - b) < 0.01 for a, b in zip(want, have))
    except Exception:
        return False


def _theme_snapshot(v3d, ui=None):
    data = {}
    if ui is not None:
        for name in HIGHLIGHT_WIDGETS:
            widget = getattr(ui, name, None)
            if widget is None:
                continue
            for attr in ("inner_sel", "item", "text_sel"):
                try:
                    data["ui:%s:%s" % (name, attr)] = list(getattr(widget, attr))
                except Exception:
                    pass
    try:
        grad = v3d.space.gradients
        data["background_type"] = grad.background_type
        data["high_gradient"] = list(grad.high_gradient)
        data["gradient"] = list(grad.gradient)
    except Exception:
        pass
    for name, _size in THEME_FIELDS:
        try:
            data[name] = list(getattr(v3d, name))
        except Exception:
            pass
    return json.dumps(data)


# Eight fixed colors, matching Blender's own collection color tags.
OBJECT_COLORS = (
    ("RED", "Red", "E5484D", "COLLECTION_COLOR_01"),
    ("ORANGE", "Orange", "E8963A", "COLLECTION_COLOR_02"),
    ("YELLOW", "Yellow", "E5C453", "COLLECTION_COLOR_03"),
    ("GREEN", "Green", "5BB85B", "COLLECTION_COLOR_04"),
    ("BLUE", "Blue", "4C8FE0", "COLLECTION_COLOR_05"),
    ("VIOLET", "Violet", "9B6BD6", "COLLECTION_COLOR_06"),
    ("PINK", "Pink", "D967A8", "COLLECTION_COLOR_07"),
    ("BROWN", "Brown", "9C7248", "COLLECTION_COLOR_08"),
)


class LANDFALL_OT_keymap_report(bpy.types.Operator):
    bl_idname = "landfall.keymap_report"
    bl_label = "Keymap report"
    bl_description = (
        "Print to the system console every Landfall shortcut and the keymap it "
        "lives in, for the current mode"
    )

    def execute(self, context):
        wm = context.window_manager
        lines = ["", "--- Landfall keymap report ---",
                 "mode: %s" % context.mode]

        for label, kc in (("addon", wm.keyconfigs.addon),
                          ("user", wm.keyconfigs.user)):
            if kc is None:
                continue
            for km in kc.keymaps:
                for kmi in km.keymap_items:
                    if not (kmi.idname.startswith("landfall.")
                            or kmi.idname in ("view3d.rotate", "view3d.move",
                                              "view3d.zoom")
                            or (kmi.idname == "wm.call_menu_pie"
                                and "landfall" in str(
                                    getattr(kmi.properties, "name", "")).lower())):
                        continue
                    lines.append("%-6s %-22s %-34s %-18s %s" % (
                        label, km.name, kmi.idname, kmi.to_string(),
                        "on" if kmi.active else "OFF"))

        text = "\n".join(lines)
        print(text)

        block = bpy.data.texts.get("landfall_keymap_report")
        if block is None:
            block = bpy.data.texts.new("landfall_keymap_report")
        block.clear()
        block.write(text)

        self.report({"INFO"}, "Report in the console and in the text block "
                              "'landfall_keymap_report'")
        return {"FINISHED"}


class LANDFALL_OT_object_color(bpy.types.Operator):
    bl_idname = "landfall.object_color"
    bl_label = "Object color"
    bl_description = (
        "Give the selected objects a viewport color and switch the shading to "
        "Object, the closest thing to Maya's layer colors"
    )
    bl_options = {"REGISTER", "UNDO"}

    # An enum rather than free text: Blender then refuses a wrong value at the
    # call, instead of the operator having to notice at run time and report
    # "Unknown color" after the fact.
    color: bpy.props.EnumProperty(
        items=[(key, label, "") for key, label, _v, _i in OBJECT_COLORS],
        default=OBJECT_COLORS[0][0],
        options={"SKIP_SAVE"},
    )

    @classmethod
    def description(cls, context, properties):
        if properties.clear:
            return "Reset the selected objects to white"
        if properties.use_custom:
            return "Apply the color picked on the left to the selected objects"
        names = dict((k, l) for k, l, _v, _i in OBJECT_COLORS)
        return "Color the selected objects %s" % names.get(properties.color, "")

    use_custom: bpy.props.BoolProperty(default=False, options={"SKIP_SAVE"})
    clear: bpy.props.BoolProperty(default=False, options={"SKIP_SAVE"})

    def execute(self, context):
        objs = list(context.selected_objects)
        if not objs:
            self.report({"WARNING"}, "No object selected")
            return {"CANCELLED"}

        if self.clear:
            rgb = (1.0, 1.0, 1.0)
        elif self.use_custom:
            rgb = tuple(context.scene.landfall_object_color)[:3]
        else:
            hexed = dict((key, value) for key, _label, value, _icon in OBJECT_COLORS)
            rgb = _hex_to_linear(hexed[self.color])

        for o in objs:
            o.color = (rgb[0], rgb[1], rgb[2], o.color[3])

        for space in _view3d_spaces(context):
            if space.shading.type == "SOLID":
                space.shading.color_type = "OBJECT"

        self.report({"INFO"}, "Colored %d objects" % len(objs))
        return {"FINISHED"}


class LANDFALL_OT_save_defaults(bpy.types.Operator):
    bl_idname = "landfall.save_defaults"
    bl_label = "Save as startup"
    bl_description = (
        "Save the preferences and the current file as the startup file, so "
        "the layout, the open panels and the scene options come back every "
        "time. It freezes the whole scene, so start from File > New"
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        try:
            bpy.ops.wm.save_userpref()
        except Exception as err:
            self.report({"WARNING"}, "Preferences not saved: %s" % err)
            return {"CANCELLED"}
        try:
            bpy.ops.wm.save_homefile()
        except Exception as err:
            self.report({"WARNING"}, "Startup file not saved: %s" % err)
            return {"CANCELLED"}
        self.report({"INFO"}, "Preferences and startup file saved")
        return {"FINISHED"}


class LANDFALL_OT_maya_setup(bpy.types.Operator):
    bl_idname = "landfall.maya_setup"
    bl_label = "Maya setup"
    bl_description = (
        "Turn on everything at once: navigation, marking menu, colors, "
        "finite grid and the wire on shaded that follows the mode. Press again "
        "all back"
    )

    enable: bpy.props.BoolProperty(default=True, options={"SKIP_SAVE"})

    @classmethod
    def description(cls, context, properties):
        if properties.enable:
            return ("Turn on navigation, marking menu, colors, finite grid "
                    "the contextual wire on shaded, all at once")
        return "Put all five back to stock Blender, theme included"

    def execute(self, context):
        p = prefs(context)
        if p is None:
            self.report({"WARNING"}, "Preferences not reachable")
            return {"CANCELLED"}

        on = self.enable
        p.maya_navigation = on
        p.marking_menu = on
        p.wire_follows_mode = on
        _safe(bpy.ops.landfall.maya_theme, restore=not on)

        if not on:
            # Applying an object color switches the viewport to shade by
            # object rather than by material, and the theme knows nothing
            # about that: restoring the colors alone left everything still
            # painted with its object color, which looks like the Maya set-up
            # never went away.
            for space in _all_view3d_spaces():
                try:
                    if space.shading.color_type == "OBJECT":
                        space.shading.color_type = "MATERIAL"
                except Exception:
                    pass

        self.report({"INFO"}, "Maya setup on" if on else "Back to stock Blender")
        return {"FINISHED"}


class LANDFALL_OT_reset_theme(bpy.types.Operator):
    bl_idname = "landfall.reset_theme"
    bl_label = "Reset theme"
    bl_description = (
        "Put the whole interface theme back to Blender's factory values. This "
        "also discards any other theme tweaks you have made"
    )

    def execute(self, context):
        try:
            bpy.ops.preferences.reset_default_theme()
        except Exception as err:
            self.report({"WARNING"}, "Could not reset the theme: %s" % err)
            return {"CANCELLED"}
        # Through the helper, so the snapshot on disk goes too: clearing only
        # the preference left the file behind, and the next restore would have
        # read a snapshot describing a theme that is no longer there.
        _theme_backup_write(prefs(context), "")
        _safe(bpy.ops.wm.save_userpref)
        self.report({"INFO"}, "Theme reset to Blender's defaults")
        return {"FINISHED"}


def _theme_backup_path():
    """A file beside Blender's own preferences, not inside ours.

    The snapshot used to live in the add-on preferences, which do not survive
    being disabled or reinstalled. That is how the awkward case arose: after a
    reinstall the snapshot was gone while the theme was still Maya's, so
    turning the set-up off handed Maya's colors straight back. Kept on disk it
    outlives all of that.
    """
    try:
        folder = os.path.join(bpy.utils.resource_path("USER"), "config")
        if not os.path.isdir(folder):
            os.makedirs(folder, exist_ok=True)
        return os.path.join(folder, "landfall_theme_backup.json")
    except Exception:
        return None


def _theme_backup_read(p):
    """The file first, the preference as a fallback for older installs."""
    path = _theme_backup_path()
    if path and os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = f.read()
            if "ui:" in raw:
                return raw
        except Exception:
            pass
    return p.theme_backup if p else ""


def _theme_backup_write(p, raw):
    if p is not None:
        p.theme_backup = raw
    path = _theme_backup_path()
    if not path:
        return
    try:
        if raw:
            with open(path, "w", encoding="utf-8") as f:
                f.write(raw)
        elif os.path.isfile(path):
            os.remove(path)
    except Exception as err:
        print("[landfall] could not keep the theme snapshot on disk: %s" % err)


def _theme_restore(context, theme, p):
    """Put back whatever was there before the Maya colors went on.

    Returns (ok, message). Without a snapshot holding widget colors there is
    nothing reliable to go back to — Blender's factory values differ per
    widget — so the job is handed to Blender's own reset.
    """
    raw = _theme_backup_read(p)
    if "ui:" not in raw:
        if not _safe(bpy.ops.preferences.reset_default_theme):
            return False, "Could not reset the theme"
        _theme_backup_write(p, "")
        _safe(bpy.ops.wm.save_userpref)
        return True, "Theme reset to Blender's defaults"

    v3d, ui = theme.view_3d, theme.user_interface
    try:
        data = json.loads(raw)
    except Exception as err:
        return False, "Restore failed: %s" % err

    grad = v3d.space.gradients
    for chiave in ("background_type", "high_gradient", "gradient"):
        if chiave in data:
            try:
                setattr(grad, chiave, data[chiave])
            except Exception:
                pass
    for name, _size in THEME_FIELDS:
        if name in data:
            try:
                setattr(v3d, name, data[name])
            except Exception:
                pass
    for key, value in data.items():
        if not key.startswith("ui:"):
            continue
        _, name, attr = key.split(":")
        widget = getattr(ui, name, None)
        if widget is not None:
            try:
                setattr(widget, attr, value)
            except Exception:
                pass

    _theme_backup_write(p, "")
    try:
        context.scene.landfall_grid_finite = False
    except Exception:
        pass
    return True, "Previous theme restored"


def _theme_write_viewport(v3d, p):
    """The 3D viewport half: background, grid, and the selection colors."""
    grad = v3d.space.gradients
    grad.background_type = "SINGLE_COLOR"
    grad.high_gradient = _hex_to_theme(MAYA_BACKGROUND)
    v3d.grid = _hex_to_theme(MAYA_GRID, 4)

    if p is None or not p.maya_selection:
        return
    v3d.object_active = _hex_to_theme(MAYA_SELECT)
    v3d.object_selected = _hex_to_theme(MAYA_SELECT, factor=0.55)
    v3d.vertex_select = _hex_to_theme(MAYA_COMPONENT)
    v3d.edge_select = _hex_to_theme(MAYA_COMPONENT)
    v3d.face_select = _hex_to_theme(MAYA_COMPONENT, 4, alpha=0.20)
    for attr, valore in (("editmesh_active",
                          _hex_to_theme(MAYA_COMPONENT, 4, alpha=0.45)),):
        try:
            setattr(v3d, attr, valore)
        except Exception:
            pass
    if p.maya_edit_wire:
        try:
            v3d.wire_edit = _hex_to_theme(MAYA_EDIT_WIRE)
        except Exception:
            pass


def _theme_write_widgets(ui):
    """The interface half: Maya's blue on everything with a selected state."""
    blue = _hex_to_theme(MAYA_HIGHLIGHT, 4)
    white = (1.0, 1.0, 1.0)
    for name in HIGHLIGHT_WIDGETS:
        widget = getattr(ui, name, None)
        if widget is None:
            continue
        for attr, valore in (("inner_sel", blue), ("text_sel", white)):
            try:
                setattr(widget, attr, valore)
            except Exception:
                pass
    try:
        ui.wcol_numslider.item = blue
    except Exception:
        pass


def _theme_apply(context, theme, p):
    v3d, ui = theme.view_3d, theme.user_interface

    if p and not _theme_backup_read(p):
        if _theme_is_maya(v3d):
            # Nothing worth keeping: go back to Blender's own values first,
            # then snapshot those as the state to return to.
            _safe(bpy.ops.preferences.reset_default_theme)
            theme = context.preferences.themes[0]
            v3d, ui = theme.view_3d, theme.user_interface
        _theme_backup_write(p, _theme_snapshot(v3d, ui))

    try:
        _theme_write_viewport(v3d, p)
        if p is None or p.maya_highlight:
            _theme_write_widgets(ui)
    except Exception as err:
        return False, "Theme not writable: %s" % err

    try:
        context.scene.landfall_grid_finite = True
    except Exception:
        pass
    return True, "Maya colors applied"


class LANDFALL_OT_maya_theme(bpy.types.Operator):
    bl_idname = "landfall.maya_theme"
    bl_label = "Maya colors"
    bl_description = (
        "Set the viewport background and grid to Maya's. Selection colors and "
        "the interface highlight are optional, see the add-on preferences. "
        "The arrow next to it puts your previous theme back"
    )

    restore: bpy.props.BoolProperty(
        default=False, options={"HIDDEN", "SKIP_SAVE"}
    )

    def execute(self, context):
        try:
            theme = context.preferences.themes[0]
        except Exception:
            self.report({"WARNING"}, "Cannot reach the viewport theme")
            return {"CANCELLED"}

        p = prefs(context)
        if self.restore:
            esito, msg = _theme_restore(context, theme, p)
        else:
            esito, msg = _theme_apply(context, theme, p)

        if not esito:
            self.report({"WARNING"}, msg)
            return {"CANCELLED"}

        _safe(bpy.ops.wm.save_userpref)
        self.report({"INFO"}, msg)
        return {"FINISHED"}



class LANDFALL_OT_toggle_gizmos(bpy.types.Operator):
    bl_idname = "landfall.toggle_gizmos"
    bl_label = "Gizmos on/off"
    bl_description = "Show or hide the transform gizmos in the viewport"

    @classmethod
    def description(cls, context, properties):
        return _with_shortcut("Show or hide the transform gizmos",
                              "landfall.toggle_gizmos")

    def execute(self, context):
        spaces = _view3d_spaces(context)
        if not spaces:
            self.report({"WARNING"}, "No 3D viewport on this screen")
            return {"CANCELLED"}
        state = not spaces[0].show_gizmo
        for space in spaces:
            space.show_gizmo = state
        return {"FINISHED"}


class LANDFALL_OT_cheatsheet(bpy.types.Operator):
    bl_idname = "landfall.cheatsheet"
    bl_label = "Shortcuts"
    bl_description = "Open a floating shortcut sheet over the viewport"

    def invoke(self, context, event):
        if _sheet["running"]:
            _sheet_stop()
            self._redraw(context)
            return {"FINISHED"}

        area, region = _view3d_area(context)
        if area is None:
            self.report({"WARNING"}, "No 3D viewport on this screen")
            return {"CANCELLED"}

        _sheet["running"] = True
        _sheet["handle"] = bpy.types.SpaceView3D.draw_handler_add(
            _draw_sheet, (), "WINDOW", "POST_PIXEL"
        )
        with context.temp_override(area=area, region=region):
            context.window_manager.modal_handler_add(self)
        self._redraw(context)
        return {"RUNNING_MODAL"}

    def _redraw(self, context):
        _redraw_view3d(context)

    def modal(self, context, event):
        if not _sheet["running"]:
            return {"FINISHED"}

        mx, my = event.mouse_region_x, event.mouse_region_y

        if event.type == "MOUSEMOVE" and _sheet["drag"] is not None:
            ox, oy = _sheet["drag"]
            _sheet["x"] = mx - ox
            _sheet["y"] = my - oy
            self._redraw(context)
            return {"RUNNING_MODAL"}

        if event.type == "LEFTMOUSE" and event.value == "PRESS":
            close = _sheet["close"]
            if close is not None:
                cx, cy, cw, ch = close
                if cx - 4 <= mx <= cx + cw + 4 and cy - 4 <= my <= cy + ch + 4:
                    _sheet_stop()
                    self._redraw(context)
                    return {"FINISHED"}

            x, y, w, h = _sheet["x"], _sheet["y"], _sheet["w"], _sheet["h"]
            scale = context.preferences.system.ui_scale
            if x <= mx <= x + w and y + h - 26 * scale <= my <= y + h:
                _sheet["drag"] = (mx - x, my - y)
                return {"RUNNING_MODAL"}

        if event.type == "LEFTMOUSE" and event.value == "RELEASE":
            if _sheet["drag"] is not None:
                _sheet["drag"] = None
                return {"RUNNING_MODAL"}

        return {"PASS_THROUGH"}


# ------------------------------------------------------- component pie


class VIEW3D_MT_landfall_model_pie(bpy.types.Menu):
    """The modeling commands you reach for constantly, in one gesture.

    Maya's speed comes from marking menus more than from shelves: a pie is a
    direction, not a target to aim at.
    """
    bl_label = "Modeling"
    bl_idname = "VIEW3D_MT_landfall_model_pie"

    def draw(self, context):
        pie = self.layout.menu_pie()
        pie.operator("mesh.extrude_region_move", text="Extrude",
                     icon="FACESEL")
        pie.operator("mesh.bevel", text="Bevel", icon="MOD_BEVEL")
        pie.operator("mesh.loopcut_slide", text="Loop cut", icon="MOD_MULTIRES")
        pie.operator("mesh.inset", text="Inset", icon="MOD_SOLIDIFY")
        pie.operator("mesh.bridge_edge_loops", text="Bridge", icon="MOD_SIMPLIFY")
        pie.operator("landfall.merge_by_distance", text="Merge by distance",
                     icon="AUTOMERGE_ON")
        pie.operator("mesh.knife_tool", text="Knife", icon="MOD_LINEART")
        pie.operator("mesh.subdivide", text="Subdivide", icon="MESH_GRID")


class VIEW3D_MT_landfall_snap_pie(bpy.types.Menu):
    """Snap targets in one gesture, the closest thing to Maya's held X, C, V.

    Blender cannot switch snap target while a transform is running, so the pie
    sets the target and turns snapping on: press, flick, then move.
    """
    bl_label = "Snap"
    bl_idname = "VIEW3D_MT_landfall_snap_pie"

    def draw(self, context):
        pie = self.layout.menu_pie()
        for label, target, icon in (
            ("Vertex", "VERTEX", "SNAP_VERTEX"),
            ("Face", "FACE", "SNAP_FACE"),
            ("Grid", "INCREMENT", "SNAP_GRID"),
            ("Edge", "EDGE", "SNAP_EDGE"),
            ("Edge center", "EDGE_MIDPOINT", "SNAP_MIDPOINT"),
            ("Perpendicular", "EDGE_PERPENDICULAR", "SNAP_PERPENDICULAR"),
            ("Volume", "VOLUME", "SNAP_VOLUME"),
        ):
            pie.operator("landfall.set_snap", text=label, icon=icon).target = target
        pie.operator("landfall.set_snap", text="Snapping off",
                     icon="SNAP_OFF").target = "OFF"


class LANDFALL_OT_set_snap(bpy.types.Operator):
    bl_idname = "landfall.set_snap"
    bl_label = "Set snap target"
    bl_description = "Choose the snap target and turn snapping on"
    bl_options = {"REGISTER", "UNDO"}

    target: bpy.props.StringProperty(default="VERTEX", options={"SKIP_SAVE"})

    def execute(self, context):
        ts = context.scene.tool_settings
        if self.target == "OFF":
            ts.use_snap = False
            self.report({"INFO"}, "Snapping off")
            return {"FINISHED"}
        try:
            ts.snap_elements = {self.target}
        except Exception as err:
            self.report({"WARNING"}, "Snap target not available: %s" % err)
            return {"CANCELLED"}
        ts.use_snap = True
        self.report({"INFO"}, "Snap: %s" % self.target.replace("_", " ").lower())
        return {"FINISHED"}


# ------------------------------------- marking menu (Maya style)

MM_DIRS = ((-142, 0), (142, 0), (0, 96), (0, -96),
           (-106, -66), (106, -66), (-106, 66), (106, 66))

# Bottom of the ring is the south chip at 96 plus half its height; the list
# starts below that with a little air.
MM_LIST_TOP = 122

# Colors of the menu. The hover pair is deliberately louder than the branch
# accent: what a click is about to do has to be unmistakable.
MM_ACCENT = (0.16, 0.48, 0.61, 0.95)
HOT_FILL = (0.24, 0.68, 0.88, 1.0)
HOT_EDGE = (1.0, 1.0, 1.0, 0.55)


# Eight directions, in the order of MM_DIRS: west, east, south, north, then
# the four corners. The cardinal ones carry what you press all day, because a
# flick straight left or up is the one you hit without looking.
MM_RADIAL = {
    # Same shape in both modes: north is Display, north-east goes deeper into
    # the work, south-east is Snap, south leaves. The left column holds what
    # you are acting on — components here, paint modes in Object Mode — so a
    # flick left always lands in the same family.
    "EDIT_MESH": (
        ("Edge", "mesh.select_mode", {"type": "EDGE"}, None),
        ("Multi", "landfall.select_mode_multi", {}, None),
        ("Object mode", "object.mode_set", {"mode": "OBJECT"}, None),
        ("Display", None, None, "display"),
        ("Vertex", "mesh.select_mode", {"type": "VERT"}, None),
        ("Modeling", None, None, "model"),
        ("Face", "mesh.select_mode", {"type": "FACE"}, None),
        ("Snap", None, None, "snap"),
    ),
    # Right side is where you go to shape things — Edit next to Display, then
    # Sculpt, then Snap. The three paint modes take the whole left column, so
    # a flick left always lands among them.
    "OBJECT": (
        ("Texture paint", "object.mode_set", {"mode": "TEXTURE_PAINT"}, None),
        ("Sculpt", "object.mode_set", {"mode": "SCULPT"}, None),
        ("Frame selected", "landfall.frame_selected", {}, None),
        ("Display", None, None, "display"),
        ("Vertex paint", "object.mode_set", {"mode": "VERTEX_PAINT"}, None),
        ("Edit", "object.mode_set", {"mode": "EDIT"}, None),
        ("Weight paint", "object.mode_set", {"mode": "WEIGHT_PAINT"}, None),
        ("Snap", None, None, "snap"),
    ),
}

# The list beside the ring. Two of them are mode specific, because selection
# and pivots mean different things on objects and on components.
MM_LISTS = {
    "base_edit": (
        ("Select all", "mesh.select_all", {"action": "SELECT"}),
        ("Select none", "mesh.select_all", {"action": "DESELECT"}),
        ("Select inverse", "landfall.select_inverse", {}),
        ("Select border edges", "landfall.select_boundaries", {}),
        ("Grow selection", "mesh.select_more", {}),
        ("Shrink selection", "mesh.select_less", {}),
    ),
    "base_object": (
        ("Select all", "object.select_all", {"action": "SELECT"}),
        ("Select none", "object.select_all", {"action": "DESELECT"}),
        ("Select inverse", "landfall.select_inverse", {}),
        ("Select hierarchy", "object.select_grouped",
         {"type": "CHILDREN_RECURSIVE"}),
        ("Freeze transforms", "object.transform_apply", {}),
        ("Isolate", "landfall.isolate", {}),
    ),
    "model": (
        ("Extrude", "mesh.extrude_region_move", {}),
        ("Bevel", "mesh.bevel", {}),
        ("Loop cut", "mesh.loopcut_slide", {}),
        ("Inset", "mesh.inset", {}),
        ("Bridge", "mesh.bridge_edge_loops", {}),
        ("Knife", "mesh.knife_tool", {}),
        ("Subdivide", "mesh.subdivide", {}),
        ("Merge by distance", "landfall.merge_by_distance", {}),
        ("Merge at center", "landfall.merge_at_center", {}),
        ("Spin edge", "mesh.edge_rotate", {}),
        ("Detach", "landfall.detach_separate", {}),
        ("Grid fill", "mesh.fill_grid", {}),
    ),
    "snap": (
        ("Vertex", "landfall.set_snap", {"target": "VERTEX"}),
        ("Edge", "landfall.set_snap", {"target": "EDGE"}),
        ("Face", "landfall.set_snap", {"target": "FACE"}),
        ("Grid", "landfall.set_snap", {"target": "INCREMENT"}),
        ("Edge center", "landfall.set_snap", {"target": "EDGE_MIDPOINT"}),
        ("Perpendicular", "landfall.set_snap", {"target": "EDGE_PERPENDICULAR"}),
        ("Volume", "landfall.set_snap", {"target": "VOLUME"}),
        ("Snapping off", "landfall.set_snap", {"target": "OFF"}),
    ),
    "display": (
        ("X-ray", "landfall.toggle_xray_object", {}),
        ("Wire on shaded", "landfall.toggle_wireframe", {}),
        ("Isolate", "landfall.isolate", {}),
        ("Hide", "landfall.hide_selected", {}),
        ("Show selected", "landfall.show_selected", {}),
        ("Show all", "landfall.show_all", {}),
        ("Border edges", "landfall.toggle_scene_flag",
         {"prop": "landfall_border_show"}),
        ("Cage", "landfall.toggle_scene_flag", {"prop": "landfall_cage_show"}),
        ("Finite grid", "landfall.toggle_scene_flag",
         {"prop": "landfall_grid_finite"}),
        ("Gizmos", "landfall.toggle_gizmos", {}),
    ),
}


def _mm_mode(context):
    """Which set to show. Anything that is not mesh editing gets the object
    ring, so sculpt and the paint modes can still reach Display and Snap."""
    return "EDIT_MESH" if context.mode == "EDIT_MESH" else "OBJECT"


def _mm_base(context):
    return "base_edit" if _mm_mode(context) == "EDIT_MESH" else "base_object"


_mm = {"open": False, "handle": None, "x": 0.0, "y": 0.0,
       "area": None, "region": None,
       "list": "base_object", "anchor": None, "hot": None, "rects": [],
       "layout": None, "hot_key": "?", "hot_ring": None, "hot_rect": None}


def _mm_reopen(x, y, area, region):
    """Bring the menu straight back at the same spot.

    Entering Edit Mode is nearly always followed by picking a component, so
    the second menu is offered without asking for the shortcut again. The
    position is handed over through _mm because a timer has no event to read
    the mouse from.
    """
    def go():
        _mm["pending"] = (x, y)
        try:
            with bpy.context.temp_override(area=area, region=region):
                bpy.ops.landfall.marking_menu("INVOKE_DEFAULT")
        except Exception as err:
            _mm["pending"] = None
            print("[landfall] reopen failed: %s" % err)
        return None
    bpy.app.timers.register(go, first_interval=0.02)


def _mm_wants_reopen(path, props):
    p = prefs(bpy.context)
    if p is None or not p.chain_after_edit:
        return False
    return path == "object.mode_set" and props.get("mode") == "EDIT"


def _mm_run(path, props, area=None, region=None, x=0.0, y=0.0):
    """Run the chosen command after the menu has closed.

    Two things matter here. Extrude, bevel and knife are modal themselves, and
    starting one from inside another modal does not work, so the call is
    deferred by a tick. And a timer has no viewport in its context: without
    the override, anything that needs one — framing the selection, the view
    commands — either fails or acts on the wrong area.
    """
    def run():
        try:
            module, name = path.split(".", 1)
            op = getattr(getattr(bpy.ops, module), name)
            if area is not None and region is not None:
                with bpy.context.temp_override(area=area, region=region):
                    op("INVOKE_DEFAULT", **props)
            else:
                op("INVOKE_DEFAULT", **props)
            if _mm_wants_reopen(path, props):
                _mm_reopen(x, y, area, region)
        except Exception as err:
            print("[landfall] %s failed: %s" % (path, err))
        return None
    bpy.app.timers.register(run, first_interval=0.01)


def _rects_batch(rects):
    """One GPU buffer for many rectangles instead of one buffer each.

    _rect allocates a vertex buffer per call, and at a dozen calls per redraw
    that is most of the cost of drawing the menu. Everything that does not
    move is batched once, when the layout is built.
    """
    verts, tris = [], []
    for x, y, w, h in rects:
        n = len(verts)
        verts.extend(((x, y), (x + w, y), (x + w, y + h), (x, y + h)))
        tris.extend(((n, n + 1, n + 2), (n, n + 2, n + 3)))
    if not verts:
        return None
    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    return batch_for_shader(shader, "TRIS", {"pos": verts}, indices=tris)


def _mm_layout(context):
    """Work out where everything goes, once.

    The menu does not move while it is open, so the geometry is computed when
    it opens and whenever the list changes, not on every redraw. Only the
    highlight follows the mouse.
    """
    font = 0
    scale = context.preferences.system.ui_scale
    size = 12 * scale
    pad_x, pad_y, row_h = 9 * scale, 5 * scale, 21 * scale
    cx, cy = _mm["x"], _mm["y"]

    chips = []
    radial = MM_RADIAL[_mm_mode(context)]
    for index, (label, path, props, branch) in enumerate(radial):
        dx, dy = MM_DIRS[index]
        w = _text_w(font, size, label) + pad_x * 2
        x, y = cx + dx * scale, cy - dy * scale
        chips.append({"key": ("radial", index), "label": label,
                      "branch": bool(branch), "branch_name": branch,
                      "open": branch is not None and branch == _mm["list"],
                      "x": x - w * 0.5, "y": y - row_h * 0.5,
                      "w": w, "h": row_h})

    # The stored key can be stale — it survives a reload, and the base list
    # is named per mode — so it is checked before use rather than trusted.
    if _mm["list"] not in MM_LISTS:
        _mm["list"] = _mm_base(context)
    items = MM_LISTS[_mm["list"]]
    two = len(items) > 7
    half = (len(items) + 1) // 2 if two else len(items)
    border, gap = 4 * scale, 6 * scale
    col_w = max(_text_w(font, size, t) for t, _p, _k in items) + pad_x * 2
    total_w = border * 2 + col_w * (2 if two else 1) + (gap if two else 0)
    total_h = border * 2 + half * row_h

    # The list opens right under the branch you clicked, and is drawn over
    # the ring rather than under it, so overlapping never turns into a
    # tangle of overlapping labels.
    ax, ay = _mm["anchor"] if _mm["anchor"] else (cx, cy - MM_LIST_TOP * scale)
    left, top = ax - total_w * 0.5, ay

    rows = []
    for index, (label, path, props) in enumerate(items):
        column = 1 if (two and index >= half) else 0
        row = index - half if column else index
        rows.append({"key": ("list", index), "label": label,
                     "x": left + border + column * (col_w + gap),
                     "y": top - border - (row + 1) * row_h,
                     "w": col_w, "h": row_h})

    _mm["layout"] = {
        "font": font, "size": size, "pad_x": pad_x, "pad_y": pad_y,
        "scale": scale, "chips": chips, "rows": rows,
        "panel": (left, top - total_h, total_w, total_h),
        "divider": (left + border + col_w + gap * 0.5 - max(0.5, scale * 0.5),
                    top - total_h + border, max(1.0, scale),
                    total_h - border * 2) if two else None,
    }
    _mm["rects"] = (
        [(c["key"], c["x"], c["y"], c["w"], c["h"]) for c in chips]
        + [(r["key"], r["x"], r["y"], r["w"], r["h"]) for r in rows])

    lay = _mm["layout"]
    plain = [(c["x"], c["y"], c["w"], c["h"]) for c in chips if not c["branch"]]
    branchy = [(c["x"], c["y"], c["w"], c["h"]) for c in chips
               if c["branch"] and not c["open"]]
    opened = [(c["x"], c["y"], c["w"], c["h"]) for c in chips if c["open"]]
    # A thin white bar under the branch whose list is showing, so you can tell
    # where you are when the panel covers half the ring.
    marks = [(c["x"], c["y"] - 3 * scale, c["w"], 2 * scale)
             for c in chips if c["open"]]
    px, py, pw, ph = lay["panel"]
    edge = max(1.0, scale)
    lay["batch_plain"] = _rects_batch(plain)
    lay["batch_branch"] = _rects_batch(branchy)
    lay["batch_open"] = _rects_batch(opened)
    lay["batch_mark"] = _rects_batch(marks)
    lay["batch_border"] = _rects_batch(
        [(px - edge, py - edge, pw + edge * 2, ph + edge * 2)])
    lay["batch_panel"] = _rects_batch([(px, py, pw, ph)])
    lay["batch_divider"] = _rects_batch(
        [lay["divider"]]) if lay["divider"] else None
    lay["theme"] = _sheet_theme(context)


def _mm_draw():
    if not _mm["open"]:
        return
    context = bpy.context
    if getattr(context, "region", None) is None:
        return
    if _mm.get("layout") is None:
        _mm_layout(context)
        _mm["hot_key"] = "?"

    lay = _mm["layout"]
    font, size = lay["font"], lay["size"]
    pad_x, pad_y, scale = lay["pad_x"], lay["pad_y"], lay["scale"]
    back, text_col = lay["theme"]
    accent = MM_ACCENT
    muted = (text_col[0], text_col[1], text_col[2], 0.55)
    hot = _mm["hot"]

    gpu.state.blend_set("ALPHA")
    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    shader.bind()

    def paint(batch, color):
        if batch is not None:
            shader.uniform_float("color", color)
            batch.draw(shader)

    # The item under the pointer gets a brighter fill than the branch chips
    # and a light outline around it, so what a click would do is unmistakable.
    #
    # The two buffers are built only when the pointer moves to a different
    # item, not on every redraw, and the item is found once at that moment
    # rather than searched for each frame.
    if _mm.get("hot_key") != hot:
        _mm["hot_key"] = hot
        _mm["hot_ring"] = _mm["hot_rect"] = None
        if hot is not None:
            for item in lay["chips"] + lay["rows"]:
                if item["key"] == hot:
                    x, y, w, h = item["x"], item["y"], item["w"], item["h"]
                    g = max(2.0, 2 * scale)
                    _mm["hot_ring"] = _rects_batch(
                        [(x - g, y - g, w + g * 2, h + g * 2)])
                    _mm["hot_rect"] = _rects_batch([(x, y, w, h)])
                    break
    hot_ring, hot_rect = _mm["hot_ring"], _mm["hot_rect"]

    # The ring first, the list over it: the other way round the ring labels
    # showed through the panel where the two crossed.
    paint(lay["batch_plain"], back)
    paint(lay["batch_branch"], accent)
    # The branch you have open is brighter, so you can tell where you are
    # even when the panel covers half the ring. It used to be painted twice
    # with two colors, the second over the first.
    paint(lay["batch_open"], (0.28, 0.66, 0.80, 1.0))
    paint(lay["batch_mark"], (1.0, 1.0, 1.0, 0.85))
    if hot_rect is not None and hot[0] == "radial":
        paint(hot_ring, HOT_EDGE)
        paint(hot_rect, HOT_FILL)

    blf.size(font, size)
    # Two color changes instead of one per label: everything ordinary first,
    # then the highlighted ones.
    blf.color(font, *text_col)
    for chip in lay["chips"]:
        if chip["branch"] or hot == chip["key"]:
            continue
        blf.position(font, chip["x"] + pad_x, chip["y"] + pad_y + scale, 0)
        blf.draw(font, chip["label"])
    blf.color(font, 1, 1, 1, 1)
    for chip in lay["chips"]:
        if not (chip["branch"] or hot == chip["key"]):
            continue
        blf.position(font, chip["x"] + pad_x, chip["y"] + pad_y + scale, 0)
        blf.draw(font, chip["label"])

    paint(lay["batch_border"], (text_col[0], text_col[1], text_col[2], 0.35))
    paint(lay["batch_panel"], (back[0], back[1], back[2], 1.0))
    paint(lay["batch_divider"], muted)
    if hot_rect is not None and hot[0] == "list":
        paint(hot_ring, HOT_EDGE)
        paint(hot_rect, HOT_FILL)

    blf.color(font, *text_col)
    for row in lay["rows"]:
        if hot == row["key"]:
            continue
        blf.position(font, row["x"] + pad_x, row["y"] + pad_y + scale, 0)
        blf.draw(font, row["label"])
    for row in lay["rows"]:
        if hot == row["key"]:
            blf.color(font, 1, 1, 1, 1)
            blf.position(font, row["x"] + pad_x, row["y"] + pad_y + scale, 0)
            blf.draw(font, row["label"])
            break

    gpu.state.blend_set("NONE")


def _mm_hit(mx, my):
    for key, x, y, w, h in _mm["rects"]:
        if x <= mx <= x + w and y <= my <= y + h:
            return key
    return None


def _mm_stop():
    if _mm["handle"] is not None:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(_mm["handle"], "WINDOW")
        except Exception:
            pass
    _mm["handle"] = None
    _mm["open"] = False
    _mm["rects"] = []
    _mm["hot"] = None


class LANDFALL_OT_self_check(bpy.types.Operator):
    bl_idname = "landfall.self_check"
    bl_label = "Self check"
    bl_description = (
        "Run Landfall's own checks and write the result to a text block. "
        "Covers the data and the geometry; the drawing and the mouse are the "
        "one part no script can verify"
    )

    def execute(self, context):
        # Not bl_info: Blender strips it from the module once the extension
        # is loaded, so it only exists while the file is being imported.
        lines = [VERSION_TEXT,
                 "Blender %s" % bpy.app.version_string, ""]
        bad = 0

        def check(ok, message):
            nonlocal bad
            if not ok:
                bad += 1
                lines.append("FAIL  %s" % message)

        # every command in the menus must resolve to a real operator
        entries = [(v[0], v[1]) for r in MM_RADIAL.values() for v in r if v[1]]
        entries += [(v[0], v[1]) for l in MM_LISTS.values() for v in l]
        for label, path in entries:
            module, _, name = path.partition(".")
            check(hasattr(getattr(bpy.ops, module, None), name),
                  "%s points at a missing operator: %s" % (label, path))
        lines.append("commands checked: %d" % len(entries))

        # eight directions, eight entries in every ring
        check(len(MM_DIRS) == 8, "MM_DIRS is not eight directions")
        for mode, ring in MM_RADIAL.items():
            check(len(ring) == 8, "%s ring has %d entries" % (mode, len(ring)))

        # every branch must name a list that exists
        for mode, ring in MM_RADIAL.items():
            for label, _p, _pr, branch in ring:
                if branch:
                    check(branch in MM_LISTS,
                          "%s: branch %s has no list" % (label, branch))

        # the highlight must never fall outside the panel
        _mm_layout(context)
        lay = _mm["layout"]
        px, py, pw, ph = lay["panel"]
        for row in lay["rows"]:
            check(row["x"] >= px - 0.01 and row["x"] + row["w"] <= px + pw + 0.01,
                  "row %s sticks out sideways" % row["label"])
            check(row["y"] >= py - 0.01 and row["y"] + row["h"] <= py + ph + 0.01,
                  "row %s sticks out vertically" % row["label"])
        lines.append("rows checked: %d" % len(lay["rows"]))
        _mm["layout"] = None

        # handlers balanced
        check(len(bpy.app.handlers.depsgraph_update_post) < 40,
              "too many depsgraph handlers, something is registering twice")

        # Truncated user keymaps: the same survey the startup repair uses,
        # so the two can never disagree about what counts as broken.
        for km, native, expected in _keymap_survey():
            bad += 1
            lines.append(
                "FAIL  the user keymap '%s' holds %d of %d stock shortcuts "
                "and hides the rest. Restart Blender to have it rebuilt, or "
                "press Restore on that entry in Preferences > Keymap"
                % (km.name, native, expected))

        # Every keymap name we write into must exist in Blender's own
        # configuration: keymaps.new() creates a missing one silently, and
        # the entries in it never fire. "Grease Pencil Stroke Edit Mode"
        # was such a ghost after the keymap was renamed.
        kc = context.window_manager.keyconfigs
        stock = {km.name for km in kc.default.keymaps} if kc.default else set()
        wanted = {name for name, _s in NAV_MODE_KEYMAPS}
        wanted |= {row[0] for row in MAYA_NAV_EXTRA}
        wanted |= {name for name, _s in KEYMAP_TARGETS} | {"Window", "Curve"}
        for name in sorted(wanted - stock):
            check(False, "keymap '%s' does not exist in this Blender" % name)

        # Our shortcuts that sit on top of one of Blender's own, in the same
        # keymap. The ones listed in SHADOWS_INTENDED are replacements made
        # on purpose and documented; anything else is worth knowing about.
        notes = []
        if kc.addon and kc.default:
            for km in kc.addon.keymaps:
                dkm = kc.default.keymaps.get(km.name)
                if dkm is None:
                    continue
                for k in km.keymap_items:
                    if not (_keymap_is_ours(k) or k.idname in NAV_IDNAMES):
                        continue
                    for d in dkm.keymap_items:
                        if d.active and _kmi_signature(d) == _kmi_signature(k):
                            pair = (km.name, k.type, bool(k.ctrl),
                                    bool(k.alt), bool(k.shift))
                            if pair not in SHADOWS_INTENDED and not (
                                    k.alt and k.type.endswith("MOUSE")):
                                notes.append("NOTE  %s: our %s on %s hides "
                                             "Blender's %s" % (km.name, k.idname,
                                                                k.to_string(),
                                                                d.idname))
        lines.extend(notes)

        lines.insert(2, "RESULT: %s" % ("all passed" if not bad
                                        else "%d problems" % bad))
        block = bpy.data.texts.get("landfall_self_check")
        if block is None:
            block = bpy.data.texts.new("landfall_self_check")
        block.clear()
        block.write("\n".join(lines))

        self.report({"INFO" if not bad else "WARNING"},
                    "Self check: %s" % ("all passed" if not bad
                                        else "%d problems, see the text block" % bad))
        return {"FINISHED"}


class LANDFALL_OT_frame_selected(bpy.types.Operator):
    bl_idname = "landfall.frame_selected"
    bl_label = "Frame selected"
    bl_description = (
        "Frame the selection with a little room around it. Blender's own "
        "framing fits the bounding box exactly, which in perspective clips "
        "the sides of the shape"
    )

    def execute(self, context):
        area, region = _view3d_area(context)
        if area is None:
            self.report({"WARNING"}, "No 3D viewport")
            return {"CANCELLED"}
        try:
            with context.temp_override(area=area, region=region):
                bpy.ops.view3d.view_selected()
                bpy.ops.view3d.zoom(delta=-1)
        except Exception as err:
            self.report({"WARNING"}, "Could not frame: %s" % err)
            return {"CANCELLED"}
        return {"FINISHED"}


class LANDFALL_OT_extrude_options(bpy.types.Operator):
    """Extrude with Maya's parameters, all adjustable afterwards.

    Blender's own extrude carries a direction and a distance, so the panel it
    offers has nothing else to show. Maya's polyExtrudeFace node carries
    thickness, offset, divisions, twist, taper and keep-faces-together, and
    those are what the hand reaches for.

    Declaring them as operator properties is what makes them adjustable: the
    bar at the bottom left, and F9 under the cursor, are drawn by Blender from
    the properties and re-run the operator on every change. No panel of ours,
    no sliders of ours — Blender's own machinery, which already knows how to
    restore the mesh before each re-run.

    What it cannot do is come back later. Once another operation follows, the
    values are frozen: Blender has no construction history to return to, and
    nothing in an add-on can supply one.
    """
    bl_idname = "landfall.extrude_options"
    bl_label = "Extrude with options"
    bl_description = (
        "Extrude the selected faces with thickness, offset, divisions, twist "
        "and taper. Press F9 afterwards to adjust them"
    )
    bl_options = {"REGISTER", "UNDO"}

    # SKIP_SAVE su tutti: Blender ricorda i valori dell'ultima esecuzione e
    # li ripropone alla successiva, quindi una seconda estrusione ripartiva
    # con le divisioni e il taper della prima. Maya azzera ogni volta, e cosi'
    # facciamo noi.
    thickness: bpy.props.FloatProperty(
        name="Thickness", description="Distance along the face normal",
        default=0.0, unit="LENGTH", options={"SKIP_SAVE"})
    offset: bpy.props.FloatProperty(
        name="Offset", description="Inset the face before extruding, as Maya's "
        "Offset does", default=0.0, unit="LENGTH", options={"SKIP_SAVE"})
    divisions: bpy.props.IntProperty(
        name="Divisions", description="How many segments along the extrusion",
        default=1, min=1, soft_max=20, options={"SKIP_SAVE"})
    keep_together: bpy.props.BoolProperty(
        name="Keep Faces Together",
        description="Extrude the selection as one region. Off extrudes every "
        "face on its own, each along its own normal",
        default=True, options={"SKIP_SAVE"})
    twist: bpy.props.FloatProperty(
        name="Twist", description="Rotation around the extrusion axis, spread "
        "over the divisions", default=0.0, subtype="ANGLE", options={"SKIP_SAVE"})
    taper: bpy.props.FloatProperty(
        name="Taper", description="Scale of the far end. 1 keeps the size, "
        "below 1 narrows it", default=1.0, min=0.0, soft_max=3.0, options={"SKIP_SAVE"})

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj is not None and obj.type == "MESH"
                and context.mode == "EDIT_MESH")

    def execute(self, context):
        obj = context.active_object
        bm = bmesh.from_edit_mesh(obj.data)
        facce = [f for f in bm.faces if f.select]
        if not facce:
            self.report({"WARNING"}, "Select at least one face")
            return {"CANCELLED"}

        try:
            if self.offset:
                bmesh.ops.inset_region(
                    bm, faces=facce, thickness=abs(self.offset),
                    depth=0.0, use_even_offset=True, use_boundary=True)
                facce = [f for f in bm.faces if f.select]

            # I cappelli si raccolgono e si selezionano una volta sola alla
            # fine: selezionandoli dentro il ciclo, ogni faccia azzerava la
            # selezione della precedente e con Keep Faces Together spento ne
            # restava selezionata una sola invece di tutte.
            cappelli = []
            if self.keep_together:
                cappelli += self._estrudi(bm, facce)
            else:
                for f in list(facce):
                    cappelli += self._estrudi(bm, [f])

            for f in bm.faces:
                f.select_set(False)
            for f in cappelli:
                if f.is_valid:
                    f.select_set(True)
            bm.select_flush(True)
        except Exception as err:
            # A failure here leaves the mesh half-built, and the caller has no
            # way to know. Say so instead of reporting success — and push the
            # bmesh back anyway, or the viewport shows a mesh that no longer
            # matches the data until the next edit.
            bmesh.update_edit_mesh(obj.data, loop_triangles=True,
                                   destructive=True)
            self.report({"ERROR"}, "Extrude failed: %s" % err)
            return {"CANCELLED"}

        bmesh.update_edit_mesh(obj.data, loop_triangles=True, destructive=True)
        return {"FINISHED"}

    def _estrudi(self, bm, facce):
        """One extrusion, divided into the requested number of segments.

        Each segment moves by its share of the thickness and takes its share
        of the twist and the taper, so the parameters describe the whole
        extrusion rather than each step. Returns the faces at the far end, for
        the caller to select once every extrusion is done.
        """
        passi = max(1, self.divisions)
        normale_grezza = mathutils.Vector((0.0, 0.0, 0.0))
        for f in facce:
            normale_grezza += f.normal * f.calc_area()
        normale = mathutils.Vector(normale_grezza)
        if normale.length < 1e-9:
            normale = mathutils.Vector(facce[0].normal)
        normale.normalize()

        # The averaged normal survives only as the twist axis and as a
        # fallback: on a closed surface it cancels out, and rotating around a
        # vector that does not exist means nothing.
        asse_valido = normale_grezza.length > 1e-9

        salto = self.thickness / passi
        giro = self.twist / passi if asse_valido else 0.0
        # Per-step scale whose product over the steps is exactly the taper.
        scala = self.taper ** (1.0 / passi) if self.taper > 0 else 0.0
        correnti = list(facce)

        for _ in range(passi):
            # Directions are worked out from the faces about to be extruded,
            # not from the caps recognised afterwards.
            #
            # Recognising them afterwards as "faces made only of new vertices"
            # looked right, but on the caps of a cylinder the side walls are
            # also made only of new vertices: a probe inside the running code
            # showed a vertex touching three faces, the cap and two radial
            # walls, and the direction came out tilted by forty-five degrees.
            #
            # Each vertex moves along the average of the normals of the
            # selected faces it belongs to, divided by the average cosine
            # between that direction and those normals. Without the division
            # the faces do not end up the requested distance apart: on a cube
            # with every face selected and a thickness of 0.5 the growth was
            # 0.289, which is 0.5 over the square root of three. On a flat
            # face the cosine is one and nothing changes.
            direzioni = {}
            if salto:
                insieme_correnti = set(correnti)
                for f in correnti:
                    for v in f.verts:
                        chiave = tuple(round(c, 5) for c in v.co)
                        if chiave in direzioni:
                            continue
                        vicine = [g for g in v.link_faces
                                  if g in insieme_correnti]
                        direzione = mathutils.Vector((0.0, 0.0, 0.0))
                        for g in vicine:
                            direzione += g.normal * g.calc_area()
                        if direzione.length < 1e-9:
                            direzione = mathutils.Vector(normale)
                        direzione.normalize()
                        fattore = 1.0
                        if vicine:
                            coseno = sum(direzione.dot(g.normal)
                                         for g in vicine) / len(vicine)
                            if coseno > 0.05:
                                fattore = 1.0 / coseno
                        direzioni[chiave] = direzione * (salto * fattore)

            ret = bmesh.ops.extrude_face_region(bm, geom=correnti)
            nuovi = [g for g in ret["geom"]
                     if isinstance(g, bmesh.types.BMVert)]
            insieme = set(nuovi)
            cappello = [g for g in ret["geom"]
                        if isinstance(g, bmesh.types.BMFace)
                        and all(v in insieme for v in g.verts)]
            if not cappello:
                break

            # The face we extruded from stays where it was and becomes an
            # internal diaphragm: one extrusion gave eleven faces instead of
            # ten and four non-manifold edges, and every division added more.
            #
            # The context is FACES rather than FACES_ONLY: the first also
            # takes away vertices and edges left without any face, the second
            # leaves them. Extruding the whole closed surface of a sphere
            # creates no side walls, so the original shell stayed inside as
            # forty-two loose vertices and a hundred and twenty loose edges.
            vecchie = [f for f in correnti if f.is_valid]
            if vecchie:
                bmesh.ops.delete(bm, geom=vecchie, context="FACES")

            # Straight after the extrusion the new vertices sit exactly on top
            # of the originals, so the directions worked out before are found
            # again by coordinate.
            if salto:
                for v in nuovi:
                    delta = direzioni.get(tuple(round(c, 5) for c in v.co))
                    if delta is not None:
                        v.co += delta

            centro = mathutils.Vector((0.0, 0.0, 0.0))
            for v in nuovi:
                centro += v.co
            centro /= len(nuovi)

            if abs(scala - 1.0) > 1e-9:
                bmesh.ops.scale(
                    bm, verts=nuovi, vec=(scala, scala, scala),
                    space=mathutils.Matrix.Translation(-centro))
            if abs(giro) > 1e-9:
                bmesh.ops.rotate(
                    bm, verts=nuovi, cent=centro,
                    matrix=mathutils.Matrix.Rotation(giro, 3, normale))

            correnti = cappello

        return correnti


class LANDFALL_OT_extrude_move(bpy.types.Macro):
    """Our extrude chained to Blender's own move, the way E already works.

    Blender's E is not a single operator but a macro: extrude, then translate.
    That is why its adjust panel shows Move X, Y and Z. Building the same
    thing with our extrude in front means the panel lists our six parameters
    and the move together, and it appears in the bottom left corner, where it
    does not sit over the geometry.

    Two things come for free this way rather than with a popup of our own: the
    drag that sets the distance is Blender's, already familiar and already
    right, and the panel is drawn and re-run by Blender.
    """
    bl_idname = "landfall.extrude_move"
    bl_label = "Extrude with options and move"
    bl_options = {"REGISTER", "UNDO"}


def _define_macro():
    """A macro's steps can only be defined once the classes they name are
    registered, so this runs after register_class, not at import time."""
    try:
        LANDFALL_OT_extrude_move.define("LANDFALL_OT_extrude_options")
        passo = LANDFALL_OT_extrude_move.define("TRANSFORM_OT_translate")
        passo.properties.orient_type = "NORMAL"
        passo.properties.constraint_axis = (False, False, True)
        # No release_confirm. With it the move confirmed as soon as E was
        # released, so a normal tap of E extruded at distance zero and the
        # mouse never got to set it. Blender's own E does not set it either:
        # press E, move, click or Enter.
    except Exception as err:
        print("[landfall] could not build the extrude macro: %s" % err)


def _remove_kmis(items):
    """Take our entries out of the add-on keymaps and forget them."""
    for km, kmi in items:
        try:
            km.keymap_items.remove(kmi)
        except Exception:
            pass
    items.clear()


_extrude_keymaps = []

NATIVE_EXTRUDE = "view3d.edit_mesh_extrude_move_normal"


def _user_keymap(name):
    try:
        return bpy.context.window_manager.keyconfigs.user.keymaps.get(name)
    except Exception:
        return None


def _set_native_extrude(active):
    """Blender's own E in the Mesh keymap, muted or back on.

    One place for it: the enable path and the post-rebuild path used to carry
    the same five-line filter each, and two copies of a filter drift apart.
    """
    km = _user_keymap("Mesh")
    if km is None:
        return
    for k in km.keymap_items:
        if (k.idname == NATIVE_EXTRUDE and k.type == "E"
                and not (k.ctrl or k.alt or k.shift or k.oskey)):
            k.active = active


def _set_native_loop_select(active):
    """Blender's Alt+click loop and ring select, muted or back on.

    Only the click entries on Alt: the double-click ones in the same keymap
    are ours, mirrored there by Blender, and muting by idname alone took
    them down with the rest. That is how loop select on double click ended
    up silently off — and stayed off, because the user keymap is saved.
    """
    for name, idname in MAYA_NAV_MUTE:
        km = _user_keymap(name)
        if km is None:
            continue
        for k in km.keymap_items:
            if (k.idname == idname and k.type == "LEFTMOUSE"
                    and k.value != "DOUBLE_CLICK" and k.alt):
                k.active = active


def _extrude_enable(context):
    """Put our extrude on E and quiet Blender's own.

    Blender's entry is muted, not removed: switching the preference off brings
    it back, and nothing of Blender's is lost.
    """
    kc = context.window_manager.keyconfigs.addon
    if kc is None:
        return
    _set_native_extrude(False)
    try:
        km = kc.keymaps.new(name="Mesh", space_type="EMPTY")
        kmi = km.keymap_items.new("landfall.extrude_move", "E", "PRESS")
        _extrude_keymaps.append((km, kmi))
    except Exception:
        pass
    _wake_user_kmi("landfall.extrude_move")


def _extrude_disable():
    _remove_kmis(_extrude_keymaps)
    _set_native_extrude(True)


def _extrude_update(self, context):
    _extrude_disable()
    if self.maya_extrude:
        _extrude_enable(context)


class LANDFALL_OT_toggle_scene_flag(bpy.types.Operator):
    bl_idname = "landfall.toggle_scene_flag"
    bl_label = "Toggle"
    bl_description = "Flip one of Landfall's scene switches"
    bl_options = {"REGISTER", "UNDO"}

    # Enum e non testo libero: Blender rifiuta un valore sbagliato alla
    # chiamata, invece che l'operatore scoprirlo a meta' e riportare
    # "Unknown switch" a cose fatte.
    prop: bpy.props.EnumProperty(
        items=[("landfall_border_show", "Border edges", ""),
               ("landfall_cage_show", "Cage", ""),
               ("landfall_grid_finite", "Finite grid", "")],
        default="landfall_border_show",
        options={"SKIP_SAVE"},
    )

    def execute(self, context):
        if not hasattr(context.scene, self.prop):
            self.report({"WARNING"}, "%s is not available" % self.prop)
            return {"CANCELLED"}
        setattr(context.scene, self.prop, not getattr(context.scene, self.prop))
        return {"FINISHED"}


class LANDFALL_OT_marking_menu(bpy.types.Operator):
    bl_idname = "landfall.marking_menu"
    bl_label = "Marking menu"
    bl_description = (
        "Maya-style marking menu: the radial ring and the list are shown at "
        "the same time, and choosing a branch never hides the ring"
    )

    def invoke(self, context, event):
        if _mm["open"]:
            _mm_stop()
            return {"CANCELLED"}
        if context.area is None or context.area.type != "VIEW_3D":
            self.report({"WARNING"}, "Open it over a 3D viewport")
            return {"CANCELLED"}

        _mm["area"] = context.area
        _mm["region"] = context.region
        pending = _mm.pop("pending", None)
        px, py = pending if pending else (event.mouse_region_x,
                                          event.mouse_region_y)
        _mm.update({"open": True, "x": px, "y": py, "list": _mm_base(context),
                    "anchor": None, "hot": None, "rects": [],
                    "layout": None})
        _mm["handle"] = bpy.types.SpaceView3D.draw_handler_add(
            _mm_draw, (), "WINDOW", "POST_PIXEL")
        context.window_manager.modal_handler_add(self)
        context.area.tag_redraw()
        return {"RUNNING_MODAL"}

    def _close(self, context):
        _mm_stop()
        if context.area:
            context.area.tag_redraw()

    def modal(self, context, event):
        if not _mm["open"]:
            return {"FINISHED"}

        if event.type == "MOUSEMOVE":
            hot = _mm_hit(event.mouse_region_x, event.mouse_region_y)
            if hot != _mm["hot"]:
                _mm["hot"] = hot
                if context.area:
                    context.area.tag_redraw()
            return {"RUNNING_MODAL"}

        if event.type == "ESC" and event.value == "PRESS":
            self._close(context)
            return {"CANCELLED"}

        if event.type == "RIGHTMOUSE" and event.value == "PRESS":
            # Same two stages as clicking outside: fold the branch first,
            # leave only if there is nothing left to fold.
            if _mm["list"] != _mm_base(context):
                _mm["list"] = _mm_base(context)
                _mm["anchor"] = None
                _mm["layout"] = None
                if context.area:
                    context.area.tag_redraw()
                return {"RUNNING_MODAL"}
            self._close(context)
            return {"CANCELLED"}

        if event.type == "LEFTMOUSE" and event.value == "PRESS":
            hit = _mm_hit(event.mouse_region_x, event.mouse_region_y)

            if hit is None:
                # First click outside steps back to the base list, the second
                # closes: the ring stays put while you look around.
                if _mm["list"] != _mm_base(context):
                    _mm["list"] = _mm_base(context)
                    _mm["anchor"] = None
                    _mm["layout"] = None
                    if context.area:
                        context.area.tag_redraw()
                    return {"RUNNING_MODAL"}
                self._close(context)
                return {"CANCELLED"}

            kind, index = hit
            if kind == "radial":
                label, path, props, branch = MM_RADIAL[_mm_mode(context)][index]
                if branch and _mm["list"] == branch:
                    # Clicking the open branch again folds it back, so the
                    # same flick both opens and closes.
                    _mm["list"] = _mm_base(context)
                    _mm["anchor"] = None
                    _mm["layout"] = None
                    if context.area:
                        context.area.tag_redraw()
                    return {"RUNNING_MODAL"}
                if branch:
                    scale = context.preferences.system.ui_scale
                    dx, dy = MM_DIRS[index]
                    _mm["list"] = branch
                    _mm["anchor"] = (_mm["x"] + dx * scale,
                                     _mm["y"] - dy * scale - 14 * scale)
                    _mm["layout"] = None
                    if context.area:
                        context.area.tag_redraw()
                    return {"RUNNING_MODAL"}
                area, region = _mm["area"], _mm["region"]
                mx, my = _mm["x"], _mm["y"]
                self._close(context)
                _mm_run(path, props, area, region, mx, my)
                return {"FINISHED"}

            label, path, props = MM_LISTS[_mm["list"]][index]
            area, region = _mm["area"], _mm["region"]
            mx, my = _mm["x"], _mm["y"]
            self._close(context)
            _mm_run(path, props, area, region, mx, my)
            return {"FINISHED"}

        return {"RUNNING_MODAL"}


class LANDFALL_OT_select_mode_multi(bpy.types.Operator):
    bl_idname = "landfall.select_mode_multi"
    bl_label = "Multi"
    bl_description = "Vertex, edge and face selection at the same time"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.mode == "EDIT_MESH"

    def execute(self, context):
        context.tool_settings.mesh_select_mode = (True, True, True)
        return {"FINISHED"}


# ------------------------------------------------------- Maya navigation

# Navigation has to be registered in every mode keymap: in Sculpt and the
# paint modes the brush grabs the mouse buttons before the general 3D View
# keymap is ever reached.
NAV_MODE_KEYMAPS = (
    ("3D View", "VIEW_3D"),
    ("Object Mode", "EMPTY"),
    ("Mesh", "EMPTY"),
    ("Curve", "EMPTY"),
    ("Armature", "EMPTY"),
    ("Lattice", "EMPTY"),
    ("Metaball", "EMPTY"),
    ("Sculpt", "EMPTY"),
    ("Vertex Paint", "EMPTY"),
    ("Weight Paint", "EMPTY"),
    ("Image Paint", "EMPTY"),
    ("Pose", "EMPTY"),
    ("Particle", "EMPTY"),
    ("Grease Pencil Edit Mode", "EMPTY"),
)

NAV_ITEMS = (
    ("view3d.rotate", "LEFTMOUSE", {"alt": True}),
    ("view3d.move", "MIDDLEMOUSE", {"alt": True}),
    ("view3d.zoom", "RIGHTMOUSE", {"alt": True}),
)

# Extra entries that only make sense in one place.
MAYA_NAV_EXTRA = (
    ("Mesh", "EMPTY", "mesh.loop_select", "LEFTMOUSE", {}, "DOUBLE_CLICK"),
    ("Mesh", "EMPTY", "mesh.edgering_select", "LEFTMOUSE", {"ctrl": True},
     "DOUBLE_CLICK"),
    ("Object Mode", "EMPTY", "view3d.view_selected", "F", {}, "PRESS"),
)

# Entries in the user keymap that would fire at the same time as the new ones.
MAYA_NAV_MUTE = (
    ("Mesh", "mesh.loop_select"),
    ("Mesh", "mesh.edgering_select"),
)

_nav_keymaps = []


def _apply_navigation_prefs(context):
    """Turn on the viewport options that make Blender feel like Maya."""
    inputs = context.preferences.inputs
    wanted = {
        "use_rotate_around_active": True,
        "use_mouse_depth_navigate": True,
        "use_zoom_to_mouse": True,
        "use_mouse_emulate_3_button": False,
    }
    for name, value in wanted.items():
        try:
            setattr(inputs, name, value)
        except Exception:
            pass


GIZMO_FLAGS = ("show_gizmo_object_translate", "show_gizmo_object_rotate",
               "show_gizmo_object_scale")


def _all_workspace_view3d():
    """Every 3D viewport of every workspace, not just the visible one.

    Each workspace keeps its own viewport settings, so the transform gizmos
    can be on in Layout and off in Modeling — which is exactly how Blender
    ships. Reaching them all is the only way to make the setting stick when
    you change tab.
    """
    out = []
    for ws in bpy.data.workspaces:
        for screen in ws.screens:
            for area in screen.areas:
                if area.type != "VIEW_3D":
                    continue
                for space in area.spaces:
                    if space.type == "VIEW_3D":
                        out.append(space)
    return out


def _gizmos_apply(state):
    """Maya keeps the manipulator on screen, so the three transform gizmos go
    on everywhere rather than per workspace."""
    for space in _all_workspace_view3d():
        try:
            space.show_gizmo = True if state else space.show_gizmo
            for flag in GIZMO_FLAGS:
                setattr(space, flag, state)
        except Exception:
            continue
    _redraw_view3d()


def _gizmos_update(self, context):
    _gizmos_apply(self.maya_gizmos)


# Same rounds as the keymap repair, for the same reason. A single pass 0.2 s
# after registering was enough on Windows and not on macOS, where nine
# viewports out of ten still had the transform gizmos off with the preference
# on: whatever builds the workspaces had not finished. Looking again a few
# times costs nothing and removes the guesswork about how long to wait.
_gizmos_attempts = [0]
GIZMO_ROUNDS = 6
GIZMO_WAIT = 1.5


def _gizmos_sync():
    """Deferred, repeated, and again after loading a file: a new file brings
    its own workspaces, each with its own gizmo settings."""
    p = prefs(bpy.context)
    if p is not None and p.maya_gizmos:
        _gizmos_apply(True)
    _gizmos_attempts[0] += 1
    if _gizmos_attempts[0] >= GIZMO_ROUNDS:
        return None
    return GIZMO_WAIT


def _gizmos_load(*args):
    """Start the rounds again: a new file brings its own workspaces."""
    _gizmos_attempts[0] = 0
    _start_timer(_gizmos_sync, 0.1)


def _reapply_mutes():
    """Silence again what a keymap rebuild has just brought back.

    Everything Landfall replaces rather than adds is muted, never removed, so
    switching a preference off restores it. A rebuild undoes those mutings,
    so they are applied again — and only for the preferences that are on.
    """
    p = prefs(bpy.context)
    if p is None:
        return
    try:
        if p.maya_navigation:
            _set_native_loop_select(False)
            _wake_user_kmi("mesh.loop_select", value="DOUBLE_CLICK")
            _wake_user_kmi("mesh.edgering_select", value="DOUBLE_CLICK")
        if p.maya_extrude:
            _set_native_extrude(False)
            _wake_user_kmi("landfall.extrude_move")
    except Exception as err:
        print("[landfall] could not re-apply the keymap mutings: %s" % err)


def _kmi_signature(kmi):
    return (kmi.type, kmi.value, bool(kmi.ctrl), bool(kmi.alt),
            bool(kmi.shift), bool(kmi.oskey))


# Blender entries we mute or replace on purpose; the self check does not
# report these. Alt plus a mouse button is the Maya navigation itself and is
# skipped by rule, since it shadows a brush or a select in every paint mode.
# Keymap name, key, ctrl, alt, shift — not to_string(), which spells the
# modifiers with symbols on macOS and with words on Windows.
SHADOWS_INTENDED = {
    ("Mesh", "E", False, False, False),
    ("Window", "O", True, False, False),
    ("Window", "S", True, False, True),
}

NAV_IDNAMES = {idname for idname, _k, _m in NAV_ITEMS} | {
    row[2] for row in MAYA_NAV_EXTRA} | {"object.delete", "curve.delete",
                                         "wm.call_menu"}


def _keymap_is_ours(kmi):
    if "landfall" in kmi.idname:
        return True
    return "landfall" in str(getattr(kmi.properties, "name", "") or "")


def _keymap_survey():
    """User keymaps that hold far fewer stock entries than they should.

    A keymap in the user configuration replaces the stock one rather than
    merging with it, so a truncated one silently removes every shortcut it is
    missing. Seen for real on two machines and reproduced on a clean
    configuration: the Mesh map came up holding two entries out of a hundred
    and eight, which takes away I, K, P, A and everything else in Edit Mode
    with no message anywhere.

    Our own mirrored entries are excluded from the count, because they pad the
    total and hid the case from an earlier version of this test.
    """
    out = []
    try:
        kc = bpy.context.window_manager.keyconfigs
    except Exception:
        return out
    if kc is None or kc.user is None or kc.default is None:
        return out
    for km in kc.user.keymaps:
        stock = kc.default.keymaps.get(km.name)
        if stock is None or len(stock.keymap_items) < 4:
            continue
        native = sum(1 for k in km.keymap_items if not _keymap_is_ours(k))
        if native < len(stock.keymap_items) * 0.5:
            out.append((km, native, len(stock.keymap_items)))
    return out


# How many more times the repair should look, and how long it waits between
# looks. A single check 0.4 s after registering was not enough: Blender had
# not finished building the user configuration yet, so the check found nothing
# wrong and the truncation appeared afterwards. Measured on a Windows install
# where E and I were gone and the repair had already run and reported nothing.
_heal_attempts = [0]
HEAL_ROUNDS = 6
HEAL_WAIT = 1.5


def _keymap_heal():
    """Rebuild any truncated user keymap.

    restore_to_default rebuilds the map from the stock entries and the add-on
    ones together, so nothing of ours is lost. The threshold is deliberately
    severe — half the stock entries missing — because no deliberate
    customisation looks like that, while the fault always does.

    Returns the number of seconds to wait before looking again, or None to
    stop. It keeps looking for a few rounds rather than trusting one glance:
    the corruption can arrive after the first check, and a keymap that loses
    its entries reports nothing anywhere.
    """
    p = prefs(bpy.context)
    if p is None or not p.heal_keymaps:
        # No preferences means the add-on has been disabled while the timer
        # was still pending: nothing to repair on its behalf.
        return None

    ricostruite = 0
    for km, native, expected in _keymap_survey():
        try:
            km.restore_to_default()
            ricostruite += 1
            print("[landfall] rebuilt the '%s' keymap: it held %d of %d "
                  "stock shortcuts" % (km.name, native, expected))
        except Exception as err:
            print("[landfall] could not rebuild '%s': %s" % (km.name, err))

    if ricostruite:
        # restore_to_default brings back every stock entry, including the ones
        # we deliberately silence. Without this, E ended up with both our
        # extrude and Blender's own active at once, and loop select came back
        # on Alt+click where the orbit lives.
        _reapply_mutes()

    _heal_attempts[0] += 1
    if _heal_attempts[0] >= HEAL_ROUNDS:
        return None
    return HEAL_WAIT


def _keymap_heal_load(*args):
    """Start the rounds again: a new file brings its own configuration."""
    _heal_attempts[0] = 0
    _start_timer(_keymap_heal, 0.4)


def _maya_nav_enable(context):
    kc = context.window_manager.keyconfigs.addon
    if kc is None:
        return

    _set_native_loop_select(False)

    for km_name, space in NAV_MODE_KEYMAPS:
        try:
            km = kc.keymaps.new(name=km_name, space_type=space)
        except Exception:
            continue
        for idname, key, mods in NAV_ITEMS:
            kmi = km.keymap_items.new(idname, key, "PRESS", **mods)
            _nav_keymaps.append((km, kmi))

    for km_name, space, idname, key, mods, value in MAYA_NAV_EXTRA:
        try:
            km = kc.keymaps.new(name=km_name, space_type=space)
        except Exception:
            continue
        kmi = km.keymap_items.new(idname, key, value, **mods)
        _nav_keymaps.append((km, kmi))

    # The mirrored user copies are what Blender actually runs, and a copy
    # muted by an earlier version stays muted in the saved preferences.
    _wake_user_kmi("mesh.loop_select", value="DOUBLE_CLICK")
    _wake_user_kmi("mesh.edgering_select", value="DOUBLE_CLICK")
    _wake_user_kmi("view3d.view_selected", keymap="Object Mode", key="F")
    _apply_navigation_prefs(context)


def _maya_nav_disable():
    _remove_kmis(_nav_keymaps)
    # Same reason as the marking menu: restore by scanning, not from memory.
    _set_native_loop_select(True)


def _maya_nav_update(self, context):
    _maya_nav_disable()
    if self.maya_navigation:
        _maya_nav_enable(context)


class LANDFALL_OT_border_refresh(bpy.types.Operator):
    bl_idname = "landfall.border_refresh"
    bl_label = "Refresh border edges"
    bl_description = "Recompute the border edge overlay"

    def execute(self, context):
        _clear_border_cache()
        _redraw_view3d(context)
        return {"FINISHED"}


class LANDFALL_OT_select_inverse(bpy.types.Operator):
    bl_idname = "landfall.select_inverse"
    bl_label = "Select inverse"
    bl_description = "Invert the selection in the current mode"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        mode = context.mode
        ops = {
            "EDIT_MESH": bpy.ops.mesh.select_all,
            "EDIT_CURVE": bpy.ops.curve.select_all,
            "EDIT_SURFACE": bpy.ops.curve.select_all,
            "EDIT_ARMATURE": bpy.ops.armature.select_all,
            "POSE": bpy.ops.pose.select_all,
            "EDIT_LATTICE": bpy.ops.lattice.select_all,
            "EDIT_METABALL": bpy.ops.mball.select_all,
        }
        op = ops.get(mode, bpy.ops.object.select_all)
        try:
            op(action="INVERT")
        except Exception:
            self.report({"WARNING"}, "Cannot invert the selection here")
            return {"CANCELLED"}
        return {"FINISHED"}


class LANDFALL_OT_select_boundaries(bpy.types.Operator):
    bl_idname = "landfall.select_boundaries"
    bl_label = "Select border edges"
    bl_description = "Select every open border edge of the mesh"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.mode == "EDIT_MESH"

    def execute(self, context):
        _safe(bpy.ops.mesh.select_all, action="DESELECT")
        context.tool_settings.mesh_select_mode = (False, True, False)
        _safe(bpy.ops.mesh.select_non_manifold, 
            extend=False,
            use_wire=False,
            use_boundary=True,
            use_multi_face=False,
            use_non_contiguous=False,
            use_verts=False,
        )
        return {"FINISHED"}


class LANDFALL_OT_merge_by_distance(bpy.types.Operator):
    bl_idname = "landfall.merge_by_distance"
    bl_label = "Merge by distance"
    bl_description = "Merge the selected vertices within the given threshold"
    bl_options = {"REGISTER", "UNDO"}

    threshold: bpy.props.FloatProperty(
        name="Threshold", default=0.01, min=0.0, precision=4
    )

    @classmethod
    def poll(cls, context):
        return context.mode == "EDIT_MESH"

    def execute(self, context):
        if not _safe(bpy.ops.mesh.remove_doubles, threshold=self.threshold):
            self.report({"WARNING"}, "Cannot merge here")
            return {"CANCELLED"}
        return {"FINISHED"}


class LANDFALL_OT_merge_at_center(bpy.types.Operator):
    bl_idname = "landfall.merge_at_center"
    bl_label = "Merge at center"
    bl_description = "Collapse the selected vertices into one point"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.mode == "EDIT_MESH"

    def execute(self, context):
        if not _safe(bpy.ops.mesh.merge, type="CENTER"):
            self.report({"WARNING"}, "Cannot merge here")
            return {"CANCELLED"}
        return {"FINISHED"}


class LANDFALL_OT_detach_separate(bpy.types.Operator):
    bl_idname = "landfall.detach_separate"
    bl_label = "Detach / separate"
    bl_description = "Detach the selected faces into a new object"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.mode == "EDIT_MESH"

    def execute(self, context):
        if not _safe(bpy.ops.mesh.separate, type="SELECTED"):
            self.report({"WARNING"}, "Nothing to detach here")
            return {"CANCELLED"}
        return {"FINISHED"}


class LANDFALL_OT_unwrap_pack(bpy.types.Operator):
    bl_idname = "landfall.unwrap_pack"
    bl_label = "Unwrap + scale + pack"
    bl_description = "Unwrap, average island scale and pack the islands"
    bl_options = {"REGISTER", "UNDO"}

    margin: bpy.props.FloatProperty(name="Margin", default=0.02, min=0.0, max=0.5)

    @classmethod
    def poll(cls, context):
        return context.mode == "EDIT_MESH"

    def execute(self, context):
        _safe(bpy.ops.mesh.select_all, action="SELECT")
        _safe(bpy.ops.uv.unwrap)
        _safe(bpy.ops.uv.select_all, action="SELECT")
        _safe(bpy.ops.uv.average_islands_scale)
        _safe(bpy.ops.uv.pack_islands, margin=self.margin)
        return {"FINISHED"}


class LANDFALL_OT_reload_textures(bpy.types.Operator):
    bl_idname = "landfall.reload_textures"
    bl_label = "Reload textures"
    bl_description = "Reload every image in the file from disk"

    def execute(self, context):
        n = 0
        for img in bpy.data.images:
            if img.filepath:
                img.reload()
                n += 1
        self.report({"INFO"}, "Reloaded %d images" % n)
        return {"FINISHED"}


class LANDFALL_OT_workspace(bpy.types.Operator):
    bl_idname = "landfall.workspace"
    bl_label = "Go to workspace"
    bl_description = "Switch to the given workspace"

    name: bpy.props.StringProperty(default="UV Editing")

    def execute(self, context):
        ws = bpy.data.workspaces.get(self.name)
        if ws is None:
            self.report({"WARNING"}, "Workspace '%s' not found" % self.name)
            return {"CANCELLED"}
        context.window.workspace = ws
        return {"FINISHED"}


# ------------------------------------------------- wire follows the mode

_wire_state = {"mode": None, "restore": None}


def _all_view3d_spaces():
    """Every 3D viewport in every window.

    Use this for state that must stay consistent everywhere — overlays, the
    grid, the wire that follows the mode. Use _view3d_spaces instead for
    commands the user aims at a particular viewport.
    """
    spaces = []
    for window in bpy.context.window_manager.windows:
        screen = window.screen
        if screen is None:
            continue
        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue
            for space in area.spaces:
                if space.type == "VIEW_3D":
                    spaces.append(space)
                    break
    return spaces


def _set_wireframes(state):
    for space in _all_view3d_spaces():
        try:
            space.overlay.show_wireframes = state
        except Exception:
            pass


def _wire_follow_mode(*args):
    """Wire on shaded off in Object Mode, on in component mode.

    Maya shows the wire as soon as you enter component mode and hides it
    again on the way out. The state you set by hand in Object Mode is stored
    and put back, so pressing Wire still sticks.
    """
    p = prefs(bpy.context)
    if p is None or not p.wire_follows_mode:
        return

    try:
        mode = bpy.context.mode
    except Exception:
        return

    previous = _wire_state["mode"]
    if mode == previous:
        return
    _wire_state["mode"] = mode

    entering = mode == "EDIT_MESH" and previous != "EDIT_MESH"
    leaving = previous == "EDIT_MESH" and mode != "EDIT_MESH"

    if entering:
        spaces = _all_view3d_spaces()
        _wire_state["restore"] = [
            getattr(sp.overlay, "show_wireframes", False) for sp in spaces
        ]
        _set_wireframes(True)
    elif leaving:
        spaces = _all_view3d_spaces()
        saved = _wire_state.get("restore")
        if saved and len(saved) == len(spaces):
            for space, value in zip(spaces, saved):
                try:
                    space.overlay.show_wireframes = value
                except Exception:
                    pass
        else:
            _set_wireframes(False)
        _wire_state["restore"] = None


def _wire_reset(*args):
    """Start clean: no wire on shaded in Object Mode."""
    p = prefs(bpy.context)
    if p is None or not p.wire_follows_mode:
        return
    _wire_state["mode"] = None
    _wire_state["restore"] = None
    try:
        if bpy.context.mode != "EDIT_MESH":
            _set_wireframes(False)
    except Exception:
        pass


# ------------------------------------------------------------ finite grid



# The grid only changes when its size or cell size does, so both the points
# and the GPU batches are kept until then instead of being rebuilt on every
# redraw of every viewport.
_grid_cache = {"key": None, "coords": None, "batches": None}


def _grid_coords(size, cell):
    """A Maya-style bounded grid on the XY plane, plus its two axis lines."""
    half = size * cell * 0.5
    plain = []
    for i in range(size + 1):
        v = -half + i * cell
        if abs(v) < cell * 0.001:
            continue
        plain.extend(((v, -half, 0.0), (v, half, 0.0)))
        plain.extend(((-half, v, 0.0), (half, v, 0.0)))
    # The two axes are drawn on their own, whatever the cell count: with an
    # odd number of cells no grid line passes through the origin, and the
    # axes simply went missing — with Blender's own switched off as well.
    axis_x = [(-half, 0.0, 0.0), (half, 0.0, 0.0)]
    axis_y = [(0.0, -half, 0.0), (0.0, half, 0.0)]
    return plain, axis_x, axis_y


def _draw_grid():
    context = bpy.context
    scene = getattr(context, "scene", None)
    if scene is None or not getattr(scene, "landfall_grid_finite", False):
        return
    region = getattr(context, "region", None)
    space = getattr(context, "space_data", None)
    if region is None or space is None or space.type != "VIEW_3D":
        return
    if space.region_3d.view_perspective == "ORTHO":
        return

    key = (scene.landfall_grid_size, scene.landfall_grid_cell)
    if _grid_cache.get("key") != key:
        _grid_cache["key"] = key
        _grid_cache["coords"] = _grid_coords(*key)
        _grid_cache["batches"] = None
    plain, axis_x, axis_y = _grid_cache["coords"]
    # Following the theme keeps the finite grid right on both backgrounds:
    # light-on-dark with Blender's own theme, dark-on-light with Maya colors.
    if scene.landfall_grid_follow_theme:
        try:
            # The theme entry carries alpha 0.5, which Blender's own grid
            # shader handles differently. Blending a plain line with it leaves
            # almost no contrast against the background, so only the color is
            # taken and the line is drawn opaque.
            grey = tuple(context.preferences.themes[0].view_3d.grid)[:3] + (1.0,)
        except Exception:
            grey = tuple(scene.landfall_grid_color)
    else:
        grey = tuple(scene.landfall_grid_color)
    if len(grey) == 3:
        grey = grey + (1.0,)
    try:
        theme = context.preferences.themes[0].user_interface
        red = tuple(theme.axis_x) + (1.0,)
        green = tuple(theme.axis_y) + (1.0,)
    except Exception:
        red, green = (0.6, 0.2, 0.2, 1.0), (0.2, 0.6, 0.2, 1.0)

    shader = gpu.shader.from_builtin("POLYLINE_UNIFORM_COLOR")
    gpu.state.blend_set("ALPHA")
    gpu.state.depth_test_set("LESS_EQUAL")
    shader.bind()
    shader.uniform_float("viewportSize", (region.width, region.height))
    shader.uniform_float("lineWidth", 1.0)

    if _grid_cache.get("batches") is None:
        _grid_cache["batches"] = tuple(
            batch_for_shader(shader, "LINES", {"pos": c}) if c else None
            for c in (plain, axis_x, axis_y))
    for batch, color in zip(_grid_cache["batches"], (grey, red, green)):
        if batch is None:
            continue
        shader.uniform_float("color", color)
        batch.draw(shader)

    gpu.state.depth_test_set("NONE")
    gpu.state.blend_set("NONE")


# The floor and the two axis lines both draw to infinity, and ours already stop
# at the edge of the grid, so the native ones go off together.
#
# An earlier version snapshotted their state to put it back later. That
# snapshot could be taken while they were already off, and restoring then
# faithfully put "off" back, leaving no grid at all. Setting them outright is
# shorter and cannot fall out of step.
GRID_OVERLAYS = ("show_floor", "show_axis_x", "show_axis_y")


def _set_native_grid(on):
    for space in _all_view3d_spaces():
        for name in GRID_OVERLAYS:
            try:
                setattr(space.overlay, name, on)
            except Exception:
                pass


def _grid_finite_update(self, context):
    _set_native_grid(not self.landfall_grid_finite)
    _redraw_view3d(context)


# ------------------------------------------------------------ cage overlay

_cage_cache = {}


def _clear_cage_cache(*args):
    _cage_cache.clear()
    _cage_batches.clear()
    _generation[0] += 1


# GPU batches, one store per 3D viewport (see _per_space).
_cage_batches = {}
_border_batches = {}


def _batches(store, shader, signature, *coord_lists):
    """Reuse the GPU batches until something in the scene actually changed.

    Rebuilding them on every redraw was the real cost: the coordinates were
    already cached, the batch was not.
    """
    if store.get("signature") == signature:
        return store["batches"]
    built = tuple(
        batch_for_shader(shader, "LINES", {"pos": coords})
        if coords is not None and len(coords) else None
        for coords in coord_lists
    )
    store["signature"] = signature
    store["batches"] = built
    return built


def _to_world(co, edge_index, matrix):
    """Transform the endpoints of a set of edges in one operation.

    The obvious loop — one matrix multiply per edge in Python — costs about
    100 ms on a forty thousand face mesh, which is a visible stutter every
    time that object changes. Done as arrays it is a few milliseconds.
    """
    pts = co[edge_index]
    m = np.array(matrix, dtype=np.float32)
    return pts @ m[:3, :3].T + m[:3, 3]


def _attr(mesh, name, field, size, dtype):
    """Read a mesh attribute straight from its own array.

    The collection wrappers — mesh.vertices, mesh.edges, mesh.loops — are a
    compatibility layer over these attributes, and reading through them is
    between thirty and two hundred times slower. Measured on six hundred
    objects: edges took 87 ms through the wrapper and 0.4 ms through the
    attribute, for byte-identical results.
    """
    layer = mesh.attributes.get(name)
    if layer is None:
        return None
    count = len(layer.data)
    out = np.empty(count * size, dtype=dtype)
    layer.data.foreach_get(field, out)
    return out


def _mesh_arrays(mesh):
    co = _attr(mesh, "position", "vector", 3, np.float32)
    if co is None:
        n = len(mesh.vertices)
        co = np.empty(n * 3, dtype=np.float32)
        mesh.vertices.foreach_get("co", co)

    ed = _attr(mesh, ".edge_verts", "value", 2, np.int32)
    if ed is None:
        ed = np.empty(len(mesh.edges) * 2, dtype=np.int32)
        mesh.edges.foreach_get("vertices", ed)

    return co.reshape(-1, 3), ed, len(ed) // 2


def _cage_coords(obj):
    """World-space edges of the base mesh, before any modifier.

    Blender's own wireframe draws the evaluated mesh, so on a subdivided
    object the lines sit on the smooth surface. Maya draws the original cage
    around it instead, which is what this reproduces.
    """
    key = _cache_key(obj)
    if key is None:
        return EMPTY_COORDS

    # The key is a memory address, and Blender reuses addresses after an undo:
    # a new object can land where an old one was and inherit its entry. The
    # stored size is checked against the mesh before the entry is trusted.
    expected = len(obj.data.edges) * 2 if obj.type == "MESH" else 0
    cached = _cage_cache.get(key)
    if cached is not None and len(cached) == expected:
        return cached

    coords = EMPTY_COORDS
    try:
        mesh = obj.data
        if len(mesh.edges) <= MAX_EDGES:
            co, ed, _ne = _mesh_arrays(mesh)
            coords = _to_world(co, ed, obj.matrix_world)
    except Exception:
        coords = EMPTY_COORDS

    _cage_cache[key] = coords
    return coords


def _draw_cage():
    context = bpy.context
    scene = getattr(context, "scene", None)
    if scene is None or not getattr(scene, "landfall_cage_show", False):
        return

    region = getattr(context, "region", None)
    if region is None:
        return

    # Maya keeps the cage visible when the object is deselected, just in a
    # dark blue instead of the selection green. Two passes, one per color.
    scan = _scan_objects(context)
    only_selected = scene.landfall_cage_selected_only
    entries = [(o, key, chosen) for o, key, chosen in scan["cage"]
               if chosen or not only_selected]
    if not entries:
        return
    signature = (_generation[0], tuple((key, chosen) for _o, key, chosen in entries))

    shader = gpu.shader.from_builtin("POLYLINE_UNIFORM_COLOR")
    store = _per_space(_cage_batches, context)
    if store.get("signature") != signature:
        selected, idle = [], []
        for obj, _key, chosen in entries:
            (selected if chosen else idle).append(_cage_coords(obj))
        batches = _batches(store, shader, signature,
                           _join(idle), _join(selected))
    else:
        batches = store["batches"]
    if all(b is None for b in batches):
        return

    gpu.state.blend_set("ALPHA")
    # Maya hides the parts of the cage that fall behind the smooth surface.
    gpu.state.depth_test_set(
        "NONE" if scene.landfall_cage_xray else "LESS_EQUAL"
    )
    shader.bind()
    shader.uniform_float("viewportSize", (region.width, region.height))
    shader.uniform_float("lineWidth", scene.landfall_cage_width)

    for batch, color in zip(batches, (scene.landfall_cage_color_idle,
                                       scene.landfall_cage_color)):
        if batch is None:
            continue
        shader.uniform_float("color", color)
        batch.draw(shader)

    gpu.state.depth_test_set("NONE")
    gpu.state.blend_set("NONE")


def _cage_show_update(self, context):
    _clear_cage_cache()
    _redraw_view3d(context)


# -------------------------------------------------------- smooth preview


def _xray_alpha_update(self, context):
    """Apply the new opacity live to whatever is already transparent.

    Reading the value only when the button is pressed made the slider look
    dead: you had to press X-ray twice to see any change.
    """
    value = self.landfall_xray_alpha
    # The list can hand back a stale entry while objects are being removed,
    # so every item is checked before it is touched.
    for obj in context.view_layer.objects:
        try:
            if obj is not None and obj.color[3] < 0.999:
                obj.color[3] = value
        except (AttributeError, ReferenceError):
            continue
    _redraw_view3d(context)


def _levels_update(self, context):
    """Push the level onto the selected meshes that already have a subdivision."""
    for o in context.selected_objects:
        if o.type != "MESH":
            continue
        for m in o.modifiers:
            if m.type == "SUBSURF":
                m.levels = self.landfall_levels
                break


def _subsurf(obj, create=True, levels=2):
    for m in obj.modifiers:
        if m.type == "SUBSURF":
            return m
    if not create:
        return None
    m = obj.modifiers.new(name="Subdivision", type="SUBSURF")
    m.levels = levels
    m.show_only_control_edges = True
    return m


class LANDFALL_OT_smooth_preview(bpy.types.Operator):
    bl_idname = "landfall.smooth_preview"
    bl_label = "Smooth preview"
    bl_description = "Smooth preview levels on the selected objects"
    bl_options = {"REGISTER", "UNDO"}

    mode: bpy.props.EnumProperty(
        name="Level",
        items=[
            ("CAGE", "1", "Cage only, no visible subdivision"),
            ("BOTH", "2", "Smooth surface with the cage drawn on top"),
            ("SMOOTH", "3", "Smooth surface only"),
        ],
        default="SMOOTH",
    )
    @classmethod
    def description(cls, context, properties):
        texts = {
            "CAGE": "Cage only, no visible subdivision",
            "BOTH": "Smooth surface with the cage drawn on top",
            "SMOOTH": "Smooth surface only",
        }
        base = texts.get(properties.mode, cls.bl_description)
        return _with_shortcut(base, "landfall.smooth_preview", {"mode": properties.mode})

    def execute(self, context):
        objs = [o for o in context.selected_objects if o.type == "MESH"]
        active = context.view_layer.objects.active
        if not objs and active is not None and active.type == "MESH":
            objs = [active]
        if not objs:
            self.report({"WARNING"}, "No mesh selected")
            return {"CANCELLED"}

        levels = context.scene.landfall_levels
        context.scene.landfall_cage_show = (self.mode == "BOTH")

        for o in objs:
            if self.mode == "CAGE":
                m = _subsurf(o, create=False)
                if m:
                    m.show_viewport = False
                o.show_wire = False
                continue

            m = _subsurf(o, create=True, levels=levels)
            m.show_viewport = True
            m.show_in_editmode = True
            m.show_only_control_edges = True
            m.show_on_cage = (self.mode == "SMOOTH")
            o.show_wire = False
            o.show_all_edges = False

        return {"FINISHED"}


class LANDFALL_OT_smooth_apply(bpy.types.Operator):
    bl_idname = "landfall.smooth_apply"
    bl_label = "Apply smooth"
    bl_description = "Permanently apply the subdivision on the selected objects"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        # Blender refuses to apply a modifier on a mesh shared by several
        # objects or carrying shape keys, and says so by raising. Letting that
        # through put a Python traceback in front of the user and abandoned
        # the rest of the selection; both are ordinary situations in a real
        # scene, so they are reported and the others still get applied.
        n = 0
        saltati = []
        for o in list(context.selected_objects):
            if o.type != "MESH":
                continue
            mod = _subsurf(o, create=False)
            if mod is None:
                continue
            try:
                context.view_layer.objects.active = o
                bpy.ops.object.modifier_apply(modifier=mod.name)
                n += 1
            except RuntimeError as err:
                motivo = str(err).replace("Error: ", "").strip()
                saltati.append("%s (%s)" % (o.name, motivo))

        if saltati:
            self.report({"WARNING"}, "Skipped %d: %s"
                        % (len(saltati), "; ".join(saltati[:3])))
            if n:
                return {"FINISHED"}
            return {"CANCELLED"}
        if n == 0:
            self.report({"WARNING"}, "No subdivision to apply")
            return {"CANCELLED"}
        self.report({"INFO"}, "Applied on %d objects" % n)
        return {"FINISHED"}


# --------------------------------------------------------------- project


DEFAULT_TREE = """scenes
assets
sourceimages
sourceimages/3dPaintTextures
images
movies
cache
cache/alembic
cache/particles
renderData
renderData/shaders
data
clips
sound
scripts
autosave"""


def _safe(call, *args, **kwargs):
    """Run a Blender operator without letting a bad context escape.

    Operators like select_all or localview raise when the context is not the
    one they expect, and a random sequence of actions gets there sooner or
    later. Unhandled, the user sees a Python traceback instead of the command
    quietly doing nothing. Returns True when it ran.
    """
    try:
        call(*args, **kwargs)
        return True
    except RuntimeError:
        return False


def prefs(context):
    try:
        return context.preferences.addons[__package__].preferences
    except Exception:
        return None


_mm_keymaps = []


def _wake_user_kmi(idname, value=None, keymap=None, key=None):
    """Make sure the mirrored user-side entry is enabled.

    Blender mirrors add-on shortcuts into the user key configuration, and that
    is the copy it actually runs. A stale disabled mirror from an earlier
    install is inherited by the new one, so the key silently does nothing.

    The optional filters narrow it to our own entry when the idname is one of
    Blender's, so nothing the user disabled on purpose is switched back on.
    """
    try:
        user = bpy.context.window_manager.keyconfigs.user
    except Exception:
        return
    if user is None:
        return
    for km in user.keymaps:
        if keymap is not None and km.name != keymap:
            continue
        for kmi in km.keymap_items:
            if kmi.idname != idname:
                continue
            if value is not None and kmi.value != value:
                continue
            if key is not None and kmi.type != key:
                continue
            if not kmi.active:
                try:
                    kmi.active = True
                except Exception:
                    pass


_del_keymaps = []


def _delete_enable(context):
    """Bind Backspace to delete as well as X and Delete.

    On some Mac keyboards the forward-delete key never reaches Blender, which
    leaves X as the only way to delete. Backspace is unbound in these keymaps,
    so it can be added without shadowing anything.
    """
    kc = context.window_manager.keyconfigs.addon
    if kc is None:
        return
    targets = (
        ("Object Mode", "object.delete", {"use_global": False}),
        ("Mesh", "wm.call_menu", {"name": "VIEW3D_MT_edit_mesh_delete"}),
        ("Curve", "curve.delete", None),
    )
    for name, idname, props in targets:
        try:
            km = kc.keymaps.new(name=name, space_type="EMPTY")
            kmi = km.keymap_items.new(idname, "BACK_SPACE", "PRESS")
            if props:
                for key, value in props.items():
                    setattr(kmi.properties, key, value)
            _del_keymaps.append((km, kmi))
        except Exception:
            pass
    _wake_user_kmi("object.delete")


def _delete_disable():
    _remove_kmis(_del_keymaps)


def _delete_update(self, context):
    _delete_disable()
    if self.backspace_deletes:
        _delete_enable(context)


def _marking_enable(context):
    kc = context.window_manager.keyconfigs.addon
    if kc is None:
        return
    for name in ("Mesh", "Object Mode"):
        km = kc.keymaps.new(name=name, space_type="EMPTY")
        kmi = km.keymap_items.new("landfall.marking_menu", "TAB", "PRESS",
                                  ctrl=True)
        _mm_keymaps.append((km, kmi))
    _wake_user_kmi("landfall.marking_menu")


def _marking_disable():
    _remove_kmis(_mm_keymaps)
    _mm_stop()


def _marking_update(self, context):
    _marking_disable()
    if self.marking_menu:
        _marking_enable(context)


class LANDFALL_Prefs(bpy.types.AddonPreferences):
    bl_idname = __package__

    project_root: bpy.props.StringProperty(name="Current project", subtype="DIR_PATH")
    tree: bpy.props.StringProperty(name="Folders", default=DEFAULT_TREE)
    maya_selection: bpy.props.BoolProperty(
        name="Also use Maya's green for the 3D selection",
        description=(
            "Off by default: Blender's orange selection reads well and there is "
            "no strong reason to change it"
        ),
        default=True,
    )
    wire_follows_mode: bpy.props.BoolProperty(
        name="Wire on shaded follows the mode",
        description=(
            "Wire on shaded off in Object Mode and on in component mode, "
            "as in Maya. What you set by hand is restored on the way out"
        ),
        default=True,
    )
    maya_edit_wire: bpy.props.BoolProperty(
        name="Also color the edit-mode wireframe like Maya",
        description=(
            "Maya turns the whole wireframe light cyan in component mode. On a "
            "dense mesh that is a lot of color, so it can be left off"
        ),
        default=True,
    )
    maya_highlight: bpy.props.BoolProperty(
        name="Also use Maya's blue for selected items in the interface",
        default=True,
    )
    write_workspace_mel: bpy.props.BoolProperty(
        name="Write a Maya workspace.mel in new projects", default=True
    )
    set_render_path: bpy.props.BoolProperty(
        name="Set render output to images/", default=True
    )
    add_asset_library: bpy.props.BoolProperty(
        name="Register assets/ as an Asset Library", default=True
    )
    keys_in_labels: bpy.props.BoolProperty(
        name="Show shortcuts on the buttons, not just in tooltips", default=False
    )
    theme_backup: bpy.props.StringProperty(default="", options={"HIDDEN"})
    show_transform_hint: bpy.props.BoolProperty(
        name="Show the transform and view reminder at the top of the panel", default=True
    )
    backspace_deletes: bpy.props.BoolProperty(
        name="Backspace also deletes",
        description=(
            "Adds Backspace next to X and Delete. Useful on Mac keyboards "
            "where the forward-delete key does not reach Blender"
        ),
        default=True,
        update=lambda self, context: _delete_update(self, context),
    )
    chain_after_edit: bpy.props.BoolProperty(
        name="Reopen the menu after entering Edit Mode",
        description=(
            "Entering Edit Mode is usually followed by choosing a component, "
            "so the menu comes straight back. Turn it off if you mostly keep "
            "the component mode you left"
        ),
        default=True,
    )
    marking_menu: bpy.props.BoolProperty(
        name="Marking menu on Ctrl+Tab",
        description=(
            "A Maya-style menu with the radial ring and the list visible at "
            "once. Components and modeling in Edit Mode, modes and display "
            "in Object Mode. Replaces Blender's own Ctrl+Tab pie"
        ),
        default=True,
        update=lambda self, context: _marking_update(self, context),
    )
    maya_extrude: bpy.props.BoolProperty(
        name="Maya extrude on E",
        description=(
            "Puts thickness, offset, divisions, twist and taper on E, chained "
            "to Blender's own move so the drag stays the same. The adjust "
            "panel at the bottom left then lists all of them together. Off "
            "restores Blender's plain extrude"
        ),
        default=True,
        update=_extrude_update,
    )
    heal_keymaps: bpy.props.BoolProperty(
        name="Rebuild truncated keymaps at startup",
        description=(
            "A user keymap that is missing most of its entries hides the "
            "stock one instead of merging with it, and the shortcuts it "
            "lacks stop working with no message. This rebuilds any keymap "
            "that has lost more than half of Blender's own shortcuts. Turn "
            "it off only if you deliberately keep a stripped-down keymap"
        ),
        default=True,
    )
    maya_gizmos: bpy.props.BoolProperty(
        name="Transform gizmos on in every workspace",
        description=(
            "Blender ships with the move, rotate and scale gizmos on in "
            "Layout and off everywhere else, and each workspace keeps its "
            "own setting. This turns them on in all of them, the way Maya "
            "always shows the manipulator"
        ),
        default=True,
        update=_gizmos_update,
    )
    maya_navigation: bpy.props.BoolProperty(
        name="Maya navigation",
        description=(
            "Alt+Left orbit, Alt+Middle pan, Alt+Right zoom, F to frame the "
            "selection in Object Mode. Loop select moves to double click"
        ),
        default=True,
        update=_maya_nav_update,
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "project_root")
        layout.prop(self, "maya_selection")
        layout.prop(self, "wire_follows_mode")
        layout.prop(self, "maya_edit_wire")
        layout.prop(self, "maya_highlight")
        layout.prop(self, "write_workspace_mel")
        layout.prop(self, "set_render_path")
        layout.prop(self, "add_asset_library")
        layout.prop(self, "keys_in_labels")
        layout.prop(self, "show_transform_hint")

        box = layout.box()
        box.prop(self, "maya_navigation")
        box.prop(self, "maya_gizmos")
        box.prop(self, "maya_extrude")
        box.prop(self, "heal_keymaps")
        col = box.column(align=True)
        col.enabled = False
        col.label(text="Alt+Left orbit, Alt+Middle pan, Alt+Right zoom")
        col.label(text="F frames the selection in Object Mode")
        col.label(text="Loop select moves to double click, edge ring to Ctrl+double click")
        col.label(text="Blender's own middle-mouse navigation keeps working")
        col.label(text="Turning this off puts everything back")
        box.operator("landfall.keymap_report", icon="CONSOLE")

        box = layout.box()
        box.prop(self, "marking_menu")
        box.prop(self, "chain_after_edit")
        box.prop(self, "backspace_deletes")
        col = box.column(align=True)
        col.enabled = False
        col.label(text="Object Mode: edit, sculpt, paint modes, object")
        col.label(text="Edit Mode: vertex, edge, face, multi, object")
        col.label(text="Replaces Blender's own Ctrl+Tab pie while enabled")
        layout.label(text="Folder structure, one per line:")
        layout.prop(self, "tree", text="")
        layout.label(text="Shortcuts: Preferences > Keymap, search 'landfall'")


def _apply_project(context, root):
    p = prefs(context)
    if p is None:
        return
    p.project_root = root

    if p.set_render_path:
        images = os.path.join(root, "images")
        if os.path.isdir(images):
            context.scene.render.filepath = images + os.sep

    if p.add_asset_library:
        assets = os.path.join(root, "assets")
        if os.path.isdir(assets):
            libs = context.preferences.filepaths.asset_libraries
            name = os.path.basename(os.path.normpath(root))
            existing = next((l for l in libs if l.name == name), None)
            if existing is None:
                bpy.ops.preferences.asset_library_add(directory=assets)
                if len(libs):
                    libs[-1].name = name
            else:
                existing.path = assets

    try:
        bpy.ops.wm.save_userpref()
    except Exception:
        pass


WORKSPACE_MEL = """//Maya Project Definition
//Written by Landfall for Blender. Safe to edit.

workspace -fr "scene" "scenes";
workspace -fr "mayaAscii" "scenes";
workspace -fr "mayaBinary" "scenes";
workspace -fr "templates" "assets";
workspace -fr "sourceImages" "sourceimages";
workspace -fr "3dPaintTextures" "sourceimages/3dPaintTextures";
workspace -fr "images" "images";
workspace -fr "movie" "movies";
workspace -fr "renderData" "renderData";
workspace -fr "shaders" "renderData/shaders";
workspace -fr "alembicCache" "cache/alembic";
workspace -fr "particles" "cache/particles";
workspace -fr "fileCache" "cache";
workspace -fr "data" "data";
workspace -fr "fbx" "data";
workspace -fr "OBJ" "data";
workspace -fr "translatorData" "data";
workspace -fr "clips" "clips";
workspace -fr "sound" "sound";
workspace -fr "scripts" "scripts";
workspace -fr "autosave" "autosave";
"""


def _write_workspace_mel(root):
    path = os.path.join(root, "workspace.mel")
    if os.path.exists(path):
        return False
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(WORKSPACE_MEL)
    return True


class LANDFALL_OT_write_workspace(bpy.types.Operator):
    bl_idname = "landfall.write_workspace"
    bl_label = "Write workspace.mel"
    bl_description = (
        "Write a Maya workspace.mel into the current project so Maya's Set "
        "Project recognizes the folder"
    )

    overwrite: bpy.props.BoolProperty(default=False, options={"SKIP_SAVE"})

    def execute(self, context):
        p = prefs(context)
        root = p.project_root if p else ""
        if not root or not os.path.isdir(root):
            self.report({"WARNING"}, "No project set")
            return {"CANCELLED"}

        path = os.path.join(root, "workspace.mel")
        if os.path.exists(path) and not self.overwrite:
            self.report({"INFO"}, "workspace.mel is already there")
            return {"CANCELLED"}

        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(WORKSPACE_MEL)
        except Exception as err:
            self.report({"WARNING"}, "Could not write it: %s" % err)
            return {"CANCELLED"}

        self.report({"INFO"}, "workspace.mel written")
        return {"FINISHED"}


class LANDFALL_OT_create_project(bpy.types.Operator):
    bl_idname = "landfall.create_project"
    bl_label = "Create project"
    bl_description = "Create a project folder tree and set it as current"

    directory: bpy.props.StringProperty(subtype="DIR_PATH")
    project_name: bpy.props.StringProperty(name="Project name", default="new_project")

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def draw(self, context):
        self.layout.prop(self, "project_name")

    def execute(self, context):
        if not self.directory:
            self.report({"WARNING"}, "No folder chosen")
            return {"CANCELLED"}

        name = self.project_name.strip().replace(" ", "_")
        if not name:
            self.report({"WARNING"}, "Empty project name")
            return {"CANCELLED"}

        root = os.path.join(self.directory, name)
        p = prefs(context)
        tree = (p.tree if p else DEFAULT_TREE).splitlines()

        made = 0
        for rel in tree:
            rel = rel.strip()
            if not rel:
                continue
            path = os.path.join(root, *rel.split("/"))
            if not os.path.isdir(path):
                os.makedirs(path, exist_ok=True)
                made += 1

        wrote = False
        if p is None or p.write_workspace_mel:
            try:
                wrote = _write_workspace_mel(root)
            except Exception:
                wrote = False

        _apply_project(context, root)
        self.report(
            {"INFO"},
            "Project '%s' created (%d folders%s)"
            % (name, made, ", workspace.mel" if wrote else ""),
        )
        return {"FINISHED"}


class LANDFALL_OT_set_project(bpy.types.Operator):
    bl_idname = "landfall.set_project"
    bl_label = "Set project"
    bl_description = "Set an existing folder as the current project"

    directory: bpy.props.StringProperty(subtype="DIR_PATH")

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        root = os.path.normpath(self.directory)
        if not os.path.isdir(root):
            self.report({"WARNING"}, "Not a valid folder")
            return {"CANCELLED"}
        _apply_project(context, root)
        self.report({"INFO"}, "Project: %s" % os.path.basename(root))
        return {"FINISHED"}


def _scenes_dir(context):
    p = prefs(context)
    root = p.project_root if p else ""
    if not root:
        return ""
    scenes = os.path.join(root, "scenes")
    return scenes if os.path.isdir(scenes) else ""


class LANDFALL_OT_project_open(bpy.types.Operator):
    bl_idname = "landfall.project_open"
    bl_label = "Open scene"
    bl_description = "Open the file browser inside the project scenes/ folder"

    def execute(self, context):
        scenes = _scenes_dir(context)
        if not scenes:
            self.report({"INFO"}, "No project set, opening the usual browser")
            bpy.ops.wm.open_mainfile("INVOKE_DEFAULT")
            return {"FINISHED"}
        bpy.ops.wm.open_mainfile("INVOKE_DEFAULT", filepath=os.path.join(scenes, ""))
        return {"FINISHED"}


class LANDFALL_OT_project_save_as(bpy.types.Operator):
    bl_idname = "landfall.project_save_as"
    bl_label = "Save scene as"
    bl_description = "Save into the project scenes/ folder with relative paths"

    def execute(self, context):
        scenes = _scenes_dir(context)
        if not scenes:
            self.report({"INFO"}, "No project set, opening the usual Save As")
            bpy.ops.wm.save_as_mainfile("INVOKE_DEFAULT", relative_remap=True)
            return {"FINISHED"}

        current = bpy.data.filepath
        # Already inside the project: keep the file where it is.
        p = prefs(context)
        root = os.path.normpath(p.project_root) if p and p.project_root else ""
        if current and root and os.path.normpath(current).startswith(root + os.sep):
            bpy.ops.wm.save_as_mainfile(
                "INVOKE_DEFAULT", filepath=current, relative_remap=True
            )
            return {"FINISHED"}

        name = os.path.basename(current) or "untitled.blend"
        if not name.lower().endswith(".blend"):
            name += ".blend"

        bpy.ops.wm.save_as_mainfile(
            "INVOKE_DEFAULT",
            filepath=os.path.join(scenes, name),
            relative_remap=True,
        )
        return {"FINISHED"}


class LANDFALL_OT_paths_relative(bpy.types.Operator):
    bl_idname = "landfall.paths_relative"
    bl_label = "Make paths relative"
    bl_description = "Convert every external path to be relative to the file"

    def execute(self, context):
        if not bpy.data.filepath:
            self.report({"WARNING"}, "Save the file first")
            return {"CANCELLED"}
        if not _safe(bpy.ops.file.make_paths_relative):
            self.report({"WARNING"}, "Save the file first")
            return {"CANCELLED"}
        self.report({"INFO"}, "Paths made relative")
        return {"FINISHED"}


# -------------------------------------------------------------- quad view


class LANDFALL_OT_toggle_regions(bpy.types.Operator):
    bl_idname = "landfall.toggle_regions"
    bl_label = "Toolbar and sidebar"
    bl_description = "Show or hide a region in every 3D viewport at once"
    bl_options = {"REGISTER", "UNDO"}

    region: bpy.props.EnumProperty(
        items=[
            ("TOOLBAR", "Toolbar", "The tool buttons on the left, normally T"),
            ("SIDEBAR", "Sidebar", "The N panel on the right"),
            ("HEADER", "Header", "The menu strip at the top of each viewport"),
        ],
        default="TOOLBAR",
        options={"SKIP_SAVE"},
    )

    @classmethod
    def description(cls, context, properties):
        names = {"TOOLBAR": "toolbar", "SIDEBAR": "sidebar", "HEADER": "header"}
        return "Show or hide the %s in every 3D viewport at once" % names.get(
            properties.region, "region")

    def execute(self, context):
        attr = {
            "TOOLBAR": "show_region_toolbar",
            "SIDEBAR": "show_region_ui",
            "HEADER": "show_region_header",
        }[self.region]

        spaces = []
        for area in context.window.screen.areas:
            if area.type != "VIEW_3D":
                continue
            for space in area.spaces:
                if space.type == "VIEW_3D":
                    spaces.append(space)
                    break
        if not spaces:
            self.report({"WARNING"}, "No 3D viewport on this screen")
            return {"CANCELLED"}

        state = not getattr(spaces[0], attr, True)
        for space in spaces:
            try:
                setattr(space, attr, state)
            except Exception:
                pass
        return {"FINISHED"}


class LANDFALL_OT_quad_view(bpy.types.Operator):
    bl_idname = "landfall.quad_view"
    bl_label = "Quad view"
    bl_description = (
        "Turn Blender's Quad View on or off in the 3D viewport. The Outliner, "
        "Properties and this panel stay where they are"
    )

    def execute(self, context):
        area, region = _view3d_area(context)
        if area is None:
            self.report({"WARNING"}, "No 3D viewport on this screen")
            return {"CANCELLED"}
        try:
            with context.temp_override(area=area, region=region):
                bpy.ops.screen.region_quadview()
        except Exception as err:
            self.report({"WARNING"}, "Could not toggle Quad View: %s" % err)
            return {"CANCELLED"}
        return {"FINISHED"}


# ------------------------------------------------------------- PBR set


MAP_RULES = [
    ("base",  ("basecolor", "base_color", "albedo", "diffuse", "_col", "color")),
    ("rough", ("roughness", "_rough", "_rgh")),
    ("metal", ("metallic", "metalness", "_metal", "_mtl")),
    ("normal", ("normalgl", "normal", "_nrm", "_nor")),
    ("height", ("displacement", "height", "_disp", "_hgt")),
    ("emit",  ("emissive", "emission", "_emit")),
    ("alpha", ("opacity", "_alpha")),
]


def classify(filename):
    low = filename.lower()
    if any(k in low for k in ("normalgl", "normal", "_nrm", "_nor")):
        return "normal"
    for kind, keys in MAP_RULES:
        if kind == "normal":
            continue
        if any(k in low for k in keys):
            return kind
    return None


def _pbr_shader_nodes(nt):
    """The Principled and the Output of a material, created if missing."""
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    output = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"), None)
    if bsdf is None:
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.location = (0, 0)
    if output is None:
        output = nt.nodes.new("ShaderNodeOutputMaterial")
        output.location = (400, 0)
    if not bsdf.outputs["BSDF"].links:
        nt.links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    return bsdf, output


class LANDFALL_OT_load_pbr_set(bpy.types.Operator):
    bl_idname = "landfall.load_pbr_set"
    bl_label = "Load PBR set"
    bl_description = "Load a texture set and wire up the Principled BSDF"
    bl_options = {"REGISTER", "UNDO"}

    directory: bpy.props.StringProperty(subtype="DIR_PATH")
    files: bpy.props.CollectionProperty(type=bpy.types.OperatorFileListElement)
    filter_glob: bpy.props.StringProperty(
        default="*.png;*.jpg;*.jpeg;*.tif;*.tiff;*.exr;*.tga;*.bmp", options={"HIDDEN"}
    )

    def invoke(self, context, event):
        if context.active_object is None:
            self.report({"WARNING"}, "Select an object first")
            return {"CANCELLED"}
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        obj = context.active_object
        if obj is None or not hasattr(obj.data, "materials"):
            self.report({"WARNING"}, "The active object cannot take materials")
            return {"CANCELLED"}

        mat = obj.active_material
        if mat is None:
            mat = bpy.data.materials.new(name=obj.name + "_mat")
            mat.use_nodes = True
            obj.data.materials.append(mat)
        if not mat.use_nodes:
            mat.use_nodes = True

        nt = mat.node_tree
        bsdf, output = _pbr_shader_nodes(nt)

        found = {}
        for f in self.files:
            kind = classify(f.name)
            if kind and kind not in found:
                found[kind] = os.path.join(self.directory, f.name)

        if not found:
            self.report({"WARNING"}, "No map recognized from the file names")
            return {"CANCELLED"}

        base_x = bsdf.location.x - 900
        base_y = bsdf.location.y + 300

        coord = nt.nodes.new("ShaderNodeTexCoord")
        coord.location = (base_x - 400, base_y)
        mapping = nt.nodes.new("ShaderNodeMapping")
        mapping.location = (base_x - 200, base_y)
        nt.links.new(coord.outputs["UV"], mapping.inputs["Vector"])

        order = ["base", "rough", "metal", "normal", "height", "emit", "alpha"]
        sockets = {
            "base": "Base Color",
            "rough": "Roughness",
            "metal": "Metallic",
            "emit": "Emission Color",
            "alpha": "Alpha",
        }
        data_maps = {"rough", "metal", "normal", "height", "alpha"}

        row = 0
        for kind in order:
            path = found.get(kind)
            if not path:
                continue

            img = bpy.data.images.load(path, check_existing=True)
            if kind in data_maps:
                try:
                    img.colorspace_settings.name = "Non-Color"
                except Exception:
                    pass

            tex = nt.nodes.new("ShaderNodeTexImage")
            tex.image = img
            tex.label = kind
            tex.location = (base_x, base_y - row * 300)
            nt.links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
            row += 1

            if kind == "normal":
                nm = nt.nodes.new("ShaderNodeNormalMap")
                nm.location = (base_x + 300, tex.location.y)
                nt.links.new(tex.outputs["Color"], nm.inputs["Color"])
                if "Normal" in bsdf.inputs:
                    nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
            elif kind == "height":
                dp = nt.nodes.new("ShaderNodeDisplacement")
                dp.location = (base_x + 300, tex.location.y)
                dp.inputs["Scale"].default_value = 0.05
                nt.links.new(tex.outputs["Color"], dp.inputs["Height"])
                if "Displacement" in output.inputs:
                    nt.links.new(dp.outputs["Displacement"], output.inputs["Displacement"])
            else:
                socket = sockets.get(kind)
                if socket and socket in bsdf.inputs:
                    nt.links.new(tex.outputs["Color"], bsdf.inputs[socket])
                    if kind == "emit" and "Emission Strength" in bsdf.inputs:
                        bsdf.inputs["Emission Strength"].default_value = 1.0
                    if kind == "alpha":
                        nt.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])

        self.report({"INFO"}, "Connected %d maps: %s" % (len(found), ", ".join(sorted(found))))
        return {"FINISHED"}


# ------------------------------------------------------------------- UI


def draw_display(layout, context):
    scene = context.scene
    col = layout.column(align=True)
    row = col.row(align=True)
    row.operator("landfall.toggle_xray_object", text="X-ray", icon="XRAY")
    sub = row.row(align=True)
    sub.scale_x = 0.55
    sub.prop(scene, "landfall_xray_alpha", text="", slider=True)
    row.operator("landfall.toggle_wireframe", text="Wire on shaded",
                 icon="SHADING_WIRE")
    row = col.row(align=True)
    row.operator("landfall.hide_selected", text="Hide", icon="HIDE_ON")
    row.operator("landfall.show_selected", text="Show sel", icon="HIDE_OFF")
    row = col.row(align=True)
    row.operator("landfall.show_last_hidden", text="Show last", icon="LOOP_BACK")
    row.operator("landfall.show_all", text="Show all", icon="RESTRICT_VIEW_OFF")
    col.operator("landfall.isolate", text="Isolate", icon="ZOOM_SELECTED")
    scene = context.scene
    box = col.box()
    row = box.row(align=True)
    row.prop(scene, "landfall_border_show", text="Border edges", toggle=True,
             icon="MOD_EDGESPLIT")
    row.operator("landfall.border_refresh", text="", icon="FILE_REFRESH")
    if scene.landfall_border_show:
        row = box.row(align=True)
        row.prop(scene, "landfall_border_width", text="Width")
        swatch = row.row(align=True)
        swatch.scale_x = 0.5
        swatch.prop(scene, "landfall_border_color", text="")
        row.prop(scene, "landfall_border_selected_only", text="Sel only",
                 toggle=True)
    sub = box.row(align=True)
    sub.enabled = context.mode == "EDIT_MESH"
    sub.operator("landfall.select_boundaries", text="Select border edges")

    col = layout.column(align=True)
    col.separator()
    col.label(text="Object color")
    row = col.row(align=True)
    for key, label, _value, icon in OBJECT_COLORS:
        op = row.operator("landfall.object_color", text="", icon=icon)
        op.color = key
    swatch = row.row(align=True)
    swatch.scale_x = 0.5
    swatch.prop(scene, "landfall_object_color", text="")
    op = row.operator("landfall.object_color", text="", icon="CHECKMARK")
    op.use_custom = True
    row.operator("landfall.object_color", text="", icon="X").clear = True


def draw_modeling(layout, context):
    edit = context.mode == "EDIT_MESH"
    p = prefs(context)
    scene = context.scene
    col = layout.column(align=True)
    row = col.row(align=True)
    row.operator("object.origin_set", text="Center pivot", icon="OBJECT_ORIGIN").type = "ORIGIN_GEOMETRY"
    row.prop(context.tool_settings, "use_transform_data_origin", text="Edit pivot", toggle=True)
    row = col.row(align=True)
    row.operator("object.transform_apply", text="Freeze", icon="CHECKMARK")
    row.operator("object.select_grouped", text="Hierarchy",
                 icon="OUTLINER").type = "CHILDREN_RECURSIVE"
    row.operator("landfall.select_inverse", text="Inverse",
                 icon="SELECT_SUBTRACT")

    sub = col.column(align=True)
    sub.enabled = edit
    # L'interruttore sta accanto al comando, non solo nelle preferenze: Luca
    # deve vedere a colpo d'occhio se E sta usando la nostra estrusione.
    riga = sub.row(align=True)
    riga.operator("landfall.extrude_options", text="Extrude with options",
                  icon="ORIENTATION_NORMAL")
    if p is not None:
        riga.prop(p, "maya_extrude", text="", toggle=True,
                  icon="EVENT_E")
    sub.operator("landfall.merge_by_distance", text="Merge by distance", icon="AUTOMERGE_ON")
    sub.operator("landfall.merge_at_center", text="Merge at center", icon="SNAP_MIDPOINT")
    row = sub.row(align=True)
    row.operator("mesh.edge_rotate", text="Spin", icon="FILE_REFRESH")
    row.operator("landfall.detach_separate", text="Detach", icon="MOD_BOOLEAN")
    sub.operator("mesh.fill_grid", text="Grid fill", icon="MESH_GRID")
    if not edit:
        col.label(text="Some commands need Edit Mode")

    col.separator()
    col.label(text="Smooth preview")
    row = col.row(align=True)
    # The keymap is only scanned when the key is going on the button: four
    # thousand entries three times per redraw is a cost worth paying only
    # for something that is actually shown.
    show_keys = p is not None and p.keys_in_labels
    for label, mode in (("1", "CAGE"), ("2", "BOTH"), ("3", "SMOOTH")):
        key = _shortcut("landfall.smooth_preview", {"mode": mode}) if show_keys else ""
        text = "%s  %s" % (label, key) if key else label
        row.operator("landfall.smooth_preview", text=text).mode = mode
    col.prop(context.scene, "landfall_levels")
    col.operator("landfall.smooth_apply", text="Apply smooth", icon="CHECKMARK")
    row = col.row(align=True)
    row.prop(scene, "landfall_cage_show", text="Cage", toggle=True,
             icon="MOD_MESHDEFORM")
    if scene.landfall_cage_show:
        row.prop(scene, "landfall_cage_width", text="")
        swatch = row.row(align=True)
        swatch.scale_x = 0.5
        swatch.prop(scene, "landfall_cage_color", text="")
        swatch.prop(scene, "landfall_cage_color_idle", text="")
        sub = col.row(align=True)
        sub.prop(scene, "landfall_cage_selected_only", text="Sel only",
                 toggle=True)
        sub.prop(scene, "landfall_cage_xray", text="See through", toggle=True)


def draw_texturing(layout, context):
    col = layout.column(align=True)
    sub = col.column(align=True)
    sub.enabled = context.mode == "EDIT_MESH"
    sub.operator("landfall.unwrap_pack", text="Unwrap + scale + pack", icon="UV")
    row = sub.row(align=True)
    row.operator("uv.project_from_view", text="Pla")
    row.operator("uv.cylinder_project", text="Cyl")
    row.operator("uv.sphere_project", text="Sph")
    row.operator("uv.smart_project", text="Auto")
    col.operator("landfall.load_pbr_set", text="Load PBR set", icon="IMAGE_DATA")
    col.operator("landfall.reload_textures", text="Reload textures", icon="FILE_REFRESH")


def draw_editors(layout, context):
    col = layout.column(align=True)
    row = col.row(align=True)
    row.operator("landfall.workspace", text="UV", icon="UV").name = "UV Editing"
    row.operator("landfall.workspace", text="Shading",
                 icon="MATERIAL").name = "Shading"
    row.operator("render.opengl", text="Playblast",
                 icon="RENDER_ANIMATION").animation = True
    col.separator()
    col.operator("landfall.quad_view", text="Quad view", icon="MESH_GRID")
    col.label(text="In every viewport")
    row = col.row(align=True)
    row.operator("landfall.toggle_regions", text="Toolbar",
                 icon="TOOL_SETTINGS").region = "TOOLBAR"
    row.operator("landfall.toggle_regions", text="Sidebar",
                 icon="MENU_PANEL").region = "SIDEBAR"
    row.operator("landfall.toggle_regions", text="Header",
                 icon="TOPBAR").region = "HEADER"


def draw_project(layout, context):
    p = prefs(context)
    col = layout.column(align=True)
    root = p.project_root if p else ""
    if root:
        col.label(text=os.path.basename(os.path.normpath(root)), icon="FILE_FOLDER")
    else:
        col.label(text="No project set", icon="ERROR")
    row = col.row(align=True)
    row.operator("landfall.create_project", text="Create", icon="NEWFOLDER")
    row.operator("landfall.set_project", text="Set", icon="FILE_FOLDER")
    row = col.row(align=True)
    row.operator("landfall.project_open", text="Open scene", icon="FILE_BLEND")
    row.operator("landfall.project_save_as", text="Save as", icon="FILE_TICK")
    col.operator("landfall.paths_relative", text="Make paths relative", icon="LINKED")
    col.operator("landfall.write_workspace", text="Write workspace.mel", icon="TEXT")


def draw_setup(layout, context):
    p = prefs(context)
    scene = context.scene

    # How many of the five Maya settings are currently on. Shown so the button
    # never has to guess which way it should go, and neither does the user.
    # The colors are read from the theme itself rather than from the stored
    # snapshot: the snapshot lives on disk since 3.2x and the preference copy
    # of it is empty after a reinstall, so the count said "off" while the
    # viewport was plainly Maya's.
    parts = []
    if p is not None:
        try:
            colors_on = _theme_is_maya(context.preferences.themes[0].view_3d)
        except Exception:
            colors_on = bool(p.theme_backup)
        parts = [p.maya_navigation, p.marking_menu, p.wire_follows_mode,
                 colors_on, scene.landfall_grid_finite]
    active = sum(1 for x in parts if x)

    box = layout.box()
    row = box.row(align=True)
    row.label(text="Maya setup: %d of %d on" % (active, len(parts))
              if parts else "Maya setup")
    row = box.row(align=True)
    on = row.operator("landfall.maya_setup", text="Turn on", icon="CHECKMARK")
    on.enable = True
    off = row.operator("landfall.maya_setup", text="Turn off", icon="X")
    off.enable = False
    box.operator("landfall.save_defaults", text="Save as startup",
                 icon="FILE_TICK")
    box.operator("landfall.self_check", text="Self check", icon="CHECKMARK")

    # L'avviso sta qui e non solo nella documentazione: nessuno legge un PDF
    # prima di disinstallare. Turn off riaccende la griglia nativa e rimette
    # il tema; disinstallare senza premerlo lascia il viewport senza griglia
    # e i colori di Maya, e a quel punto l'addon non c'e' piu' per rimediare.
    nota = box.column(align=True)
    nota.scale_y = 0.8
    nota.label(text="Press Turn off before uninstalling:", icon="INFO")
    nota.label(text="it puts the grid and the theme back.")

    layout.separator()
    draw_nav_toggle(layout, context)


# In use order: what you press constantly first, what you set once last.
SECTIONS = (
    ("Display", draw_display),
    ("Modeling", draw_modeling),
    ("Texturing", draw_texturing),
    ("Gizmos", draw_gizmos),
    ("Editors and output", draw_editors),
    ("Project", draw_project),
    ("Setup", draw_setup),
)

# Sections that only make sense in some modes.
MODELLING_MODES = {"OBJECT", "EDIT_MESH"}


def _poll_modeling(context):
    return context.mode in MODELLING_MODES


class LANDFALL_PT_sidebar(bpy.types.Panel):
    bl_label = "Landfall"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Landfall"

    def draw(self, context):
        draw_transform_hint(self.layout, context)


class _SubPanel:
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Landfall"
    bl_parent_id = "LANDFALL_PT_sidebar"


class LANDFALL_PT_sb_display(_SubPanel, bpy.types.Panel):
    bl_label = "Display"
    bl_order = 0

    def draw(self, context):
        draw_display(self.layout, context)


class LANDFALL_PT_sb_modeling(_SubPanel, bpy.types.Panel):
    bl_label = "Modeling"
    bl_order = 1

    @classmethod
    def poll(cls, context):
        return _poll_modeling(context)

    def draw(self, context):
        draw_modeling(self.layout, context)


class LANDFALL_PT_sb_texturing(_SubPanel, bpy.types.Panel):
    bl_label = "Texturing"
    bl_order = 2

    @classmethod
    def poll(cls, context):
        return _poll_modeling(context)

    def draw(self, context):
        draw_texturing(self.layout, context)


class LANDFALL_PT_sb_gizmos(_SubPanel, bpy.types.Panel):
    bl_label = "Gizmos"
    bl_order = 3
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        draw_gizmos(self.layout, context)


class LANDFALL_PT_sb_editors(_SubPanel, bpy.types.Panel):
    bl_label = "Editors and output"
    bl_order = 4

    def draw(self, context):
        draw_editors(self.layout, context)


class LANDFALL_PT_sb_project(_SubPanel, bpy.types.Panel):
    bl_label = "Project"
    bl_order = 5

    def draw(self, context):
        draw_project(self.layout, context)


class LANDFALL_PT_sb_setup(_SubPanel, bpy.types.Panel):
    bl_label = "Setup"
    bl_order = 6
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        draw_setup(self.layout, context)


class LANDFALL_PT_sb_about(_SubPanel, bpy.types.Panel):
    bl_label = "About"
    bl_options = {"HIDE_HEADER"}
    bl_order = 100

    def draw(self, context):
        draw_footer(self.layout)


class LANDFALL_PT_properties(bpy.types.Panel):
    # The Scene tab. Object was wrong because that tab disappears with no
    # active object, taking the panel with it; "tool" looked right by name but
    # is not a context the Properties editor accepts, so nothing rendered at
    # all. Scene is always present, verified live.
    bl_label = "Landfall"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        draw_transform_hint(self.layout, context)


class _PropSubPanel:
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_parent_id = "LANDFALL_PT_properties"
    bl_options = {"DEFAULT_CLOSED"}


def _make_prop_panels():
    """One class per section instead of eight near-identical definitions."""
    classes = []
    for order, (title, draw_fn) in enumerate(SECTIONS):
        name = "LANDFALL_PT_pr_%d" % order
        needs_mode = draw_fn in (draw_modeling, draw_texturing)
        members = {
            "bl_label": title,
            "bl_order": order,
            "draw": (lambda fn: lambda self, context: fn(self.layout, context))(draw_fn),
        }
        if needs_mode:
            members["poll"] = classmethod(lambda cls, context: _poll_modeling(context))
        classes.append(type(name, (_PropSubPanel, bpy.types.Panel), members))

    members = {
        "bl_label": "About",
        "bl_options": {"HIDE_HEADER"},
        "bl_order": 100,
        "draw": lambda self, context: draw_footer(self.layout),
    }
    classes.append(type("LANDFALL_PT_pr_about", (_PropSubPanel, bpy.types.Panel), members))
    return tuple(classes)


PROP_PANELS = _make_prop_panels()


class VIEW3D_MT_landfall_pie(bpy.types.Menu):
    bl_label = "Landfall"
    bl_idname = "VIEW3D_MT_landfall_pie"

    def draw(self, context):
        pie = self.layout.menu_pie()
        pie.operator("landfall.hide_selected", text="Hide", icon="HIDE_ON")
        pie.operator("landfall.select_boundaries", text="Border edges", icon="MOD_EDGESPLIT")
        pie.operator("landfall.isolate", text="Isolate", icon="ZOOM_SELECTED")
        pie.operator("landfall.toggle_xray_object", text="X-ray", icon="XRAY")
        pie.operator("landfall.show_all", text="Show all", icon="HIDE_OFF")
        pie.operator("landfall.toggle_wireframe", text="Wire", icon="SHADING_WIRE")
        pie.operator("landfall.merge_by_distance", text="Merge by distance", icon="AUTOMERGE_ON")
        pie.operator("object.transform_apply", text="Freeze", icon="CHECKMARK")


class LANDFALL_OT_hotbox(bpy.types.Operator):
    bl_idname = "landfall.hotbox"
    bl_label = "Landfall hotbox"
    bl_description = "Open the hotbox at the mouse cursor"

    @classmethod
    def description(cls, context, properties):
        return _with_shortcut("Open the hotbox at the mouse cursor", "landfall.hotbox")

    def invoke(self, context, event):
        return context.window_manager.invoke_popup(self, width=620)

    def draw(self, context):
        row = self.layout.row()
        for title, fn in SECTIONS:
            col = row.column()
            col.label(text=title)
            fn(col, context)
        draw_footer(self.layout)

    def execute(self, context):
        return {"FINISHED"}


# ---------------------------------------------------------- registration


CLASSES = (
    LANDFALL_Prefs,
    LANDFALL_OT_smooth_preview,
    LANDFALL_OT_smooth_apply,
    LANDFALL_OT_write_workspace,
    LANDFALL_OT_create_project,
    LANDFALL_OT_set_project,
    LANDFALL_OT_project_open,
    LANDFALL_OT_project_save_as,
    LANDFALL_OT_paths_relative,
    LANDFALL_OT_toggle_xray_object,
    LANDFALL_OT_toggle_wireframe,
    LANDFALL_OT_hide_selected,
    LANDFALL_OT_show_selected,
    LANDFALL_OT_show_all,
    LANDFALL_OT_isolate,
    LANDFALL_OT_show_last_hidden,
    LANDFALL_OT_keymap_report,
    LANDFALL_OT_object_color,
    LANDFALL_OT_save_defaults,
    LANDFALL_OT_maya_setup,
    LANDFALL_OT_reset_theme,
    LANDFALL_OT_maya_theme,
    LANDFALL_OT_toggle_gizmos,
    LANDFALL_OT_self_check,
    LANDFALL_OT_frame_selected,
    LANDFALL_OT_extrude_options,
    LANDFALL_OT_extrude_move,
    LANDFALL_OT_toggle_scene_flag,
    LANDFALL_OT_marking_menu,
    LANDFALL_OT_select_mode_multi,
    LANDFALL_OT_set_snap,
    LANDFALL_OT_cheatsheet,
    LANDFALL_OT_border_refresh,
    LANDFALL_OT_select_inverse,
    LANDFALL_OT_select_boundaries,
    LANDFALL_OT_merge_by_distance,
    LANDFALL_OT_merge_at_center,
    LANDFALL_OT_detach_separate,
    LANDFALL_OT_unwrap_pack,
    LANDFALL_OT_reload_textures,
    LANDFALL_OT_workspace,
    LANDFALL_OT_toggle_regions,
    LANDFALL_OT_quad_view,
    LANDFALL_OT_load_pbr_set,
    LANDFALL_OT_hotbox,
    LANDFALL_PT_sidebar,
    LANDFALL_PT_sb_gizmos,
    LANDFALL_PT_sb_display,
    LANDFALL_PT_sb_modeling,
    LANDFALL_PT_sb_texturing,
    LANDFALL_PT_sb_editors,
    LANDFALL_PT_sb_project,
    LANDFALL_PT_sb_setup,
    LANDFALL_PT_sb_about,
    LANDFALL_PT_properties,
    VIEW3D_MT_landfall_pie,
    VIEW3D_MT_landfall_model_pie,
    VIEW3D_MT_landfall_snap_pie,
)

_keymaps = []

# Where the general shortcuts go: the viewport keymap and every mode keymap
# that would otherwise catch the key first.
KEYMAP_TARGETS = (("3D View", "VIEW_3D"),) + tuple(
    (name, "EMPTY") for name in (
        "Object Mode", "Mesh", "Sculpt", "Vertex Paint", "Weight Paint",
        "Image Paint", "Pose"))


def _register_properties():
    bpy.types.Scene.landfall_xray_alpha = bpy.props.FloatProperty(
        name="X-ray",
        description=(
            "Opacity given to the selected objects by the X-ray button. "
            "Dragging it changes the objects that are already transparent"
        ),
        default=0.3, min=0.0, max=1.0, subtype="FACTOR",
        update=_xray_alpha_update,
    )
    bpy.types.Scene.landfall_grid_finite = bpy.props.BoolProperty(
        name="Finite grid",
        description=(
            "Draw a bounded grid like Maya's instead of Blender's infinite "
            "floor. Blender's own grid_lines setting has no effect in "
            "perspective view, so the floor is replaced rather than resized"
        ),
        default=True,
        update=_grid_finite_update,
    )
    bpy.types.Scene.landfall_grid_follow_theme = bpy.props.BoolProperty(
        name="Grid follows the theme",
        description=(
            "Take the color from the theme's own grid entry, so the finite "
            "grid stays right whichever theme is loaded. Grid shade drives "
            "that entry, so one slider controls both grids"
        ),
        default=True,
    )
    bpy.types.Scene.landfall_grid_color = bpy.props.FloatVectorProperty(
        name="Grid color",
        description=(
            "Color of the finite grid. Separate from Grid shade, which sets "
            "the theme color of Blender's own grid: a value that reads well "
            "on one background is invisible on the other"
        ),
        subtype="COLOR", size=4,
        default=(0.42, 0.42, 0.42, 1.0), min=0.0, max=1.0,
    )
    bpy.types.Scene.landfall_grid_size = bpy.props.IntProperty(
        name="Grid size", description="Number of cells across",
        default=22, min=2, max=400,
    )
    bpy.types.Scene.landfall_grid_cell = bpy.props.FloatProperty(
        name="Cell size", description="Size of one cell in scene units",
        default=1.0, min=0.001, max=100.0,
    )
    bpy.types.Scene.landfall_cage_show = bpy.props.BoolProperty(
        name="Cage",
        description=(
            "Draw the original cage around the subdivided surface, the way "
            "Maya's 2 does. Blender's own wireframe follows the smooth mesh "
            "instead"
        ),
        default=False,
        update=_cage_show_update,
    )
    bpy.types.Scene.landfall_cage_width = bpy.props.FloatProperty(
        name="Cage width", default=1.6, min=1.0, max=8.0
    )
    bpy.types.Scene.landfall_cage_color = bpy.props.FloatVectorProperty(
        name="Cage color", subtype="COLOR", size=4,
        default=(0.26, 1.0, 0.64, 0.9), min=0.0, max=1.0,
    )
    bpy.types.Scene.landfall_cage_color_idle = bpy.props.FloatVectorProperty(
        name="Cage color, unselected",
        description="Maya draws the cage of deselected objects in dark blue",
        subtype="COLOR", size=4,
        default=(0.0, 0.016, 0.376, 0.9), min=0.0, max=1.0,
    )
    bpy.types.Scene.landfall_cage_xray = bpy.props.BoolProperty(
        name="Cage through the surface",
        description=(
            "Off by default, like Maya: the parts of the cage behind the "
            "smooth surface are hidden"
        ),
        default=False,
    )
    bpy.types.Scene.landfall_cage_selected_only = bpy.props.BoolProperty(
        name="Cage on the selection only",
        description=(
            "Off by default, like Maya: the cage stays visible on deselected "
            "objects too, in the second color"
        ),
        default=False,
    )
    bpy.types.Scene.landfall_grid_shade = bpy.props.FloatProperty(
        name="Grid shade",
        description=(
            "Brightness of the floor grid. Maya's own value is 0.25, but "
            "Blender fades the grid with distance and angle, so a darker "
            "setting reads closer to Maya"
        ),
        default=0.19,
        min=0.0,
        max=1.0,
        update=_grid_update,
    )
    bpy.types.Scene.landfall_object_color = bpy.props.FloatVectorProperty(
        name="Custom color",
        description="Free color for the selected objects",
        subtype="COLOR",
        size=3,
        default=(0.3, 0.6, 0.9),
        min=0.0,
        max=1.0,
    )
    bpy.types.Scene.landfall_border_show = bpy.props.BoolProperty(
        name="Border edges",
        description="Draw open border edges thicker, in object and edit mode",
        default=False,
        update=_border_show_update,
    )
    bpy.types.Scene.landfall_border_width = bpy.props.FloatProperty(
        name="Width",
        description="Thickness of the border edge lines, in pixels",
        default=3.0,
        min=1.0,
        max=12.0,
    )
    bpy.types.Scene.landfall_border_color = bpy.props.FloatVectorProperty(
        name="Color",
        description="Color of the border edge lines",
        subtype="COLOR",
        size=4,
        default=(1.0, 0.35, 0.1, 1.0),
        min=0.0,
        max=1.0,
    )
    bpy.types.Scene.landfall_border_selected_only = bpy.props.BoolProperty(
        name="Selected only",
        description="Draw borders only on the selected objects",
        default=True,
    )

    bpy.types.Scene.landfall_levels = bpy.props.IntProperty(
        name="Subdivisions",
        description="Subdivision level used by the smooth preview buttons",
        default=2,
        min=1,
        max=6,
        update=_levels_update,
    )



# The three overlays, drawn after the scene in every 3D viewport. Their
# handles live here rather than in three globals with three pairs of
# enable/disable functions that differed only by name.
_DRAW = {"borders": _draw_borders, "cage": _draw_cage, "grid": _draw_grid}
_draw_handles = {}


def _draw_handlers(on):
    for name, fn in _DRAW.items():
        handle = _draw_handles.pop(name, None)
        if handle is not None:
            try:
                bpy.types.SpaceView3D.draw_handler_remove(handle, "WINDOW")
            except Exception:
                pass
        if on:
            _draw_handles[name] = bpy.types.SpaceView3D.draw_handler_add(
                fn, (), "WINDOW", "POST_VIEW")


def _close_floating(*args):
    """The modal operators behind the sheet and the marking menu die with
    the file they were started in; their draw handlers did not, and a new
    file opened with a sheet nobody could close."""
    _sheet_stop()
    _mm_stop()


# Every handler in one table, so register and unregister cannot disagree
# about what was added. A new file, an undo and a redo all rebuild the
# datablocks, so the caches go as a whole in those three cases.
HANDLERS = (
    ("depsgraph_update_post", _on_depsgraph),
    ("depsgraph_update_post", _wire_follow_mode),
    ("load_post", _clear_all_caches),
    ("load_post", _close_floating),
    ("load_post", _wire_reset),
    ("load_post", _grid_sync),
    ("load_post", _gizmos_load),
    ("load_post", _keymap_heal_load),
    ("undo_post", _clear_all_caches),
    ("redo_post", _clear_all_caches),
)

TIMERS = (_gizmos_sync, _keymap_heal)


def _deferred_sync():
    # During register Blender hands out a restricted context in which the
    # window list is not reachable yet, so both of these would run on nothing.
    # A timer defers them to the first moment the real context exists.
    _wire_reset()
    _grid_sync()
    return None


def _register_handlers():
    for name, fn in HANDLERS:
        lista = getattr(bpy.app.handlers, name)
        if fn not in lista:
            lista.append(fn)
    _gizmos_attempts[0] = 0
    _heal_attempts[0] = 0
    _start_timer(_gizmos_sync, 0.2)
    _start_timer(_keymap_heal, 0.4)
    _start_timer(_deferred_sync, 0.1)


def _register_keymaps(wm):
    kc = wm.keyconfigs.addon
    if kc is not None:
        # Blender checks a mode's own keymap before the general 3D View one,
        # so the same items go into every mode or they never fire in Sculpt,
        # Paint or Pose.
        # Keymaps where a shortcut of ours would shadow something Blender
        # already uses for that mode. Checked against the real user keymap
        # rather than assumed.
        skip = {
            "gizmos": {"Sculpt", "Pose"},        # face set edit, bone options
            "smooth": {"Sculpt"},                # multires levels on Alt+1/2
            "snap": {"Pose"},                    # bendy bone resize
        }

        for km_name, space in KEYMAP_TARGETS:
            try:
                km = kc.keymaps.new(name=km_name, space_type=space)
            except Exception:
                continue

            kmi = km.keymap_items.new("wm.call_menu_pie", "Q", "PRESS", shift=True)
            kmi.properties.name = "VIEW3D_MT_landfall_pie"
            _keymaps.append((km, kmi))

            kmi = km.keymap_items.new("landfall.hotbox", "Q", "PRESS", alt=True)
            _keymaps.append((km, kmi))

            if km_name not in skip["gizmos"]:
                kmi = km.keymap_items.new("landfall.toggle_gizmos", "W",
                                          "PRESS", alt=True)
                _keymaps.append((km, kmi))

            # Shift+Alt+X, not S: in Edit Mode Blender has To Sphere on
            # Shift+Alt+S, the shortcut every tutorial uses to round a hole,
            # and the pie hid it. X is Maya's snap-to-grid key, and the
            # combination is free in every keymap listed here — checked
            # against Blender 5.2's own configuration.
            if km_name not in skip["snap"]:
                kmi = km.keymap_items.new("wm.call_menu_pie", "X", "PRESS",
                                          shift=True, alt=True)
                kmi.properties.name = "VIEW3D_MT_landfall_snap_pie"
                _keymaps.append((km, kmi))

            if km_name == "Mesh":
                kmi = km.keymap_items.new("wm.call_menu_pie", "Q", "PRESS",
                                          shift=True, alt=True)
                kmi.properties.name = "VIEW3D_MT_landfall_model_pie"
                _keymaps.append((km, kmi))

            if km_name not in skip["smooth"]:
                for key, mode in (("ONE", "CAGE"), ("TWO", "BOTH"),
                                  ("THREE", "SMOOTH")):
                    kmi = km.keymap_items.new("landfall.smooth_preview", key,
                                              "PRESS", alt=True)
                    kmi.properties.mode = mode
                    _keymaps.append((km, kmi))

        kmw = kc.keymaps.new(name="Window")
        kmi = kmw.keymap_items.new("landfall.project_save_as", "S", "PRESS",
                                   ctrl=True, shift=True)
        _keymaps.append((kmw, kmi))
        kmi = kmw.keymap_items.new("landfall.project_open", "O", "PRESS",
                                   ctrl=True)
        _keymaps.append((kmw, kmi))



def register():
    for cls in CLASSES + PROP_PANELS:
        bpy.utils.register_class(cls)

    _register_properties()
    _register_handlers()
    _register_keymaps(bpy.context.window_manager)

    # The three draw handlers stay registered for the whole life of the
    # add-on; the scene flags decide whether they draw anything, and a flag
    # that is off costs one comparison per redraw. Adding them only from the
    # buttons' update callbacks meant that a file saved with an overlay on,
    # or the add-on re-enabled over such a scene, showed the button lit and
    # drew nothing until it was switched off and on again.
    _draw_handlers(True)

    _define_macro()

    p = prefs(bpy.context)
    if p is not None:
        if p.maya_extrude:
            _extrude_enable(bpy.context)
        if p.maya_navigation:
            _maya_nav_enable(bpy.context)
        if p.marking_menu:
            _marking_enable(bpy.context)
        if p.backspace_deletes:
            _delete_enable(bpy.context)


def unregister():
    _extrude_disable()
    _delete_disable()
    _marking_disable()
    _sheet_stop()
    _maya_nav_disable()
    _draw_handlers(False)
    _clear_border_cache()
    _clear_cage_cache()
    _border_recent.clear()
    _border_batches.clear()
    _cage_batches.clear()

    # Every handler registered above has to come back off, or the draw calls
    # and the mode watcher keep running after the add-on is disabled. The
    # timers too: a pending one would otherwise fire into a module that is
    # no longer registered.
    for name, fn in HANDLERS:
        lista = getattr(bpy.app.handlers, name)
        if fn in lista:
            lista.remove(fn)
    for fn in TIMERS + (_deferred_sync,):
        _stop_timer(fn)

    _remove_kmis(_keymaps)

    for cls in reversed(CLASSES + PROP_PANELS):
        bpy.utils.unregister_class(cls)

    for prop in (
        "landfall_levels",
        "landfall_border_show",
        "landfall_border_width",
        "landfall_border_color",
        "landfall_border_selected_only",
        "landfall_object_color",
        "landfall_grid_shade",
        "landfall_xray_alpha",
        "landfall_grid_finite",
        "landfall_grid_color",
        "landfall_grid_follow_theme",
        "landfall_grid_size",
        "landfall_grid_cell",
        "landfall_cage_show",
        "landfall_cage_width",
        "landfall_cage_color",
        "landfall_cage_color_idle",
        "landfall_cage_xray",
        "landfall_cage_selected_only",
    ):
        if hasattr(bpy.types.Scene, prop):
            delattr(bpy.types.Scene, prop)

