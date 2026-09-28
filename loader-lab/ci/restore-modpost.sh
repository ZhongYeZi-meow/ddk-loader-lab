#!/usr/bin/env bash
# Re-enable normal build-time export/version checking in an ephemeral DDK image.
# stdout contains only the rebuilt host-tool executable; diagnostics go to stderr.
set -euo pipefail
: "${KDIR:?}"
export DDK_MODPOST_SOURCE
src="$(readlink -f "$KDIR/source")"
DDK_MODPOST_SOURCE="$src/scripts/mod/modpost.c"
original_sha="$(sha256sum "$KDIR/scripts/mod/modpost" | cut -d ' ' -f1)"
printf 'original modpost sha256: %s\n' "$original_sha" >&2
# Retain the actual prepared-tree rules in the build evidence.
for rules in "$KDIR/Makefile" "$src/scripts/mod/Makefile"; do
    printf '\n=== %s ===\n' "$rules" >&2
    sed -n '1,180p' "$rules" >&2
done
grep -n -A 6 -B 3 -E '^scripts:|^scripts/mod:|^scripts_basic:' "$src/Makefile" >&2 || true
python3 - <<'PY' >&2
import hashlib
import os
from pathlib import Path
import re

path = Path(os.environ['DDK_MODPOST_SOURCE'])
source = path.read_text()
print('modpost source:', path)
print('before sha256:', hashlib.sha256(source.encode()).hexdigest())
for statement in ('check_exports(mod);', 's->module = exp->module;'):
    pattern = r'^\s*//\s*(' + re.escape(statement) + r')\s*$'
    source, count = re.subn(pattern, r'\t\1', source, flags=re.MULTILINE)
    if count != 1:
        raise SystemExit(f'Expected one DDK change for {statement!r}, found {count}')
    print('restored standard statement:', statement)
path.write_text(source)
print('after sha256:', hashlib.sha256(source.encode()).hexdigest())
PY
# The prepared DDK is for external modules; do not rely on its top-level
# "scripts" target rebuilding host tools. Build the three modpost translation
# units explicitly, using the image's generated target-ELF/device-table headers.
test -s "$KDIR/scripts/mod/elfconfig.h"
test -s "$KDIR/scripts/mod/devicetable-offsets.h"
sha256sum "$KDIR/scripts/mod/elfconfig.h" \
    "$KDIR/scripts/mod/devicetable-offsets.h" >&2
build_dir="$(mktemp -d /tmp/loader-modpost.XXXXXX)"
clang --version >&2
(
    set -x
    clang -O2 -Wall -Wmissing-prototypes -Wstrict-prototypes -std=gnu89 \
        -I"$KDIR/scripts/mod" -I"$src/scripts/mod" -I"$src/tools/include" \
        "$src/scripts/mod/modpost.c" "$src/scripts/mod/file2alias.c" \
        "$src/scripts/mod/sumversion.c" -o "$build_dir/modpost"
) >&2
test -x "$build_dir/modpost"
rebuilt_sha="$(sha256sum "$build_dir/modpost" | cut -d ' ' -f1)"
printf 'rebuilt modpost sha256: %s\n' "$rebuilt_sha" >&2
test "$original_sha" != "$rebuilt_sha"
cat "$build_dir/modpost"
