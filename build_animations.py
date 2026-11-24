"""Build animations for every artwork, with explicit generated-motion fallbacks.
Host dependencies: Pillow, numpy. Sources are a pinned PokeAPI sparse checkout.
"""
from pathlib import Path
import argparse, concurrent.futures, hashlib, io, json, math, struct, subprocess, zlib
import numpy as np
from PIL import Image
ROOT = Path(__file__).resolve().parent
SOURCE_COMMIT = 'c0542f7c51215d9672439012838c99f520596cbd'
PACK_ENTRIES = 128
MAX_FRAMES = 64


def rgb565(image):
    a = np.asarray(image, dtype=np.uint16)
    return (((a[:,:,0]>>3)<<11)|((a[:,:,1]>>2)<<5)|(a[:,:,2]>>3)).astype('>u2').tobytes()


def encode(frames, durations):
    w,h=frames[0].size
    out=io.BytesIO();out.write(struct.pack('<4sHHH',b'PKA3',w*3,h,len(frames)))
    for frame,delay in zip(frames,durations):
        rgba=frame.convert('RGBA')
        rgb=Image.new('RGB',rgba.size,'black');rgb.paste(rgba,mask=rgba.getchannel('A'))
        raw=rgb565(rgb.resize((w*3,h),Image.Resampling.NEAREST))
        c=zlib.compressobj(6,zlib.DEFLATED,-9);packed=c.compress(raw)+c.flush()
        if len(packed)>65535:raise ValueError('Compressed frame too large')
        out.write(struct.pack('<HH',max(60,min(2000,delay)),len(packed)));out.write(packed)
    return out.getvalue()


def source_frames(path):
    with Image.open(path) as gif:
        n=gif.n_frames
        if n<2:raise ValueError('Source GIF is static')
        stride=math.ceil(n/MAX_FRAMES)
        w,h=gif.size;ratio=min(1,64/w,64/h);size=(max(1,int(w*ratio)),max(1,int(h*ratio)))
        frames=[];delays=[]
        for i in range(n):
            gif.seek(i)
            if i%stride==0:
                frames.append(gif.convert('RGBA').resize(size,Image.Resampling.NEAREST));delays.append(0)
            delays[-1]+=gif.info.get('duration',100) or 100
        return frames,delays,n


def artwork_motion(record):
    with (ROOT/'pokemon_hd.dat').open('rb') as f:
        f.seek(record['offset']);raw=zlib.decompress(f.read(record['size']),-10)
    v=np.frombuffer(raw,dtype='>u2').reshape(240,240).astype(np.uint32)
    rgb=np.stack((((v>>11)&31)*255//31,((v>>5)&63)*255//63,(v&31)*255//31),axis=2).astype('uint8')
    image=Image.fromarray(rgb);box=image.getbbox()
    if box:image=image.crop(box)
    image.thumbnail((60,58),Image.Resampling.LANCZOS)
    frames=[]
    for dy in (0,-1,-2,-1,0,1):
        canvas=Image.new('RGB',(64,64),'black')
        canvas.paste(image,((64-image.width)//2,(64-image.height)//2+dy));frames.append(canvas)
    return frames,[180]*6


def convert(record, source, cache):
    gif=source/record['source_path'] if record['source_path'] else None
    key=hashlib.sha256((record.get('source_sha','')+'|'+str(record['index'])+'|pka3-64-frames64-v1').encode()).hexdigest()
    path=cache/(key+'.pka');meta=cache/(key+'.json')
    if path.exists() and meta.exists():return record|json.loads(meta.read_text())|{'cache':str(path)}
    mode='sprite';reason=None;original_frames=0
    try:
        if gif is None:raise FileNotFoundError('No matching source animation')
        frames,delays,original_frames=source_frames(gif)
    except (OSError,ValueError) as e:
        mode='artwork_motion';reason=str(e);frames,delays=artwork_motion(record)
    data=encode(frames,delays);path.write_bytes(data)
    info={'mode':mode,'reason':reason,'frames':len(frames),'original_frames':original_frames,
          'width':frames[0].width*3,'height':frames[0].height*3,'bytes':len(data),
          'sha256':hashlib.sha256(data).hexdigest()}
    meta.write_text(json.dumps(info))
    return record|info|{'cache':str(path)}


def build(workers=4):
    upstream=ROOT/'.cache/animations/upstream'
    commit=subprocess.check_output(['git','-C',str(upstream),'rev-parse','HEAD'],text=True).strip()
    if commit!=SOURCE_COMMIT:raise ValueError('Source checkout must be pinned to '+SOURCE_COMMIT)
    tree_file=ROOT/'.cache/animations/showdown-tree.json'
    if not tree_file.exists():
        tree_sha=subprocess.check_output(['git','-C',str(upstream),'rev-parse','HEAD:sprites/pokemon/other/showdown'],text=True).strip()
        listing=subprocess.check_output(['git','-C',str(upstream),'ls-tree','-r','-l','HEAD:sprites/pokemon/other/showdown'],text=True)
        entries=[]
        for line in listing.splitlines():
            mode,kind,sha,size,path=line.split(None,4)
            entries.append({'path':path,'type':kind,'sha':sha,'size':int(size)})
        tree_file.write_text(json.dumps({'sha':tree_sha,'truncated':False,'tree':entries}))
    tree=json.loads(tree_file.read_text())
    if tree.get('truncated'):raise ValueError('Incomplete upstream tree')
    expected_tree=subprocess.check_output(['git','-C',str(upstream),'rev-parse','HEAD:sprites/pokemon/other/showdown'],text=True).strip()
    if tree['sha']!=expected_tree:raise ValueError('Source tree does not match the pinned checkout')
    files={e['path']:e for e in tree['tree'] if e['type']=='blob'}
    source=ROOT/'.cache/animations/upstream/sprites/pokemon/other/showdown'
    cache=ROOT/'.cache/animations/converted';cache.mkdir(parents=True,exist_ok=True)
    rows=sorted(json.loads((ROOT/'pokemon_descriptions_es.json').read_text())['pokemon'],
                key=lambda r:(int(r['id'].split('-')[0]),r['id']))
    with (ROOT/'pokemon_hd.dat').open('rb') as f:
        count,=struct.unpack('<I',f.read(4));art=[struct.unpack('<IIII',f.read(16)) for _ in range(count)]
        assert count==len(rows)==1538
        records=[]
        for i,(row,entry) in enumerate(zip(rows,art)):
            number,offset,size,name_offset=entry;assert number==int(row['id'].split('-')[0])
            f.seek(name_offset);name=f.read(100).split(b'\0')[0].decode();assert name==row['label']
            key=row['id']+'.gif'
            if key not in files and row['id'].endswith('-female'):key='female/'+row['id'][:-7]+'.gif'
            exists=key in files
            records.append({'index':i,'id':row['id'],'name':name,'art_id':number,'offset':offset,'size':size,
                            'source_path':key if exists else None,'source_sha':files[key]['sha'] if exists else ''})
    results=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for i,result in enumerate(pool.map(lambda r:convert(r,source,cache),records),1):
            results.append(result)
            if i%50==0:print('Converted',i,'/',count,flush=True)
    out=ROOT/'assets/animations';out.mkdir(parents=True,exist_ok=True)
    packs=[]
    for start in range(0,count,PACK_ENTRIES):
        group=results[start:start+PACK_ENTRIES];path=out/('pack-%02d.bin'%(start//PACK_ENTRIES))
        with path.open('wb') as f:
            f.write(struct.pack('<4sH',b'PAX1',len(group)));f.write(bytes(len(group)*8));table=[]
            for r in group:
                data=Path(r['cache']).read_bytes();table.append((f.tell(),len(data)));f.write(data)
            f.seek(6)
            for offset,size in table:f.write(struct.pack('<II',offset,size))
        packs.append({'file':path.name,'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    entries=[{k:v for k,v in r.items() if k not in ('cache','offset','size')} for r in results]
    manifest={'source_repository':'PokeAPI/sprites','source_commit':SOURCE_COMMIT,'source_tree':tree['sha'],
              'pack_entries':PACK_ENTRIES,'count':count,'sprite_count':sum(r['mode']=='sprite' for r in results),
              'artwork_motion_count':sum(r['mode']=='artwork_motion' for r in results),'packs':packs,'entries':entries}
    (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print('COMPLETE',manifest['sprite_count'],'sprite animations,',manifest['artwork_motion_count'],
          'generated artwork motions;',sum(p['bytes'] for p in packs),'bytes',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--workers',type=int,default=4)
    build(parser.parse_args().workers)
