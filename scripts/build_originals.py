#!/usr/bin/env python3
"""Package original KOI8-R source entries alongside the existing YAML shards."""
import gzip,json,sys,unicodedata,re
from collections import defaultdict
from pathlib import Path

out=Path('dist/data')
def norm(s):
 return unicodedata.normalize('NFC',''.join(c for c in unicodedata.normalize('NFD',s.lower().replace('ё','е')) if c not in '\u0300\u0301'))
def exact(s):return unicodedata.normalize('NFC',''.join(c for c in unicodedata.normalize('NFD',s.lower()) if c not in '\u0300\u0301'))
def source_key(line):
 parts=line.split()
 word=list(parts[0].lower())
 if len(parts)>1 and re.fullmatch(r'[0-9.,]+',parts[1]):
  positions=parts[1].split(',')[1:]
  for item in positions:
   if item.isdigit() and 0<int(item)<=len(word) and word[int(item)-1]=='е':word[int(item)-1]='ё'
 return exact(''.join(word))
def shard(s):return '-'.join(f'{ord(c):x}' for c in norm(s)[:2]) or '5f'
source=defaultdict(list)
with open(sys.argv[1],encoding='koi8-r') as f:
 for line in f:
  line=line.rstrip('\r\n')
  if line and not line.startswith('#'):
   source[source_key(line)].append(line)
related={'две':'два','обе':'оба','полторы':'полтора','пфефер':'фефер'}
count=0
for path in out.glob('d-*.bin'):
 with gzip.open(path,'rt',encoding='utf8') as f:entries=json.load(f)
 result={}
 for lemma in entries:
  direct=source.get(exact(lemma))
  if direct:result[lemma]={'entries':direct}
  elif lemma in related and source.get(exact(related[lemma])):
   result[lemma]={'entries':source[exact(related[lemma])],'related':related[lemma]}
  else:continue
  count+=1
 with gzip.open(out/('o-'+path.name[2:]),'wt',encoding='utf8',compresslevel=9) as f:json.dump(result,f,ensure_ascii=False,separators=(',',':'))
print(f'Original entries found for {count} of {sum(1 for p in out.glob("d-*.bin") for _ in json.load(gzip.open(p,"rt",encoding="utf8")))} lemmas')
