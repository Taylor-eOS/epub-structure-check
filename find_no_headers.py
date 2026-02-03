import os
import sys
from zipfile import ZipFile
from lxml import etree
from pathlib import Path

def count_headings_in_epub(epub_path):
    try:
        with ZipFile(epub_path, 'r') as z:
            namelist = z.namelist()
            opf_path = None
            for name in namelist:
                if name.lower().endswith('.opf'):
                    opf_path = name
                    break
            if not opf_path:
                return -1
            with z.open(opf_path) as f:
                tree = etree.parse(f)
                root = tree.getroot()
                ns = {'opf': 'http://www.idpf.org/2007/opf'}
                spine = root.find('opf:spine', ns)
                if spine is None:
                    return -1
                itemrefs = spine.findall('opf:itemref', ns)
                if not itemrefs:
                    return -1
                manifest = root.find('opf:manifest', ns)
                if manifest is None:
                    return -1
                id_to_href = {}
                for item in manifest.findall('opf:item', ns):
                    item_id = item.get('id')
                    href = item.get('href')
                    if item_id and href:
                        id_to_href[item_id] = href
                heading_count = 0
                for itemref in itemrefs:
                    item_id = itemref.get('idref')
                    if item_id not in id_to_href:
                        continue
                    content_path = id_to_href[item_id]
                    if not content_path.lower().endswith(('.xhtml', '.html', '.htm')):
                        continue
                    full_content_path = os.path.dirname(opf_path)
                    if full_content_path:
                        full_content_path = full_content_path + '/' + content_path
                    else:
                        full_content_path = content_path
                    if full_content_path not in namelist:
                        continue
                    with z.open(full_content_path) as content_file:
                        try:
                            content_tree = etree.parse(content_file)
                            content_root = content_tree.getroot()
                            nsmap = content_root.nsmap
                            html_ns = nsmap.get(None, 'http://www.w3.org/1999/xhtml')
                            headings = content_root.xpath('.//h:h1 | .//h:h2 | .//h:h3 | .//h:h4 | .//h:h5 | .//h:h6', namespaces={'h': html_ns})
                            heading_count += len(headings)
                        except etree.XMLSyntaxError:
                            continue
        return heading_count
    except Exception:
        return -1

def main(folder_path):
    folder = Path(folder_path).resolve()
    if not folder.is_dir():
        print(f"Folder not found: {folder}")
        sys.exit(1)
    print(f"Scanning EPUB files in: {folder}")
    print("Files with 2 or fewer headings (h1–h6):")
    found = False
    for file_path in sorted(folder.glob('**/*.epub')):
        count = count_headings_in_epub(file_path)
        if count >= 0 and count <= 2:
            print(os.path.basename(file_path))
            found = True
    if not found:
        print("No EPUB files with 2 or fewer headings found.")

if __name__ == '__main__':
    folder_path = input('Folder: ')
    main(folder_path)

