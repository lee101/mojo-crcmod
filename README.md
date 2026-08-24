# mojo-crcmod

`mojo-crcmod` is a standalone Mojo implementation of parameterized cyclic
redundancy checks with a Python API matching
[`crcmod`](https://crcmod.sourceforge.net/). It implements the algorithm
rather than linking to crcmod or another CRC library.

Use it by changing the import and keeping the crcmod calls:

```python
import mojo_crcmod as crcmod

crc32 = crcmod.mkCrcFun(
    0x104C11DB7, initCrc=0, rev=True, xorOut=0xFFFFFFFF
)
assert crc32(b"123456789") == 0xCBF43926

state = crcmod.Crc(0x11021, initCrc=0, rev=False, xorOut=0)
state.update(b"1234")
state.update(b"56789")
assert state.hexdigest() == "31C3"
```

## Coverage

The covered crcmod surface is:

- arbitrary 8, 16, 24, 32, and 64-bit generator polynomials
- forward and bit-reflected computation, custom initial values, and final XOR
- `mkCrcFun(poly, initCrc=-1, rev=True, xorOut=0)`, including continuation
  through its optional `crc` argument
- `Crc`, including `update`, `digest`, `hexdigest`, `new`, `copy`,
  `crcValue`, metadata, the public table, and `generateCode`
- `predefined.mkPredefinedCrcFun`, `predefined.PredefinedCrc`, and their
  aliases
- all 41 predefined algorithms shipped by crcmod 1.7
- contiguous Python buffer-protocol inputs, treated as raw bytes

The test suite checks numerical and behavioral parity against the real
`crcmod==1.7` package. It also checks every predefined algorithm against its
published `b"123456789"` check value.

This does not replace crcmod's private `_crcfunext` or `_crcfunpy` modules, and
generated C source is equivalent rather than byte-for-byte identical. The
distribution currently targets Linux shared libraries and does not include a
pure-Python fallback. Because the import name is `mojo_crcmod`, adopting it
requires changing the import line; the covered public names and signatures are
otherwise crcmod-shaped.

## Install

Install the pinned Mojo nightly, Python, and parity-test dependencies, then
build the shared library:

```bash
pixi install
pixi run build
pixi run test
```

Pixi adds `python/` to `PYTHONPATH`. The build writes
`dist/libmojo-crcmod.so`; Python raises a clear error asking for
`pixi run build` if it is absent.

## Predefined algorithms

```python
from mojo_crcmod import predefined

crc32c = predefined.mkCrcFun("crc-32c")
assert crc32c(b"123456789") == 0xE3069283

crc64 = predefined.Crc("crc-64")
crc64.update(memoryview(b"payload"))
print(crc64.hexdigest())
```

Names have crcmod's normalization rules, so spellings such as `"crc-32"`,
`"CRC 32"`, `"32"`, and `"Crc32"` select the same definition.

## Benchmarks

These are best-of-five measurements produced by `pixi run bench` in this
checkout on an Intel Xeon E5-2697 v4 at 2.30 GHz, Linux x86-64, Python
3.13.14. Each measurement includes the Python call and FFI boundary. A ratio
below `1.00x` means Mojo was slower.

| Algorithm | Input | Mojo | Upstream crcmod | Mojo / upstream |
|---|---:|---:|---:|---:|
| crc-8 | 64 B | 0.43 us | 0.43 us | 1.02x |
| crc-8 | 4 KiB | 1.30 GB/s | 0.38 GB/s | 3.41x |
| crc-8 | 1 MiB | 1.49 GB/s | 0.39 GB/s | 3.78x |
| crc-8 | 16 MiB | 1.92 GB/s | 0.41 GB/s | 4.65x |
| xmodem | 64 B | 0.41 us | 0.45 us | 1.11x |
| xmodem | 4 KiB | 1.39 GB/s | 0.30 GB/s | 4.61x |
| xmodem | 1 MiB | 1.68 GB/s | 0.32 GB/s | 5.22x |
| xmodem | 16 MiB | 1.94 GB/s | 0.31 GB/s | 6.24x |
| crc-32 | 64 B | 0.46 us | 0.57 us | 1.24x |
| crc-32 | 4 KiB | 1.31 GB/s | 0.34 GB/s | 3.92x |
| crc-32 | 1 MiB | 1.63 GB/s | 0.35 GB/s | 4.64x |
| crc-32 | 16 MiB | 1.86 GB/s | 0.33 GB/s | 5.66x |
| crc-64 | 64 B | 0.44 us | 0.45 us | 1.03x |
| crc-64 | 4 KiB | 1.33 GB/s | 0.33 GB/s | 4.00x |
| crc-64 | 1 MiB | 1.62 GB/s | 0.35 GB/s | 4.57x |
| crc-64 | 16 MiB | 1.80 GB/s | 0.34 GB/s | 5.35x |

The native CPython buffer bridge keeps 64-byte inputs at parity or ahead for
all four measured algorithms. At 4 KiB Mojo is 3.41–4.61 times faster, and at
1 MiB and above it is 3.78–6.24 times faster in this run.

No GPU path is provided. CRC has a state-dependent recurrence and low
arithmetic intensity: slicing-by-16 performs table lookups and XORs rather
than enough computation per byte to amortize device transfer and kernel
launch costs. A GPU implementation would be expected to lose, so the CPU
path remains the only path.

Run the same locked benchmark locally with:

```bash
pixi run bench
```

## How it works

Python validates the polynomial and builds crcmod's 256-entry public lookup
table once when a function or state object is created. The native buffer also
contains 16 slicing tables and a precomputed GF(2) advance operator. Mojo
loads input in unaligned SIMD groups and uses slicing-by-16 to replace the
byte-dependent chain with independent lookups, followed by a scalar tail.
One kernel supports all five CRC widths; narrower CRCs are masked to their
declared width.

Inputs below 8 MiB stay serial. Inputs of 8 MiB and larger are divided into
independent 4 MiB chunks and processed by up to four CPU workers, then
combined in order with the advance operator. The parallel scratch space is
owned by the CRC function and reused.

The native CPython bridge passes integer addresses and scalar parameters to a
direct-value `@export` C ABI function. Exact `bytes` inputs use their internal
storage directly; other inputs acquire a C-contiguous buffer view. Both routes
borrow the input without a copy, including contiguous NumPy arrays and
multidimensional buffers, and the GIL remains held while Mojo reads it. Python
owns the buffers and controls their lifetimes. A separate validated ABI entry
point remains available to C callers and rejects invalid pointer, length, and
width arguments before pointer construction.

For CRC objects, each `update` immediately advances the native recurrence; the
object does not retain input chunks. This keeps streaming memory use constant
and makes `copy` and `new` inexpensive.

## License

MIT
