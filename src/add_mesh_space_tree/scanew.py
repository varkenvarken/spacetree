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

from random import random,seed,expovariate
from functools import partial
from math import sqrt
from time import time
from array import array

from mathutils import Vector

from .csca import sca

class Branchpoint:

    count = 0
    
    def __init__(self, p, parent, generation):
        self.v=Vector(p)
        self.parent = parent
        self.connections = 1
        self.generation = generation
        self.apex = None
        self.shoot = None
        Branchpoint.count += 1
        self.index = Branchpoint.count

    def __str__(self):
        return str(self.v)+" "+str(self.parent)
        
def sphere(r,p):
    r2 = r*r
    while True:
        x = (random()*2-1)*r
        y = (random()*2-1)*r
        z = (random()*2-1)*r
        if x*x+y*y+z*z <= r2:
            yield p+Vector((x,y,z))
            
class SCA:

  def __init__(self,NENDPOINTS = 100,d = 0.3,NBP = 2000, KILLDIST = 5, INFLUENCE = 15, SEED=42, volume=partial(sphere,5,Vector((0,0,8))), TROPISM=0.0, exclude=None,
        startingpoints=[], apicalcontrol=0, apicalcontrolfalloff=1, apicaltiming=0):
    self.killdistance = KILLDIST
    self.branchlength = d
    self.maxiterations = NBP
    self.startpoints = startingpoints
    
    self.tropism = TROPISM
    
    # not yet implemented in C extension
    #self.influence = INFLUENCE if INFLUENCE > 0 else 1e16
    #self.apicalcontrol = apicalcontrol
    #self.apicalcontrolfalloff = apicalcontrolfalloff
    #self.apicaltiming = apicaltiming
    #self.apicalstep = apicalcontrol / apicaltiming if apicaltiming > 0 else 0.0
    
    seed(SEED)
    self.volumepoint=volume()
    
    # not yet implemented in C extension
    self.exclude=exclude

    # result arrays, filled *after* iterations
    self.branchpoints = []
    self.endpoints = []

    self.ep = []
    for i in range(NENDPOINTS):
        self.ep.append(tuple(next(self.volumepoint)))
    
    if len(self.startpoints) == 0:
        self.startpoints.append((0,0,0))

  def iterate(self, newendpointsper1000=0, maxtime=0.0):
    starttime=time() 
    
    # not yet implemented in C extension
    #endpointsadded=0.0
    #niterations=0.0
    #newendpointsper1000 /= 1000.0
    #t=expovariate(newendpointsper1000) if newendpointsper1000 > 0.0 else 1 # time to the first new 'endpoint add event'

    extra_eps = []
    for i in range(int(newendpointsper1000*self.maxiterations/1000.0)):
        extra_eps.append(tuple(next(self.volumepoint)))
        
    print('n=%d bl=%.3f kd=%3.f'%(self.maxiterations, self.branchlength, self.killdistance))
    print('endpoints')
    print(self.ep)
    print('startpoints')
    print(self.startpoints)
    print('--------')
    
    self.bp, self.bpp = sca(self.ep, self.startpoints, extra_eps, self.maxiterations, self.branchlength, self.killdistance, self.tropism, self.exclude)
    
    print('--------')
    print('branchpoints')
    print(self.bp)
    print('branchpoints parents')
    print(self.bpp)
    print('--------')
    
    for bp, bpp in zip(self.bp, self.bpp):
        self.branchpoints.append(Branchpoint(bp, bpp if bpp >= 0 else None, 0)) # gen not yet available in C extension
        # note that we do not actually discriminate betwee apex and sideshoot, the first to connect is the apex
        if bpp >= 0:
            parent = self.branchpoints[bpp]
            if parent.apex is None:
                parent.apex = self.branchpoints[-1]
            else:
                parent.shoot = self.branchpoints[-1]
    print('created Branchpoints')
    for bp in self.branchpoints:
        bpp = bp
        while bpp.parent is not None:
            bpp = self.branchpoints[bpp.parent]
            bpp.connections += 1 # a bit of a misnomer: this is the sum of all connected children for this branchpoint
    print('calculated Branchpoint connectivity')    
    self.endpoints=[]
    for ep in self.ep:
        self.endpoints.append(Vector(ep))
    print('converted endpoints')
