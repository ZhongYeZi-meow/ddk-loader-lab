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


def version_records(basic=None, ext_crcs=None, ext_names=None):
    crcs = {}
    formats = []
    if basic is not None:
        require(basic and len(basic) % 64 == 0, 'invalid basic modversion size')
        formats.append('basic')
        for crc, name in struct.iter_unpack('<Q56s', basic):
            require(b'\0' in name, 'unterminated version name')
            name = name.split(b'\0', 1)[0].decode()
            require(name and name not in crcs and crc <= 0xffffffff,
                    'empty, duplicate, or invalid basic version')
            crcs[name] = f'0x{crc:08x}'
    if ext_crcs is not None or ext_names is not None:
        require(ext_crcs is not None and ext_names is not None,
                'incomplete extended version sections')
        require(ext_crcs and len(ext_crcs) % 4 == 0, 'invalid extended CRC size')
        formats.append('extended')
        pos = 0
        seen = set()
        for (crc,) in struct.iter_unpack('<I', ext_crcs):
            end = ext_names.find(b'\0', pos)
            require(end > pos, 'missing or empty extended version name')
            name = ext_names[pos:end].decode()
            pos = end + 1
            require(name not in seen, 'duplicate extended version')
            seen.add(name)
            value = f'0x{crc:08x}'
            require(name not in crcs or crcs[name] == value, 'basic/extended CRC conflict')
            crcs[name] = value
        # Kbuild emits a C string literal: a final implicit NUL may follow.
        require(ext_names[pos:] in (b'', b'\0'), 'trailing extended names')
    require(crcs, 'empty or missing symbol versions')
    return crcs, formats


def inspect(path, symvers_path=None):
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
        module_name = meta.get('name')
        name_source = 'modinfo'
        if module_name is None:
            # Older standard modpost initializes only __this_module.name.
            # Use compiler DWARF to locate that member, not an assumed offset.
            tm_name = elf.get_section_by_name('.gnu.linkonce.this_module')
            require(tm_name is not None and elf.has_dwarf_info(), 'missing legacy name evidence')
            offsets = set()
            for cu in elf.get_dwarf_info().iter_CUs():
                for die in cu.iter_DIEs():
                    attrs = die.attributes
                    if die.tag != 'DW_TAG_structure_type' or attrs.get('DW_AT_name') is None or attrs['DW_AT_name'].value != b'module':
                        continue
                    if attrs.get('DW_AT_byte_size') is None or attrs['DW_AT_byte_size'].value != tm_name['sh_size']:
                        continue
                    for member in die.iter_children():
                        name = member.attributes.get('DW_AT_name')
                        loc = member.attributes.get('DW_AT_data_member_location')
                        if member.tag == 'DW_TAG_member' and name and name.value == b'name' and loc and isinstance(loc.value, int):
                            offsets.add(loc.value)
            require(len(offsets) == 1, 'ambiguous legacy module name location')
            off = offsets.pop()
            require(off >= 0 and off + 56 <= tm_name['sh_size'], 'legacy name outside module')
            raw_name = tm_name.data()[off:off+56]
            require(b'\0' in raw_name, 'unterminated legacy name')
            module_name = [raw_name.split(b'\0', 1)[0].decode()]
            name_source = 'this_module + compiler DWARF'
        require(module_name == ['kh_loader_smoke'], 'unexpected module name')
        require(meta.get('license') == ['GPL'], 'unexpected module license')
        version_sections = [elf.get_section_by_name(name) for name in
                            ('__versions', '__version_ext_crcs', '__version_ext_names')]
        crcs, formats = version_records(*(s.data() if s is not None else None
                                         for s in version_sections))
        require('module_layout' in crcs, 'missing module_layout version')
        symbols = elf.get_section_by_name('.symtab')
        imports = sorted(s.name for s in symbols.iter_symbols()
                         if s.name and s['st_shndx'] == 'SHN_UNDEF'
                         and s['st_info']['bind'] != 'STB_WEAK')
        missing = sorted(set(imports) - set(crcs))
        require(not missing, 'missing versions for imports: ' + ', '.join(missing))
        if symvers_path is not None:
            expected = {}
            for line in symvers_path.read_text().splitlines():
                fields = line.split()
                require(len(fields) >= 4, 'invalid Module.symvers record')
                value = f'0x{int(fields[0], 16):08x}'
                require(fields[1] not in expected or expected[fields[1]] == value,
                        'conflicting Module.symvers CRC: ' + fields[1])
                expected[fields[1]] = value
            for name, value in crcs.items():
                require(expected.get(name) == value, 'DDK CRC mismatch: ' + name)
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
                'module_name': module_name[0], 'module_name_source': name_source,
                'version_formats': formats,
                'sections': [{'name': s.name, 'size': s['sh_size'], 'type': s['sh_type'],
                              'flags': s['sh_flags'], 'alignment': s['sh_addralign']}
                             for s in elf.iter_sections()],
                'instrumentation_symbols': sorted(s.name for s in symbols.iter_symbols()
                    if any(x in s.name for x in ('__cfi', '__kcfi', '.cfi_jt', '__ubsan'))),
                'this_module_size': tm['sh_size'], 'this_module_relocations': relocs,
                'source_commit': os.environ.get('GITHUB_SHA'),
                'workflow_run': os.environ.get('GITHUB_RUN_ID'),
                'ddk_image': os.environ.get('DDK_IMAGE'),
                'ddk_crc_comparison': 'passed' if symvers_path is not None else 'not_run',
                'build_audit': 'passed', 'device_load_test': 'not_run'}


if __name__ == '__main__':
    path = Path(sys.argv[1])
    report = inspect(path, Path(sys.argv[2]) if len(sys.argv) > 2 else None)
    (path.parent / 'audit.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    (path.parent / 'SHA256SUMS').write_text(report['sha256'] + '  ' + path.name + '\n', encoding='ascii')
    print(json.dumps(report, indent=2))
