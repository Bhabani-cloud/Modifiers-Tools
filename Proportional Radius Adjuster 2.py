bl_info = {
    "name": "Proportional Radius Adjuster with HUD (4.4+)",
    "author": "Bhabani Tudu",
    "version": (1, 0),
    "blender": (4, 4, 0),
    "location": "3D Viewport",
    "description": "Hold D and drag mouse to adjust proportional editing radius with real-time HUD",
    "category": "3D View"
}

import bpy
import blf
import gpu
import math
from gpu_extras.batch import batch_for_shader
from bpy_extras import view3d_utils
from mathutils import Vector


def draw_callback_px(self, context):
    font_id = 4
    blf.position(font_id, 100, 50, 1)
    blf.size(font_id, 30)
    blf.color(font_id, 0.00, 0.233, 0.093, 1.0)
#    blf.color(font_id, 1.0, 1.0, 1.0, 1.0) ## White font
    blf.draw(font_id, f"Proportional Size: {context.tool_settings.proportional_size:.2f}")

    region = context.region
    rv3d = context.region_data
    obj = context.active_object

    if obj and obj.mode == 'EDIT':
        mesh = obj.data
        bm = bpy.context.object.data

        selected = []
        if mesh.total_vert_sel > 0:
            selected = [v.co for v in mesh.vertices if v.select]
        elif mesh.total_edge_sel > 0:
            selected = [(mesh.vertices[e.vertices[0]].co + mesh.vertices[e.vertices[1]].co) / 2
                        for e in mesh.edges if e.select]
        elif mesh.total_face_sel > 0:
            selected = [f.center for f in mesh.polygons if f.select]

        if selected:
            center = sum((obj.matrix_world @ co for co in selected), Vector()) / len(selected)
            center_2d = view3d_utils.location_3d_to_region_2d(region, rv3d, center)

            if center_2d:
                shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
                gpu.state.blend_set('ALPHA')

                radius = context.tool_settings.proportional_size * 50
                segments = 64
                circle = []
                for i in range(segments + 1):
                    angle = 2 * math.pi * i / segments
                    x = center_2d[0] + radius * math.cos(angle)
                    y = center_2d[1] + radius * math.sin(angle)
                    circle.append((x, y))

                shader.bind()
                shader.uniform_float("color", (1.0, 1.0, 1.0, 0.6))
                batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": circle})
                batch.draw(shader)
                gpu.state.blend_set('NONE')


class ProportionalAdjustOperator(bpy.types.Operator):
    bl_idname = "view3d.proportional_adjust"
    bl_label = "Adjust Proportional Size"

    initial_mouse_x: bpy.props.IntProperty()
    initial_size: bpy.props.FloatProperty()
    is_adjusting: bpy.props.BoolProperty(default=False)
    _handle = None

    @classmethod
    def poll(cls, context):
        return (context.active_object and
                context.active_object.mode == 'EDIT' and
                context.tool_settings.use_proportional_edit)

    def modal(self, context, event):
        if event.type == 'D' and event.value == 'PRESS':
            self.is_adjusting = True
            self.initial_mouse_x = event.mouse_x
            self.initial_size = context.tool_settings.proportional_size

            if not self._handle:
                args = (self, context)
                self._handle = bpy.types.SpaceView3D.draw_handler_add(draw_callback_px, args, 'WINDOW', 'POST_PIXEL')
            context.area.tag_redraw()
            return {'RUNNING_MODAL'}

        if event.type == 'D' and event.value == 'RELEASE':
            self.is_adjusting = False
            if self._handle:
                bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
                self._handle = None
            context.area.tag_redraw()
            return {'RUNNING_MODAL'}

        if self.is_adjusting and event.type == 'MOUSEMOVE':
            delta = (event.mouse_x - self.initial_mouse_x) * 0.005
            context.tool_settings.proportional_size = max(0.01, self.initial_size + delta)
            context.area.tag_redraw()
            return {'RUNNING_MODAL'}

        if event.type in {'LEFTMOUSE', 'RIGHTMOUSE', 'ESC'}:
            if self._handle:
                bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
                self._handle = None
            return {'FINISHED'}

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        if context.area.type != 'VIEW_3D':
            return {'CANCELLED'}

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}


addon_keymaps = []

def register():
    bpy.utils.register_class(ProportionalAdjustOperator)

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name='Mesh', space_type='EMPTY')
        kmi = km.keymap_items.new(ProportionalAdjustOperator.bl_idname, 'D', 'PRESS')
        addon_keymaps.append((km, kmi))
        


def unregister():
    bpy.utils.unregister_class(ProportionalAdjustOperator)
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()
    


if __name__ == "__main__":
    register()