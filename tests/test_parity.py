from __future__ import annotations

import array
import ctypes
import inspect
import io
import random
import shutil
import subprocess

import numpy as np
import pytest

import crcmod as upstream
import crcmod.predefined as upstream_predefined
import mojo_crcmod as mojo
from mojo_crcmod import predefined
from mojo_crcmod._lib import lib


CUSTOM_PARAMETERS = (
    (0x107, -1, False, 0),
    (0x139, -2, True, -1),
    (0x11021, 0, False, 0),
    (0x18005, -1, True, 0xFFFF),
    (0x1864CFB, 0x123456, False, 0xFFFFFF),
    (0x15D6DCB, -1, True, 123),
    (0x104C11DB7, 0, True, 0xFFFFFFFF),
    (0x1814141AB, -1, False, 12),
    (0x1000000000000001B, 0, True, 0),
    (0x142F0E1EBA9EA3693, -1, False, -1),
)
LENGTHS = (0, 1, 7, 8, 9, 31, 32, 255, 4097)
PARALLEL_THRESHOLD = 8 * 1024 * 1024


def data_for(length: int) -> bytes:
    return random.Random(length).randbytes(length)


def test_public_factory_and_constructor_signatures_match_upstream():
    assert inspect.signature(mojo.mkCrcFun) == inspect.signature(upstream.mkCrcFun)
    assert inspect.signature(mojo.Crc) == inspect.signature(upstream.Crc)
    assert inspect.signature(
        predefined.mkPredefinedCrcFun
    ) == inspect.signature(upstream_predefined.mkPredefinedCrcFun)
    assert inspect.signature(predefined.PredefinedCrc) == inspect.signature(
        upstream_predefined.PredefinedCrc
    )


@pytest.mark.parametrize("parameters", CUSTOM_PARAMETERS)
@pytest.mark.parametrize("length", LENGTHS)
def test_custom_parameter_parity(parameters, length):
    data = data_for(length)
    ours = mojo.mkCrcFun(*parameters)
    theirs = upstream.mkCrcFun(*parameters)
    assert ours(data) == theirs(data)


@pytest.mark.parametrize("parameters", CUSTOM_PARAMETERS)
def test_function_incremental_crc_argument_matches_upstream(parameters):
    data = data_for(10_003)
    ours = mojo.mkCrcFun(*parameters)
    theirs = upstream.mkCrcFun(*parameters)
    ours_crc = ours(data[:17])
    theirs_crc = theirs(data[:17])
    for chunk in (data[17:999], data[999:4096], data[4096:]):
        ours_crc = ours(chunk, ours_crc)
        theirs_crc = theirs(chunk, theirs_crc)
    assert ours_crc == theirs_crc


@pytest.mark.parametrize("name", ("crc-8", "xmodem", "crc-32", "crc-64"))
@pytest.mark.parametrize("length", (15, 16, 17))
def test_simd_block_boundaries_and_scalar_tail_match_upstream(name, length):
    data = data_for(length)
    assert predefined.mkCrcFun(name)(data) == upstream_predefined.mkCrcFun(
        name
    )(data)


@pytest.mark.parametrize(
    ("name", "length"),
    (
        ("crc-8", PARALLEL_THRESHOLD - 1),
        ("crc-8-darc", PARALLEL_THRESHOLD + 7),
        ("xmodem", PARALLEL_THRESHOLD),
        ("crc-24", PARALLEL_THRESHOLD + 3),
        ("crc-32", PARALLEL_THRESHOLD + 31),
        ("crc-64", PARALLEL_THRESHOLD + 17),
    ),
)
def test_parallel_threshold_and_tail_match_upstream(name, length):
    data = data_for(length)
    assert predefined.mkCrcFun(name)(data) == upstream_predefined.mkCrcFun(
        name
    )(data)


def test_parallel_reflected_24_bit_crc_matches_upstream():
    parameters = (0x15D6DCB, -1, True, 123)
    data = data_for(PARALLEL_THRESHOLD + 5)
    assert mojo.mkCrcFun(*parameters)(data) == upstream.mkCrcFun(*parameters)(
        data
    )


@pytest.mark.parametrize(
    "definition", upstream_predefined._crc_definitions, ids=lambda d: d["name"]
)
def test_every_predefined_algorithm_and_published_check_value(definition):
    ours = predefined.mkPredefinedCrcFun(definition["name"])(b"123456789")
    theirs = upstream_predefined.mkPredefinedCrcFun(definition["name"])(
        b"123456789"
    )
    assert ours == theirs == definition["check"]


@pytest.mark.parametrize(
    "name",
    (
        "crc-32",
        "CRC 32",
        "crc32",
        "32",
        "Crc32",
        "xmodem",
        "XMODEM",
        "crc-64-jones",
    ),
)
def test_predefined_name_normalization_matches_upstream(name):
    data = data_for(333)
    assert predefined.mkCrcFun(name)(data) == upstream_predefined.mkCrcFun(name)(
        data
    )


@pytest.mark.parametrize("parameters", CUSTOM_PARAMETERS)
def test_crc_object_state_digest_copy_new_and_metadata(parameters):
    ours = mojo.Crc(*parameters)
    theirs = upstream.Crc(*parameters)
    assert ours.digest_size == theirs.digest_size
    assert ours.initCrc == theirs.initCrc
    assert ours.xorOut == theirs.xorOut
    assert ours.poly == theirs.poly
    assert ours.reverse == theirs.reverse
    assert ours.table == theirs.table
    assert str(ours) == str(theirs)

    for chunk in (b"prefix", bytearray(b"-middle"), memoryview(b"-suffix")):
        assert ours.update(chunk) is theirs.update(chunk) is None
    assert ours.crcValue == theirs.crcValue
    assert ours.digest() == theirs.digest()
    assert ours.hexdigest() == theirs.hexdigest()

    ours_copy = ours.copy()
    theirs_copy = theirs.copy()
    ours_copy.update(b"-copy")
    theirs_copy.update(b"-copy")
    assert ours_copy.hexdigest() == theirs_copy.hexdigest()
    assert ours.new(b"fresh").hexdigest() == theirs.new(b"fresh").hexdigest()


@pytest.mark.parametrize(
    "data",
    (
        b"buffer",
        bytearray(b"buffer"),
        memoryview(b"buffer"),
        array.array("H", range(20)),
        np.arange(50, dtype=np.uint16),
        np.arange(48, dtype=np.uint8).reshape(6, 8),
    ),
)
def test_contiguous_buffer_protocol_inputs_match_upstream(data):
    ours = predefined.mkCrcFun("crc-32c")
    theirs = upstream_predefined.mkCrcFun("crc-32c")
    assert ours(data) == theirs(data)


def test_strided_buffers_are_rejected_like_upstream():
    data = np.arange(50, dtype=np.uint8)[::2]
    ours = predefined.mkCrcFun("crc-32")
    theirs = upstream_predefined.mkCrcFun("crc-32")
    with pytest.raises(ValueError, match="not C-contiguous"):
        ours(data)
    with pytest.raises(ValueError, match="not C-contiguous"):
        theirs(data)


def test_unicode_is_rejected_with_upstream_message():
    function = mojo.mkCrcFun(0x107)
    with pytest.raises(
        TypeError, match="Unicode-objects must be encoded before calculating a CRC"
    ):
        function("not bytes")


@pytest.mark.parametrize(
    "arguments",
    (
        (0, 1, 1, 1, 0, 8, 0, 0),
        (1, 0, 1, 1, 0, 8, 0, 0),
        (1, 1, 0, 1, 0, 8, 0, 0),
        (1, 1, 1, -1, 0, 8, 0, 0),
        (1, 1, 1, 1, 0, 7, 0, 0),
    ),
)
def test_native_abi_rejects_unsafe_arguments(arguments):
    assert lib().mojo_crc_update(*arguments) != 0


@pytest.mark.parametrize("poly", (0, 1, 0xFF, 0x200, 0x20000, 1 << 65))
def test_invalid_polynomial_matches_upstream(poly):
    with pytest.raises(ValueError) as ours:
        mojo.mkCrcFun(poly)
    with pytest.raises(ValueError) as theirs:
        upstream.mkCrcFun(poly)
    assert str(ours.value) == str(theirs.value)


def test_initial_crc_and_xor_out_are_masked_like_upstream():
    parameters = (0x11021, -0x1234567, False, 0x123456)
    ours = mojo.Crc(*parameters)
    theirs = upstream.Crc(*parameters)
    assert (ours.initCrc, ours.xorOut) == (theirs.initCrc, theirs.xorOut)
    ours.crcValue = -(1 << 80) + 7
    theirs.crcValue = -(1 << 80) + 7
    ours.update(b"masked state")
    theirs.update(b"masked state")
    assert ours.crcValue == theirs.crcValue


def test_unknown_predefined_name_matches_upstream():
    with pytest.raises(KeyError) as ours:
        predefined.mkCrcFun("missing")
    with pytest.raises(KeyError) as theirs:
        upstream_predefined.mkCrcFun("missing")
    assert str(ours.value) == str(theirs.value)


@pytest.mark.parametrize("name", ("crc-8", "crc-24", "crc-32", "crc-64"))
def test_predefined_class_alias_and_incremental_parity(name):
    ours = predefined.Crc(name)
    theirs = upstream_predefined.Crc(name)
    for chunk in (b"123", b"456", b"789"):
        ours.update(chunk)
        theirs.update(chunk)
    assert ours.crcValue == theirs.crcValue
    assert ours.digest() == theirs.digest()
    assert ours.hexdigest() == theirs.hexdigest()


@pytest.mark.parametrize("parameters", CUSTOM_PARAMETERS)
def test_generated_code_contains_the_same_table_and_contract(parameters):
    crc = mojo.Crc(*parameters)
    destination = io.StringIO()
    assert crc.generateCode("calculate_crc", destination) is None
    source = destination.getvalue()
    assert "calculate_crc" in source
    assert "table[256]" in source
    assert f"polynomial: 0x{crc.poly:X}" in source
    for value in (crc.table[0], crc.table[127], crc.table[255]):
        assert f"0x{value:0{crc.digest_size * 2}X}" in source


@pytest.mark.parametrize(
    "parameters",
    (
        (0x107, 0, False, 0),
        (0x1864CFB, 0x123456, False, 0xFFFFFF),
        (0x104C11DB7, 0, True, 0xFFFFFFFF),
        (0x1000000000000001B, 0, True, 0),
    ),
)
def test_generated_code_compiles_and_computes_crc(parameters, tmp_path):
    compiler = shutil.which("cc")
    if compiler is None:
        pytest.skip("a C compiler is required to compile generated code")

    crc = mojo.Crc(*parameters)
    generated = io.StringIO()
    crc.generateCode("calculate_crc", generated)
    source = tmp_path / "generated.c"
    library = tmp_path / "generated.so"
    source.write_text(
        "#include <stdint.h>\n"
        "typedef uint8_t UINT8;\n"
        "typedef uint16_t UINT16;\n"
        "typedef uint32_t UINT24;\n"
        "typedef uint32_t UINT32;\n"
        "typedef uint64_t UINT64;\n"
        + generated.getvalue()
    )
    subprocess.run(
        [compiler, "-shared", "-fPIC", "-Werror", "-o", library, source],
        check=True,
        capture_output=True,
        text=True,
    )
    compiled = ctypes.CDLL(str(library)).calculate_crc
    crc_type = {
        1: ctypes.c_uint8,
        2: ctypes.c_uint16,
        3: ctypes.c_uint32,
        4: ctypes.c_uint32,
        8: ctypes.c_uint64,
    }[crc.digest_size]
    compiled.argtypes = [
        ctypes.POINTER(ctypes.c_uint8),
        ctypes.c_int,
        crc_type,
    ]
    compiled.restype = crc_type
    data = data_for(257)
    native_data = (ctypes.c_uint8 * len(data)).from_buffer_copy(data)
    assert compiled(native_data, len(data), crc.initCrc) == crc._crc(data)
