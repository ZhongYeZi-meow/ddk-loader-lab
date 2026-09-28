"""Extract compiler DWARF member locations for comparison; no module edits."""
import json
from pathlib import Path
import sys
from elftools.elf.elffile import ELFFile

path=Path(sys.argv[1]); rows={}
with path.open('rb') as stream:
    elf=ELFFile(stream)
    if not elf.has_dwarf_info(): raise ValueError('source build must retain DWARF')
    for cu in elf.get_dwarf_info().iter_CUs():
        for die in cu.iter_DIEs():
            if die.tag not in ('DW_TAG_structure_type','DW_TAG_union_type'): continue
            a=die.attributes.get('DW_AT_name'); size=die.attributes.get('DW_AT_byte_size')
            name=a.value.decode() if a and isinstance(a.value,bytes) else ''
            if name not in ('module','kernel_param','kernel_param_ops') or not size: continue
            members=[]
            for m in die.iter_children():
                if m.tag!='DW_TAG_member': continue
                n=m.attributes.get('DW_AT_name'); off=m.attributes.get('DW_AT_data_member_location')
                if off and not isinstance(off.value,int): raise ValueError('nonconstant member offset')
                members.append({'name':n.value.decode() if n else '<anonymous>',
                                'offset':off.value if off else 0,
                                'type_die':m.get_DIE_from_attribute('DW_AT_type').offset})
            row={'size':size.value,'members':members}
            # Type DIE identities are CU-local evidence, not stable ABI ids.
            if name not in rows: rows[name]=row
    if not all(n in rows for n in ('module','kernel_param','kernel_param_ops')):
        raise ValueError('missing required compiler type evidence')
(path.parent/'source-layouts.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps(rows,indent=2))
