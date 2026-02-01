import os
import json

root = 'C:/Users/derri/.openclaw/media/inbound'

print('=== Folder Structure ===')
for item in os.listdir(root):
    path = os.path.join(root, item)
    if os.path.isfile(path):
        size = os.path.getsize(path)
        print(f'  [FILE] {item} ({size:,} bytes)')
    else:
        print(f'  [DIR] {item}')

print('\n=== Index Contents ===')
with open(os.path.join(root, 'financial_data_index.json'), 'r') as f:
    idx = json.load(f)
    for src in idx['sources']:
        print(f"Excel: {os.path.basename(src['excel'])}")
        print(f"  -> CSV: {os.path.basename(src['csv'])}")
        print(f"  -> Subfolder: {src['subfolder']}")
        print(f"  -> Rows: {src['rows']}")
