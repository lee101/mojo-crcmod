"""Parameterized table-driven CRC computation exposed through a C ABI."""

from std.sys.info import simd_width_of

comptime BPtr = UnsafePointer[UInt8, AnyOrigin[mut=True]]
comptime U64Ptr = UnsafePointer[UInt64, AnyOrigin[mut=True]]
comptime SLICE_BYTES = 16
comptime ADVANCE_OFFSET = SLICE_BYTES * 256
comptime SCRATCH_OFFSET = ADVANCE_OFFSET + 8 * 256
comptime PARALLEL_CHUNK_BYTES = 4 * 1024 * 1024
comptime PARALLEL_THRESHOLD = 2 * PARALLEL_CHUNK_BYTES
comptime PARALLEL_WORKERS = 4
comptime PARALLEL_SCRATCH_WORDS = 8


def crc_slicing_reflected(
    data: BPtr, table: U64Ptr, n: Int, initial: UInt64
) -> UInt64:
    comptime W = simd_width_of[DType.float64]()
    var state = initial
    var i = 0
    while i + SLICE_BYTES <= n:
        var next_state = UInt64(0)
        comptime for group in range(SLICE_BYTES // W):
            var bytes = data.load[width=W, alignment=1](i + group * W)
            comptime for lane in range(W):
                comptime position = group * W + lane
                var byte = bytes[lane]
                if position < 8:
                    byte ^= UInt8(state >> UInt64(8 * position))
                next_state ^= table[position * 256 + Int(byte)]
        state = next_state
        i += SLICE_BYTES
    while i < n:
        var index = Int((state ^ UInt64(data[i])) & UInt64(0xFF))
        state = table[15 * 256 + index] ^ (state >> UInt64(8))
        i += 1
    return state


def crc_slicing_forward(
    data: BPtr,
    table: U64Ptr,
    n: Int,
    initial: UInt64,
    width: Int,
    mask: UInt64,
) -> UInt64:
    comptime W = simd_width_of[DType.float64]()
    var state = initial
    var aligned_state = UInt64(0)
    var i = 0
    while i + SLICE_BYTES <= n:
        aligned_state = state << UInt64(64 - width)
        var next_state = UInt64(0)
        comptime for group in range(SLICE_BYTES // W):
            var bytes = data.load[width=W, alignment=1](i + group * W)
            comptime for lane in range(W):
                comptime position = group * W + lane
                var byte = bytes[lane]
                if position < 8:
                    byte ^= UInt8(
                        aligned_state >> UInt64(56 - 8 * position)
                    )
                next_state ^= table[position * 256 + Int(byte)]
        state = next_state
        i += SLICE_BYTES
    if width == 8:
        while i < n:
            state = table[15 * 256 + Int(state ^ UInt64(data[i]))]
            i += 1
    else:
        var shift = UInt64(width - 8)
        while i < n:
            var index = Int(
                ((state >> shift) ^ UInt64(data[i])) & UInt64(0xFF)
            )
            state = table[15 * 256 + index] ^ ((state << 8) & mask)
            i += 1
    return state


def advance_chunk_reflected(state: UInt64, table: U64Ptr) -> UInt64:
    return (
        table[ADVANCE_OFFSET + 0 * 256 + Int(UInt8(state))]
        ^ table[ADVANCE_OFFSET + 1 * 256 + Int(UInt8(state >> 8))]
        ^ table[ADVANCE_OFFSET + 2 * 256 + Int(UInt8(state >> 16))]
        ^ table[ADVANCE_OFFSET + 3 * 256 + Int(UInt8(state >> 24))]
        ^ table[ADVANCE_OFFSET + 4 * 256 + Int(UInt8(state >> 32))]
        ^ table[ADVANCE_OFFSET + 5 * 256 + Int(UInt8(state >> 40))]
        ^ table[ADVANCE_OFFSET + 6 * 256 + Int(UInt8(state >> 48))]
        ^ table[ADVANCE_OFFSET + 7 * 256 + Int(UInt8(state >> 56))]
    )


def advance_chunk_forward(
    state: UInt64, table: U64Ptr, width: Int
) -> UInt64:
    var aligned_state = state << UInt64(64 - width)
    return (
        table[ADVANCE_OFFSET + 0 * 256 + Int(UInt8(aligned_state >> 56))]
        ^ table[ADVANCE_OFFSET + 1 * 256 + Int(UInt8(aligned_state >> 48))]
        ^ table[ADVANCE_OFFSET + 2 * 256 + Int(UInt8(aligned_state >> 40))]
        ^ table[ADVANCE_OFFSET + 3 * 256 + Int(UInt8(aligned_state >> 32))]
        ^ table[ADVANCE_OFFSET + 4 * 256 + Int(UInt8(aligned_state >> 24))]
        ^ table[ADVANCE_OFFSET + 5 * 256 + Int(UInt8(aligned_state >> 16))]
        ^ table[ADVANCE_OFFSET + 6 * 256 + Int(UInt8(aligned_state >> 8))]
        ^ table[ADVANCE_OFFSET + 7 * 256 + Int(UInt8(aligned_state))]
    )


def crc_update(
    data: BPtr,
    table: U64Ptr,
    n: Int,
    initial: UInt64,
    width: Int,
    reflected: Bool,
    xor_out: UInt64,
) -> UInt64:
    var mask = (
        UInt64(0xFFFFFFFFFFFFFFFF)
        if width == 64
        else (UInt64(1) << UInt64(width)) - UInt64(1)
    )
    var state = (initial ^ xor_out) & mask
    var data_position = 0

    if n >= PARALLEL_THRESHOLD:
        var full_chunks = n // PARALLEL_CHUNK_BYTES
        var first_chunk = 0
        while first_chunk < full_chunks:
            var chunk_count = min(
                PARALLEL_SCRATCH_WORDS, full_chunks - first_chunk
            )

            for chunk in range(chunk_count):
                var start = (first_chunk + chunk) * PARALLEL_CHUNK_BYTES
                if reflected:
                    table[SCRATCH_OFFSET + chunk] = crc_slicing_reflected(
                        data + start,
                        table,
                        PARALLEL_CHUNK_BYTES,
                        UInt64(0),
                    )
                else:
                    table[SCRATCH_OFFSET + chunk] = crc_slicing_forward(
                        data + start,
                        table,
                        PARALLEL_CHUNK_BYTES,
                        UInt64(0),
                        width,
                        mask,
                    )
            for chunk in range(chunk_count):
                if reflected:
                    state = advance_chunk_reflected(state, table)
                else:
                    state = advance_chunk_forward(state, table, width)
                state ^= table[SCRATCH_OFFSET + chunk]
            first_chunk += chunk_count
        data_position = full_chunks * PARALLEL_CHUNK_BYTES

    if reflected:
        state = crc_slicing_reflected(
            data + data_position, table, n - data_position, state
        )
    else:
        state = crc_slicing_forward(
            data + data_position,
            table,
            n - data_position,
            state,
            width,
            mask,
        )

    return (state ^ xor_out) & mask


@export("mojo_crc_update_value")
def mojo_crc_update_value(
    data_addr: Int,
    table_addr: Int,
    n: Int,
    initial: UInt64,
    width: Int,
    reflected: Int,
    xor_out: UInt64,
) abi("C") -> UInt64:
    var table = U64Ptr(unsafe_from_address=table_addr)
    var safe_data_addr = data_addr if data_addr != 0 else table_addr
    return crc_update(
        BPtr(unsafe_from_address=safe_data_addr),
        table,
        n,
        initial,
        width,
        reflected != 0,
        xor_out,
    )


@export("mojo_crc_update")
def mojo_crc_update(
    data_addr: Int,
    table_addr: Int,
    result_addr: Int,
    n: Int,
    initial: UInt64,
    width: Int,
    reflected: Int,
    xor_out: UInt64,
) abi("C") -> Int:
    # Validate every value that affects pointer construction or indexing.  The
    # shared-library entry point is callable independently of the Python
    # wrapper, so malformed C callers must not be able to create null pointers
    # or turn a negative length into an unbounded read.
    if (
        table_addr == 0
        or result_addr == 0
        or n < 0
        or (n > 0 and data_addr == 0)
        or (
            width != 8
            and width != 16
            and width != 24
            and width != 32
            and width != 64
        )
    ):
        return 1

    var table = U64Ptr(unsafe_from_address=table_addr)
    # No input is dereferenced for an empty update.  Reuse the known-non-null
    # table address because Mojo's UnsafePointer cannot represent null.
    var safe_data_addr = data_addr if data_addr != 0 else table_addr
    var result = crc_update(
        BPtr(unsafe_from_address=safe_data_addr),
        table,
        n,
        initial,
        width,
        reflected != 0,
        xor_out,
    )
    U64Ptr(unsafe_from_address=result_addr)[0] = result
    return 0
