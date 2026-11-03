#!/usr/bin/env python3
import gzip,json,os,re,sqlite3,sys,unicodedata,yaml,collections
from pathlib import Path

out=Path('dist/data'); out.mkdir(parents=True,exist_ok=True)
def norm(s): return unicodedata.normalize('NFC', ''.join(c for c in unicodedata.normalize('NFD',str(s).lower().replace('ё','е')) if c not in '\u0300\u0301'))
def shard(s): return '-'.join(f'{ord(c):x}' for c in (norm(s)[:2] or '_'))
def flatten(obj):
 if isinstance(obj,dict): yield obj
 elif isinstance(obj,list):
  for v in obj: yield from flatten(v)
def split_alts(s): return re.split(r',(?=(?:[^\[\]]*\[[^\[\]]*\])*[^\[\]]*$)(?=(?:[^()]*\([^()]*\))*[^()]*$)',s)
def expand(e):
 if 'п' not in e: return []
 forms=[]
 for cell in str(e['п']).split(';'):
  for part in split_alts(cell):
   if part == '-' or part.endswith('-'): continue
   part=re.sub(r'[\(\[].*','',part).rstrip('*?')
   m=re.match(r'^([1-5])',part)
   stem=e.get('о'+m.group(1),'') if m else e.get('о','')
   if m: part=part[1:]
   f=str(stem or '')+part
   if f: forms.append(f)
 return forms

db=sqlite3.connect('/tmp/morph-zaliz-index.sqlite'); db.execute('PRAGMA journal_mode=OFF');db.execute('PRAGMA synchronous=OFF');db.execute('CREATE TABLE IF NOT EXISTS pairs (sh TEXT, form TEXT, lemma TEXT, PRIMARY KEY(sh,form,lemma)) WITHOUT ROWID');db.execute('DELETE FROM pairs')
entries=collections.defaultdict(dict); n=0
for filename in sys.argv[1:]:
 with open(filename,encoding='utf8') as f:
  buf=[]
  def emit(buf):
   global n
   if not buf:return
   try: data=yaml.load(''.join(buf),Loader=yaml.CSafeLoader)
   except Exception as exc: raise RuntimeError(f'{filename}: {buf[0]} {exc}')
   if not isinstance(data,dict):return
   for lemma,obj in data.items():
    lemma=str(lemma); entries[shard(lemma)][lemma]=obj
    allforms={norm(lemma)}
    for entry in flatten(obj):
     allforms.update(norm(x) for x in expand(entry))
    db.executemany('INSERT OR IGNORE INTO pairs VALUES (?,?,?)',((shard(form),form,lemma) for form in allforms if form))
    n+=1
  for line in f:
   if line and not line[0].isspace() and not line.startswith(('-', '#')):
    emit(buf);buf=[line]
   elif buf:buf.append(line)
  emit(buf)
 db.commit(); print(filename,n,flush=True)
def write(path,obj):
 with gzip.open(path,'wt',encoding='utf8',compresslevel=9) as f:json.dump(obj,f,ensure_ascii=False,separators=(',',':'))
for k,v in entries.items():write(out/f'd-{k}.bin',v)
print('dictionary shards',len(entries),flush=True)
cur=db.execute('SELECT sh,form,lemma FROM pairs ORDER BY sh,form,lemma'); current=None; block={}
for sh,form,lemma in cur:
 if sh!=current:
  if current is not None:write(out/f'i-{current}.bin',block)
  current=sh;block={}
 block.setdefault(form,[]).append(lemma)
if current is not None:write(out/f'i-{current}.bin',block)
print('completed',n,flush=True)
