import importlib
import io
import sys
import types
import zlib
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch


class LCD:
    def __init__(self):
        self.buffer = bytearray(b'\x12\x34')*57600
        self.shows = 0
    def fill_rect(self,x,y,w,h,color):
        for row in range(y,y+h):
            pos=(row*240+x)*2
            self.buffer[pos:pos+w*2]=bytes(w*2)
    def show(self): self.shows += 1


class AnimationTests(unittest.TestCase):
    def setUp(self):
        stub = types.SimpleNamespace(RAW=0, DeflateIO=lambda f,*a: io.BytesIO(zlib.decompress(f.read(),-9)))
        self.modules = patch.dict(sys.modules, {'deflate': stub})
        self.modules.start();self.addCleanup(self.modules.stop)
        self.module=importlib.import_module('pokemon_animation')
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'pack-00.bin'
        frames = []
        for delay, raw in ((100,b'\xf8\x00'*3+b'\x00\x1f'*3),(200,b'\x07\xe0'*3+b'\xff\xff'*3)):
            compressor=zlib.compressobj(9,zlib.DEFLATED,-9)
            packed=compressor.compress(raw)+compressor.flush()
            frames.append(struct.pack('<HH',delay,len(packed))+packed)
        self.body=struct.pack('<4sHHH',b'PKA3',6,1,2)+b''.join(frames)
        self.path.write_bytes(struct.pack('<4sHII',b'PAX1',1,14,len(self.body))+self.body)
        self.clock=patch.multiple(self.module.time,ticks_ms=lambda:0,
            ticks_diff=lambda a,b:a-b,ticks_add=lambda a,b:a+b,create=True)
        self.clock.start();self.addCleanup(self.clock.stop)

    def test_rgb_scaling_timing_loop_and_footer(self):
        lcd=LCD();footer=bytes(lcd.buffer[216*480:])
        p=self.module.Player(lcd,0,self.temp.name);self.addCleanup(p.close)
        self.assertEqual(len(p.row),12)
        self.assertTrue(p.step(0))
        for y in range(p.y,p.y+3):
            pos=(y*240+p.x)*2
            self.assertEqual(lcd.buffer[pos:pos+12],b'\xf8\x00'*3+b'\x00\x1f'*3)
        self.assertEqual(lcd.buffer[216*480:],footer)
        self.assertFalse(p.step(99))
        self.assertTrue(p.step(100))
        self.assertEqual(p.frame,0)
        self.assertFalse(p.step(299))
        self.assertTrue(p.step(300))
        self.assertEqual(lcd.shows,3)

    def test_invalid_or_truncated_pack_rejected_before_render(self):
        lcd=LCD()
        for data in (b'bad',struct.pack('<4sHII',b'PAX1',1,1,50),
                     struct.pack('<4sHII',b'PAX1',1,14,99999)+self.body):
            self.path.write_bytes(data)
            with self.assertRaises((ValueError,struct.error)):
                self.module.Player(lcd,0,self.temp.name)
            self.assertEqual(lcd.shows,0)

    def test_pack_boundary_and_artwork_index(self):
        second=Path(self.temp.name)/'pack-01.bin'
        second.write_bytes(self.path.read_bytes())
        p=self.module.Player(LCD(),128,self.temp.name);self.addCleanup(p.close)
        self.assertTrue(p.step(0))
        with self.assertRaises(ValueError):
            self.module.Player(LCD(),129,self.temp.name)

    def test_frame_cannot_escape_its_pack_entry(self):
        body=bytearray(self.body)
        struct.pack_into('<H',body,12,65535)
        self.path.write_bytes(struct.pack('<4sHII',b'PAX1',1,14,len(body))+body)
        p=self.module.Player(LCD(),0,self.temp.name);self.addCleanup(p.close)
        with self.assertRaises(ValueError):p.step(0)
