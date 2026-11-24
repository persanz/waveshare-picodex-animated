import ast
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

class LifecycleTests(unittest.TestCase):
    def test_description_releases_player_and_restores_playback_position(self):
        source=ast.parse((Path(__file__).resolve().parents[1]/'frame_app.py').read_text())
        start=next(n for n in source.body if isinstance(n,ast.FunctionDef) and n.name=='start')
        helpers=[n for n in start.body if isinstance(n,ast.FunctionDef) and n.name in ('pause_animation','resume_animation')]
        factory=ast.parse('''
def factory(lcd, initial):
 animation=initial
 animation_resume=None
 def state(): return animation,animation_resume
 return pause_animation,resume_animation,state
''')
        factory.body[0].body[2:2]=helpers
        ns={};exec(compile(ast.fix_missing_locations(factory),'<lifecycle>','exec'),ns)
        class File:
            def __init__(self):self.position=12345
            def tell(self):return self.position
            def seek(self,pos):self.position=pos
        class Player:
            def __init__(self,lcd,index):
                self.index=index;self.frame=0;self.file=File();self.first=True;self.closed=False
            def close(self):self.closed=True
        initial=Player(None,99);initial.frame=7
        pause,resume,state=ns['factory'](None,initial)
        module=types.SimpleNamespace(Player=Player)
        with patch.dict(sys.modules,{'pokemon_animation':module}):
            pause()
            self.assertTrue(initial.closed)
            self.assertNotIn('pokemon_animation',sys.modules)
            self.assertEqual(state(),(None,(99,7,12345)))
            sys.modules['pokemon_animation']=module
            resume()
            active,pending=state()
            self.assertIsNot(active,initial)
            self.assertEqual((active.index,active.frame,active.file.tell()),(99,7,12345))
            self.assertFalse(active.first)
            self.assertIsNone(pending)
