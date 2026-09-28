#!/usr/bin/env bash
set -euo pipefail
cd /work
SRC=/work/source-kernel
BUILD=/work/source-build
mkdir -p "$BUILD" out
export ARCH=arm64 LLVM=1 LLVM_IAS=1
export KBUILD_BUILD_USER=loader-lab KBUILD_BUILD_HOST=github-actions
export KBUILD_BUILD_TIMESTAMP='Mon Jan 1 00:00:00 UTC 2024'
unset KDIR KBUILD_MODPOST_WARN KBUILD_EXTRA_SYMBOLS
clang --version > out/compiler.txt
sha256sum "$SRC/scripts/mod/modpost.c" "$SRC/scripts/genksyms/genksyms.c" > out/source-tools.sha256
case "${SOURCE_SERIES:-5.15.149}" in
  5.15.149) FRAGMENT=/work/loader-lab/ci/source-minimal.config ;;
  5.10.209) FRAGMENT=/work/loader-lab/ci/source-minimal-5.10.config ;;
  *) echo 'Unsupported pinned source series' >&2; exit 1 ;;
esac
cp "$FRAGMENT" out/requested.config

# Fresh source/config/output; do not reuse the DDK headers or Module.symvers.
make -C "$SRC" O="$BUILD" KCONFIG_ALLCONFIG="$FRAGMENT" allnoconfig \
  2>&1 | tee out/configure.log
cp "$BUILD/.config" out/kernel.config
for option in MODULES MODULE_UNLOAD MODVERSIONS SMP PREEMPT SYSFS PRINTK \
              LTO_CLANG_THIN CFI_CLANG SHADOW_CALL_STACK ARM64_BTI_KERNEL ARM64_PTR_AUTH; do
  grep -qx "CONFIG_${option}=y" "$BUILD/.config"
done
if [ "${SOURCE_SERIES:-5.15.149}" = 5.15.149 ]; then
  grep -qx 'CONFIG_ARM64_PTR_AUTH_KERNEL=y' "$BUILD/.config"
fi
grep -qx '# CONFIG_CFI_PERMISSIVE is not set' "$BUILD/.config"
grep -qx '# CONFIG_TRIM_UNUSED_KSYMS is not set' "$BUILD/.config"
make -s -C "$SRC" O="$BUILD" kernelrelease > out/kernel-release.txt

# A complete vmlinux link generates authoritative versions through standard
# genksyms/modpost. modules_prepare alone is not used as a substitute.
make -C "$SRC" O="$BUILD" -j2 V=0 vmlinux 2>&1 | tee out/kernel-build.log
# Linux 5.15 emits vmlinux.symvers first; the modules target aggregates it
# into Module.symvers and prepares the external-module linker script.
make -C "$SRC" O="$BUILD" -j2 V=0 modules 2>&1 | tee out/kernel-modules.log
test -s "$BUILD/Module.symvers"
cp "$BUILD/Module.symvers" out/kernel.Module.symvers
sha256sum "$BUILD/scripts/mod/modpost" > out/modpost-used.sha256
sha256sum "$BUILD/vmlinux" > out/vmlinux.sha256
cp "$BUILD/include/generated/utsrelease.h" out/
make -C "$SRC" O="$BUILD" M=/work/loader-lab/module -j2 V=1 modules \
  2>&1 | tee out/build.log
cp loader-lab/module/kh_loader_smoke.ko loader-lab/module/kh_loader_smoke.mod.c out/
llvm-readelf -h -SW -r -s out/kh_loader_smoke.ko > out/elf.txt
llvm-objdump -d out/kh_loader_smoke.ko > out/disassembly.txt
printf '%s\n' 'source_build=fresh Android source + independent compile-only config' \
  'device_load_test=not_run' > out/build-scope.txt
