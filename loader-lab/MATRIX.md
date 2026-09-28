# Pinned ordinary KO compilation matrix

Use **Build loader smoke module**, mode `matrix-all`, `matrix-common`, or
`matrix-vendor` (or `matrix-gcc` to retry just the old compiler family and
`matrix-modern` for 6.12/6.18).
Optional comma-separated exact `source_id` values select manifest entries for
an independent diagnostic run. Original DDK and 5.10/5.15 modes remain available.

`ci/matrix-sources.json` fixes public repository commits and versions read from
their Makefiles: ten Android common series (4.9, 4.14, 4.19, 5.4, 5.10, 5.15,
6.1, 6.6, 6.12, 6.18) and five Xiaomi, OnePlus, OPPO, RedMagic and community
source representatives. Branch names are provenance, not floating build inputs.

These are **independent minimal compile-only configurations**, not vendor stock
kernel reproductions. The ordinary smoke-module business source is unchanged.
Every row builds vmlinux and modules using that source's standard genksyms and
modpost before compiling the external module. Neither imported symbol tables
nor fabricated CRCs substitute for a complete source build.

## Toolchain families

* 4.x: AOSP GCC 4.9 pinned to commit
  `84fb09fafc92a3d9b4d160f049d46c3c784cc941` (android10-release), with an explicit **no-CFI** profile.
  This is a separate compiler ABI class, not evidence of compatibility with
  a strict CFI target. `HOSTCFLAGS=-O2 -fcommon` handles old host build tools.
  The newer android12L branch retains binutils but no GCC executable and is
  therefore not used as a C compiler.
  Its retained compiler wrapper uses `/usr/bin/python`; the build environment
  supplies Python 3 for that Python-3-compatible wrapper.
  Later stable 4.9/4.14/4.19 and the community 4.19.325 tree require GCC >=5.1;
  those rows instead select the recorded GCC 12 cross package, with no-CFI
  unchanged. Old vendor kernel warning wrappers retain their checks and run
  under Python 2.7 from a separate digest-pinned image stage. This interpreter
  exists only in the runner build container.
  Vendor kernel warning wrappers call the actual GCC 4.9 executable via REAL_CC,
  avoiding a prebuilt deprecation banner contaminating old cc-option probes.
  A local compiler launcher also handles probes which call CROSS_COMPILE gcc
  directly rather than REAL_CC. It executes the unchanged `gcc-4.9.x` ELF binary;
  `gcc-4.9` is only a symlink back to the banner wrapper in this prebuilt.
  The community SM8250 tree explicitly needs COMPAT for compat_uptr_t.
* 5.x: the existing digest-pinned public DDK Clang 14 image; fresh source only,
  with legacy Clang CFI and ThinLTO enabled. 5.4 uses `LTO_CLANG`/`THINLTO`;
  5.10/5.15 use `LTO_CLANG_THIN`.
* 6.x: Clang/LLVM/LLD 18 packages in an amd64 Ubuntu image with a pinned base
  digest; actual package versions and compiler hashes are artifacts. Package
  repositories remain mutable, so this is not a byte-reproducible package lock.
  KCFI and ThinLTO are enabled. 6.18 uses `CONFIG_CFI`, replacing the older
  `CONFIG_CFI_CLANG` selection.
  6.12/6.18 explicitly request GENKSYMS and both basic/extended version records;
  MODVERSIONS alone under allnoconfig does not select those record formats.
  The selected 6.12 Android tree additionally needs BLOCK enabled for the
  rq_list definition included by init/main.c.

Configuration assertions fail if requested features disappear. Source compilation
runs without network, capabilities, or persisted checkout credentials. Images
are local to the ephemeral runner and never published. At most four matrix
jobs run simultaneously, failures do not cancel other rows, and each uploads
its available logs independently.

## Evidence

Artifacts contain source identity, requested and resolved configs, compiler and
linker versions, full build logs, freshly generated Module.symvers, module SHA256,
ELF/relocation/disassembly data, basic/extended symbol-version audit, and DWARF
module/parameter layouts. `device_load_test=not_run` is deliberate: this repository
does compilation and artifact inspection only.
Old 4.9 modpost omits the modinfo name key; the auditor verifies the name from
this_module using its DWARF member location instead. No metadata is fabricated.
The 6.18 source pin currently produces a **6.18.0-rc6** release string, not a
final 6.18 release; all artifacts retain the complete actual release.

Build organization was studied read-only from JackA1ltman's
`NonGKI_Kernel_Build_2nd` (`19c0215d4bc0b23392ab11ea1645547bbf93fbf4`),
`op9pro-kernel-build` (`1466eca16b3278832bbf232a35c5eb19a7202b42`) and
`ColorOS_NonGKI_Kernel_Build` (`ff93c03a88c63cdea86734d80a99dc3179b589f6`).
Only the separation of source/ref, configuration, toolchain, build and evidence
is used. Their additional root, hiding, patching and flash packaging steps are
not incorporated. RedMagic uses the expanded NX659J_Q_kernel source; NX729J's
split archives are not a built row.
