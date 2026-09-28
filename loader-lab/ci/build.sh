#!/usr/bin/env bash
set -euo pipefail
cd /work
: "${KDIR:?DDK image must provide KDIR}"
test -s "$KDIR/Module.symvers"
test -f "$KDIR/.config"
mkdir -p out
cp "$KDIR/.config" out/kernel.config
cp "$KDIR/Module.symvers" out/kernel.Module.symvers
sha256sum "$KDIR/Module.symvers" > out/kernel-symvers.sha256
cmp out/modpost "$KDIR/scripts/mod/modpost"
sha256sum "$KDIR/scripts/mod/modpost" > out/modpost-used.sha256
clang --version > out/compiler.txt
printf 'KDIR=%s\nARCH=%s\nLLVM=%s\nLLVM_IAS=%s\n' \
    "$KDIR" "${ARCH:-}" "${LLVM:-}" "${LLVM_IAS:-}" > out/build-environment.txt
make -C loader-lab/module -j2 V=1 2>&1 | tee out/build.log
cmp out/modpost "$KDIR/scripts/mod/modpost"
cp loader-lab/module/kh_loader_smoke.ko out/
cp loader-lab/module/kh_loader_smoke.mod.c out/
llvm-readelf -h -SW -r -s out/kh_loader_smoke.ko > out/elf.txt
llvm-objdump -d out/kh_loader_smoke.ko > out/disassembly.txt
