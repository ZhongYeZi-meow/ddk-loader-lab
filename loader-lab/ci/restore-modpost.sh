#!/usr/bin/env bash
# Re-enable normal build-time export/version checking in an ephemeral DDK image.
# stdout contains only the rebuilt host-tool executable; diagnostics go to stderr.
set -euo pipefail
: "${KDIR:?}"
export DDK_MODPOST_SOURCE
DDK_MODPOST_SOURCE="$(readlink -f "$KDIR/source")/scripts/mod/modpost.c"
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
make -C "$KDIR" -j2 scripts >&2
test -x "$KDIR/scripts/mod/modpost"
cat "$KDIR/scripts/mod/modpost"
