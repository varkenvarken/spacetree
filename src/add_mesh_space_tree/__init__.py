# ##### BEGIN GPL LICENSE BLOCK #####
#
#  SCA Tree Generator, a Blender addon
#  (c) 2013 Michel J. Anders (varkenvarken)
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
	"version": (0, 0, 2),
	"blender": (2, 66, 0),
	"location": "View3D > Add > Mesh",
	"description": "Adds a tree created with the space colonization algorithm starting at the 3D cursor",
	"warning": "",
	"wiki_url": "http://to be determined",
	"tracker_url": "",
	"category": "Add Mesh"}


from random import random
from functools import partial
from math import sin,cos

import bpy
from bpy.props import FloatProperty, IntProperty, BoolProperty
from mathutils import Vector,Euler,Matrix

from .sca import SCA # the core class that implements the space colonization algorithm

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

def pointInsideMesh(point,ob):
	# adapted from http://blenderartists.org/forum/showthread.php?195605-Detecting-if-a-point-is-inside-a-mesh-2-5-API&p=1691633&viewfull=1#post1691633
	mat = ob.matrix_world.inverted()
	orig = mat*(point+bpy.context.scene.cursor_location)
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
		r = random()**(surfacebias/2)
		x = r*rxy*cos(theta)*cos(phi)
		y = r*rxy*cos(theta)*sin(phi)
		st=sin(theta)
		st = (((st+1)/2)**topbias)*2-1
		z = r*rz*st
		#print(">>>%.2f %.2f %.2f "%(x,y,z))
		m = p+Vector((x,y,z))
		reject = False
		for ob in bpy.context.selected_objects:
			# probably we should check if each object is a mesh
			if pointInsideMesh(m,ob) :
				reject = True
				break
		if not reject:
			yield m

def createLeaves(tree, probability=0.5, size=0.5, randomsize=0.1, randomrot=0.1, maxconnections=2):
	p=bpy.context.scene.cursor_location
	
	verts=[]
	faces=[]
	c1=Vector((-size/10,-size/2,0))
	c2=Vector((    size,-size/2,0))
	c3=Vector((    size, size/2,0))
	c4=Vector((-size/10, size/2,0))
	for bp in tree.branchpoints:
		if (bp.connections < maxconnections) and (random() <= probability) :
			rx = (random()-0.5)*randomrot*6.283
			ry = (random()-0.5)*randomrot*6.283
			rot = Euler((rx,ry,random()*6.283),'ZXY')
			scale = 1+(random()-0.5)*randomsize
			v=c1.copy()
			v.rotate(rot)
			verts.append(v*scale+bp.v)
			v=c2.copy()
			v.rotate(rot)
			verts.append(v*scale+bp.v)
			v=c3.copy()
			v.rotate(rot)
			verts.append(v*scale+bp.v)
			v=c4.copy()
			v.rotate(rot)
			verts.append(v*scale+bp.v)
			n = len(verts)
			faces.append((n-4,n-3,n-2,n-1))
	mesh = bpy.data.meshes.new('Leaves')
	mesh.from_pydata(verts,[],faces)
	mesh.update(calc_edges=True)
	mesh.uv_textures.new()
	return mesh

def createMarkers(tree,scale=0.05):
	p=bpy.context.scene.cursor_location
	
	verts=[]
	faces=[]

	tetraeder = [Vector((-1,1,-1)),Vector((1,-1,-1)),Vector((1,1,1)),Vector((-1,-1,1))]
	tetraeder = [v * scale for v in tetraeder]
	tfaces = [(0,1,2),(0,1,3),(1,2,3),(0,3,2)]
	
	for ep in tree.endpoints:
		verts.extend([ep + v for v in tetraeder])
		n=len(faces)
		faces.extend([(f1+n,f2+n,f3+n) for f1,f2,f3 in tfaces])
		
	mesh = bpy.data.meshes.new('Markers')
	mesh.from_pydata(verts,[],faces)
	mesh.update(calc_edges=True)
	return mesh

def createGeometry(tree, power=0.5, scale=0.01, addleaves=False, pleaf=0.5, leafsize=0.5, leafrandomsize=0.1, leafrandomrot=0.1, nomodifiers=False, maxleafconnections=2):
	
	p=bpy.context.scene.cursor_location
	verts=[]
	edges=[]
	radii=[]
	# Loop over all branchpoints and create connected edges
	for bp in tree.branchpoints:
		verts.append(bp.v+p)
		radii.append(bp.connections)
		if not (bp.parent is None) :
			edges.append((len(verts)-1,bp.parent))
	
	# create the tree mesh
	mesh = bpy.data.meshes.new('Tree')
	mesh.from_pydata(verts, edges, [])
	mesh.update()
	
	# create the tree object an make it the only selected and active object in the scene
	obj_new = bpy.data.objects.new(mesh.name, mesh)
	base = bpy.context.scene.objects.link(obj_new)
	for ob in bpy.context.scene.objects:
		ob.select = False
	base.select = True
	bpy.context.scene.objects.active = obj_new
	bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
	
	# add a subsurf modifier to smooth the branches
	if nomodifiers == False:
		bpy.ops.object.modifier_add(type='SUBSURF')
		bpy.context.active_object.modifiers[0].levels = 1
		bpy.context.active_object.modifiers[0].render_levels = 1

		# add a skin modifier
		bpy.ops.object.modifier_add(type='SKIN')
		bpy.context.active_object.modifiers[1].use_smooth_shade=True
		bpy.context.active_object.modifiers[1].use_x_symmetry=True
		bpy.context.active_object.modifiers[1].use_y_symmetry=True
		bpy.context.active_object.modifiers[1].use_z_symmetry=True

		skinverts = bpy.context.active_object.data.skin_vertices[0].data

		for i,v in enumerate(skinverts):
			v.radius = [(radii[i]**power)*scale,(radii[i]**power)*scale]
		
		# add a subsurf modifier to smooth the skin
		bpy.ops.object.modifier_add(type='SUBSURF')
		bpy.context.active_object.modifiers[2].levels = 1
		bpy.context.active_object.modifiers[2].render_levels = 2

	# create the leaves object
	if addleaves:
		mesh = createLeaves(tree, pleaf, leafsize, leafrandomsize, leafrandomrot, maxleafconnections)
		obj_leaves = bpy.data.objects.new(mesh.name, mesh)
		base = bpy.context.scene.objects.link(obj_leaves)
		obj_leaves.parent = obj_new
		bpy.context.scene.objects.active = obj_leaves
		bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
		bpy.context.scene.objects.active = obj_new
		
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
					default=5,
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
	power = FloatProperty(name="Power",
					description="Tapering power of branch connections",
					default=0.5,
					min=0.01,
					soft_max=1.0)
	scale = FloatProperty(name="Scale",
					description="Branch size",
					default=0.01,
					min=0.0001,
					soft_max=1.0)
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
					min=-10,
					soft_max=10)
	topBias = FloatProperty(name="Top Bias",
					description="Top bias (how much markers are favored near the top)",
					default=1,
					min=-10,
					soft_max=10)
	randomSeed = IntProperty(name="Random Seed",
					description="The seed governing random generation",
					default=0,
					min=0)
	maxIterations = IntProperty(name="Maximum Iterations",
					description="The maximum number of iterations allowed for tree generation",
					default=40,
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
								"in seconds generation (0.0 = Disabled)"),
					default=0.0,
					min=0.0,
					soft_max=10)
	pLeaf = FloatProperty(name="Leaves per internode",
					description=("The number of leaves per internode"),
					default=0.5,
					min=0.0,
					soft_max=1)
	leafSize = FloatProperty(name="Leaf Size",
					description=("The leaf size"),
					default=0.5,
					min=0.0,
					soft_max=1)
	leafRandomSize = FloatProperty(name="Leaf Random Size",
					description=("The amount of randomness to add to the leaf size"),
					default=0.1,
					min=0.0,
					soft_max=10)
	leafRandomRot = FloatProperty(name="Leaf Random Rotation",
					description=("The amount of random rotation to add to the leaf"),
					default=0.1,
					min=0.0,
					soft_max=1)
	leafMaxConnections = IntProperty(name="Max Connections",
					description="The maximum number of connections of an internode elegible for a leaf",
					default=2,
					min=0)
	addLeaves = BoolProperty(name="Add Leaves", default=False)
	updateTree = BoolProperty(name="Update Tree", default=False)
	noModifiers = BoolProperty(name="No Modifers", default=False)
	showMarkers = BoolProperty(name="Show Markers", default=False)
	markerScale = FloatProperty(name="Marker Scale",
					description=("The size of the markers"),
					default=0.05,
					min=0.001,
					soft_max=0.2)
	
	@classmethod
	def poll(self, context):
		# Check if we are in object mode
		return context.mode == 'OBJECT'

	def execute(self, context):
		if not self.updateTree:
			return {'PASS_THROUGH'}

		# necessary otherwize ray casts toward these objects may fail. However if nothing is selected, we get a runtime error ...
		try:
			bpy.ops.object.mode_set(mode='EDIT', toggle=False)
			bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
		except RuntimeError:
			pass
			
		sca = SCA(NBP = self.maxIterations,
			NENDPOINTS=self.numberOfEndpoints,
			d=self.internodeLength,
			KILLDIST=self.killDistance,
			INFLUENCE=self.influenceRange,
			SEED=self.randomSeed,
			TROPISM=self.tropism,
			volume=partial(ellipsoid2,self.crownSize*self.crownShape,self.crownSize,Vector((0,0,self.crownSize+self.crownOffset)),self.surfaceBias,self.topBias))

		if self.showMarkers:
			mesh = createMarkers(sca, self.markerScale)
			obj_markers = bpy.data.objects.new(mesh.name, mesh)
			base = bpy.context.scene.objects.link(obj_markers)
		
		sca.iterate(newendpointsper1000=self.newEndPointsPer1000,maxtime=self.maxTime)
		
		obj_new=createGeometry(sca,self.power,self.scale,self.addLeaves, self.pLeaf, self.leafSize, self.leafRandomSize, self.leafRandomRot, self.noModifiers, self.leafMaxConnections)
		
		if self.showMarkers:
			obj_markers.parent = obj_new
		
		self.updateTree = False
		return {'FINISHED'}

	def draw(self, context):
		layout = self.layout

		layout.prop(self, 'updateTree', icon='MESH_DATA')

		box = layout.box()
		box.label("Generation Settings:")
		box.prop(self, 'randomSeed')
		box.prop(self, 'maxIterations')

		box = layout.box()
		box.label("Shape Settings:")
		box.prop(self, 'numberOfEndpoints')
		box.prop(self, 'internodeLength')
		box.prop(self, 'influenceRange')
		box.prop(self, 'killDistance')
		box.prop(self, 'power')
		box.prop(self, 'scale')
		box.prop(self, 'tropism')
		box.prop(self, 'crownSize')
		box.prop(self, 'crownShape')
		box.prop(self, 'crownOffset')
		box.prop(self, 'surfaceBias')
		box.prop(self, 'topBias')
		box.prop(self, 'newEndPointsPer1000')
		
		layout.prop(self, 'addLeaves', icon='MESH_DATA')
		if self.addLeaves:
			box = layout.box()
			box.label("Leaf Settings:")
			box.prop(self,'pLeaf')
			box.prop(self,'leafSize') 
			box.prop(self,'leafRandomSize') 	
			box.prop(self,'leafRandomRot')
			box.prop(self,'leafMaxConnections')
		
		box = layout.box()
		box.label("Debug Settings:")
		box.prop(self, 'noModifiers')
		box.prop(self, 'showMarkers')
		box.prop(self, 'markerScale')
		
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