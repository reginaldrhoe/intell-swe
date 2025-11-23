import os
import sys
import json

print('PYTHON_OK')
try:
    from openai import OpenAI
    print('OPENAI_PACKAGE_OK')
except Exception as e:
    print('OPENAI_PACKAGE_IMPORT_ERROR', str(e))
    sys.exit(2)

try:
    client = OpenAI()
    print('OPENAI_CLIENT_INSTANTIATED')
except Exception as e:
    print('OPENAI_CLIENT_INSTANTIATE_ERROR', str(e))
    # continue to try embedding to see exact error

try:
    q = 'test embedding ping'
    resp = client.embeddings.create(model='text-embedding-3-small', input=q)
    vec = resp.data[0].embedding
    print('EMBED_OK', len(vec))
except Exception as e:
    print('EMBED_ERROR', str(e))
    # try to dump env vars that matter
    print('OPENAI_API_KEY_PRESENT', bool(os.getenv('OPENAI_API_KEY')))
    sys.exit(3)
