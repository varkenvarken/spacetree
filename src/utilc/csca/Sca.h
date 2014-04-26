// ##### BEGIN GPL LICENSE BLOCK #####
//
//  SCA Tree Generator, a Blender addon
//  (c) 2013, 2014 Michel J. Anders (varkenvarken)
//
//  This program is free software; you can redistribute it and / or
//  modify it under the terms of the GNU General Public License
//  as published by the Free Software Foundation; either version 2
//  of the License, or(at your option) any later version.
//
//  This program is distributed in the hope that it will be useful,
//  but WITHOUT ANY WARRANTY; without even the implied warranty of
//  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.See the
//  GNU General Public License for more details.
//
//  You should have received a copy of the GNU General Public License
//  along with this program; if not, write to the Free Software Foundation,
// Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110 - 1301, USA.
//
// ##### END GPL LICENSE BLOCK #####

#include "Python.h"
#include <vector>
#include <array>

using namespace std;

typedef array<double, 3> point;
typedef vector<point> points;
typedef vector<int> indices;

int iterate(
	points endpoints,
	points startpoints,
	points additionalendpoints,
	int niterations,
	double branchlength,
	double killdistance,
	double tropism,
    PyObject *excludecallback,

	points &branchpoints,
	indices &branchpointparents);

