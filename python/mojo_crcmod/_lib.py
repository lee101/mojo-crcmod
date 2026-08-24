"""ctypes bridge to the compiled Mojo CRC kernel."""

from __future__ import annotations

import ctypes
from pathlib import Path

try:
    from ._bridge import update
except ImportError as error:
    raise RuntimeError("Mojo bridge is missing; run `pixi run build`") from error

ROOT = Path(__file__).resolve().parents[2]
LIB_PATH = ROOT / "dist" / "libmojo-crcmod.so"

_I64 = ctypes.c_int64
_U64 = ctypes.c_uint64
_lib: ctypes.PyDLL | None = None


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


def table_address(table: ctypes.Array) -> int:
    return ctypes.addressof(table)
