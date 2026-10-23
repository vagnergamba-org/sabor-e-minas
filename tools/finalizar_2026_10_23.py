from pathlib import Path
from urllib.parse import unquote
from PIL import Image, ImageOps
import re, zipfile

ROOT=Path(__file__).resolve().parents[1]
TEXT_EXTS={'.html','.css','.js','.xml','.txt','.json'}
IMAGE_EXTS={'.png','.jpg','.jpeg','.webp','.svg','.avif','.gif'}
SKIP_CONVERT={'logo-local.png'}

def collect_refs():
    existing={p.name for p in ROOT.iterdir() if p.is_file()}
    refs=set(); missing=[]
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
            if not n or n.endswith('/'): continue
            refs.add(n)
            if n not in existing: missing.append((p.name,n))
    return refs,missing

def audit():
    refs,missing=collect_refs()
    conflicts=[]
    for p in ROOT.iterdir():
        if p.is_file() and p.suffix.lower() in {'.html','.css','.js'}:
            t=p.read_text(encoding='utf-8',errors='ignore')
            if re.search(r'^(?:<<<<<<< |=======|>>>>>>> )',t,re.M): conflicts.append(p.name)
    if missing:
        for f,n in missing: print('ERRO referencia ausente:',f,'->',n)
        raise SystemExit(2)
    if conflicts:
        print('ERRO conflito merge:',','.join(conflicts)); raise SystemExit(3)
    htmls=[p for p in ROOT.iterdir() if p.is_file() and p.suffix.lower()=='.html']
    print('Auditoria OK - paginas HTML:',len(htmls),'refs locais:',len(refs))
    return refs

def optimize_used(refs):
    changed={}
    for name in sorted(refs):
        p=ROOT/name
        if not p.exists() or p.name in SKIP_CONVERT: continue
        if p.suffix.lower() not in {'.png','.jpg','.jpeg'}: continue
        if p.name.lower().startswith('tabela') or 'tabela ' in p.name.lower(): continue
        if p.stat().st_size < 450_000: continue
        target=p.with_name(p.stem+'-web.webp')
        if target.exists():
            changed[name]=target.name; continue
        try:
            with Image.open(p) as im:
                im=ImageOps.exif_transpose(im)
                if max(im.size)>1800:
                    r=1800/max(im.size)
                    im=im.resize((round(im.width*r),round(im.height*r)),Image.Resampling.LANCZOS)
                if im.mode not in ('RGB','RGBA'): im=im.convert('RGBA' if 'transparency' in im.info else 'RGB')
                im.save(target,'WEBP',quality=88,method=6,exact=True)
            changed[name]=target.name
            print('OTIMIZADA',name,p.stat().st_size,'->',target.name,target.stat().st_size)
        except Exception as e:
            print('AVISO sem conversao',name,e)
    if changed:
        for p in ROOT.iterdir():
            if not (p.is_file() and p.suffix.lower() in TEXT_EXTS): continue
            t=p.read_text(encoding='utf-8',errors='ignore'); new=t
            for old,newname in changed.items():
                new=new.replace(old,newname).replace(old.replace(' ','%20'),newname)
            if new!=t: p.write_text(new,encoding='utf-8')
    return changed

def make_zip(name,full=False):
    refs,_=collect_refs()
    out=ROOT/name
    if out.exists(): out.unlink()
    always={'index.html','styles.css','mobile.css','site.js','mobile.js','contact.js','robots.txt','sitemap.xml','vercel.json','logo-local.png'}
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in ROOT.iterdir():
            if not p.is_file() or p.name==out.name: continue
            if p.suffix.lower() in {'.py','.md'}: continue
            if not full and p.suffix.lower() in IMAGE_EXTS and p.name not in refs and p.name not in always: continue
            z.write(p,p.name)
    print('ZIP',name,out.stat().st_size)

refs=audit()
optimize_used(refs)
refs=audit()
make_zip('Sabor-e-Minas-publicacao-final-2026-10-23.zip',False)
make_zip('Sabor-e-Minas-backup-completo-2026-10-23.zip',True)
