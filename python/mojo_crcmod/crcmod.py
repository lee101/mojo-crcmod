"""Parameterized CRC functions and hashlib-style state objects backed by Mojo."""

from __future__ import annotations

import operator

from ._lib import make_table, table_address, update as _mojo_update

__all__ = ["mkCrcFun", "Crc"]

_PARALLEL_CHUNK_BYTES = 4 * 1024 * 1024
_PARALLEL_SCRATCH_WORDS = 8


def _verify_poly(poly: int) -> int:
    message = "The degree of the polynomial must be 8, 16, 24, 32 or 64"
    for width in (8, 16, 24, 32, 64):
        if (1 << width) <= poly < (1 << (width + 1)):
            return width
    raise ValueError(message)


def _verify_params(poly: int, init_crc: int, xor_out: int) -> tuple[int, int, int]:
    width = _verify_poly(poly)
    mask = (1 << width) - 1
    return width, init_crc & mask, xor_out & mask


def _bit_reverse(value: int, width: int) -> int:
    result = 0
    for _ in range(width):
        result = (result << 1) | (value & 1)
        value >>= 1
    return result


def _byte_crc(value: int, poly: int, width: int) -> int:
    high_bit = 1 << (width - 1)
    for _ in range(8):
        value = ((value << 1) ^ poly) if value & high_bit else value << 1
    return value & ((1 << width) - 1)


def _byte_crc_reflected(value: int, poly: int, width: int) -> int:
    for _ in range(8):
        value = ((value >> 1) ^ poly) if value & 1 else value >> 1
    return value & ((1 << width) - 1)


def _make_table(poly: int, width: int, reflected: bool) -> list[int]:
    mask = (1 << width) - 1
    if reflected:
        reversed_poly = _bit_reverse(poly & mask, width)
        return [_byte_crc_reflected(i, reversed_poly, width) for i in range(256)]
    stripped_poly = poly & mask
    return [
        _byte_crc(i << (width - 8), stripped_poly, width) for i in range(256)
    ]


def _make_slicing_table(
    table: list[int], width: int, reflected: bool
) -> list[int]:
    mask = (1 << width) - 1

    def advance_zero(value: int) -> int:
        if reflected:
            return table[value & 0xFF] ^ (value >> 8)
        if width == 8:
            return table[value & 0xFF]
        return table[(value >> (width - 8)) & 0xFF] ^ (
            (value << 8) & mask
        )

    slicing_table = []
    for position in range(16):
        advances = 15 - position
        for byte in range(256):
            value = table[byte]
            for _ in range(advances):
                value = advance_zero(value)
            slicing_table.append(value)
    return slicing_table


def _make_advance_table(
    table: list[int], width: int, reflected: bool
) -> list[int]:
    mask = (1 << width) - 1

    def advance_zero(value: int) -> int:
        if reflected:
            return table[value & 0xFF] ^ (value >> 8)
        if width == 8:
            return table[value & 0xFF]
        return table[(value >> (width - 8)) & 0xFF] ^ (
            (value << 8) & mask
        )

    def apply(operator: list[int], value: int) -> int:
        result = 0
        bit = 0
        while value:
            if value & 1:
                result ^= operator[bit]
            value >>= 1
            bit += 1
        return result

    operator = [advance_zero(1 << bit) for bit in range(width)]
    exponent = _PARALLEL_CHUNK_BYTES
    powers = []
    while exponent:
        if exponent & 1:
            powers.append(operator)
        operator = [apply(operator, value) for value in operator]
        exponent >>= 1

    def advance_chunk(value: int) -> int:
        for power in powers:
            value = apply(power, value)
        return value

    advance_table = []
    for position in range(8):
        if position < width // 8:
            shift = 8 * position if reflected else width - 8 * (position + 1)
            advance_table.extend(
                advance_chunk(byte << shift) for byte in range(256)
            )
        else:
            advance_table.extend([0] * 256)
    return advance_table


def _make_crc_function(
    poly: int, width: int, init_crc: int, reflected: bool, xor_out: int
):
    reflected_flag = bool(reflected)
    mask = (1 << width) - 1
    table = _make_table(poly, width, reflected_flag)
    native_table = make_table(
        _make_slicing_table(table, width, reflected_flag)
        + _make_advance_table(table, width, reflected_flag)
        + [0] * _PARALLEL_SCRATCH_WORDS
    )
    native_table_address = table_address(native_table)

    def crcfun(data, crc=init_crc):
        return _mojo_update(
            data,
            native_table_address,
            operator.index(crc) & mask,
            width,
            reflected_flag,
            xor_out,
        )

    crcfun._native_table = native_table
    return crcfun, table, native_table


def mkCrcFun(poly, initCrc=-1, rev=True, xorOut=0):
    """Return a function that computes the requested parameterized CRC."""
    width, init_crc, xor_out = _verify_params(poly, initCrc, xorOut)
    return _make_crc_function(poly, width, init_crc, rev, xor_out)[0]


class Crc:
    """Compute a parameterized CRC through an incremental hashlib-style API."""

    def __init__(
        self, poly, initCrc=-1, rev=True, xorOut=0, initialize=True
    ):
        if not initialize:
            return
        width, init_crc, xor_out = _verify_params(poly, initCrc, xorOut)
        self.digest_size = width // 8
        self.initCrc = init_crc
        self.xorOut = xor_out
        self.poly = poly
        self.reverse = rev
        self._crc, self.table, self._native_table = _make_crc_function(
            poly, width, init_crc, rev, xor_out
        )
        self.crcValue = self.initCrc

    def __str__(self):
        width = self.digest_size * 2
        return "\n".join(
            (
                f"poly = 0x{self.poly:X}",
                f"reverse = {self.reverse}",
                f"initCrc  = 0x{self.initCrc:0{width}X}",
                f"xorOut   = 0x{self.xorOut:0{width}X}",
                f"crcValue = 0x{self.crcValue:0{width}X}",
            )
        )

    def new(self, arg=None):
        duplicate = Crc(poly=None, initialize=False)
        duplicate._crc = self._crc
        duplicate._native_table = self._native_table
        duplicate.digest_size = self.digest_size
        duplicate.initCrc = self.initCrc
        duplicate.xorOut = self.xorOut
        duplicate.table = self.table
        duplicate.crcValue = self.initCrc
        duplicate.reverse = self.reverse
        duplicate.poly = self.poly
        if arg is not None:
            duplicate.update(arg)
        return duplicate

    def copy(self):
        duplicate = self.new()
        duplicate.crcValue = self.crcValue
        return duplicate

    def update(self, data):
        self.crcValue = self._crc(data, self.crcValue)

    def digest(self):
        return self.crcValue.to_bytes(self.digest_size, "big")

    def hexdigest(self):
        return f"{self.crcValue:0{self.digest_size * 2}X}"

    def generateCode(
        self,
        functionName,
        out,
        dataType=None,
        crcType=None,
    ):
        """Generate a standalone C/C++ table-driven CRC function."""
        data_type = dataType or "UINT8"
        if crcType is None:
            storage_width = 32 if self.digest_size == 3 else 8 * self.digest_size
            crc_type = f"UINT{storage_width}"
        else:
            crc_type = crcType

        if self.digest_size == 1:
            expression = f"table[*data ^ ({data_type})crc]"
        elif self.reverse:
            expression = f"table[*data ^ ({data_type})crc] ^ (crc >> 8)"
        else:
            shift = 8 * (self.digest_size - 1)
            expression = (
                f"table[*data ^ ({data_type})(crc >> {shift})] ^ (crc << 8)"
            )

        suffix = "U" if self.digest_size <= 4 else "ULL"
        digits = 2 * self.digest_size
        per_row = {1: 8, 2: 8, 3: 4, 4: 4, 8: 2}[self.digest_size]
        rows = []
        for start in range(0, 256, per_row):
            values = ", ".join(
                f"0x{value:0{digits}X}{suffix}"
                for value in self.table[start : start + per_row]
            )
            rows.append(f"        {values},")

        pre = []
        post = []
        if self.xorOut:
            line = f"    crc = crc ^ 0x{self.xorOut:0{digits}X}{suffix};"
            pre.append(line)
            post.append(line)
        if self.digest_size == 3:
            line = "    crc = crc & 0xFFFFFFU;"
            (pre if self.reverse else post).append(line)

        polynomial = f"0x{self.poly:X}"
        mode = ", bit reverse algorithm" if self.reverse else ""
        source = [
            "// Automatically generated CRC function",
            f"// polynomial: {polynomial}{mode}",
            f"{crc_type}",
            f"{functionName}({data_type} *data, int len, {crc_type} crc)",
            "{",
            f"    static const {crc_type} table[256] = {{",
            *rows,
            "    };",
            *pre,
            "    while (len > 0)",
            "    {",
            f"        crc = {expression};",
            "        data++;",
            "        len--;",
            "    }",
            *post,
            "    return crc;",
            "}",
            "",
        ]
        out.write("\n".join(source))
