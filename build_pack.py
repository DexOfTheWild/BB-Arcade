"""Build a deterministic data/art-only BB-Arcade release; Python standard library."""
import argparse,hashlib,json,math,re,zipfile
from pathlib import Path,PurePosixPath

def identifier(s):
    return isinstance(s,str) and re.fullmatch(r'[a-z0-9][a-z0-9._-]{0,62}',s) and '..' not in s and not s.endswith('.')

def safe_asset(s):
    if not isinstance(s,str) or len(s)>220 or not re.fullmatch(r'assets/[a-z0-9_./-]+',s):return False
    p=PurePosixPath(s)
    if str(p)!=s or any(x in ('','.','..') or x.endswith('.') for x in p.parts):return False
    for x in p.parts:
        stem=x.split('.')[0]
        if stem in {'con','prn','aux','nul'} or re.fullmatch(r'(com|lpt)[0-9]',stem):return False
    return p.suffix in {'.obj','.mtl','.png'}

def validate_catalog(p):
    if not isinstance(p,dict) or type(p.get('format')) is not int or p.get('format')!=1 or p.get('id')!='bb-arcade' or not identifier(p.get('version')):
        raise ValueError('Unsupported cabinet catalog')
    cabinets=p.get('cabinets')
    if not isinstance(cabinets,list) or not 1<=len(cabinets)<=128:raise ValueError('Invalid cabinet count')
    ids=set();furniture=set();content=set()
    for c in cabinets:
        if not isinstance(c,dict) or not identifier(c.get('id')) or c['id'] in ids:raise ValueError('Invalid/duplicate cabinet id')
        ids.add(c['id'])
        name=c.get('name','')
        if not isinstance(name,str) or not 1<=len(name)<=64 or not name.isascii() or '|' in name or any(ord(x)<32 or ord(x)>126 for x in name):raise ValueError('Invalid name')
        if c.get('status') not in ('integrated','authoring') or c.get('backend')!='fbneo':raise ValueError('Invalid status/backend')
        if c.get('footprint')!=[1,1] or c.get('world_units_per_metre')!=40 or c.get('screen_aspect') not in ([4,3],[3,4]) or type(c['world_units_per_metre']) is not int or any(type(x) is not int for x in c['footprint']+c['screen_aspect']):raise ValueError('Invalid physical contract')
        rom=c.get('rom','')
        if not isinstance(rom,str) or not re.fullmatch(r'[a-z0-9_]+\.(zip|7z)',rom):raise ValueError('Invalid informational ROM shortname')
        for key,ext in (('model','.obj'),('material','.mtl'),('body','.obj'),('screen','.obj')):
            if key not in c:
                if key in ('model','material') or c['status']=='integrated':raise ValueError('Missing '+key)
                continue
            if not safe_asset(c[key]) or not c[key].startswith('assets/'+c['id']+'/') or not c[key].endswith(ext):raise ValueError('Invalid asset reference')
        if c['status']=='integrated':
            if c.get('adapter')!=c['id'] or type(c.get('furniture_id')) is not int or not 1<=c['furniture_id']<65536 or type(c.get('content_id')) is not int or not 0<=c['content_id']<1024:raise ValueError('Invalid native identities')
            if c['furniture_id'] in furniture or c['content_id'] in content:raise ValueError('Duplicate native identity')
            furniture.add(c['furniture_id']);content.add(c['content_id'])
        elif any(k in c for k in ('adapter','furniture_id','content_id')):raise ValueError('Authoring cabinet cannot claim runtime identity')

def validate_asset(name,data,files):
    if name.endswith('.png'):
        if len(data)<33 or data[:8]!=b'\x89PNG\r\n\x1a\n' or data[12:16]!=b'IHDR':raise ValueError('Invalid PNG')
        if any(not 4<=int.from_bytes(data[i:i+4],'big')<=4096 for i in (16,20)):raise ValueError('Invalid PNG dimensions')
        return
    lines=data.decode('ascii').splitlines()
    for line in lines:
        f=line.split()
        if not f or f[0].startswith('#'):continue
        if f[0]=='mtllib' or f[0].startswith('map_'):
            ext='.mtl' if f[0]=='mtllib' else '.png'
            if len(f)!=2 or (f[0]!='mtllib' and f[0]!='map_Kd') or '/' in f[1] or '\\' in f[1] or not f[1].endswith(ext):raise ValueError('Non-adjacent material/texture reference')
            if str(PurePosixPath(name).parent/f[1]) not in files:raise ValueError('Unlisted asset dependency')
        if f[0] in ('v','vn','vt','Kd','Ka','Ke','Ks','Ns','d'):
            if not all(math.isfinite(float(x)) for x in f[1:]):raise ValueError('Non-finite art value')

def build(root,out):
    root=Path(root).resolve();out=Path(out)
    p=json.loads((root/'catalog.json').read_text(encoding='utf-8'));validate_catalog(p)
    files={}
    for path in sorted((root/'assets').rglob('*')):
        if path.is_symlink() or not path.resolve().is_relative_to(root):raise ValueError('Linked asset')
        if path.is_dir():continue
        name=path.relative_to(root).as_posix()
        if not safe_asset(name):raise ValueError('Unexpected file (art only): '+name)
        data=path.read_bytes()
        if not 0<len(data)<=16*1024*1024:raise ValueError('Invalid file size')
        files[name]=data
    if not files or len(files)>1024 or sum(map(len,files.values()))>128*1024*1024:raise ValueError('Pack limits exceeded')
    for c in p['cabinets']:
        for key in ('model','material','body','screen'):
            if key in c and c[key] not in files:raise ValueError('Missing '+key)
    for name,data in files.items():validate_asset(name,data,files)
    p['files']=[{'path':name,'size':len(data),'sha256':hashlib.sha256(data).hexdigest()} for name,data in files.items()]
    out.mkdir(parents=True,exist_ok=True);archive=out/'BB-Arcade.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,data in {'pack.json':(json.dumps(p,indent=2)+'\n').encode(),**files}.items():
            info=zipfile.ZipInfo(name,date_time=(2026,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644<<16;z.writestr(info,data)
    data=archive.read_bytes()
    descriptor={'format':1,'repository':'DexOfTheWild/BB-Arcade','tag':'v'+p['version'],
                'asset':archive.name,'size':len(data),'sha256':hashlib.sha256(data).hexdigest()}
    (out/'BB-Arcade.json').write_text(json.dumps(descriptor,indent=2)+'\n',encoding='utf-8')
    print(f'Built {len(p["cabinets"])} cabinet records, {len(files)} art files, {len(data)} bytes; no ROMs/BIOS.')
    return p

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,default=Path(__file__).resolve().parent/'dist')
    build(Path(__file__).resolve().parent,parser.parse_args().out)
