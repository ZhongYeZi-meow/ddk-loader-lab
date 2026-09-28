"""Generate an explicit compile-only profile; never infer device compatibility."""
import json
from pathlib import Path
import re
import sys

root = Path('/work')
row = next(x for x in json.loads((root / 'loader-lab/ci/matrix-sources.json').read_text())
           if x['id'] == sys.argv[1])
src = root / 'source-kernel'
makefile = (src / 'Makefile').read_text()
version = '.'.join(re.search(r'^' + key + r'\s*=\s*(\d+)', makefile, re.M)[1]
                   for key in ('VERSION', 'PATCHLEVEL', 'SUBLEVEL'))
if version != row['version']:
    raise ValueError(f'actual source version {version} != pinned {row["version"]}')
required = ['EXPERT', 'SMP', 'PREEMPT', 'MODULES', 'MODULE_UNLOAD', 'MODVERSIONS',
            'SYSFS', 'PROC_FS', 'PRINTK', 'BUG', 'DEBUG_KERNEL', 'DEBUG_INFO', 'KALLSYMS']
if row['compiler'] == 'clang14':
    required += ['LTO_CLANG', 'THINLTO'] if row['series'] == '5.4' else ['LTO_CLANG_THIN']
    required += ['CFI_CLANG', 'SHADOW_CALL_STACK']
    if row['series'] in ('5.10', '5.15'):
        required += ['ARM64_PTR_AUTH', 'ARM64_BTI', 'ARM64_BTI_KERNEL']
    if row['series'] == '5.15':
        required += ['ARM64_PTR_AUTH_KERNEL']
elif row['compiler'] == 'clang18':
    required += ['LTO_CLANG_THIN', 'SHADOW_CALL_STACK', 'ARM64_PTR_AUTH',
                 'ARM64_PTR_AUTH_KERNEL', 'ARM64_BTI', 'ARM64_BTI_KERNEL',
                 'CFI' if row['series'] == '6.18' else 'CFI_CLANG']
elif row['compiler'] != 'gcc49':
    raise ValueError('unknown compiler profile')
disabled = ['LOCALVERSION_AUTO', 'TRIM_UNUSED_KSYMS', 'CFI_PERMISSIVE',
            'CFI_CLANG_PERMISSIVE', 'WERROR', 'KSU', 'SUSFS', 'KPM', 'RUST']
if row['compiler'] == 'gcc49':
    disabled += ['CFI', 'CFI_CLANG', 'LTO_CLANG', 'SHADOW_CALL_STACK']
fragment = '\n'.join('CONFIG_' + x + '=y' for x in required)
fragment += '\nCONFIG_DEBUG_INFO_DWARF4=y\nCONFIG_LOCALVERSION="-kh-matrix"\n'
fragment += '\n'.join('# CONFIG_' + x + ' is not set' for x in disabled) + '\n'
(root / 'out/requested.config').write_text(fragment)
profile = dict(row, required=required, disabled=disabled,
               config_scope='independent compile-only; not vendor stock',
               expected_cfi='none' if row['compiler'] == 'gcc49' else
                            'legacy-clang-cfi' if row['compiler'] == 'clang14' else 'kcfi',
               device_load_test='not_run')
(root / 'out/matrix-profile.json').write_text(json.dumps(profile, indent=2) + '\n')
