import os,hashlib,sys
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest

def iter_files(root):
    for dirpath,_,filenames in os.walk(root):
        for fn in filenames:
            if fn.endswith(('.py','.md','.rst','.txt')):
                yield os.path.join(dirpath,fn)

def load_text(path):
    try:
        with open(path,'r',encoding='utf-8',errors='ignore') as f:
            return f.read()
    except Exception:
        return ''

def chunk_text(text,size=1000,overlap=200):
    i=0
    while i < len(text):
        yield text[i:i+size]
        i+= size-overlap

def embed_text(text,dim=64):
    h=hashlib.sha256(text.encode('utf-8')).digest()
    reps=(dim+len(h)-1)//len(h)
    data=(h*reps)[:dim]
    return [ (b/255.0)*2.0-1.0 for b in data]

if __name__=='__main__':
    repo='/tmp/fastapi'
    collection='fastapi-repo'
    qurl=os.environ.get('QDRANT_URL','http://qdrant:6333')
    print('Repo:',repo,'collection:',collection,'qdrant:',qurl)
    client=QdrantClient(url=qurl)
    try:
        client.recreate_collection(collection_name=collection, vectors_config=rest.VectorParams(size=64, distance=rest.Distance.COSINE))
    except Exception as e:
        print('Collection create error (ignored):',e)
    points=[]
    ctr=0
    for fp in iter_files(repo):
        txt=load_text(fp)
        if not txt.strip():
            continue
        for chunk in chunk_text(txt):
            emb=embed_text(chunk)
            payload={'path': os.path.relpath(fp,repo),'text': chunk[:1000]}
            points.append(rest.PointStruct(id=ctr, vector=emb, payload=payload))
            ctr+=1
            if len(points)>=256:
                client.upsert(collection_name=collection, points=points)
                print('Upserted',len(points),'points...')
                points=[]
    if points:
        client.upsert(collection_name=collection, points=points)
        print('Upserted',len(points),'points (final)')
    print('Done. Inserted',ctr,'chunks.')
