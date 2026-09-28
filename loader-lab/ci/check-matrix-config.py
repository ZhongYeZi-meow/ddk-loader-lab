"""Check actual Kconfig result; a lost requested feature fails the build."""
import json
from pathlib import Path

root = Path('/work')
profile = json.loads((root / 'out/matrix-profile.json').read_text())
lines = set((root / 'out/kernel.config').read_text().splitlines())
missing = [x for x in profile['required'] if 'CONFIG_' + x + '=y' not in lines]
missing += [key + '=' + value for key, value in profile.get('required_values', {}).items()
            if 'CONFIG_' + key + '=' + value not in lines]
unexpected = [x for x in profile['disabled'] if 'CONFIG_' + x + '=y' in lines
              or 'CONFIG_' + x + '=m' in lines]
if missing or unexpected:
    raise ValueError(f'missing requested={missing}; unexpected enabled={unexpected}')
profile['config_check'] = 'passed'
(root / 'out/matrix-profile.json').write_text(json.dumps(profile, indent=2) + '\n')
