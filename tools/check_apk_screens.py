from pathlib import Path
import argparse, json, struct, zipfile

SCREENS = {'Screen1', 'Play', 'EditorSettings', 'Recorder'}

def classes(data):
    def u32(offset): return struct.unpack_from('<I', data, offset)[0]
    def string(offset):
        while data[offset] & 128: offset += 1
        offset += 1
        return data[offset:data.index(b'\0', offset)].decode('utf-8', errors='replace')
    strings = [string(u32(u32(60) + 4*i)) for i in range(u32(56))]
    types = [strings[u32(u32(68) + 4*i)] for i in range(u32(64))]
    return [types[u32(u32(100) + 32*i)] for i in range(u32(96))]

def inspect(path):
    with zipfile.ZipFile(path) as z:
        defined = {c for n in z.namelist() if n.endswith('.dex') for c in classes(z.read(n))}
    found = sorted(c for c in defined if c.startswith('Lappinventor/ai_') and '$' not in c)
    packages = {c.rsplit('/', 1)[0] for c in found if c.endswith('/Screen1;')}
    missing = {p: sorted(s for s in SCREENS if p+'/'+s+';' not in defined) for p in packages}
    return {'apk': str(path), 'classes': found, 'missing': missing,
            'complete': bool(packages) and all(not v for v in missing.values())}

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('apk', type=Path)
    args = parser.parse_args()
    result = inspect(args.apk)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result['complete'] else 1)
