# this is a testscript for the csca module.
# it assumes that the module is in the python path

from csca import sca

out = open('C:/temp/testoutput.txt','w')
# sca(endpoints, startpoints, extraendpoints, iterations, branchlength, killdistance, tropism)
out.write(str(sca([(1,0,0)], [(0,0,0)], [], 2, 0.25, 0.5, 0))+'\n')
out.write(str(sca([(5,-5,10),(5,5,10),(-5,5,10),(-5,-5,10)], [(0,0,0)], [], 6, 3, 0.5, 0))+'\n')

from random import random, seed
seed(42)
endpoints = [(random(),random(),3+random()) for i in range(100)]
extraendpoints = [(random(),random(),3+random()) for i in range(80)]
points, parents = sca(endpoints,[(0,0,0)], extraendpoints, 40, 0.5, 0.5, 0)
n=0
for p,v in zip(points,parents):
	out.write(str(n)+' '+str(p)+' '+str(v)+"\n")
	n+=1

print('module test suite completed')
