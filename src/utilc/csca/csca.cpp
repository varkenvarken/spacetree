#include "Python.h"
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
	auto startpoints = points();
	auto endpoints = points();
	auto additionalendpoints = points();
	//printf("py_sca start \n");

	PyObject *endpointlist, *startpointlist, *additionalendpointlist;
	int niterations;
	double branchlength, killdistance, tropism;

	if (!PyArg_ParseTuple(args, "OOOiddd", 
		&endpointlist, &startpointlist, &additionalendpointlist, 
		&niterations, &branchlength, &killdistance, &tropism)) {
		return NULL;
	}

	if (!py_sequence_of_3sequence(endpointlist, endpoints)){ return NULL; }
	if (!py_sequence_of_3sequence(startpointlist, startpoints)){ return NULL; }
	if (!py_sequence_of_3sequence(additionalendpointlist, additionalendpoints)){ return NULL; }

	auto branchpoints = points();
	auto branchpointparents = indices();

	//printf("py_sca start iterate\n");
	int n = iterate(startpoints, endpoints, additionalendpoints,
					niterations, branchlength, killdistance, tropism,branchpoints, branchpointparents);
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

static PyMethodDef csca_methods[] = {
	{ "sca", py_sca, METH_VARARGS, "sca doc string" },
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