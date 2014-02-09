from random import random,seed,expovariate
from functools import partial
from math import sqrt
from time import time

from mathutils import Vector

class Branchpoint:
    def __init__(self, p, parent):
        self.v=Vector(p)
        self.parent = parent
        self.connections = 1
        self.apex = None
        self.shoot = None
        self.index = None

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

  def __init__(self,NENDPOINTS = 100,d = 0.3,NBP = 2000, KILLDIST = 5, INFLUENCE = 15, SEED=42, volume=partial(sphere,5,Vector((0,0,8))), TROPISM=0.0, exclude=lambda p: False,
        startingpoints=[]):
    self.killdistance = KILLDIST
    self.branchlength = d
    self.maxiterations = NBP
    self.tropism = TROPISM
    
    seed(SEED)
    
    self.bp =[(0,0,0)]
    self.bpp=[None]
    self.bpc=[0]
    self.ep =[]
    self.epb=[] # index of closest branchpoint
    self.epv=[] # normalized direction of closest bp to this ep
    self.epd=[] # distance to closest bp
    
    self.volumepoint=volume()
    self.exclude=exclude

    # result arrays, filled *after* iterations
    self.branchpoints = []
    self.endpoints = []

    for i in range(NENDPOINTS):
        self.addEndPoint(next(self.volumepoint))

    if len(startingpoints)>0:
        self.bp=[]
        self.bpp=[]
        self.bpc=[]
        for bp in startingpoints:
            self.addBranchPoint(bp.v, -1)

  def addBranchPoint(self, bp, pi):
    # maybe add lookip for bps with more than one child and remove them from endpoints list
    self.bp.append(tuple(bp))# even if it is passed as a vector we turn it in to a tuple to ease a later coversion to numpy
    self.bpp.append(pi)
    self.bpc.append(0)
    self.bpc[pi]+=1
    bi = len(self.bp)-1
    for epi,(ep,epd,epb) in enumerate(zip(self.ep,self.epd, self.epb)):
      if epb >= 0: # not a dead endpoint
        v = ep[0]-bp[0],ep[1]-bp[1],ep[2]-bp[2]
        d2= v[0]*v[0]+v[1]*v[1]+v[2]*v[2]
        d = sqrt(d2)
        if d < epd:
          if d>self.killdistance:
            self.epb[epi]=bi
            self.epv[epi]= v[0]/d,v[1]/d,v[2]/d
            self.epd[epi]=d
          else:
            self.epb[epi]=-1
    if self.bpc[pi]>1:  
      for epi,epb in enumerate(self.epb):
        if epb == pi:
          bi, v, d = self.closestBranchPoint(self.ep[epi])
          self.epb[epi]=bi
          self.epv[epi]=v
          self.epd[epi]=d
         
  def addEndPoint(self,ep):
    self.ep.append(tuple(ep)) # even if it is passed as a vector we turn it in to a tuple to ease a later coversion to numpy
    bi, v, d = self.closestBranchPoint(ep)
    self.epb.append(bi)
    self.epv.append(v)
    self.epd.append(d)

  def closestBranchPoint(self, p):
    bd2=1e16
    for bi,bp in enumerate(self.bp):
      if self.bpc[bi]>1 : continue
      v = p[0]-bp[0],p[1]-bp[1],p[2]-bp[2]
      d2= v[0]*v[0]+v[1]*v[1]+v[2]*v[2]
      if d2<bd2:
        bd2=d2
        bv =v
        bbi=bi
    d=sqrt(d2)
    return bbi, (v[0]/d,v[1]/d,v[2]/d), d

  def growBranches(self):
    bis = set(self.epb) # unique bps that have closests endpoints
    bis.discard(-1) # remove if present
    newbps=[]
    newbpps=[]
    for bpi in bis:
      epvs = [v for epi,v in enumerate(self.epv) if self.epb[epi]==bpi ]
      v = sum(v[0] for v in epvs), sum(v[1] for v in epvs), sum(v[2] for v in epvs)
      d2= v[0]*v[0]+v[1]*v[1]+v[2]*v[2]
      d = sqrt(d2) / self.branchlength
      vd= v[0]/d,v[1]/d,v[2]/d
      newbps.append((self.bp[bpi][0]+vd[0], self.bp[bpi][1]+vd[1], self.bp[bpi][2]+vd[2]+self.tropism ))
      newbpps.append(bpi)
    for newbp,newbpp in zip(newbps,newbpps):
      if not self.exclude(Vector(newbp)):
        self.addBranchPoint(newbp,newbpp)

   
  def iterate(self, newendpointsper1000=0, maxtime=0.0):
    starttime=time()      
    endpointsadded=0.0
    niterations=0.0
    newendpointsper1000 /= 1000.0
    t=expovariate(newendpointsper1000) if newendpointsper1000 > 0.0 else 1 # time to the first new 'endpoint add event'

    for i in range(self.maxiterations):
        self.growBranches()
        if maxtime>0 and time()-starttime>maxtime: break
        if newendpointsper1000 > 0.0:
            # generate new endpoints with a poisson process
            # when we first arrive here, t already holds the time to the first event
            niterations+=1
            while t < niterations: # we keep on adding endpoints as long as the next event still happens within this iteration
                self.addEndPoint(next(self.volumepoint))
                endpointsadded+=1
                t+=expovariate(newendpointsper1000) # time to new 'endpoint add event'


    self.branchpoints=[]
    for bp,bpp in zip(self.bp, self.bpp):
        self.branchpoints.append(Branchpoint(bp, bpp))
        # note that we do not actually discriminate betwee apex and sideshoot, the first to connect is the apex
        if bpp is not None:
            parent = self.branchpoints[bpp]
            if parent.apex is None:
                parent.apex = self.branchpoints[-1]
            else:
                parent.shoot = self.branchpoints[-1]

    for bp in self.branchpoints:
        bpp = bp
        while bpp.parent is not None:
            bpp = self.branchpoints[bpp.parent]
            bpp.connections += 1
        
    self.endpoints=[]
    for ep in self.ep:
        self.endpoints.append(Vector(ep))
    #print('endpoints',len(self.endpoints))    