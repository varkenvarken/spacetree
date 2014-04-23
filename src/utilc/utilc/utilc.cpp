#include "Python.h"

double closest(double *pos, int *count, int n, double x, double y, double z, int *index, double v[3]){

	double d2 = 1e30;
	for (int i = 0; i<n; i++){
		if (count[i]>1) continue;
		double dx = x - pos[i * 3];
		double dy = y - pos[i * 3 + 1];
		double dz = z - pos[i * 3 + 2];
		double d = dx*dx + dy*dy + dz*dz;
		if (d < d2){
			d2 = d;
			*index = i;
			v[0] = dx; v[1] = dy; v[2] = dz;
		}
	}
	return d2;
}

double direction(double *pos, int n, double v[3]){
	double *end = pos + n * 3;
	v[0] = v[1] = v[2] = 0;
	while (pos < end){
		v[0] += *pos++;
		v[1] += *pos++;
		v[2] += *pos++;
	}
	return v[0] * v[0] + v[1] * v[1] + v[2] * v[2];
}

static PyObject *
py_closest(PyObject *self, PyObject *args)
{
	PyObject *pos, *count;
	Py_buffer posview, countview;
	int n;
	double x, y, z;
	double d2, v[3];
	int index;

	/* Get the passed Python objects */
	if (!PyArg_ParseTuple(args, "OOiddd", &pos, &count, &n, &x, &y, &z)) {
		return NULL;
	}


	if (PyObject_GetBuffer(pos, &posview,
		PyBUF_ANY_CONTIGUOUS | PyBUF_FORMAT) == -1) {
		return NULL;
	}
	if (posview.ndim != 1) {
		PyErr_SetString(PyExc_TypeError, "Expected a 1-dimensional array");
		PyBuffer_Release(&posview);
		return NULL;
	}
	/* Check the type of items in the array */
	if (strcmp(posview.format, "d") != 0) {
		PyErr_SetString(PyExc_TypeError, "Expected an array of doubles");
		PyBuffer_Release(&posview);
		return NULL;
	}

	if (PyObject_GetBuffer(count, &countview,
		PyBUF_ANY_CONTIGUOUS | PyBUF_FORMAT) == -1) {
		PyBuffer_Release(&posview);
		return NULL;
	}
	if (countview.ndim != 1) {
		PyErr_SetString(PyExc_TypeError, "Expected a 1-dimensional array");
		PyBuffer_Release(&posview);
		PyBuffer_Release(&countview);
		return NULL;
	}
	/* Check the type of items in the array */
	if (strcmp(countview.format, "i") != 0) {
		PyErr_SetString(PyExc_TypeError, "Expected an array of ints");
		PyBuffer_Release(&posview);
		PyBuffer_Release(&countview);
		return NULL;
	}


	/* Pass the raw buffer and size to the C function */
	d2 = closest((double *)posview.buf, (int *)countview.buf, n, x, y, z, &index, v);
	/* Indicate we're done working with the buffer */

	PyBuffer_Release(&posview);
	PyBuffer_Release(&countview);

	return Py_BuildValue("di(ddd)", d2, index, v[0], v[1], v[2]);
}

static PyObject *
py_direction(PyObject *self, PyObject *args)
{
	PyObject *pos;
	Py_buffer posview;
	double d2, v[3];

	/* Get the passed Python objects */
	if (!PyArg_ParseTuple(args, "O", &pos)) {
		return NULL;
	}


	if (PyObject_GetBuffer(pos, &posview,
		PyBUF_ANY_CONTIGUOUS | PyBUF_FORMAT) == -1) {
		return NULL;
	}
	if (posview.ndim != 1) {
		PyErr_SetString(PyExc_TypeError, "Expected a 1-dimensional array");
		PyBuffer_Release(&posview);
		return NULL;
	}
	if (strcmp(posview.format, "d") != 0) {
		PyErr_SetString(PyExc_TypeError, "Expected an array of doubles");
		PyBuffer_Release(&posview);
		return NULL;
	}

	d2 = direction((double *)posview.buf, (posview.len / posview.itemsize) / 3, v);
	PyBuffer_Release(&posview);

	return Py_BuildValue("(ddd)d", v[0], v[1], v[2], d2);
}

static PyMethodDef utilc_methods[] = {
	{ "closest", py_closest, METH_VARARGS, "closest doc string" },
	{ "direction", py_direction, METH_VARARGS, "direction doc string" },
	{ NULL, NULL }
};

static struct PyModuleDef utilcmodule = {
	PyModuleDef_HEAD_INIT,
	"utilc",
	"utilc module doc string",
	-1,
	utilc_methods,
	NULL,
	NULL,
	NULL,
	NULL
};

PyMODINIT_FUNC
PyInit_utilc(void)
{
	return PyModule_Create(&utilcmodule);
}