#!/usr/bin/env bash
set -euo pipefail
cd /work
mkdir -p out source-build
SRC=/work/source-kernel
BUILD=/work/source-build
export ARCH=arm64
export KBUILD_BUILD_USER=loader-lab KBUILD_BUILD_HOST=github-actions
export KBUILD_BUILD_TIMESTAMP='Mon Jan 1 00:00:00 UTC 2024'
unset KDIR KBUILD_MODPOST_WARN KBUILD_EXTRA_SYMBOLS
python3 loader-lab/ci/configure-matrix.py "$MATRIX_ID"
args=(-C "$SRC" O="$BUILD")
if [[ "$COMPILER" = gcc49 ]]; then
  export PATH="/work/gcc49/bin:$PATH"
  args+=(CROSS_COMPILE=aarch64-linux-android- HOSTCC=gcc 'HOSTCFLAGS=-O2 -fcommon')
  aarch64-linux-android-gcc --version > out/compiler.txt
  aarch64-linux-android-ld --version > out/linker.txt
  sha256sum /work/gcc49/bin/aarch64-linux-android-gcc > out/compiler.sha256
else
  args+=(LLVM=1 LLVM_IAS=1)
  clang --version > out/compiler.txt
  ld.lld --version > out/linker.txt
  sha256sum "$(command -v clang)" > out/compiler.sha256
fi
if [[ -f /build-packages.txt ]]; then cp /build-packages.txt out/; fi
sha256sum "$SRC/scripts/mod/modpost.c" "$SRC/scripts/genksyms/genksyms.c" > out/source-tools.sha256
make "${args[@]}" KCONFIG_ALLCONFIG=/work/out/requested.config allnoconfig 2>&1 | tee out/configure.log
cp "$BUILD/.config" out/kernel.config
python3 loader-lab/ci/check-matrix-config.py
make -s "${args[@]}" kernelrelease > out/kernel-release.txt
make "${args[@]}" -j2 V=0 vmlinux 2>&1 | tee out/kernel-build.log
make "${args[@]}" -j2 V=0 modules 2>&1 | tee out/kernel-modules.log
test -s "$BUILD/Module.symvers"
cp "$BUILD/Module.symvers" out/kernel.Module.symvers
sha256sum "$BUILD/scripts/mod/modpost" > out/modpost-used.sha256
sha256sum "$BUILD/vmlinux" > out/vmlinux.sha256
make "${args[@]}" M=/work/loader-lab/module -j2 V=1 modules 2>&1 | tee out/build.log
cp loader-lab/module/kh_loader_smoke.ko loader-lab/module/kh_loader_smoke.mod.c out/
llvm-readelf -h -SW -r -s out/kh_loader_smoke.ko > out/elf.txt
llvm-objdump -d out/kh_loader_smoke.ko > out/disassembly.txt
printf '%s\n' 'source_build=fresh pinned source; independent compile-only config' \
  'device_load_test=not_run' > out/build-scope.txt
