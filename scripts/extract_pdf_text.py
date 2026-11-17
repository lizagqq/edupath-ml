"""Minimal local PDF text extractor for the two supplied PDFs (no external packages)."""
import re, zlib, sys
from pathlib import Path

def extract(path):
    blob=Path(path).read_bytes()
    objs={int(m.group(1)):m.group(2) for m in re.finditer(rb'(\d+)\s+\d+\s+obj\b(.*?)endobj',blob,re.S)}
    def stream(body):
        m=re.search(rb'stream\r?\n',body)
        if not m:return b''
        raw=body[m.end():body.find(b'endstream',m.end())].rstrip(b'\r\n')
        try:return zlib.decompress(raw)
        except:return raw
    # Expand compressed object streams used by the laboratory PDF.
    for body in list(objs.values()):
        if b'/Type/ObjStm' not in body: continue
        n=re.search(rb'/N\s*(\d+)',body);first=re.search(rb'/First\s*(\d+)',body)
        if not n or not first: continue
        d=stream(body); count=int(n.group(1)); start=int(first.group(1))
        pairs=[(int(a),int(b)) for a,b in re.findall(rb'(\d+)\s+(\d+)',d[:start])[:count]]
        for j,(oid,offset) in enumerate(pairs):
            end=start+(pairs[j+1][1] if j+1<len(pairs) else len(d)-start)
            objs[oid]=d[start+offset:end]
    maps={}
    for oid,body in objs.items():
        if b'begincmap' not in stream(body):continue
        cm=stream(body); mp={}
        for a,b in re.findall(rb'<([0-9A-F]+)>\s*<([0-9A-F]+)>',cm):
            try:mp[bytes.fromhex(a.decode())]=bytes.fromhex(b.decode()).decode('utf-16-be')
            except:pass
        for a,b,c in re.findall(rb'<([0-9A-F]+)>\s*<([0-9A-F]+)>\s*<([0-9A-F]+)>',cm):
            n=int(b,16)-int(a,16)
            if n<500:
                for i in range(n+1):
                    try:mp[(int(a,16)+i).to_bytes(len(a)//2,'big')]=(int(c,16)+i).to_bytes(len(c)//2,'big').decode('utf-16-be')
                    except:pass
        maps[oid]=mp
    fonts={}
    for oid,body in objs.items():
        m=re.search(rb'/ToUnicode\s+(\d+)\s+\d+\s+R',body)
        if m:fonts[oid]=maps.get(int(m.group(1)),{})
    named={}
    for body in objs.values():
        for name,num in re.findall(rb'/(F\d+)\s+(\d+)\s+\d+\s+R',body):
            named[name.decode()]=fonts.get(int(num),{})
    out=[]
    for body in objs.values():
        d=stream(body)
        if b'BT' not in d:continue
        for block in re.findall(rb'BT(.*?)ET',d,re.S):
            fm=re.search(rb'/(F\d+)\s+[\d.]+\s+Tf',block)
            mp=named.get(fm.group(1).decode(),{}) if fm else {}
            size=len(next(iter(mp),b'\x00\x00'))
            parts=[]
            for h in re.findall(rb'<([0-9A-F]+)>',block):
                raw=bytes.fromhex(h.decode());parts.append(''.join(mp.get(raw[i:i+size],'') for i in range(0,len(raw),size)))
            if parts:out.append(''.join(parts))
    return '\n'.join(out)
if __name__=='__main__':
    for p in sys.argv[1:]:
        dest=Path('/tmp')/(Path(p).stem+'.txt');txt=extract(p);dest.write_text(txt);print(p,len(txt),'characters ->',dest)
