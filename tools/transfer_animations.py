"""Stream verified animation packs over USB serial to an SD card.

Run only with the board in watchdog-free maintenance mode, after backing up
main.py. Source/firmware activation is separate: an interrupted transfer must
not replace a working firmware. Requires pyserial on the host.
"""
from pathlib import Path
import argparse,base64,json,time
import serial
ROOT=Path(__file__).resolve().parents[1]
RECEIVER='''import sys,os,ubinascii,hashlib,micropython
from machine import Pin,SPI
import sdcard
Pin(28,Pin.OUT,value=1)
spi=SPI(0,baudrate=1000000,sck=Pin(18),mosi=Pin(19),miso=Pin(20))
card=sdcard.SDCard(spi,Pin(23,Pin.OUT),baudrate=5000000)
os.mount(card,'/sd')
try:os.mkdir('/sd/picodex_animations')
except OSError:pass
micropython.kbd_intr(-1)
print('ANIM_READY')
try:
 while True:
  line=sys.stdin.readline().strip()
  if line=='QUIT':break
  name,length,expected=line.split();length=int(length)
  if '/' in name or not name.startswith('pack-') or not name.endswith('.bin'):raise ValueError('Invalid pack name')
  path='/sd/picodex_animations/'+name
  # Never overwrite a previously installed pack without preserving a backup.
  try:
   good=os.stat(path)[6]==length
  except OSError:good=False
  if good:
   digest=hashlib.sha256()
   with open(path,'rb') as f:
    while True:
     block=f.read(4096)
     if not block:break
     digest.update(block)
   good=ubinascii.hexlify(digest.digest()).decode()==expected
  if good:
   print('SKIP',name);continue
  print('SEND',name)
  received=0;digest=hashlib.sha256()
  with open(path+'.stage','wb') as f:
   while received<length:
    line=sys.stdin.readline()
    if line.strip()=='ABORT':raise ValueError('Transfer aborted')
    block=ubinascii.a2b_base64(line)
    if received+len(block)>length:raise ValueError('Oversized transfer')
    f.write(block);digest.update(block);received+=len(block)
    print('ACK',received)
  os.sync()
  if ubinascii.hexlify(digest.digest()).decode()!=expected:raise ValueError('Checksum mismatch')
  try:os.stat(path)
  except OSError:pass
  else:
   backup=path+'.previous'
   try:os.stat(backup)
   except OSError:os.rename(path,backup)
   else:raise ValueError('Prior pack backup exists; preserve it before retry')
  os.rename(path+'.stage',path);os.sync();print('DONE',name)
 print('ANIM_FINISHED')
except Exception as e:print('ANIM_ERROR',repr(e))
finally:
 micropython.kbd_intr(3)
 os.umount('/sd')
'''


def receive(port,needle,timeout=30):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        line=port.readline().decode(errors='replace').strip()
        if line.startswith('ANIM_ERROR'):raise RuntimeError(line)
        if needle in line:return line
    raise TimeoutError('No response: '+needle)


def transfer(port_name,only=None):
    manifest=json.loads((ROOT/'assets/animations/manifest.json').read_text())
    packs=[p for p in manifest['packs'] if only is None or p['file']==only]
    total=sum(p['bytes'] for p in packs);done=0;start=time.monotonic()
    with serial.Serial(port_name,115200,timeout=1,write_timeout=30) as port:
        port.write(b'\r\x03\x03');time.sleep(.1);port.write(b'\r\x01');time.sleep(.1);port.reset_input_buffer()
        code=RECEIVER.encode()
        for i in range(0,len(code),128):port.write(code[i:i+128]);time.sleep(.005)
        port.write(b'\x04');receive(port,'ANIM_READY')
        for pack in packs:
            name=pack['file'];data=ROOT/'assets/animations'/name
            print('Sending',name,pack['bytes'],'bytes',flush=True)
            port.write(('%s %d %s\n'%(name,pack['bytes'],pack['sha256'])).encode())
            response=receive(port,name)
            if response.startswith('SKIP'):
                done+=pack['bytes'];print('Verified existing',name,flush=True);continue
            if not response.startswith('SEND'):raise RuntimeError(response)
            count=0
            with data.open('rb') as f:
                while True:
                    block=f.read(12288)
                    if not block:break
                    port.write(base64.b64encode(block)+b'\n');count+=len(block)
                    response=receive(port,'ACK')
                    if response!='ACK '+str(count):raise RuntimeError('Incorrect acknowledgement: '+response)
            receive(port,'DONE '+name)
            done+=pack['bytes'];elapsed=time.monotonic()-start
            print('Verified',name,'total',round(done/1048576,1),'/',round(total/1048576,1),'MiB;',round(done/elapsed/1024),'KiB/s',flush=True)
        port.write(b'QUIT\n');receive(port,'ANIM_FINISHED');print('All requested packs verified',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',required=True);parser.add_argument('--only')
    args=parser.parse_args();transfer(args.port,args.only)
