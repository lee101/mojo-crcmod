#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "${repo_dir}/dist"
mojo build --emit shared-lib "${repo_dir}/src/crc.mojo" \
    -o "${repo_dir}/dist/libmojo-crcmod.so"

python_include="$(python -c 'import sysconfig; print(sysconfig.get_paths()["include"])')"
extension_suffix="$(python -c 'import sysconfig; print(sysconfig.get_config_var("EXT_SUFFIX"))')"
cc -O3 -fPIC -shared \
    -I"${python_include}" \
    "${repo_dir}/src/bridge.c" \
    -L"${repo_dir}/dist" \
    -Wl,-rpath,'$ORIGIN/../../dist' \
    -Wl,--no-as-needed -l:libmojo-crcmod.so \
    -o "${repo_dir}/python/mojo_crcmod/_bridge${extension_suffix}"
