"""Exercise the actual driver method with delayed-token and timeout SPI mocks."""
import ast
from pathlib import Path
import types
import unittest

class ReadTests(unittest.TestCase):
    def reader(self,tokens,clock_step):
        source=ast.parse((Path(__file__).resolve().parents[1]/'sdcard.py').read_text())
        cls=next(n for n in source.body if isinstance(n,ast.ClassDef))
        method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='readinto')
        now=[0];polls=[0];states=[]
        class SPI:
            def readinto(self,buf,fill):
                buf[0]=0xfe if polls[0]>=tokens else 0xff
                polls[0]+=1;now[0]+=clock_step
            def write_readinto(self,source,target):target[:]=bytes([42])*len(target)
            def write(self,data):pass
        namespace={'time':types.SimpleNamespace(ticks_ms=lambda:now[0],ticks_diff=lambda a,b:a-b),'_TOKEN_DATA':0xfe,'_CMD_TIMEOUT':100}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[method],type_ignores=[])),'<sdcard-read>','exec'),namespace)
        obj=types.SimpleNamespace(spi=SPI(),tokenbuf=bytearray(1),dummybuf_memoryview=memoryview(bytearray(512)),cs=states.append)
        return lambda b:namespace['readinto'](obj,b),polls,states

    def test_many_fast_filler_bytes_do_not_cause_false_timeout(self):
        read,polls,states=self.reader(300,0)
        buf=bytearray(512);read(buf)
        self.assertEqual(polls[0],301)
        self.assertEqual(buf,bytes([42])*512)
        self.assertEqual(states[-1],1)

    def test_missing_token_still_has_bounded_timeout(self):
        read,polls,states=self.reader(1000,1)
        with self.assertRaises(OSError):read(bytearray(512))
        self.assertEqual(polls[0],100)
        self.assertEqual(states[-1],1)
