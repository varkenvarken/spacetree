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



from collections import defaultdict as dd
from random import random,seed,expovariate
from math import sqrt,pow,sin,cos
from functools import partial

from mathutils import Vector

class Branchpoint:
	def __init__(self, p, parent):
		self.v=Vector(p)
		self.parent = parent
		self.connections = 0

def sphere(r,p):
	r2 = r*r
	while True:
		x = (random()*2-1)*r
		y = (random()*2-1)*r
		z = (random()*2-1)*r
		if x*x+y*y+z*z <= r2:
			yield p+Vector((x,y,z))

class SCA:
	def __init__(self,NENDPOINTS = 100,d = 0.3,NBP = 2000, KILLDIST = 5, INFLUENCE = 15, SEED=42, volume=partial(sphere,5,Vector((0,0,8))), TROPISM=0.0, exclude=lambda p: False,
		startingpoints=[]):
		seed(SEED)
		self.d = d
		self.NBP = NBP
		self.KILLDIST = KILLDIST*KILLDIST*d*d
		self.INFLUENCE = INFLUENCE*INFLUENCE*d*d
		self.TROPISM = TROPISM
		self.exclude = exclude
		self.endpoints = []

		self.volumepoint=volume()
		for i in range(NENDPOINTS):
			self.endpoints.append(next(self.volumepoint))
	
		self.branchpoints = [ Branchpoint((0,0,0),None) ] if len(startingpoints)==0 else startingpoints
		
	def iterate(self, newendpointsper1000=0, maxtime=0.0): # maxtime still ignored for now
		
		endpointsadded=0.0
		niterations=0.0
		newendpointsper1000 /= 1000.0
		t=expovariate(newendpointsper1000) if newendpointsper1000 > 0.0 else 1 # time to the first new 'endpoint add event'
		
		while self.NBP>0 and (len(self.endpoints)>0):
			self.NBP -= 1
			closestsendpoints=dd(list)

			kill = set()
			
			for ei,e in enumerate(self.endpoints):
				distance = None
				closestbp = None
				for bi,b in enumerate(self.branchpoints):
					ddd = b.v-e
					ddd = ddd.dot(ddd)
					if ddd < self.KILLDIST:
						kill.add(ei)
					elif (ddd<self.INFLUENCE) and ((distance is None) or (ddd < distance)):
						closestbp = bi
						distance = ddd
				if not (closestbp is None):
					closestsendpoints[closestbp].append(ei)
			
			if len(closestsendpoints)<1:
				break
			
			for bi in closestsendpoints:
				sd=Vector((0,0,0))
				n=0
				for ei in closestsendpoints[bi]:
					dv=self.branchpoints[bi].v-self.endpoints[ei]
					ll=sqrt(dv.dot(dv))
					sd-=dv/ll
					n+=1
				sd/=n
				ll=sqrt(sd.dot(sd))
				sd/=ll
				sd[2]+=self.TROPISM
				ll=sqrt(sd.dot(sd))
				sd/=ll
			
				if sd < 1e-7 : print('SD very small')
				newp = self.branchpoints[bi].v+sd*self.d
				if not self.exclude(newp):
					bp = Branchpoint(newp,bi)
					self.branchpoints.append(bp)
					bp = self.branchpoints[bi]
					bp.connections+=1
					while not (bp.parent is None):
						bp = self.branchpoints[bp.parent]
						bp.connections+=1
					
			self.endpoints = [ep for ei,ep in enumerate(self.endpoints) if not(ei in kill)]
		
			if newendpointsper1000 > 0.0:
				# generate new endpoints with a poisson process
				# when we first arrive here, t already hold the time to the first event
				niterations+=1
				while t < niterations: # we keep on adding endpoints as long as the next event still happens within this iteration
					self.endpoints.append(next(self.volumepoint))
					endpointsadded+=1
					t+=expovariate(newendpointsper1000) # time to new 'endpoint add event'
				
		if newendpointsper1000 > 0.0:
			print("newendpoints/iteration %.3f, actual %.3f in %5.f iterations"%(newendpointsper1000,endpointsadded/niterations,niterations))