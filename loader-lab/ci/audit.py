"""Audit a normal, unmodified ARM64 Kbuild artifact. Never edits the module."""
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
from elftools.elf.elffile import ELFFile
from elftools.elf.relocation import RelocationSection


def require(condition, message):
    if not condition:
        raise ValueError(message)


def inspect(path):
    data = path.read_bytes()
    with path.open('rb') as stream:
        elf = ELFFile(stream)
        require(elf.elfclass == 64 and elf.little_endian, 'expected ELF64 little endian')
        require(elf['e_machine'] == 'EM_AARCH64' and elf['e_type'] == 'ET_REL', 'wrong ELF target')
        meta = {}
        for item in elf.get_section_by_name('.modinfo').data().split(b'\0'):
            key, sep, value = item.partition(b'=')
            if sep:
                meta.setdefault(key.decode(), []).append(value.decode())
        require(meta.get('name') == ['kh_loader_smoke'], 'unexpected module name')
        require(meta.get('license') == ['GPL'], 'unexpected module license')
        section = elf.get_section_by_name('__versions')
        require(section is not None and section['sh_size'] > 0, 'empty or missing __versions')
        require(section['sh_size'] % 64 == 0, 'invalid basic modversion record size')
        crcs = {}
        for crc, name in struct.iter_unpack('<Q56s', section.data()):
            require(b'\0' in name, 'unterminated version name')
            name = name.split(b'\0', 1)[0].decode()
            require(name and name not in crcs, 'empty or duplicate version name')
            crcs[name] = f'0x{crc & 0xffffffff:08x}'
        require('module_layout' in crcs, 'missing module_layout version')
        symbols = elf.get_section_by_name('.symtab')
        imports = sorted(s.name for s in symbols.iter_symbols()
                         if s.name and s['st_shndx'] == 'SHN_UNDEF'
                         and s['st_info']['bind'] != 'STB_WEAK')
        missing = sorted(set(imports) - set(crcs))
        require(not missing, 'missing versions for imports: ' + ', '.join(missing))
        tm = elf.get_section_by_name('.gnu.linkonce.this_module')
        require(tm is not None, 'missing this_module')
        relocs = []
        for rs in elf.iter_sections():
            if not isinstance(rs, RelocationSection):
                continue
            if elf.get_section(rs['sh_info']).name != tm.name:
                continue
            syms = elf.get_section(rs['sh_link'])
            for r in rs.iter_relocations():
                require(r['r_offset'] + 8 <= tm['sh_size'], 'entry outside this_module')
                relocs.append({'offset': r['r_offset'], 'type': r['r_info_type'],
                               'symbol': syms.get_symbol(r['r_info_sym']).name})
        for name in ('init_module', 'cleanup_module'):
            require(sum(r['symbol'] in (name, name + '.cfi_jt') for r in relocs) == 1,
                    'missing or ambiguous entry: ' + name)
        return {'schema_version': 1, 'module': path.name,
                'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data),
                'modinfo': meta, 'imports': imports, 'crcs': crcs,
                'this_module_size': tm['sh_size'], 'this_module_relocations': relocs,
                'source_commit': os.environ.get('GITHUB_SHA'),
                'workflow_run': os.environ.get('GITHUB_RUN_ID'),
                'ddk_image': os.environ.get('DDK_IMAGE'),
                'build_audit': 'passed', 'device_load_test': 'not_run'}


if __name__ == '__main__':
    path = Path(sys.argv[1])
    report = inspect(path)
    (path.parent / 'audit.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    (path.parent / 'SHA256SUMS').write_text(report['sha256'] + '  ' + path.name + '\n', encoding='ascii')
    print(json.dumps(report, indent=2))
