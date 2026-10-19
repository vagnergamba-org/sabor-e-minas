from pathlib import Path
from urllib.parse import unquote
import re, zipfile

ROOT=Path(__file__).resolve().parents[1]
TEXT_EXTS={'.html','.css','.js','.xml','.txt','.json'}
IMAGE_EXTS={'.png','.jpg','.jpeg','.webp','.svg','.avif','.gif'}

def refs():
    found=set()
    attr=re.compile(r'''(?:src|href)=["']([^"'#?]+)''',re.I)
    css=re.compile(r'''url\(([^)]+)\)''',re.I)
    for p in ROOT.iterdir():
        if not (p.is_file() and p.suffix.lower() in TEXT_EXTS): continue
        t=p.read_text(encoding='utf-8',errors='ignore')
        vals=[m.group(1) for m in attr.finditer(t)]+[m.group(1) for m in css.finditer(t)]
        for raw in vals:
            raw=raw.strip().strip(chr(34)+chr(39))
            if re.match(r'^(?:https?:|mailto:|tel:|data:|javascript:)',raw,re.I): continue
            n=unquote(raw.split('#',1)[0].split('?',1)[0])
            if n.startswith('./'): n=n[2:]
            if n.startswith('/'): n=n[1:]
            if n: found.add(n)
    return found

def zip_clean(name):
    used=refs(); out=ROOT/name
    if out.exists(): out.unlink()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in ROOT.iterdir():
            if not p.is_file() or p.name==out.name: continue
            if p.suffix.lower() in {'.py','.md'}: continue
            if p.suffix.lower() in IMAGE_EXTS and p.name not in used and p.name!='logo-local.png': continue
            z.write(p,p.name)
    return out

def zip_full(name):
    out=ROOT/name
    if out.exists(): out.unlink()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in ROOT.iterdir():
            if not p.is_file() or p.name in {out.name,'Sabor-e-Minas-publicacao-final-2026-10-19.zip'}: continue
            if p.suffix.lower() in {'.py','.md'}: continue
            z.write(p,p.name)
    return out

clean=zip_clean('Sabor-e-Minas-publicacao-final-2026-10-19.zip')
full=zip_full('Sabor-e-Minas-backup-completo-2026-10-19.zip')
print(clean.name, clean.stat().st_size)
print(full.name, full.stat().st_size)
