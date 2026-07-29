"""ctypes bridge to the compiled Mojo CRC kernel."""

from __future__ import annotations

import ctypes
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIB_PATH = ROOT / "dist" / "libmojo-crcmod.so"

_I64 = ctypes.c_int64
_U64 = ctypes.c_uint64
_lib: ctypes.PyDLL | None = None
_bytes_address = ctypes.pythonapi.PyBytes_AsString
_bytes_address.argtypes = [ctypes.py_object]
_bytes_address.restype = ctypes.c_void_p


class _PyBuffer(ctypes.Structure):
    _fields_ = [
        ("buf", ctypes.c_void_p),
        ("obj", ctypes.c_void_p),
        ("len", ctypes.c_ssize_t),
        ("itemsize", ctypes.c_ssize_t),
        ("readonly", ctypes.c_int),
        ("ndim", ctypes.c_int),
        ("format", ctypes.c_char_p),
        ("shape", ctypes.POINTER(ctypes.c_ssize_t)),
        ("strides", ctypes.POINTER(ctypes.c_ssize_t)),
        ("suboffsets", ctypes.POINTER(ctypes.c_ssize_t)),
        ("internal", ctypes.c_void_p),
    ]


_get_buffer = ctypes.pythonapi.PyObject_GetBuffer
_get_buffer.argtypes = [ctypes.py_object, ctypes.POINTER(_PyBuffer), ctypes.c_int]
_get_buffer.restype = ctypes.c_int
_release_buffer = ctypes.pythonapi.PyBuffer_Release
_release_buffer.argtypes = [ctypes.POINTER(_PyBuffer)]
_release_buffer.restype = None


def lib() -> ctypes.PyDLL:
    global _lib
    if _lib is None:
        if not LIB_PATH.exists():
            raise RuntimeError("Mojo library is missing; run `pixi run build`")
        loaded = ctypes.PyDLL(str(LIB_PATH))
        loaded.mojo_crc_update.argtypes = [
            _I64,
            _I64,
            _I64,
            _I64,
            _U64,
            _I64,
            _I64,
            _U64,
        ]
        loaded.mojo_crc_update.restype = _I64
        _lib = loaded
    return _lib


def make_table(values: list[int]) -> ctypes.Array:
    return (_U64 * len(values))(*values)


def update(
    data: object,
    table: ctypes.Array,
    crc: int,
    width: int,
    reflected: bool,
    xor_out: int,
) -> int:
    if isinstance(data, str):
        raise TypeError("Unicode-objects must be encoded before calculating a CRC")
    if isinstance(data, bytes):
        return _call_update(
            _bytes_address(data),
            len(data),
            table,
            crc,
            width,
            reflected,
            xor_out,
        )
    view = _PyBuffer()
    _get_buffer(data, ctypes.byref(view), 0)
    try:
        address = view.buf or _bytes_address(b"")
        return _call_update(
            address,
            view.len,
            table,
            crc,
            width,
            reflected,
            xor_out,
        )
    finally:
        _release_buffer(ctypes.byref(view))


def _call_update(
    address: int,
    length: int,
    table: ctypes.Array,
    crc: int,
    width: int,
    reflected: bool,
    xor_out: int,
) -> int:
    result = _U64()
    status = lib().mojo_crc_update(
        address,
        ctypes.addressof(table),
        ctypes.addressof(result),
        length,
        crc,
        width,
        reflected,
        xor_out,
    )
    if status != 0:
        raise RuntimeError("Mojo CRC kernel rejected invalid arguments")
    return int(result.value)
