from __future__ import annotations
from pathlib import Path
from PIL import Image, ImageOps
import re, sys, zipfile
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]

CONVERT = {
    "conjunto.jpg": "conjunto-web.webp",
    "cesta.png": "cesta-web.webp",
    "azeitona.png": "azeitona-web.webp",
    "marca_propria.png": "marca-propria-web.webp",
    "selo-qualidade.png": "selo-qualidade-web.webp",
    "ricota.png": "ricota-web.webp",
    "peito_peru.png": "peito-peru-web.webp",
    "tomate seco.png": "tomate-seco-web.webp",
    "doce de leite.png": "doce-de-leite-web.webp",
    "morango.png": "morango-web.webp",
    "sardinha.png": "sardinha-web.webp",
    "alho.png": "alho-web.webp",
    "goiabada.png": "goiabada-web.webp",
    "parmesao.png": "parmesao-web.webp",
    "nozes.png": "nozes-web.webp",
    "requeijao cremoso.png": "requeijao-cremoso-web.webp",
    "Broa_SaborMinas.png": "broa-saborminas-web.webp",
    "Chipa_2kg.png": "chipa-2kg-web.webp",
    "Multi_Graos_400.png": "multigraos-400-web.webp",
    "Tradicional_1kg.png": "tradicional-1kg-web.webp",
    "Tradicional_400.png": "tradicional-400-web.webp",
    "Coquetel2kg.png": "coquetel-2kg-web.webp",
    "Mini_Chipa_500.png": "mini-chipa-500-web.webp",
    "dadinho de tapioca.png": "dadinho-tapioca-web.webp",
    "Lanche_2kg.png": "lanche-2kg-web.webp",
    "Palito_Permium800g.png": "palito-premium-800g-web.webp",
    "Premium_400.png": "premium-400-web.webp",
    "Lanchinho1kg.png": "lanchinho-1kg-web.webp",
    "SuperLanche2kg.png": "superlanche-2kg-web.webp",
    "Tradicional2kg.png": "tradicional-2kg-web.webp",
    "Permium300g.png": "premium-300g-web.webp",
    "Palito_2kg[5267].jpg": "palito-2kg-web.webp",
}

TEXT_EXTS = {".html", ".css", ".js", ".xml", ".txt", ".json"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".svg", ".avif", ".gif"}

def convert_image(src: Path, dst: Path) -> tuple[int, int]:
    before = src.stat().st_size
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)
        if max(im.size) > 1800:
            ratio = 1800 / max(im.size)
            im = im.resize((round(im.width * ratio), round(im.height * ratio)), Image.Resampling.LANCZOS)
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGBA" if "transparency" in im.info else "RGB")
        im.save(dst, "WEBP", quality=88, method=6, exact=True)
    return before, dst.stat().st_size

def patch_references() -> int:
    changed = 0
    for p in ROOT.iterdir():
        if p.is_file() and p.suffix.lower() in TEXT_EXTS:
            text = p.read_text(encoding="utf-8")
            new = text
            for old, target in CONVERT.items():
                new = new.replace(old, target)
                new = new.replace(old.replace(" ", "%20"), target)
            if new != text:
                p.write_text(new, encoding="utf-8")
                changed += 1
    return changed

def collect_local_refs() -> tuple[set[str], list[tuple[str,str]]]:
    existing = {p.name for p in ROOT.iterdir() if p.is_file()}
    referenced: set[str] = set()
    missing: list[tuple[str,str]] = []
    attr = re.compile(r'''(?:src|href)=["']([^"'#?]+)''', re.I)
    cssurl = re.compile(r'''url\\(([^)]+)\\)''', re.I)
    for p in ROOT.iterdir():
        if not (p.is_file() and p.suffix.lower() in TEXT_EXTS):
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        raw_refs = [m.group(1) for m in attr.finditer(text)] + [m.group(1) for m in cssurl.finditer(text)]
        for raw in raw_refs:
            raw = raw.strip().strip(chr(34) + chr(39))
            if re.match(r'^(?:https?:|mailto:|tel:|data:|javascript:)', raw, re.I):
                continue
            name = unquote(raw.split("#",1)[0].split("?",1)[0])
            if name.startswith("./"):
                name = name[2:]
            if name.startswith("/"):
                name = name.lstrip("/")
            if not name or name.endswith("/"):
                continue
            referenced.add(name)
            if name not in existing:
                missing.append((p.name, name))
    return referenced, missing
def audit() -> None:
    _, missing = collect_local_refs()
    conflicts = []
    for p in ROOT.iterdir():
        if p.is_file() and p.suffix.lower() in {".html",".css",".js"}:
            t = p.read_text(encoding="utf-8", errors="ignore")
            if re.search(r'^(?:<<<<<<< |=======|>>>>>>> )', t, re.M):
                conflicts.append(p.name)
    if missing:
        for f, r in missing:
            print(f"ERRO referência ausente: {f} -> {r}")
        raise SystemExit(2)
    if conflicts:
        print("ERRO marcadores de merge:", ", ".join(conflicts))
        raise SystemExit(3)
    print("Auditoria: referências locais e conflitos OK")

def build_zip() -> Path:
    referenced, _ = collect_local_refs()
    keep_always = {
        "index.html","styles.css","mobile.css","site.js","mobile.js","contact.js",
        "robots.txt","sitemap.xml","vercel.json","logo-local.png"
    }
    out = ROOT / "sabor-e-minas-publicacao-2026-10-19.zip"
    if out.exists():
        out.unlink()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in ROOT.iterdir():
            if not p.is_file() or p.name == out.name:
                continue
            if p.name.startswith("."):
                continue
            if p.suffix.lower() in IMAGE_EXTS and p.name not in referenced and p.name not in keep_always:
                continue
            if p.suffix.lower() in {".py",".md"}:
                continue
            z.write(p, p.name)
    print("ZIP:", out.name, out.stat().st_size)
    return out

def main():
    audit_only = "--audit-only" in sys.argv
    if not audit_only:
        total_before = total_after = 0
        for old, new in CONVERT.items():
            src, dst = ROOT / old, ROOT / new
            if not src.exists():
                print("AVISO fonte não encontrada:", old)
                continue
            b, a = convert_image(src, dst)
            total_before += b; total_after += a
            print(f"{old}: {b/1024:.0f} KB -> {new}: {a/1024:.0f} KB")
        patch_references()
        if total_before:
            print(f"Imagens convertidas: {total_before/1024/1024:.1f} MB -> {total_after/1024/1024:.1f} MB")
    audit()
    if not audit_only:
        build_zip()

if __name__ == "__main__":
    main()
