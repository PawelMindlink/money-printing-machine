import xml.etree.ElementTree as ET

tree = ET.parse('Input/Iiyama/iiyama_product_feed.xml')
root = tree.getroot()
ns = {'g': 'http://base.google.com/ns/1.0'}

count = 0
found_items = []
for item in root.findall('.//item'):
    count += 1
    title = item.findtext('g:title', namespaces=ns) or item.findtext('title') or ""
    brand = item.findtext('g:brand', namespaces=ns) or ""
    ptype = item.findtext('g:product_type', namespaces=ns) or ""
    
    if "filtr" in title.lower() or "foli" in title.lower() or "3mk" in brand.lower() or "filtr" in ptype.lower():
        found_items.append({'title': title, 'brand': brand, 'type': ptype})

print(f"Total items in XML: {count}")
print(f"Items matching 'filtr'/'foli'/'3mk': {len(found_items)}")
for i in found_items[:5]:
    print(f" - {i['title'][:50]}... | Brand: {i['brand']} | Type: {i['type'][:50]}")
