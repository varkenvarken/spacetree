# ##### BEGIN GPL LICENSE BLOCK #####
#
#  SCA Tree Generator, a Blender addon
#  (c) 2013, 2014 Michel J. Anders (varkenvarken)
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

bl_info = {
    "name": "SCA Tree Generator",
    "author": "michel anders (varkenvarken)",
    "version": (0, 2, 14),
    "blender": (2, 70, 0),
    "location": "View3D > Add > Mesh",
    "description": "Adds a tree created with the space colonization algorithm starting at the 3D cursor",
    "warning": "",
    "wiki_url": "https://github.com/varkenvarken/spacetree/wiki",
    "tracker_url": "",
    "category": "Add Mesh"}

from time import time
from random import random,gauss
from functools import partial
from math import sin,cos

import bpy
from bpy.props import FloatProperty, IntProperty, BoolProperty, EnumProperty
from mathutils import Vector,Euler,Matrix,Quaternion

from .scanew import SCA, Branchpoint # the core class that implements the space colonization algorithm and the definition of a segment
from .timer import Timer
from .utils import load_materials_from_bundled_lib, load_particlesettings_from_bundled_lib, get_vertex_group

def availableGroups(self, context):
    return [(name, name, name, n) for n,name in enumerate(bpy.data.groups.keys())]

def availableGroupsOrNone(self, context):
    groups = [ ('None', 'None', 'None', 0) ]
    return groups + [(name, name, name, n+1) for n,name in enumerate(bpy.data.groups.keys())]

def availableObjects(self, context):
    return [(name, name, name, n+1) for n,name in enumerate(bpy.data.objects.keys())]

particlesettings = None
barkmaterials = None

def availableParticleSettings(self, context):
    global particlesettings
    # im am not sure why self.__class__.particlesettings != bpy.types.MESH_OT_sca_tree ....
    settings = [ ('None', 'None', 'None', 0) ]
    #    return settings + [(name, name, name, n+1) for n,name in enumerate(bpy.types.MESH_OT_sca_tree.particlesettings.keys())]
    # (identifier, name, description, number)
    # note, when we create a new tree the particles settings will be made unique so they can be tweaked individually for
    # each tree. That also means they will  have distinct names, but we manipulate those to be displayed in a consistent way
    return settings + [(name, name.split('.')[0], name, n+1) for n,name in enumerate(particlesettings.keys())]

def availableBarkMaterials(self, context):
    global barkmaterials
    return [(name, name.split('.')[0], name, n) for n,name in enumerate(barkmaterials.keys())]

def ellipsoid(r=5,rz=5,p=Vector((0,0,8)),taper=0):
    r2=r*r
    z2=rz*rz
    if rz>r : r = rz
    while True:
        x = (random()*2-1)*r
        y = (random()*2-1)*r
        z = (random()*2-1)*r
        f = (z+r)/(2*r)
        f = 1 + f*taper if taper>=0 else (1-f)*-taper
        if f*x*x/r2+f*y*y/r2+z*z/z2 <= 1:
            yield p+Vector((x,y,z))

def pointInsideMesh(pointrelativetocursor,ob):
    # adapted from http://blenderartists.org/forum/showthread.php?195605-Detecting-if-a-point-is-inside-a-mesh-2-5-API&p=1691633&viewfull=1#post1691633
    mat = ob.matrix_world.inverted()
    orig = mat*(pointrelativetocursor+bpy.context.scene.cursor_location)
    count = 0
    axis=Vector((0,0,1))
    while True:
        location,normal,index = ob.ray_cast(orig,orig+axis*10000.0)
        if index == -1: break
        count += 1
        orig = location + axis*0.00001
    if count%2 == 0:
        return False
    return True
    
def ellipsoid2(rxy=5,rz=5,p=Vector((0,0,8)),surfacebias=1,topbias=1):
    while True:
        phi = 6.283*random()
        theta = 3.1415*(random()-0.5)
        r = random()**((1.0/surfacebias)/2)
        x = r*rxy*cos(theta)*cos(phi)
        y = r*rxy*cos(theta)*sin(phi)
        st=sin(theta)
        st = (((st+1)/2)**(1.0/topbias))*2-1
        z = r*rz*st
        #print(">>>%.2f %.2f %.2f "%(x,y,z))
        m = p+Vector((x,y,z))
# undocumented feature: bombs if any selected object is not a mesh. Use crown and shadow/exclusion groups instead
#        reject = False
#        for ob in bpy.context.selected_objects:
#            # probably we should check if each object is a mesh
#            if pointInsideMesh(m,ob) :
#                reject = True
#                break
#        if not reject:
        yield m

def halton3D(index):
    """
    return a quasi random 3D vector R3 in [0,1].
    each component is based on a halton sequence. 
    quasi random is good enough for our purposes and is 
    more evenly distributed then pseudo random sequences. 
    See en.m.wikipedia.org/wiki/Halton_sequence
    """

    def halton(index, base):
        result=0
        f=1.0/base
        I=index
        while I>0:
            result += f*(I%base)
            I=int(I/base)
            f/=base
        return result
    return Vector((halton(index,2),halton(index,3),halton(index,5)))

def insidegroup(pointrelativetocursor, group):
    if bpy.data.groups.find(group)<0 : return False
    for ob in bpy.data.groups[group].objects:
        if isinstance(ob.data, bpy.types.Mesh) and pointInsideMesh(pointrelativetocursor,ob):
            return True
    return False

def groupdistribution(crowngroup,shadowgroup=None,shadowdensity=0.5, seed=0,size=Vector((1,1,1)),pointrelativetocursor=Vector((0,0,0))):
    if crowngroup == shadowgroup:
        shadowgroup = None # safeguard otherwise every marker would be rejected
    nocrowngroup = bpy.data.groups.find(crowngroup)<0
    noshadowgroup = (shadowgroup is None) or (bpy.data.groups.find(shadowgroup)<0) or (shadowgroup == 'None')
    index=100+seed
    nmarkers=0
    nyield=0
    while True:
        nmarkers+=1
        v = halton3D(index)
        v[0] *= size[0]
        v[1] *= size[1]
        v[2] *= size[2]
        v+=pointrelativetocursor
        index+=1
        insidecrown = nocrowngroup or insidegroup(v,crowngroup)
        outsideshadow = noshadowgroup # if there's no shadowgroup we're always outside of it
        if not outsideshadow:
            inshadow = insidegroup(v,shadowgroup) # if there is, check if we're inside the group
            if not inshadow:
                outsideshadow = True
            else:
                outsideshadow = random() > shadowdensity  # if inside the group we might still generate a marker if the density is low
        # if shadowgroup overlaps all or a significant part of the crowngroup
        # no markers will be yielded and we would be in an endless loop.
        # so if we yield too few correct markers we start yielding them anyway.
        lowyieldrate = (nmarkers>200) and (nyield/nmarkers < 0.01)
        if (insidecrown and outsideshadow) or lowyieldrate:
            nyield+=1
            yield v
        
def groupExtends(group):
    """
    return a size,minimum tuple both Vector elements, describing the size and position
    of the bounding box in world space that encapsulates all objects in a group.
    """
    bb=[]
    if bpy.data.groups.find(group) >=0 :
        for ob in bpy.data.groups[group].objects:
            rot = ob.matrix_world.to_quaternion()
            scale = ob.matrix_world.to_scale()
            translate = ob.matrix_world.translation
            for v in ob.bound_box: # v is not a vector but an array of floats
                p = ob.matrix_world * Vector(v[0:3])
                bb.extend(p[0:3])
        mx = Vector((max(bb[0::3]), max(bb[1::3]), max(bb[2::3])))
        mn = Vector((min(bb[0::3]), min(bb[1::3]), min(bb[2::3])))
        return mx-mn,mn
    return Vector((2,2,2)),Vector((-1,-1,-1)) # a 2x2x2 cube when the group does not exist
    
def createMarkers(tree,scale=0.05):
    #not used as markers are parented to tree object that is created at the cursor position
    #p=bpy.context.scene.cursor_location
    
    verts=[]
    faces=[]

    tetraeder = [Vector((-1,1,-1)),Vector((1,-1,-1)),Vector((1,1,1)),Vector((-1,-1,1))]
    tetraeder = [v * scale for v in tetraeder]
    tfaces = [(0,1,2),(0,1,3),(1,2,3),(0,3,2)]
    
    for eip,ep in enumerate(tree.endpoints):
        verts.extend([ep + v for v in tetraeder])
        n=len(faces)
        faces.extend([(f1+n,f2+n,f3+n) for f1,f2,f3 in tfaces])
        
    mesh = bpy.data.meshes.new('Markers')
    mesh.from_pydata(verts,[],faces)
    mesh.update(calc_edges=True)
    return mesh

def basictri(bp, verts, radii, power, scale, p):
    v = bp.v + p
    nv = len(verts)
    r=(bp.connections**power)*scale
    a=-r
    b=r*0.5   # cos(60)
    c=r*0.866 # sin(60)
    verts.extend([v+Vector((a,0,0)), v+Vector((b,-c,0)), v+Vector((b,c,0))]) # provisional, should become an optimally rotated triangle
    radii.extend([bp.connections,bp.connections,bp.connections])
    return (nv, nv+1, nv+2)
    
def _simpleskin(bp, loop, verts, faces, radii, power, scale, p):
    newloop = basictri(bp, verts, radii, power, scale, p)
    for i in range(3):
        faces.append((loop[i],loop[(i+1)%3],newloop[(i+1)%3],newloop[i]))
    if bp.apex:
        _simpleskin(bp.apex, newloop, verts, faces, radii, power, scale, p)
    if bp.shoot:
        _simpleskin(bp.shoot, newloop, verts, faces, radii, power, scale, p)
    
def simpleskin(bp, verts, faces, radii, power, scale, p):
    loop = basictri(bp, verts, radii, power, scale, p)
    if bp.apex:
        _simpleskin(bp.apex, loop, verts, faces, radii, power, scale, p)
    if bp.shoot:
        _simpleskin(bp.shoot, loop, verts, faces, radii, power, scale, p)

def leafnode(bp, verts, faces, radii, p1, p2, scale=0.1):
    loop1 = basictri(bp, verts, radii, 0.0, scale, p1)
    loop2 = basictri(bp, verts, radii, 0.0, scale, p2)
    for i in range(3):
        faces.append((loop1[i],loop1[(i+1)%3],loop2[(i+1)%3],loop2[i]))
    if bp.apex:
        leafnode(bp.apex, verts, faces, radii, p1, p2, scale)
    if bp.shoot:
        leafnode(bp.shoot, verts, faces, radii, p1, p2, scale)

def createLeaves2(tree, roots, p, scale):
    verts = []
    faces = []
    radii = []
    for r in roots:
        leafnode(r, verts, faces, radii, p, p++Vector((0,0, scale)), scale)
    mesh = bpy.data.meshes.new('LeafEmitter')
    mesh.from_pydata(verts, [], faces)
    mesh.update(calc_edges=True)
    return mesh, verts, faces, radii

def pruneTree(tree, generation):
    nbp = []
    i2p = {}
    #print()
    for i,bp in enumerate(tree):
        #print(i, bp.v, bp.generation, bp.parent, end='')
        if bp.generation >= generation:
            #print(' keep', end='')
            bp.index = i
            i2p[i] = len(nbp)
            nbp.append(bp)
        #print()
    return nbp, i2p
    
def createGeometry(tree, power=0.5, scale=0.01,
    nomodifiers=True, skinmethod='NATIVE', subsurface=False,
    bleaf=1.0,
    leafParticles='None',
    objectParticles='None',
    emitterscale=0.1,
    timeperf=True,
    prune=0):

    global particlesettings
    
    timings = Timer()
    
    p=bpy.context.scene.cursor_location
    verts=[]
    edges=[]
    faces=[]
    radii=[]
    roots=set()
    
    # prune if requested
    tree.branchpoints, index2position = pruneTree(tree.branchpoints, prune)
        
    # Loop over all branchpoints and create connected edges
    #print('\ngenerating skeleton')
    
    for n,bp in enumerate(tree.branchpoints):
        #print(n, bp.index, bp.v, bp.generation, bp.parent)
        verts.append(bp.v+p)
        radii.append(bp.connections)
        if not (bp.parent is None) :
            #print(bp.parent,index2position[bp.parent])
            edges.append((len(verts)-1,index2position[bp.parent]))
        else :
            nv=len(verts)
            roots.add(bp)
        bp.index=n
        
    timings.add('skeleton')
    
    # native skinning method
    if nomodifiers == False and skinmethod == 'NATIVE': 
        # add a quad edge loop to all roots
        for r in roots:
            simpleskin(r, verts, faces, radii, power, scale, p)
            
    # end of native skinning section
    timings.add('nativeskin')
    
    # create the (skinned) tree mesh
    mesh = bpy.data.meshes.new('Tree')
    mesh.from_pydata(verts, edges, faces)
    mesh.update(calc_edges=True)
    
    # create the tree object an make it the only selected and active object in the scene
    obj_new = bpy.data.objects.new(mesh.name, mesh)
    base = bpy.context.scene.objects.link(obj_new)
    for ob in bpy.context.scene.objects:
        ob.select = False
    base.select = True
    bpy.context.scene.objects.active = obj_new
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    
    # add a leaves vertex group
    leavesgroup = get_vertex_group(bpy.context, 'Leaves')
    
    maxr = max(radii) if len(radii)>0 else 0.03 # pruning might have been so aggressive that there are no radii (NB. python 3.3 does not know the default keyword for the max() fie
    if maxr<=0 : maxr=1.0
    maxr=float(maxr)
    for v,r in zip(mesh.vertices,radii):
        leavesgroup.add([v.index], (1.0-r/maxr)**bleaf, 'REPLACE')
    timings.add('createmesh')
    
    # add a subsurf modifier to smooth the branches 
    if nomodifiers == False:
        if subsurface:
            bpy.ops.object.modifier_add(type='SUBSURF')
            bpy.context.active_object.modifiers[0].levels = 1
            bpy.context.active_object.modifiers[0].render_levels = 1
            bpy.context.active_object.modifiers[0].use_subsurf_uv = True

        # add a skin modifier
        if skinmethod == 'BLENDER':
            bpy.ops.object.modifier_add(type='SKIN')
            bpy.context.active_object.modifiers[-1].use_smooth_shade=True
            bpy.context.active_object.modifiers[-1].use_x_symmetry=True
            bpy.context.active_object.modifiers[-1].use_y_symmetry=True
            bpy.context.active_object.modifiers[-1].use_z_symmetry=True

            skinverts = bpy.context.active_object.data.skin_vertices[0].data

            for i,v in enumerate(skinverts):
                v.radius = [(radii[i]**power)*scale,(radii[i]**power)*scale]
                if i in roots:
                    v.use_root = True
            
            # add an extra subsurf modifier to smooth the skin
            bpy.ops.object.modifier_add(type='SUBSURF')
            bpy.context.active_object.modifiers[-1].levels = 1
            bpy.context.active_object.modifiers[-1].render_levels = 2
            bpy.context.active_object.modifiers[-1].use_subsurf_uv = True

    timings.add('modifiers')

    # create a particles based leaf emitter (if we have leaves and/or objects)
    if leafParticles != 'None' or objectParticles != 'None':
        mesh, verts, faces, radii = createLeaves2(tree, roots, Vector((0,0,0)), emitterscale)
        obj_leaves2 = bpy.data.objects.new(mesh.name, mesh)
        base = bpy.context.scene.objects.link(obj_leaves2)
        obj_leaves2.parent = obj_new
        bpy.context.scene.objects.active = obj_leaves2
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
        # add a LeafDensity vertex group to the LeafEmitter object
        leavesgroup = get_vertex_group(bpy.context, 'LeafDensity')
        maxr = max(radii)
        if maxr<=0 : maxr=1.0
        maxr=float(maxr)
        for v,r in zip(mesh.vertices,radii):
            leavesgroup.add([v.index], (1.0-r/maxr)**bleaf, 'REPLACE')

        if leafParticles != 'None':
            bpy.ops.object.particle_system_add()
            obj_leaves2.particle_systems.active.settings = particlesettings[leafParticles]
            obj_leaves2.particle_systems.active.settings.count = len(faces)
            obj_leaves2.particle_systems.active.name = 'Leaves'
            obj_leaves2.particle_systems.active.vertex_group_density = leavesgroup.name
        if objectParticles != 'None':
            bpy.ops.object.particle_system_add()
            obj_leaves2.particle_systems.active.settings = particlesettings[objectParticles]
            obj_leaves2.particle_systems.active.settings.count = len(faces)
            obj_leaves2.particle_systems.active.name = 'Objects'
            obj_leaves2.particle_systems.active.vertex_group_density = leavesgroup.name
        
    bpy.context.scene.objects.active = obj_new
    bpy.ops.object.shade_smooth()
    
    timings.add('leaves')
    
    if timeperf:
        print(timings)
        
    return obj_new
    
class SCATree(bpy.types.Operator):
    bl_idname = "mesh.sca_tree"
    bl_label = "SCATree"
    bl_options = {'REGISTER', 'UNDO', 'PRESET'}

    internodeLength = FloatProperty(name="Internode Length",
                    description="Internode length in Blender Units",
                    default=0.75,
                    min=0.01,
                    soft_max=3.0,
                    subtype='DISTANCE',
                    unit='LENGTH')
    killDistance = FloatProperty(name="Kill Distance",
                    description="Kill Distance as a multiple of the internode length",
                    default=3,
                    min=0.01,
                    soft_max=100.0)
    influenceRange = FloatProperty(name="Influence Range",
                    description="Influence Range as a multiple of the internode length",
                    default=15,
                    min=0.01,
                    soft_max=100.0)
    tropism = FloatProperty(name="Tropism",
                    description="The tendency of branches to bend up or down",
                    default=0,
                    min=-1.0,
                    soft_max=1.0)
    power = FloatProperty(name="Branch tapering",
                    description="How fast a branch tapers off as it splits",
                    default=0.3,
                    min=0.01,
                    soft_max=1.0)
    scale = FloatProperty(name="Branch diameter",
                    description="Branch base diameter (gets smaller near the tips)",
                    default=0.01,
                    min=0.0001,
                    soft_max=1.0)
    
    # the group related properties are not saved as presets because on reload no groups with the same names might exist, causing an exception
    useGroups = BoolProperty(name="Use object groups",
                    options={'ANIMATABLE','SKIP_SAVE'},
                    description="Use groups of objects to specify marker distribution",
                    default=False)
    
    crownGroup = EnumProperty(items=availableGroupsOrNone,
                    options={'ANIMATABLE','SKIP_SAVE'},
                    name='Crown Group',
                    description='Group of objects that specify crown shape')
    
    shadowGroup = EnumProperty(items=availableGroupsOrNone,
                    options={'ANIMATABLE','SKIP_SAVE'},
                    name='Shadow Group',
                    description='Group of objects subtracted from the crown shape')
    shadowDensity = FloatProperty(name="Shadow density",
                    description="Shadow density, bigger means less markers in shadow group volume",
                    default=0.5,
                    min=0.0,
                    max=1.0)
    
    exclusionGroup = EnumProperty(items=availableGroupsOrNone,
                    options={'ANIMATABLE','SKIP_SAVE'},
                    name='Exclusion Group',
                    description='Group of objects that will not be penetrated by growing branches')
    
    useTrunkGroup = BoolProperty(name="Use trunk group", 
                    options={'ANIMATABLE','SKIP_SAVE'},
                    description="Use the locations of a group of objects to specify trunk starting points instead of 3d cursor",
                    default=False)
    
    trunkGroup = EnumProperty(items=availableGroups,
                    options={'ANIMATABLE','SKIP_SAVE'},
                    name='Trunk Group',
                    description='Group of objects whose locations specify trunk starting points')
    
    crownSize = FloatProperty(name="Crown Size",
                    description="Crown size",
                    default=5,
                    min=1,
                    soft_max=29)
    crownShape = FloatProperty(name="Crown Shape",
                    description="Crown shape",
                    default=1,
                    min=0.2,
                    soft_max=5)
    crownOffset = FloatProperty(name="Crown Offset",
                    description="Crown offset (the length of the bole)",
                    default=3,
                    min=0,
                    soft_max=20.0)
    surfaceBias = FloatProperty(name="Surface Bias",
                    description="Surface bias (how much markers are favored near the surface)",
                    default=1,
                    min=0.1,
                    soft_max=10)
    topBias = FloatProperty(name="Top Bias",
                    description="Top bias (how much markers are favored near the top)",
                    default=1,
                    min=0.1,
                    soft_max=10)
    randomSeed = IntProperty(name="Random Seed",
                    description="The seed governing random generation",
                    default=0,
                    min=0)
    maxIterations = IntProperty(name="Maximum Iterations",
                    description="The maximum number of iterations allowed for tree generation",
                    default=40,
                    min=0)
    pruningGen = IntProperty(name="Pruning Generation",
                    description="Prune branches last touched in this generation (0 won't prune anythin)",
                    default=0,
                    min=0)
    numberOfEndpoints = IntProperty(name="Number of Endpoints",
                    description="The number of endpoints generated in the growing volume",
                    default=100,
                    min=0)
    newEndPointsPer1000 = IntProperty(name="Number of new Endpoints",
                    description="The number of new endpoints generated in the growing volume per thousand iterations",
                    default=0,
                    min=0)
    maxTime = FloatProperty(name="Maximum Time",
                    description=("The maximum time to run the generation for "
                                "in seconds/generation (0.0 = Disabled). Currently ignored"),
                    default=0.0,
                    min=0.0,
                    soft_max=10)
    bLeaf = FloatProperty(name="Leaf clustering",
                    description=("How much leaves cluster to the end of the internode"),
                    default=1,
                    min=0,
                    soft_min=0.3,
                    soft_max=4)

    addLeaves = BoolProperty(name="Add Leaves & Objects", default=False)
    leafParticles = EnumProperty(items=availableParticleSettings,
                    options={'ANIMATABLE','SKIP_SAVE'},
                    name='Leaf distribution',
                    description='Settings for a leaf particle system')
    objectParticles = EnumProperty(items=availableParticleSettings,
                    options={'ANIMATABLE','SKIP_SAVE'},
                    name='Additional object distribution',
                    description='Settings for a extra particle system')
    emitterScale = FloatProperty(name="Emitter scale",
                    description="Leaf emitter scale (will not be rendered anyway)",
                    default=0.01,
                    min=0.0001,
                    soft_max=1.0)
    
    barkMaterial = EnumProperty(items=availableBarkMaterials,
                    options={'ANIMATABLE','SKIP_SAVE'},
                    name='Bark material',
                    description='Bark material to use on branches')
    
    updateTree = BoolProperty(name="Update Tree", default=False)
    
    noModifiers = BoolProperty(name="No Modifers", default=True)
    subSurface = BoolProperty(name="Sub Surface", default=False, description="Add subsurface modifier to trunk skin")
    skinMethod = EnumProperty(items=[('NATIVE','Space tree','Spacetrees own skinning method',1),('BLENDER','Skin modifier','Use Blenders skin modifier',2)],
                    options={'ANIMATABLE','SKIP_SAVE'},
                    name='Skinning method',
                    description='How to add a surface to the trunk skeleton')
    
    showMarkers = BoolProperty(name="Show Markers", default=False)
    markerScale = FloatProperty(name="Marker Scale",
                    description=("The size of the markers"),
                    default=0.05,
                    min=0.001,
                    soft_max=0.2)
    timePerformance = BoolProperty(name="Time performance", default=False, description="Show duration of generation steps on console")

    apicalcontrol = FloatProperty(name="Apical Control",
                    description=("The amount of apical control"),
                    default=0.0,
                    min=0.0,
                    soft_max=0.8)    
    apicalcontrolfalloff = FloatProperty(name="Apical Falloff",
                    description=("Fallof along branch. Values < 1 will ease falloff, > 1 will sharpen it"),
                    default=1.0,
                    min=0.0,
                    soft_max=2)    
    apicalcontroltiming = IntProperty(name="Apical Timing",
                    description=("Maximum number of generations with apical control. 0 = always."),
                    default=10,
                    min=0,
                    soft_max=40)    

    @classmethod
    def poll(self, context):
        # Check if we are in object mode
        return context.mode == 'OBJECT'

    def execute(self, context):
        
        # we load this library matrial unconditionally, i.e. each time we execute() which sounds like a waste
        # but library loads get undone as well if we redo the operator ...
        global barkmaterials
        barkmaterials = load_materials_from_bundled_lib('add_mesh_space_tree', 'material_lib.blend', 'Bark')
        bpy.types.MESH_OT_sca_tree.barkmaterials = barkmaterials
        
        global particlesettings
        # we *must* execute this every time because this operator has UNDO as attribute so anything that's changed will be reverted on each execution. If we initialize this only once, the operator crashes Blender because it will refer to stale data.
        particlesettings = load_particlesettings_from_bundled_lib('add_mesh_space_tree', 'material_lib.blend', 'LeafEmitter')
        bpy.types.MESH_OT_sca_tree.particlesettings = particlesettings
                
        if not self.updateTree:
            return {'PASS_THROUGH'}

        timings=Timer()
        
        
        # necessary otherwise ray casts toward these objects may fail. However if nothing is selected, we get a runtime error ...
        # and if an object is selected that has no edit mode (e.g. an empty) we get a type error
        try:
            bpy.ops.object.mode_set(mode='EDIT', toggle=False)
            bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        except RuntimeError:
            pass
        except TypeError:
            pass
        
        if self.useGroups:
            size,minp = groupExtends(self.crownGroup)
            volumefie=partial(groupdistribution,self.crownGroup,self.shadowGroup,self.shadowDensity,self.randomSeed,size,minp-bpy.context.scene.cursor_location)
        else:
            volumefie=partial(ellipsoid2,self.crownSize*self.crownShape,self.crownSize,Vector((0,0,self.crownSize+self.crownOffset)),self.surfaceBias,self.topBias)
        
        startingpoints = []
        if self.useTrunkGroup:
            if bpy.data.groups.find(self.trunkGroup)>=0 :
                for ob in bpy.data.groups[self.trunkGroup].objects :
                    p = ob.location - context.scene.cursor_location
                    startingpoints.append(Branchpoint(p,None))
        
        timings.add('scastart')
        sca = SCA(NBP = self.maxIterations,
            NENDPOINTS=self.numberOfEndpoints,
            d=self.internodeLength,
            KILLDIST=self.killDistance,
            INFLUENCE=self.influenceRange,
            SEED=self.randomSeed,
            TROPISM=self.tropism,
            volume=volumefie,
            exclude=lambda p: insidegroup(p, self.exclusionGroup),
            startingpoints=startingpoints,
            apicalcontrol=self.apicalcontrol,
            apicalcontrolfalloff=self.apicalcontrolfalloff,
            apicaltiming=self.apicalcontroltiming
            )
        timings.add('sca')
            
        sca.iterate(newendpointsper1000=self.newEndPointsPer1000,maxtime=self.maxTime)
        timings.add('iterate')
        print('execute: iterate done')
        if self.showMarkers:
            mesh = createMarkers(sca, self.markerScale)
            obj_markers = bpy.data.objects.new(mesh.name, mesh)
            base = bpy.context.scene.objects.link(obj_markers)
        timings.add('showmarkers')
        print('execute: showmarkers done')
        
        obj_new=createGeometry(sca,self.power,self.scale,
            self.noModifiers, self.skinMethod, self.subSurface,
            self.bLeaf, 
            self.leafParticles if self.addLeaves else 'None', 
            self.objectParticles if self.addLeaves else 'None',
            self.emitterScale,
            self.timePerformance,
            self.pruningGen)
        print('execute: create geometry done')
        
        bpy.ops.object.material_slot_add()
        obj_new.material_slots[-1].material = barkmaterials[self.barkMaterial]
        
        if self.showMarkers:
            obj_markers.parent = obj_new
        
        self.updateTree = False
        
        if self.timePerformance:
            timings.add('Total')
            print(timings)
        
        self.timings = timings
        
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout

        layout.prop(self, 'updateTree', icon='MESH_DATA')

        columns=layout.row()
        col1=columns.column()
        col2=columns.column()
        
        box = col1.box()
        box.label("Generation Settings:")
        box.prop(self, 'randomSeed')
        box.prop(self, 'maxIterations')

        box = col1.box()
        box.label("Shape Settings:")
        box.prop(self, 'numberOfEndpoints')
        box.prop(self, 'internodeLength')
        box.prop(self, 'influenceRange')
        box.prop(self, 'killDistance')
        box.prop(self, 'tropism')
        box.prop(self, 'apicalcontrol')
        if self.apicalcontrol > 0:
            box.prop(self, 'apicalcontrolfalloff')
            box.prop(self, 'apicalcontroltiming')
        box.prop(self, 'pruningGen')
        
        newbox = col2.box()
        newbox.label("Crown shape")
        newbox.prop(self,'useGroups')
        if self.useGroups:
            newbox.label("Object groups defining crown shape")
            groupbox = newbox.box()
            groupbox.prop(self,'crownGroup')
            groupbox = newbox.box()
            groupbox.alert=(self.shadowGroup != 'None' and self.shadowGroup == self.crownGroup)
            groupbox.prop(self,'shadowGroup')
            groupbox.prop(self,'shadowDensity')
            groupbox = newbox.box()
            groupbox.alert=(self.exclusionGroup != 'None' and self.exclusionGroup == self.crownGroup)
            groupbox.prop(self,'exclusionGroup')
        else:
            newbox.label("Simple ellipsoid defining crown shape")
            newbox.prop(self, 'crownSize')
            newbox.prop(self, 'crownShape')
            newbox.prop(self, 'crownOffset')
            newbox.label("Distribution bias of new endpoints added while iterating")
            newbox.prop(self, 'surfaceBias')
            newbox.prop(self, 'topBias')
        newbox = col2.box()
        newbox.prop(self,'useTrunkGroup')
        if self.useTrunkGroup:
            newbox.prop(self,'trunkGroup')
            
        box.prop(self, 'newEndPointsPer1000')
        
        box = col2.box()
        box.label("Skin options:")
        box.prop(self, 'noModifiers')
        if not self.noModifiers:
            box.prop(self, 'skinMethod')
            box.prop(self, 'subSurface')
            box.prop(self, 'power')
            box.prop(self, 'scale')
            box.prop(self, 'barkMaterial')
            
        box = layout.box()
        box.prop(self, 'addLeaves')
        if self.addLeaves:
            box.prop(self,'bLeaf')
            box.prop(self,'leafParticles')
            box.prop(self,'objectParticles')
            box.prop(self,'emitterScale')

        box = layout.box()
        box.label("Debug Settings:")
        box.prop(self, 'showMarkers')
        if self.showMarkers:
            box.prop(self, 'markerScale')
        box.prop(self, 'timePerformance')
        if self.timePerformance:
            for line in str(self.timings).split('\n'):
                box.label(line)
        
def menu_func(self, context):
    self.layout.operator(SCATree.bl_idname, text="Add Tree to Scene",
                                                icon='PLUGIN').updateTree = True

def register():
    bpy.utils.register_module(__name__)
    bpy.types.INFO_MT_mesh_add.append(menu_func)


def unregister():
    bpy.types.INFO_MT_mesh_add.remove(menu_func)
    bpy.utils.unregister_module(__name__)


if __name__ == "__main__":
    register()
