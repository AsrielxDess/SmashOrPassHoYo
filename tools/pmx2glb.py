"""Convert an official HoYoverse MMD model (PMX) to a web-ready GLB with two looping animations.

Usage:
  blender -b --python tools/pmx2glb.py -- <in.pmx> <out.glb> [--walk <walk.vmd>]

- Materials: unlit, alpha cut-out, double-sided (anime look, no sorting bugs).
- "Idle": procedural standing loop (arms down, breathing).
- "Walk": a looping MMD walk cycle (VMD) applied as-is (in place).
- Both animations are played with the model's own MMD physics (hair, skirt, tail...)
  simulated under gravity for several cycles, then baked to keyframes; the last cycle
  is kept and its seam is blended so it loops cleanly.
"""
import sys, math, json, struct, re
import bpy, bmesh, addon_utils
from mathutils import Quaternion, Vector

argv = sys.argv[sys.argv.index("--") + 1:]
src, dst = argv[0], argv[1]
walk_vmd = argv[argv.index("--walk") + 1] if "--walk" in argv else None
MMD_SCALE = 0.08
FPS = 30


def enable_mmd_tools():
    for mod in ("bl_ext.user_default.mmd_tools", "mmd_tools"):
        try:
            addon_utils.enable(mod, default_set=True)
            return
        except Exception:
            pass


enable_mmd_tools()
bpy.ops.wm.read_factory_settings(use_empty=True)
enable_mmd_tools()
scene = bpy.context.scene
scene.render.fps = FPS

bpy.ops.mmd_tools.import_model(filepath=src, scale=MMD_SCALE, types={'MESH', 'ARMATURE', 'PHYSICS'})
root = next(o for o in bpy.data.objects if getattr(o, 'mmd_type', '') == 'ROOT')
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
PB = arm.pose.bones


def select_only(ob):
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob


select_only(root)
if not root.mmd_root.is_built:
    bpy.ops.mmd_tools.build_rig()
print("physics:", sum(1 for o in bpy.data.objects if getattr(o, 'mmd_type', '') == 'RIGID_BODY'), "rigid bodies")

# ---------- Materials ----------
def is_overlay(mat):
    if not (mat and mat.use_nodes):
        return False
    base = next((n.image for n in mat.node_tree.nodes
                 if n.type == 'TEX_IMAGE' and n.name == 'mmd_base_tex' and n.image), None)
    if base is None:   # no base texture: an outline/effect layer if its only texture is a toon ramp
        imgs = [n.image for n in mat.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image]
        return bool(imgs) and all(i.name.lower().startswith('toon') for i in imgs)
    # base texture is a sphere map (sp, sh, spa_h, hair_spa, 髮sph+...) or a toon ramp:
    # these layers are additive highlights / outlines in MMD and turn opaque (dark) in glTF
    stem = re.sub(r'\.[a-z0-9]+$', '', base.name.lower())
    return bool(re.match(r'^(sp|sh|spa|sph)(_[a-z0-9]+)?$', stem) or 'sph' in stem or 'spa' in stem
                or stem.startswith('toon'))

char_meshes = [o for o in bpy.data.objects if o.type == 'MESH' and o.parent == arm]
for ob in char_meshes:
    bad = {i for i, s in enumerate(ob.material_slots) if is_overlay(s.material)}
    if bad:   # sphere-map overlay layers: additive in MMD, opaque in glTF -> they hide the hair
        print("dropping overlay materials", [ob.material_slots[i].material.name for i in bad])
        bm = bmesh.new(); bm.from_mesh(ob.data)
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index in bad], context='FACES')
        bm.to_mesh(ob.data); bm.free()

for mat in {s.material for o in char_meshes for s in o.material_slots if s.material}:
    nt = mat.node_tree
    tex_img = next((n.image for n in nt.nodes if n.type == 'TEX_IMAGE' and n.image and n.name == 'mmd_base_tex'), None) \
        or next((n.image for n in nt.nodes if n.type == 'TEX_IMAGE' and n.image), None)
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
    nt.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    if tex_img:
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = tex_img
        nt.links.new(t.outputs['Color'], bsdf.inputs['Base Color'])
        nt.links.new(t.outputs['Alpha'], bsdf.inputs['Alpha'])

# ---------- Action helpers (Blender 4.4+ layered actions, with legacy fallback) ----------
def fcurves(act):
    if hasattr(act, 'layers') and len(act.layers):
        return [fc for l in act.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]
    return list(getattr(act, 'fcurves', []))


def assign(act):
    arm.animation_data_create()
    arm.animation_data.action = act
    if hasattr(arm.animation_data, 'action_slot') and act and len(getattr(act, 'slots', [])):
        arm.animation_data.action_slot = act.slots[0]


def make_cyclic(act):
    for fc in fcurves(act):
        if not any(m.type == 'CYCLES' for m in fc.modifiers):
            fc.modifiers.new('CYCLES')


def reset_pose():
    for pb in PB:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = Quaternion(); pb.location = (0, 0, 0); pb.scale = (1, 1, 1)

# ---------- Idle (procedural, 120 frames) ----------
X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))   # model faces -Y, its left is +X

def q(name, *rots):
    m = PB[name].bone.matrix_local.to_3x3().inverted()
    out = Quaternion()
    for axis, deg in rots:
        out = Quaternion((m @ axis).normalized(), math.radians(deg)) @ out
    return out

def key(name, quat=None, loc=None, f=0):
    if name not in PB:
        return
    pb = PB[name]
    if quat is not None:
        pb.rotation_quaternion = quat
        pb.keyframe_insert('rotation_quaternion', frame=f)
    if loc is not None:
        pb.location = pb.bone.matrix_local.to_3x3().inverted() @ loc
        pb.keyframe_insert('location', frame=f)

def build_idle(length=120):
    reset_pose()
    act = bpy.data.actions.new('Idle_src'); assign(act)
    for f in range(0, length + 1, 5):
        p = 2 * math.pi * f / length
        s = math.sin(p)
        key('腕.L', q('腕.L', (Y, 45 + 2 * s)), f=f + 1)
        key('腕.R', q('腕.R', (Y, -45 - 2 * s)), f=f + 1)
        key('ひじ.L', q('ひじ.L', (Z, -15)), f=f + 1)
        key('ひじ.R', q('ひじ.R', (Z, 15)), f=f + 1)
        key('上半身2', q('上半身2', (X, 1.5 * s)), f=f + 1)
        key('頭', q('頭', (Z, 3 * math.sin(p + 0.8)), (X, -1.5 * s)), f=f + 1)
        key('センター', loc=Vector((0, 0, 0.004 * s)), f=f + 1)
        key('腰', q('腰', (Y, 1.5 * math.sin(p + 1))), f=f + 1)
    return act, length

def build_walk(path):
    reset_pose()
    select_only(root)
    bpy.ops.mmd_tools.import_vmd(filepath=path, scale=MMD_SCALE, margin=0)
    act = arm.animation_data.action
    start, end = act.frame_range
    period = int(round(end - start))
    # shift so the cycle starts at frame 1
    if int(start) != 1:
        for fc in fcurves(act):
            for kp in fc.keyframe_points:
                kp.co.x += 1 - start; kp.handle_left.x += 1 - start; kp.handle_right.x += 1 - start
    act.name = 'Walk_src'
    return act, period

# ---------- Physics bake ----------
def bake_with_physics(name, src_act, period, cycles):
    assign(src_act)
    make_cyclic(src_act)
    total = 1 + period * cycles
    rbw = scene.rigidbody_world
    rbw.point_cache.frame_start = 1
    rbw.point_cache.frame_end = total + 1
    scene.frame_start, scene.frame_end = 1, total
    scene.frame_set(1)
    select_only(arm)
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.pose.select_all(action='SELECT')
    bpy.ops.nla.bake(frame_start=1, frame_end=total, step=1, only_selected=False,
                     visual_keying=True, clear_constraints=False, clear_parents=False,
                     use_current_action=False, clean_curves=False, bake_types={'POSE'})
    bpy.ops.object.mode_set(mode='OBJECT')
    baked = arm.animation_data.action
    baked.name = name
    keep0 = total - period
    seam = min(8, period // 3)
    for fc in fcurves(baked):
        kps = fc.keyframe_points
        for kp in list(kps)[::-1]:
            if kp.co.x < keep0:
                kps.remove(kp)
        for kp in kps:
            kp.co.x -= keep0; kp.handle_left.x -= keep0; kp.handle_right.x -= keep0
            kp.interpolation = 'LINEAR'
    # seam blend: make frame `period` match frame 0 (quaternion sign-aware)
    groups = {}
    for fc in fcurves(baked):
        groups.setdefault(fc.data_path, {})[fc.array_index] = fc
    for path, comps in groups.items():
        idx = sorted(comps)
        v0 = [comps[i].evaluate(0) for i in idx]
        vN = [comps[i].evaluate(period) for i in idx]
        if path.endswith('rotation_quaternion') and sum(a * b for a, b in zip(v0, vN)) < 0:
            v0 = [-a for a in v0]
        for j, i in enumerate(idx):
            d = v0[j] - vN[j]
            if abs(d) < 1e-6:
                continue
            for kp in comps[i].keyframe_points:
                t = kp.co.x
                if t > period - seam:
                    w = (t - (period - seam)) / seam
                    kp.co.y += d * (w * w * (3 - 2 * w))
    tr = arm.animation_data.nla_tracks.new(); tr.name = name
    tr.strips.new(name, 0, baked)
    arm.animation_data.action = None
    print("baked", name, "period", period, "frames")

idle_act, idle_len = build_idle()
bake_with_physics('Idle', idle_act, idle_len, cycles=3)
if walk_vmd:
    walk_act, walk_len = build_walk(walk_vmd)
    bake_with_physics('Walk', walk_act, walk_len, cycles=5)

# ---------- Strip the rig: bone constraints off (the bake holds the result), export only the character ----------
# (deleting rigid bodies / joints crashes Blender 5.3, so they are simply left out of the export selection)
for pb in PB:
    for c in list(pb.constraints):
        pb.constraints.remove(c)
scene.rigidbody_world.enabled = False
arm.animation_data.action = None
if arm.parent:
    mw = arm.matrix_world.copy(); arm.parent = None; arm.matrix_world = mw
bpy.ops.object.select_all(action='DESELECT')
arm.select_set(True)
for o in char_meshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = arm

bpy.ops.export_scene.gltf(
    filepath=dst, export_format='GLB', use_selection=True,
    export_draco_mesh_compression_enable=True,
    export_image_format='WEBP',
    export_animations=True, export_animation_mode='NLA_TRACKS',
    export_force_sampling=True, export_morph=False,
)

# ---------- Post-process the GLB JSON: unlit, alpha cut-out, double-sided ----------
def patch_glb(path):
    b = open(path, 'rb').read()
    jlen = struct.unpack('<I', b[12:16])[0]
    j = json.loads(b[20:20 + jlen])
    for m in j.get('materials', []):
        m['alphaMode'] = 'MASK'; m['alphaCutoff'] = 0.5; m['doubleSided'] = True
        m.setdefault('extensions', {})['KHR_materials_unlit'] = {}
        m.pop('emissiveFactor', None)
    used = j.setdefault('extensionsUsed', [])
    if 'KHR_materials_unlit' not in used:
        used.append('KHR_materials_unlit')
    js = json.dumps(j, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    js += b' ' * ((4 - len(js) % 4) % 4)
    rest = b[20 + jlen:]
    open(path, 'wb').write(struct.pack('<III', 0x46546C67, 2, 20 + len(js) + len(rest))
                           + struct.pack('<II', len(js), 0x4E4F534A) + js + rest)

patch_glb(dst)
print("EXPORTED", dst)
