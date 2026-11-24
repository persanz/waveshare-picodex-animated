"""Validate every packed frame and ensure every entry actually moves."""
from pathlib import Path
import hashlib,json,struct,zlib
ROOT=Path(__file__).resolve().parent

def main():
    manifest=json.loads((ROOT/'assets/animations/manifest.json').read_text())
    assert manifest['count']==1538
    motionless=[];frames=0;used=set()
    for pack in manifest['packs']:
        data=(ROOT/'assets/animations'/pack['file']).read_bytes()
        assert len(data)==pack['bytes'] and hashlib.sha256(data).hexdigest()==pack['sha256']
        magic,count=struct.unpack_from('<4sH',data);assert magic==b'PAX1'
        pack_index=int(pack['file'][5:7])
        for slot in range(count):
            index=pack_index*128+slot;entry=manifest['entries'][index];assert entry['index']==index
            offset,size=struct.unpack_from('<II',data,6+slot*8)
            assert offset>=6+count*8 and offset+size<=len(data)
            body=data[offset:offset+size];assert hashlib.sha256(body).hexdigest()==entry['sha256']
            tag,w,h,n=struct.unpack_from('<4sHHH',body)
            assert tag==b'PKA3' and 1<=w<=192 and 1<=h<=64 and 2<=n<=256
            pos=10;distinct=set()
            for _ in range(n):
                delay,compressed=struct.unpack_from('<HH',body,pos);pos+=4
                assert 60<=delay<=2000 and compressed and pos+compressed<=len(body)
                frame=zlib.decompress(body[pos:pos+compressed],-9);pos+=compressed
                assert len(frame)==w*h*2
                distinct.add(hashlib.sha256(frame).digest());frames+=1
            assert pos==len(body)
            if len(distinct)<2:motionless.append(index)
            used.add(index)
    assert len(used)==1538
    print('Validated',len(used),'animations,',frames,'frames; motionless entries:',motionless)
    assert not motionless, 'Every entry must visibly animate'

if __name__=='__main__':main()
