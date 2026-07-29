"""crcmod-compatible parameterized CRC computation backed by Mojo."""

from . import predefined
from .crcmod import Crc, mkCrcFun

__all__ = ["mkCrcFun", "Crc"]
__version__ = "0.1.0"
