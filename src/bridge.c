#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdint.h>

extern uint64_t mojo_crc_update_value(
    int64_t data_addr,
    int64_t table_addr,
    int64_t length,
    uint64_t initial,
    int64_t width,
    int64_t reflected,
    uint64_t xor_out
);

static PyObject *crc_update(PyObject *self, PyObject *args)
{
    PyObject *data;
    unsigned long long table_addr;
    unsigned long long initial;
    int width;
    int reflected;
    unsigned long long xor_out;
    const char *buffer;
    Py_ssize_t length;
    Py_buffer view;
    int acquired = 0;

    if (!PyArg_ParseTuple(
            args,
            "OKKiiK:update",
            &data,
            &table_addr,
            &initial,
            &width,
            &reflected,
            &xor_out)) {
        return NULL;
    }
    if (PyUnicode_Check(data)) {
        PyErr_SetString(
            PyExc_TypeError,
            "Unicode-objects must be encoded before calculating a CRC"
        );
        return NULL;
    }
    if (PyBytes_CheckExact(data)) {
        buffer = PyBytes_AS_STRING(data);
        length = PyBytes_GET_SIZE(data);
    } else {
        if (PyObject_GetBuffer(data, &view, PyBUF_SIMPLE) < 0) {
            return NULL;
        }
        acquired = 1;
        buffer = view.buf;
        length = view.len;
    }

    uint64_t result = mojo_crc_update_value(
        (int64_t)(uintptr_t)buffer,
        (int64_t)table_addr,
        (int64_t)length,
        (uint64_t)initial,
        (int64_t)width,
        (int64_t)reflected,
        (uint64_t)xor_out
    );
    if (acquired) {
        PyBuffer_Release(&view);
    }
    return PyLong_FromUnsignedLongLong(result);
}

static PyMethodDef methods[] = {
    {"update", crc_update, METH_VARARGS, NULL},
    {NULL, NULL, 0, NULL},
};

static struct PyModuleDef module = {
    PyModuleDef_HEAD_INIT,
    "_bridge",
    NULL,
    -1,
    methods,
};

PyMODINIT_FUNC PyInit__bridge(void)
{
    return PyModule_Create(&module);
}
