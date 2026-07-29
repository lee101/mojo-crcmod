"""Named CRC definitions compatible with crcmod.predefined."""

from __future__ import annotations

from . import crcmod

__all__ = ["PredefinedCrc", "mkPredefinedCrcFun"]

_TABLE = [
    ("crc-8", "Crc8", 0x107, False, 0x00, 0x00, 0xF4),
    ("crc-8-darc", "Crc8Darc", 0x139, True, 0x00, 0x00, 0x15),
    ("crc-8-i-code", "Crc8ICode", 0x11D, False, 0xFD, 0x00, 0x7E),
    ("crc-8-itu", "Crc8Itu", 0x107, False, 0x55, 0x55, 0xA1),
    ("crc-8-maxim", "Crc8Maxim", 0x131, True, 0x00, 0x00, 0xA1),
    ("crc-8-rohc", "Crc8Rohc", 0x107, True, 0xFF, 0x00, 0xD0),
    ("crc-8-wcdma", "Crc8Wcdma", 0x19B, True, 0x00, 0x00, 0x25),
    ("crc-16", "Crc16", 0x18005, True, 0x0000, 0x0000, 0xBB3D),
    (
        "crc-16-buypass",
        "Crc16Buypass",
        0x18005,
        False,
        0x0000,
        0x0000,
        0xFEE8,
    ),
    (
        "crc-16-dds-110",
        "Crc16Dds110",
        0x18005,
        False,
        0x800D,
        0x0000,
        0x9ECF,
    ),
    (
        "crc-16-dect",
        "Crc16Dect",
        0x10589,
        False,
        0x0001,
        0x0001,
        0x007E,
    ),
    ("crc-16-dnp", "Crc16Dnp", 0x13D65, True, 0xFFFF, 0xFFFF, 0xEA82),
    (
        "crc-16-en-13757",
        "Crc16En13757",
        0x13D65,
        False,
        0xFFFF,
        0xFFFF,
        0xC2B7,
    ),
    (
        "crc-16-genibus",
        "Crc16Genibus",
        0x11021,
        False,
        0x0000,
        0xFFFF,
        0xD64E,
    ),
    (
        "crc-16-maxim",
        "Crc16Maxim",
        0x18005,
        True,
        0xFFFF,
        0xFFFF,
        0x44C2,
    ),
    (
        "crc-16-mcrf4xx",
        "Crc16Mcrf4xx",
        0x11021,
        True,
        0xFFFF,
        0x0000,
        0x6F91,
    ),
    (
        "crc-16-riello",
        "Crc16Riello",
        0x11021,
        True,
        0x554D,
        0x0000,
        0x63D0,
    ),
    (
        "crc-16-t10-dif",
        "Crc16T10Dif",
        0x18BB7,
        False,
        0x0000,
        0x0000,
        0xD0DB,
    ),
    (
        "crc-16-teledisk",
        "Crc16Teledisk",
        0x1A097,
        False,
        0x0000,
        0x0000,
        0x0FB3,
    ),
    (
        "crc-16-usb",
        "Crc16Usb",
        0x18005,
        True,
        0x0000,
        0xFFFF,
        0xB4C8,
    ),
    ("x-25", "CrcX25", 0x11021, True, 0x0000, 0xFFFF, 0x906E),
    ("xmodem", "CrcXmodem", 0x11021, False, 0x0000, 0x0000, 0x31C3),
    ("modbus", "CrcModbus", 0x18005, True, 0xFFFF, 0x0000, 0x4B37),
    ("kermit", "CrcKermit", 0x11021, True, 0x0000, 0x0000, 0x2189),
    (
        "crc-ccitt-false",
        "CrcCcittFalse",
        0x11021,
        False,
        0xFFFF,
        0x0000,
        0x29B1,
    ),
    (
        "crc-aug-ccitt",
        "CrcAugCcitt",
        0x11021,
        False,
        0x1D0F,
        0x0000,
        0xE5CC,
    ),
    (
        "crc-24",
        "Crc24",
        0x1864CFB,
        False,
        0xB704CE,
        0x000000,
        0x21CF02,
    ),
    (
        "crc-24-flexray-a",
        "Crc24FlexrayA",
        0x15D6DCB,
        False,
        0xFEDCBA,
        0x000000,
        0x7979BD,
    ),
    (
        "crc-24-flexray-b",
        "Crc24FlexrayB",
        0x15D6DCB,
        False,
        0xABCDEF,
        0x000000,
        0x1F23B8,
    ),
    (
        "crc-32",
        "Crc32",
        0x104C11DB7,
        True,
        0x00000000,
        0xFFFFFFFF,
        0xCBF43926,
    ),
    (
        "crc-32-bzip2",
        "Crc32Bzip2",
        0x104C11DB7,
        False,
        0x00000000,
        0xFFFFFFFF,
        0xFC891918,
    ),
    (
        "crc-32c",
        "Crc32C",
        0x11EDC6F41,
        True,
        0x00000000,
        0xFFFFFFFF,
        0xE3069283,
    ),
    (
        "crc-32d",
        "Crc32D",
        0x1A833982B,
        True,
        0x00000000,
        0xFFFFFFFF,
        0x87315576,
    ),
    (
        "crc-32-mpeg",
        "Crc32Mpeg",
        0x104C11DB7,
        False,
        0xFFFFFFFF,
        0x00000000,
        0x0376E6E7,
    ),
    (
        "posix",
        "CrcPosix",
        0x104C11DB7,
        False,
        0xFFFFFFFF,
        0xFFFFFFFF,
        0x765E7680,
    ),
    (
        "crc-32q",
        "Crc32Q",
        0x1814141AB,
        False,
        0x00000000,
        0x00000000,
        0x3010BF7F,
    ),
    (
        "jamcrc",
        "CrcJamCrc",
        0x104C11DB7,
        True,
        0xFFFFFFFF,
        0x00000000,
        0x340BC6D9,
    ),
    (
        "xfer",
        "CrcXfer",
        0x1000000AF,
        False,
        0x00000000,
        0x00000000,
        0xBD0BE338,
    ),
    (
        "crc-64",
        "Crc64",
        0x1000000000000001B,
        True,
        0x0000000000000000,
        0x0000000000000000,
        0x46A5A9388A5BEFFE,
    ),
    (
        "crc-64-we",
        "Crc64We",
        0x142F0E1EBA9EA3693,
        False,
        0x0000000000000000,
        0xFFFFFFFFFFFFFFFF,
        0x62EC59E3F1A4F00A,
    ),
    (
        "crc-64-jones",
        "Crc64Jones",
        0x1AD93D23594C935A9,
        True,
        0xFFFFFFFFFFFFFFFF,
        0x0000000000000000,
        0xCAA717168609F281,
    ),
]

_HEADINGS = ("name", "identifier", "poly", "reverse", "init", "xor_out", "check")
_crc_definitions = [dict(zip(_HEADINGS, row)) for row in _TABLE]


def _simplify_name(name):
    simplified = name.lower().replace("-", "").replace(" ", "")
    return simplified[3:] if simplified.startswith("crc") else simplified


_crc_definitions_by_name = {
    _simplify_name(definition["name"]): definition
    for definition in _crc_definitions
}
_crc_definitions_by_identifier = {
    definition["identifier"]: definition for definition in _crc_definitions
}


def _get_definition_by_name(crc_name):
    definition = _crc_definitions_by_name.get(_simplify_name(crc_name))
    if definition is None:
        definition = _crc_definitions_by_identifier.get(crc_name)
    if definition is None:
        raise KeyError(f"Unkown CRC name '{crc_name}'")
    return definition


class PredefinedCrc(crcmod.Crc):
    def __init__(self, crc_name):
        definition = _get_definition_by_name(crc_name)
        super().__init__(
            poly=definition["poly"],
            initCrc=definition["init"],
            rev=definition["reverse"],
            xorOut=definition["xor_out"],
        )


Crc = PredefinedCrc


def mkPredefinedCrcFun(crc_name):
    definition = _get_definition_by_name(crc_name)
    return crcmod.mkCrcFun(
        poly=definition["poly"],
        initCrc=definition["init"],
        rev=definition["reverse"],
        xorOut=definition["xor_out"],
    )


mkCrcFun = mkPredefinedCrcFun
