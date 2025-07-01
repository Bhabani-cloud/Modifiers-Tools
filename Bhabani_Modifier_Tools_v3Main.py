bl_info = {
    "name": "Bhabani Modifier Tools 3.3delux",
    "author": "Bhabani Tudu",
    "version": (1, 1),
    "blender": (4, 4, 0),
    "location": "View3D > Sidebar > Modifier Tools",
    "description": "Toggle a modifier's visibility, sync shading, and toggle Emulate 3 Button Mouse",
    "category": "Object",
}

import bpy
import math
import bmesh

addon_keymaps = []

# ===========================
# Operators
# ===========================

class OBJECT_OT_toggle_modifier_and_shading(bpy.types.Operator):
    bl_idname = "object.toggle_modifier_shading"
    bl_label = "Toggle Modifier + Shading"
    bl_options = {'REGISTER', 'UNDO'}

    modifier_name: bpy.props.StringProperty(
        name="Modifier Name",
        default="Subdivision"
    )

    def execute(self, context):
        for obj in context.selected_objects:
            mod = obj.modifiers.get(self.modifier_name)
            if not mod:
                continue

            mod.show_viewport = not mod.show_viewport
            context.view_layer.objects.active = obj

            if context.mode == 'OBJECT':
                if mod.show_viewport:
                    bpy.ops.object.shade_smooth()
                else:
                    bpy.ops.object.shade_flat()

            elif context.mode == 'EDIT_MESH':
                bm = bmesh.from_edit_mesh(obj.data)
                for face in bm.faces:
                    face.smooth = False
                bmesh.update_edit_mesh(obj.data)

        return {'FINISHED'}


class PREFERENCES_OT_toggle_emulate_3_button_mouse(bpy.types.Operator):
    bl_idname = "preferences.toggle_emulate_3_button_mouse"
    bl_label = "Toggle Emulate 3 Button Mouse"

    def execute(self, context):
        try:
            prefs = bpy.context.preferences
            inputs = prefs.inputs
            inputs.use_mouse_emulate_3_button = not inputs.use_mouse_emulate_3_button
            self.report({'INFO'}, f"Emulate 3 Button Mouse: {inputs.use_mouse_emulate_3_button}")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Preferences not ready. Try opening Preferences once. ({e})")
            return {'CANCELLED'}


class PREFERENCES_OT_toggle_auto_perspective(bpy.types.Operator):
    bl_idname = "preferences.toggle_auto_perspective"
    bl_label = "Toggle Auto Perspective"

    def execute(self, context):
        prefs = bpy.context.preferences.inputs
        prefs.use_auto_perspective = not prefs.use_auto_perspective
        self.report({'INFO'}, f"Auto Perspective: {prefs.use_auto_perspective}")
        return {'FINISHED'}


class BMT_OT_gizmo_resize_modal(bpy.types.Operator):
    bl_idname = "wm.gizmo_resize_modal"
    bl_label = "Gizmo Resize Modal"
    bl_options = {'REGISTER'}

    start_mouse_x: bpy.props.IntProperty()
    start_gizmo_size: bpy.props.IntProperty()

    def modal(self, context, event):
        if event.type == 'MOUSEMOVE':
            delta = event.mouse_x - self.start_mouse_x
            new_size = self.start_gizmo_size + delta
            context.preferences.view.gizmo_size = max(20, min(200, new_size))
            return {'RUNNING_MODAL'}

        if event.type in {'ESC', 'F'} and event.value == 'RELEASE' and event.shift:
            return {'FINISHED'}

        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        self.start_mouse_x = event.mouse_x
        self.start_gizmo_size = context.preferences.view.gizmo_size
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}


# ===========================
# Panel
# ===========================

class VIEW3D_PT_modifier_shading_panel(bpy.types.Panel):
    bl_label = "Modifier Tools"
    bl_idname = "VIEW3D_PT_modifier_shading_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Modifier Tools'
    
    def draw(self, context):
        layout = self.layout
        layout.operator("preferences.toggle_auto_perspective", icon="VIEW_PERSPECTIVE")
        layout.operator("preferences.toggle_emulate_3_button_mouse", icon="MOUSE_LMB")
        layout.operator("object.toggle_modifier_shading", icon="SHADING_SOLID")
        layout.label(text="⚠️ If Emulate 3 Button fails at startup, open Preferences once.")
        BMT_UI_gizmo_size.draw(layout, context)


# ===========================
# Gizmo Size UI
# ===========================

class BMT_UI_gizmo_size:
    @staticmethod
    def draw(layout, context):
        layout.prop(context.preferences.view, "gizmo_size", text="Gizmo Size")


# ===========================
# Registration
# ===========================

classes = [
    OBJECT_OT_toggle_modifier_and_shading,
    PREFERENCES_OT_toggle_emulate_3_button_mouse,
    PREFERENCES_OT_toggle_auto_perspective,
    VIEW3D_PT_modifier_shading_panel,
    BMT_OT_gizmo_resize_modal
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        # Screen keymap for Object Mode
        km = kc.keymaps.new(name='Screen', space_type='EMPTY')
        # Mesh keymap for Edit Mode
        km_mesh = kc.keymaps.new(name='Mesh', space_type='EMPTY')

        # Shortcuts
        kmi1 = km.keymap_items.new(
            PREFERENCES_OT_toggle_emulate_3_button_mouse.bl_idname,
            type='ONE', value='PRESS', ctrl=True, shift=True
        )
        kmi2 = km.keymap_items.new(
            PREFERENCES_OT_toggle_auto_perspective.bl_idname,
            type='TWO', value='PRESS', ctrl=True, shift=True
        )
        kmi3 = km.keymap_items.new(
            BMT_OT_gizmo_resize_modal.bl_idname,
            type='F', value='PRESS', shift=True
        )
        kmi4 = km.keymap_items.new(
            OBJECT_OT_toggle_modifier_and_shading.bl_idname,
            type='R', value='PRESS', alt=True, shift=True
        )
        # Add same shortcut for Edit Mode
        kmi4_mesh = km_mesh.keymap_items.new(
            OBJECT_OT_toggle_modifier_and_shading.bl_idname,
            type='R', value='PRESS', alt=True, shift=True
        )

        addon_keymaps.extend([
            (km, kmi1), (km, kmi2), (km, kmi3), (km, kmi4),
            (km_mesh, kmi4_mesh)
        ])


    # Force-load preferences to avoid early-context issues
    try:
        _ = bpy.context.preferences.inputs.use_mouse_emulate_3_button
    except:
        pass


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()


if __name__ == "__main__":
    register()
