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

#include "Sca.h"
#include <cstdio>

using namespace std;

static int py_sequence_of_3sequence(PyObject *sequence, points &result){
	if (!PySequence_Check(sequence)){ return 0; }

	auto n = PySequence_Size(sequence);
	for (decltype(n) i = 0; i < n; i++){
		auto item = PySequence_GetItem(sequence, i);
		if (item == NULL || !PySequence_Check(item) || PySequence_Size(item)!=3) return 0;
		double x = PyFloat_AsDouble(PySequence_GetItem(item, 0));
		double y = PyFloat_AsDouble(PySequence_GetItem(item, 1));
		double z = PyFloat_AsDouble(PySequence_GetItem(item, 2));
		result.push_back(*new point{ x, y, z });
	}
	return 1;
}

static PyObject *py_sca(PyObject *self, PyObject *args)
{
	printf("py_sca\n");
	auto startpoints = points();
	auto endpoints = points();
	auto additionalendpoints = points();
	//printf("py_sca start \n");

	PyObject *endpointlist, *startpointlist, *additionalendpointlist, *callback = NULL;
	int niterations;
	double branchlength, killdistance, tropism;

	if (!PyArg_ParseTuple(args, "OOOiddd|O:exclude", 
		&endpointlist, &startpointlist, &additionalendpointlist, 
		&niterations, &branchlength, &killdistance, &tropism, &callback)) {
		return NULL;
	}

	if (!py_sequence_of_3sequence(endpointlist, endpoints)){ return NULL; }
	if (!py_sequence_of_3sequence(startpointlist, startpoints)){ return NULL; }
	if (!py_sequence_of_3sequence(additionalendpointlist, additionalendpoints)){ return NULL; }
	if (callback != NULL){ // if no callback argument was given it's NULL
		if (callback == Py_None){ // None is also allowed to indicate absence
			callback = NULL;
		}else if (!PyCallable_Check(callback)) {
			PyErr_SetString(PyExc_TypeError, "parameter must be callable");
			return NULL;
		}
	}
	auto branchpoints = points();
	auto branchpointparents = indices();

	//printf("py_sca start iterate\n");
	// TODO add some exception handling in iterate()
	int n = iterate(startpoints, endpoints, additionalendpoints,
		niterations, branchlength, killdistance, tropism, callback, 
		branchpoints, branchpointparents);
	//printf("n brachpoints %d\n", branchpoints.size());

	PyObject *branchpointlist = PyList_New(0);
	for (auto v: branchpoints){
		PyList_Append(branchpointlist, Py_BuildValue("(ddd)", v[0], v[1], v[2]));
	}
	PyObject *branchpointparentlist = PyList_New(0);
	for (auto v : branchpointparents){
		PyList_Append(branchpointparentlist, Py_BuildValue("i", v));
	}

	return Py_BuildValue("OO", branchpointlist,branchpointparentlist);
}

static PyObject *py_testcallback(PyObject *self, PyObject *args){
	printf("py_testcallback\n");
	PyObject *callback = NULL;
	if (!PyArg_ParseTuple(args, "|O:callback", &callback)) {
		return NULL;
	}

	if (callback != NULL){ // if no callback argument was given it's NULL
		if (callback == Py_None){ // None is also allowed to indicate absence
			callback = NULL;
		}
		else if (!PyCallable_Check(callback)) {
			PyErr_SetString(PyExc_TypeError, "parameter must be callable");
			return NULL;
		}
	}
	printf("py_testcallback 2\n");

	PyObject *arg;
	PyObject *result;
	//arg = Py_BuildValue("((ddd))", 1.1, 2.2, 3.3);
	arg = PyTuple_New(3);
	PyTuple_SetItem(arg, 0, PyFloat_FromDouble(1.1));
	PyTuple_SetItem(arg, 1, PyFloat_FromDouble(2.2));
	PyTuple_SetItem(arg, 2, PyFloat_FromDouble(3.3));
	printf("py_testcallback 3\n");

	if (!PyTuple_Check(arg))printf("not a typle\n");
	//result = PyObject_CallObject(callback, arg);
	printf("start calling callback\n");
	result = PyObject_CallFunctionObjArgs(callback, arg, NULL);
	Py_DECREF(arg);
	int iresult;
	if (result != NULL){
		//if (!PyArg_ParseTuple(result, "i", &iresult)){
		//	printf("py_testcallback error on parsing callback return value");
		//	return NULL;
		//}
		if (!PyArg_Parse(result, "i", &iresult)){
			printf("py_testcallback error on parsing callback return value");
			return NULL;
		}

		//Py_DECREF(result);
		return result;
	}
	return Py_None;
}

static PyMethodDef csca_methods[] = {
	{ "sca", py_sca, METH_VARARGS, "sca doc string" },
	{ "testcallback", py_testcallback, METH_VARARGS, "testcallback doc string" },
	{ NULL, NULL }
};

static struct PyModuleDef cscamodule = {
	PyModuleDef_HEAD_INIT,
	"csca",
	"csca module doc string",
	-1,
	csca_methods,
	NULL,
	NULL,
	NULL,
	NULL
};

PyMODINIT_FUNC
PyInit_csca(void)
{
	return PyModule_Create(&cscamodule);
}