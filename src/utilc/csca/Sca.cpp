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

#include <omp.h>
#include <math.h>
#include <unordered_set>
#include <algorithm>
#include "Sca.h"

#include <cstdio>
#include <iostream>

#define SQRT_DBL_MAX sqrt(DBL_MAX)
#define EPS 1e-7

using namespace std;

// endpoint properties
static auto ep_closestbranchpointindex = indices();
static auto ep_closestdistance = vector<double>();
static auto ep_normalizeddirection = points();
static auto ep_position = points();

// branchpoint properties
static points *bp_position;
static indices * bp_parent;
static auto bp_connections = vector<int>();

// debug functions
void dump_endpoints(int it){
	printf("endpoints (iteration %d)\n", it);
	printf("---------\n");
	for (int i = 0; i < ep_position.size(); i++){
		printf("%3d <%5.1f,%5.1f,%5.1f> cbpi=%3d d=%5.1f v=<%5.1f,%5.1f,%5.1f>\n", i, 
			ep_position[i][0], ep_position[i][1], ep_position[i][2], 
			ep_closestbranchpointindex[i], ep_closestdistance[i], 
			ep_normalizeddirection[i][0], ep_normalizeddirection[i][1], ep_normalizeddirection[i][2] );
	}
	printf("---------\n");
}

// utility functions
static point *subtract(const point &a, const point &b){
	return new point{ a[0] - b[0], a[1] - b[1], a[2] - b[2]};
}

static point *add(const point &a, const point &b){
	return new point{ a[0] + b[0], a[1] + b[1], a[2] + b[2] };
}

static point *multiply(const point &a, const double b){
	return new point{ a[0] * b, a[1] * b, a[2] * b };
}

// normalize the length of a point. Leaves point intact if length is small.
static point *normalize(const point &a){
	auto len = a[0] * a[0] + a[1] * a[1] + a[2] * a[2];
	if (len > EPS){
		len = sqrt(len);
		return new point{ a[0] / len, a[1] / len, a[2] / len };
	}
	else{
		return new point{ a[0], a[1], a[2] };
	}
}

static double dot(const point *a, const point *b){
	return (*a)[0] * (*b)[0] + (*a)[1] * (*b)[1] + (*a)[2] * (*b)[2];
}

// call a Python function that returns a boolean value
static bool exclude(point *p, PyObject *callback){
	PyObject *arg;
	PyObject *result;
	arg = Py_BuildValue("(ddd)", (*p)[0], (*p)[1], (*p)[2]);
	if(!PyTuple_Check(arg))printf("not a typle\n");
	result = PyObject_CallObject(callback, arg);
	Py_DECREF(arg);
	if (result != NULL){
		int iresult;
		if (!PyArg_Parse(result, "p", &iresult)){ // we don't use PyArg_ParseTuple because apparently a callback returns old style arguments?
			// ignore error
		}
		Py_DECREF(result);
		return iresult;
	}
	return false;
}

// functions to actually evolve a tree with the space tree colonization algorithm

// returns the distance to the branchpoint closest to a given endpoint. Also, returns the index and the normalized 
// direction from this branchpoint to the endpoint. Fully connected branchpoints (i.e. with two children) are ignored.
static double closest_branchpoint(const point endpoint, int &branchpointindex, point &normalizeddirection){
	double mind2 = DBL_MAX;
	point *mindir = NULL;
	point *dir;
	double d2;

	int n = bp_position->size();
//#pragma omp parallel for private(dir, d2)
	for (decltype(n) bpi = 0; bpi<n; bpi++){
		if (bp_connections[bpi] > 1) continue; // fully connected branchpoints will not grow new shoots
		dir = subtract(endpoint, (*bp_position)[bpi]);
		d2 = dot(dir, dir);
		if (d2 < mind2){
			mind2 = d2;
			mindir = dir;
			branchpointindex = bpi;
		}
		else{
			delete dir;
		}
	}

	double d = sqrt(mind2);
	if (d > EPS){
		normalizeddirection[0] = (*mindir)[0] / d;
		normalizeddirection[1] = (*mindir)[1] / d;
		normalizeddirection[2] = (*mindir)[2] / d;
	}
	
	return d;
}

// add a new endpoint and update all dependent information (like what's the closest branchpoint)
static void add_endpoint(point &ep){
	int bpi;
	point dir;

	double distance = closest_branchpoint(ep, bpi, dir);
	
	ep_closestbranchpointindex.push_back(bpi);
	ep_closestdistance.push_back(distance);
	ep_normalizeddirection.push_back(dir);
	ep_position.push_back(ep);
}

// add a child branchpoint to the branchpoint at branchpointindex
static void add_branchpoint(int branchpointindex, const point &dir, double branchlength, double killdistance, PyObject *excludecallback){

	// calculate the position of the new branchpoint
	point *branch = multiply(dir, branchlength);
	point *newbranchpoint = add((*bp_position)[branchpointindex], *branch);

	// if a callback is defined, call it to determine if the new position is allowed.
	if (excludecallback != NULL && exclude(newbranchpoint, excludecallback)) return;

	// connect the new branchpoint
	(*bp_position).push_back(*newbranchpoint);
	(*bp_parent).push_back(branchpointindex);
	bp_connections[branchpointindex]++;
	bp_connections.push_back(0);

	// check if the new branchpoint is closer than other bps to any endpoint
	int bpi = bp_position->size()-1; // index of newly added branchpoint
	int epi = -1;
	for (auto ep : ep_position){
		epi++;
		point *dir = subtract(ep, *newbranchpoint);
		double d = sqrt(dot(dir, dir));
		if (d < killdistance){	
			ep_closestbranchpointindex[epi] = -1;
			delete dir;
		}
		else if (d < ep_closestdistance[epi]){
			ep_closestbranchpointindex[epi] = bpi;
			ep_closestdistance[epi] = d;
			if (d>EPS){
				(*dir)[0] /= d;
				(*dir)[1] /= d;
				(*dir)[2] /= d;
			}
			ep_normalizeddirection[epi] = *dir;
		}
		else{
			delete dir;
		}
	}

	// if the parent now has 2 connections, we have to reassign any endpoints pointing to the parent
	if (bp_connections[branchpointindex]>1){
		int epi = -1;
		point dir;
		int cbpi;
		for (auto ccbpi : ep_closestbranchpointindex){
			epi++;
			if (ccbpi == branchpointindex){
				double distance = closest_branchpoint(ep_position[epi], cbpi, dir);
				if (distance < SQRT_DBL_MAX){
					ep_closestbranchpointindex[epi] = cbpi;
					ep_normalizeddirection[epi] = dir;
					ep_closestdistance[epi] = distance;
				}
			}
		}
	}
	delete branch;
	delete newbranchpoint;
}

// process a single iteration of new branchpoints
static void newbranchpoints(double branchlength, double killdistance, double tropism, PyObject *excludecallback){
	
	// create a set of unique branchpoint indices
	auto live_branchpoints = unordered_set<int>(ep_closestbranchpointindex.begin(), ep_closestbranchpointindex.end());

	for (auto bpi : live_branchpoints){
		if (bpi < 0) continue; // endpoints that are dead for various reasons
		auto sumdir = point();
		int epi = -1;
		for (auto ep : ep_normalizeddirection){
			epi++;
			if (ep_closestbranchpointindex[epi] == bpi){
				sumdir[0] += ep[0];
				sumdir[1] += ep[1];
				sumdir[2] += ep[2];
			}
		}
		sumdir = *normalize(sumdir);
		sumdir[2] += tropism;
		sumdir = *normalize(sumdir);

		add_branchpoint(bpi, sumdir, branchlength, killdistance, excludecallback);
	}
}

int iterate(
	points startpoints,
	points endpoints,
	points additionalendpoints,
	int niterations,
	double branchlength,
	double killdistance,
	double tropism,
	PyObject *excludecallback,

	points &branchpoints,
	indices &branchpointparents)
{
	// truncate globals to remove stuff from a previous call to iterate
	ep_closestbranchpointindex.clear();
	ep_closestdistance.clear();
	ep_normalizeddirection.clear();
	ep_position.clear();
	bp_connections.clear();

	// create global pointers so we don't have to pass these arguments again and again
	bp_position = &branchpoints;
	bp_parent = &branchpointparents;

	// initialize branchpoints
	for (auto sp : startpoints){
		bp_position->push_back(sp);
		bp_parent->push_back(-1);
		bp_connections.push_back(0);
	}

	// initialize endpoints
	for (auto ep : endpoints){
		add_endpoint(ep);
	}

	int extra_eps = additionalendpoints.size() / niterations; // extra eps per iteration
	for (int i = 0; i < niterations; i++){
		//dump_endpoints(i);
		newbranchpoints(branchlength, killdistance, tropism, excludecallback);
		for (int j = 0; j < extra_eps; j++){
			if (additionalendpoints.size() <= 0) break;
			add_endpoint(additionalendpoints.back());
			additionalendpoints.pop_back();
		}
	}
	//dump_endpoints(niterations);
	return 1;
}