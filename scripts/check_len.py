import os, glob
for f in glob.glob('data/knowledge_base/*.txt'):
    content = open(f, encoding='utf-8').read()
    print(f"{f}: {len(content)} chars, {os.path.getsize(f)} bytes")
