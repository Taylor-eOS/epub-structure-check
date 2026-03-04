import sys
import zipfile
from pathlib import Path, PurePosixPath
from lxml import etree
from urllib.parse import unquote
from collections import Counter
import last_folder_helper
from complex_scan import find_opf_path

def parse_opf(z, opf_path):
    with z.open(opf_path) as f:
        parser = etree.XMLParser(recover=True)
        tree = etree.parse(f, parser)
        root = tree.getroot()
        opf_ns = None
        for ns in (root.nsmap or {}).values():
            if ns and 'opf' in ns:
                opf_ns = ns
                break
        if opf_ns is None:
            opf_ns = 'http://www.idpf.org/2007/opf'
        ns = {'opf': opf_ns}
        manifest = {}
        manifest_el = root.find('opf:manifest', ns)
        if manifest_el is not None:
            for item in manifest_el.findall('opf:item', ns):
                iid = item.get('id')
                href = item.get('href')
                media = item.get('media-type')
                if iid and href:
                    manifest[iid] = {'href': href, 'media-type': media}
        spine = []
        spine_el = root.find('opf:spine', ns)
        if spine_el is not None:
            for itemref in spine_el.findall('opf:itemref', ns):
                idref = itemref.get('idref')
                if idref:
                    spine.append(idref)
        opf_dir = PurePosixPath(opf_path).parent.as_posix()
        return manifest, spine, opf_dir

def resolve_href(opf_dir, href):
    decoded = unquote(href)
    if not opf_dir:
        return PurePosixPath(decoded).as_posix()
    return (PurePosixPath(opf_dir) / PurePosixPath(decoded)).as_posix()

def get_spine_xhtml_paths(z, manifest, spine, opf_dir):
    paths = []
    for idref in spine:
        item = manifest.get(idref)
        if not item:
            continue
        mt = item.get('media-type') or ''
        if mt not in ('application/xhtml+xml', 'text/html'):
            continue
        href = resolve_href(opf_dir, item['href'])
        if href in z.namelist():
            paths.append(href)
    return paths

def collect_img_classes(z, xhtml_paths):
    xhtml_ns = 'http://www.w3.org/1999/xhtml'
    counts = Counter()
    for zip_path in xhtml_paths:
        try:
            with z.open(zip_path) as f:
                parser = etree.XMLParser(recover=True)
                tree = etree.parse(f, parser)
            for tag in (f'{{{xhtml_ns}}}img', 'img'):
                for el in tree.findall(f'.//{tag}'):
                    cls = el.get('class', '').strip()
                    if cls:
                        for c in cls.split():
                            counts[c] += 1
        except Exception:
            continue
    return counts

def analyze_epub(epub_path):
    try:
        with zipfile.ZipFile(epub_path, 'r') as z:
            opf_path = find_opf_path(z)
            if opf_path is None:
                return None, 'no_opf'
            manifest, spine, opf_dir = parse_opf(z, opf_path)
            xhtml_paths = get_spine_xhtml_paths(z, manifest, spine, opf_dir)
            if not xhtml_paths:
                return None, 'no_xhtml'
            counts = collect_img_classes(z, xhtml_paths)
            return counts, None
    except Exception as e:
        return None, f'error: {e}'

def main(folder):
    p = Path(folder).expanduser().resolve()
    if not p.is_dir():
        print(f"Folder not found: {p}")
        sys.exit(1)
    epub_paths = sorted(p.rglob('*.epub'))
    if not epub_paths:
        print("No EPUB files found")
        return
    for epub_path in epub_paths:
        counts, err = analyze_epub(str(epub_path))
        name = epub_path.stem
        if err:
            print(f"{name}: {err}")
            continue
        if not counts:
            print(f"{name}: no image classes found")
            continue
        classes_str = ', '.join(f'{cls}({n})' for cls, n in counts.most_common())
        print(f"{name}: {classes_str}")

if __name__ == "__main__":
    default = last_folder_helper.get_last_folder()
    user_input = input(f'Input folder ({default}): ').strip()
    folder = user_input or default
    if not folder:
        folder = '.'
    last_folder_helper.save_last_folder(folder)
    main(folder)

