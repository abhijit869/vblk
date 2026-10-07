import os
import re

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    orig = content
    # Replace Debian 13 (Bookworm) with Debian 12 (Bookworm)
    content = re.sub(r'Debian 13 \(Bookworm\)', 'Debian 12 (Bookworm)', content)
    content = re.sub(r'Debian 13 Bookworm', 'Debian 12 Bookworm', content)
    
    # Replace Qwen2.5 with Qwen3 unless it's marked as invalid
    # Wait, simple regex is risky. I'll just let the check-doc-consistency script find them and I'll manually replace if needed.
    
    # Replace "2048 layers" with "2048-token context"
    content = re.sub(r'2048 layers', '2048-token context', content)

    if content != orig:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {filepath}")

for root, dirs, files in os.walk('.'):
    if '.git' in root or 'node_modules' in root or 'downloads' in root:
        continue
    for file in files:
        if file.endswith('.md'):
            process_file(os.path.join(root, file))
